"""
Plugin Discovery and Loading for CV Generator.

Provides a simple mechanism for discovering and loading plugins from:
1. A plugins/ directory in the repository
2. User plugins directory (~/.cv_generator/plugins/)

Plugins are Python modules that can:
- Register custom section adapters
- Register hook callbacks
- Extend CV generation functionality
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .hooks import get_hook_manager, register_hook
from .paths import get_repo_root
from .registry import (
    GenericSectionAdapter,
    get_default_registry,
    register_section,
)

logger = logging.getLogger(__name__)

# Prefix for plugin module names in sys.modules
PLUGIN_MODULE_PREFIX = "cv_generator.plugins"


class PluginError(Exception):
    """Exception raised when a plugin fails to load or execute."""

    def __init__(self, plugin_name: str, message: str, cause: Optional[Exception] = None):
        self.plugin_name = plugin_name
        self.message = message
        self.cause = cause
        super().__init__(f"Plugin '{plugin_name}': {message}")


class PluginInfo:
    """Information about a loaded plugin."""

    def __init__(
        self,
        name: str,
        path: Path,
        module: Any = None,
        enabled: bool = True,
        error: Optional[str] = None,
    ):
        self.name = name
        self.path = path
        self.module = module
        self.enabled = enabled
        self.error = error

    @property
    def loaded(self) -> bool:
        """Check if the plugin was loaded successfully."""
        return self.module is not None and self.error is None

    def __repr__(self) -> str:
        status = "loaded" if self.loaded else f"error: {self.error}"
        return f"PluginInfo(name={self.name!r}, status={status})"


class PluginManager:
    """
    Manager for plugin discovery and loading.

    Scans plugin directories for Python modules and loads them,
    allowing plugins to register sections and hooks.
    """

    def __init__(self):
        """Initialize the plugin manager."""
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugin_dirs: List[Path] = []
        self._initialized = False

    def add_plugin_directory(self, path: Path) -> None:
        """
        Add a directory to scan for plugins.

        Args:
            path: Path to the plugins directory.
        """
        if path.is_dir() and path not in self._plugin_dirs:
            self._plugin_dirs.append(path)
            logger.debug(f"Added plugin directory: {path}")

    def discover_plugins(self) -> List[Path]:
        """
        Discover plugin files in all registered directories.

        Returns:
            List of paths to discovered plugin files.
        """
        discovered = []

        # Files to exclude from plugin discovery
        excluded_patterns = {"__init__", "__pycache__", "__main__"}

        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue

            # Look for Python files (excluding private/special files)
            for py_file in plugin_dir.glob("*.py"):
                stem = py_file.stem
                # Skip files starting with underscore or in excluded patterns
                if stem.startswith("_") or stem in excluded_patterns:
                    continue
                # Skip compiled Python files
                if py_file.suffix in (".pyc", ".pyo"):
                    continue
                discovered.append(py_file)

            # Also look for plugin packages (directories with __init__.py)
            for subdir in plugin_dir.iterdir():
                if not subdir.is_dir():
                    continue
                # Skip __pycache__ and other special directories
                if subdir.name.startswith("_") or subdir.name in excluded_patterns:
                    continue
                if (subdir / "__init__.py").exists():
                    discovered.append(subdir / "__init__.py")

        logger.debug(f"Discovered {len(discovered)} plugin files")
        return discovered

    def load_plugin(self, path: Path) -> PluginInfo:
        """
        Load a single plugin from a file path.

        Args:
            path: Path to the plugin file.

        Returns:
            PluginInfo object with load status.
        """
        # Determine plugin name
        if path.name == "__init__.py":
            plugin_name = path.parent.name
        else:
            plugin_name = path.stem

        # Check if already loaded
        if plugin_name in self._plugins:
            return self._plugins[plugin_name]

        logger.info(f"Loading plugin: {plugin_name}")

        try:
            # Create module spec with configurable prefix
            module_name = f"{PLUGIN_MODULE_PREFIX}.{plugin_name}"
            spec = importlib.util.spec_from_file_location(
                module_name,
                path,
            )

            if spec is None or spec.loader is None:
                raise PluginError(plugin_name, f"Cannot load module from {path}")

            # Create and execute module
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module

            try:
                spec.loader.exec_module(module)
            except Exception:
                # Clean up partial load
                if spec.name in sys.modules:
                    del sys.modules[spec.name]
                raise

            # Check for plugin initialization function
            if hasattr(module, "register"):
                # Call plugin's register function with context
                module.register(
                    registry=get_default_registry(),
                    hook_manager=get_hook_manager(),
                )

            plugin_info = PluginInfo(
                name=plugin_name,
                path=path,
                module=module,
                enabled=True,
            )
            logger.info(f"Successfully loaded plugin: {plugin_name}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to load plugin '{plugin_name}': {error_msg}")
            plugin_info = PluginInfo(
                name=plugin_name,
                path=path,
                module=None,
                enabled=False,
                error=error_msg,
            )

        self._plugins[plugin_name] = plugin_info
        return plugin_info

    def load_all(self) -> List[PluginInfo]:
        """
        Discover and load all plugins.

        Returns:
            List of PluginInfo objects for all plugins.
        """
        discovered = self.discover_plugins()

        for path in discovered:
            self.load_plugin(path)

        return list(self._plugins.values())

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """
        Get information about a loaded plugin.

        Args:
            name: Plugin name.

        Returns:
            PluginInfo or None if not found.
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginInfo]:
        """
        List all loaded plugins.

        Returns:
            List of PluginInfo objects.
        """
        return list(self._plugins.values())

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin.

        Note: This removes the plugin from the manager but cannot fully
        unload hooks or sections that were registered.

        Args:
            name: Plugin name.

        Returns:
            True if plugin was unloaded, False if not found.
        """
        if name in self._plugins:
            plugin = self._plugins[name]
            if plugin.module:
                # Remove from sys.modules using the configurable prefix
                module_name = f"{PLUGIN_MODULE_PREFIX}.{name}"
                if module_name in sys.modules:
                    del sys.modules[module_name]

                # Call cleanup if available
                if hasattr(plugin.module, "unregister"):
                    try:
                        plugin.module.unregister()
                    except Exception as e:
                        logger.warning(f"Error during plugin cleanup: {e}")

            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True

        return False

    def clear(self) -> None:
        """Unload all plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)


# Default plugin manager instance
_default_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """
    Get the default plugin manager.

    Returns:
        The default PluginManager instance.
    """
    global _default_plugin_manager
    if _default_plugin_manager is None:
        _default_plugin_manager = PluginManager()
        _setup_default_plugin_dirs(_default_plugin_manager)
    return _default_plugin_manager


def reset_plugin_manager() -> None:
    """Reset the default plugin manager."""
    global _default_plugin_manager
    if _default_plugin_manager:
        _default_plugin_manager.clear()
    _default_plugin_manager = None


def _setup_default_plugin_dirs(manager: PluginManager) -> None:
    """Set up default plugin directories."""
    # Repository plugins directory
    repo_plugins = get_repo_root() / "plugins"
    if repo_plugins.is_dir():
        manager.add_plugin_directory(repo_plugins)

    # User plugins directory
    user_plugins = Path.home() / ".cv_generator" / "plugins"
    if user_plugins.is_dir():
        manager.add_plugin_directory(user_plugins)


def discover_and_load_plugins() -> List[PluginInfo]:
    """
    Convenience function to discover and load all plugins.

    Returns:
        List of loaded plugin information.
    """
    return get_plugin_manager().load_all()


# Plugin API helpers for use in plugin modules


def plugin_register_section(
    name: str,
    template: str,
    data_key: Optional[str] = None,
    required: bool = False,
    priority: Optional[int] = None,
) -> GenericSectionAdapter:
    """
    Helper for plugins to register a new section.

    Args:
        name: Unique section name.
        template: Template filename.
        data_key: Key in CV data (defaults to name).
        required: Whether section is required.
        priority: Optional priority for ordering.

    Returns:
        The created adapter.
    """
    return register_section(
        name=name,
        template=template,
        data_key=data_key,
        required=required,
        priority=priority,
    )


def plugin_register_hook(
    hook_type: str,
    callback: Callable,
    *,
    name: Optional[str] = None,
    priority: int = 100,
    plugin_name: str = "plugin",
) -> None:
    """
    Helper for plugins to register a hook callback.

    Args:
        hook_type: Hook type ('pre_validate', 'post_render', 'pre_compile', 'post_export').
        callback: The callback function.
        name: Optional name for the hook.
        priority: Execution priority (lower = earlier).
        plugin_name: Name of the plugin.
    """
    register_hook(
        hook_type,
        callback,
        name=name,
        priority=priority,
        plugin_name=plugin_name,
    )
