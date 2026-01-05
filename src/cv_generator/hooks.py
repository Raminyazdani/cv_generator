"""
Plugin Hook System for CV Generator.

Provides a hook mechanism that allows plugins to extend the CV generation pipeline
without modifying core generator logic.

Supported hooks:
- pre_validate: Called before CV data validation
- post_render: Called after sections are rendered
- pre_compile: Called before LaTeX compilation
- post_export: Called after PDF export

Each hook receives context information and can modify the data or abort processing.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class HookType(Enum):
    """Available hook types in the CV generation pipeline."""

    PRE_VALIDATE = "pre_validate"
    POST_RENDER = "post_render"
    PRE_COMPILE = "pre_compile"
    POST_EXPORT = "post_export"


@dataclass
class HookContext:
    """
    Context passed to hook callbacks.

    Contains information about the current CV being processed
    and allows hooks to modify data or signal errors.
    """

    # CV identification
    cv_name: str = ""
    lang: str = "en"

    # Data at various stages
    data: Dict[str, Any] = field(default_factory=dict)
    rendered_sections: Dict[str, str] = field(default_factory=dict)

    # File paths (may be None depending on hook type)
    tex_path: Optional[Path] = None
    pdf_path: Optional[Path] = None

    # Error collection
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Control flags
    abort: bool = False
    abort_reason: str = ""

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def signal_abort(self, reason: str) -> None:
        """Signal that processing should be aborted."""
        self.abort = True
        self.abort_reason = reason


# Hook callback type
HookCallback = Callable[[HookContext], None]


@dataclass
class RegisteredHook:
    """Information about a registered hook callback."""

    callback: HookCallback
    name: str
    priority: int = 100
    plugin_name: str = "unknown"
    abort_on_error: bool = False


class HookManager:
    """
    Manager for plugin hooks.

    Handles registration and execution of hook callbacks at various
    points in the CV generation pipeline.
    """

    def __init__(self):
        """Initialize an empty hook manager."""
        self._hooks: Dict[HookType, List[RegisteredHook]] = {
            hook_type: [] for hook_type in HookType
        }

    def register(
        self,
        hook_type: Union[HookType, str],
        callback: HookCallback,
        *,
        name: Optional[str] = None,
        priority: int = 100,
        plugin_name: str = "unknown",
        abort_on_error: bool = False,
    ) -> None:
        """
        Register a hook callback.

        Args:
            hook_type: The type of hook to register for.
            callback: The callback function to execute.
            name: Optional name for this hook registration.
            priority: Execution priority (lower = earlier). Default is 100.
            plugin_name: Name of the plugin registering this hook.
            abort_on_error: If True, abort build if this hook fails.

        Raises:
            ValueError: If hook_type is invalid.
        """
        # Convert string to enum if needed
        if isinstance(hook_type, str):
            try:
                hook_type = HookType(hook_type)
            except ValueError:
                valid_types = [h.value for h in HookType]
                raise ValueError(
                    f"Invalid hook type '{hook_type}'. Valid types: {valid_types}"
                )

        hook_name = name or callback.__name__
        registered = RegisteredHook(
            callback=callback,
            name=hook_name,
            priority=priority,
            plugin_name=plugin_name,
            abort_on_error=abort_on_error,
        )

        self._hooks[hook_type].append(registered)
        # Sort by priority
        self._hooks[hook_type].sort(key=lambda h: h.priority)

        logger.debug(
            f"Registered hook '{hook_name}' for {hook_type.value} "
            f"(plugin: {plugin_name}, priority: {priority}, abort_on_error: {abort_on_error})"
        )

    def unregister(
        self,
        hook_type: Union[HookType, str],
        name: Optional[str] = None,
        plugin_name: Optional[str] = None,
    ) -> int:
        """
        Unregister hook callbacks.

        Args:
            hook_type: The type of hook to unregister from.
            name: If provided, only unregister hooks with this name.
            plugin_name: If provided, only unregister hooks from this plugin.

        Returns:
            Number of hooks unregistered.
        """
        if isinstance(hook_type, str):
            hook_type = HookType(hook_type)

        hooks = self._hooks[hook_type]
        original_count = len(hooks)

        def should_keep(h: RegisteredHook) -> bool:
            if name and h.name != name:
                return True
            if plugin_name and h.plugin_name != plugin_name:
                return True
            return False

        self._hooks[hook_type] = [h for h in hooks if should_keep(h)]
        removed = original_count - len(self._hooks[hook_type])

        if removed > 0:
            logger.debug(f"Unregistered {removed} hooks from {hook_type.value}")

        return removed

    def execute(
        self,
        hook_type: Union[HookType, str],
        context: HookContext,
    ) -> HookContext:
        """
        Execute all registered callbacks for a hook type.

        Args:
            hook_type: The type of hook to execute.
            context: The context to pass to callbacks.

        Returns:
            The context after all callbacks have executed.
        """
        if isinstance(hook_type, str):
            hook_type = HookType(hook_type)

        hooks = self._hooks[hook_type]

        if not hooks:
            return context

        logger.debug(f"Executing {len(hooks)} hooks for {hook_type.value}")

        for registered in hooks:
            if context.abort:
                logger.warning(
                    f"Hook execution aborted before '{registered.name}': "
                    f"{context.abort_reason}"
                )
                break

            try:
                registered.callback(context)
            except Exception as e:
                error_msg = (
                    f"Hook '{registered.name}' (plugin: {registered.plugin_name}) "
                    f"raised an error: {e}"
                )
                # Log at WARNING level so users always see it, not just in debug mode
                logger.warning(error_msg)
                context.add_error(error_msg)

                # Log detailed error for debugging
                logger.debug("Hook error details:", exc_info=True)

                # If abort_on_error is set, abort the build
                if registered.abort_on_error:
                    context.signal_abort(
                        f"Plugin '{registered.plugin_name}' failed with abort_on_error=True: {e}"
                    )
                    logger.error(
                        f"Aborting build due to plugin error in '{registered.name}'"
                    )
                    break

        # Log summary of plugin errors if any occurred
        if context.errors:
            logger.warning(
                f"Plugin execution completed with {len(context.errors)} error(s). "
                "Errors may affect build output."
            )

        return context

    def list_hooks(
        self, hook_type: Optional[Union[HookType, str]] = None
    ) -> Dict[str, List[str]]:
        """
        List registered hooks.

        Args:
            hook_type: If provided, only list hooks for this type.

        Returns:
            Dictionary mapping hook types to lists of hook names.
        """
        if hook_type is not None:
            if isinstance(hook_type, str):
                hook_type = HookType(hook_type)
            return {
                hook_type.value: [h.name for h in self._hooks[hook_type]]
            }

        return {
            ht.value: [h.name for h in hooks]
            for ht, hooks in self._hooks.items()
        }

    def clear(self, hook_type: Optional[Union[HookType, str]] = None) -> None:
        """
        Clear registered hooks.

        Args:
            hook_type: If provided, only clear hooks for this type.
                      Otherwise, clear all hooks.
        """
        if hook_type is not None:
            if isinstance(hook_type, str):
                hook_type = HookType(hook_type)
            self._hooks[hook_type].clear()
            logger.debug(f"Cleared all hooks for {hook_type.value}")
        else:
            for ht in HookType:
                self._hooks[ht].clear()
            logger.debug("Cleared all hooks")

    def __len__(self) -> int:
        """Get total number of registered hooks."""
        return sum(len(hooks) for hooks in self._hooks.values())


# Default hook manager instance
_default_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """
    Get the default hook manager.

    Returns:
        The default HookManager instance.
    """
    global _default_hook_manager
    if _default_hook_manager is None:
        _default_hook_manager = HookManager()
    return _default_hook_manager


def reset_hook_manager() -> None:
    """Reset the default hook manager."""
    global _default_hook_manager
    _default_hook_manager = None


def register_hook(
    hook_type: Union[HookType, str],
    callback: HookCallback,
    *,
    name: Optional[str] = None,
    priority: int = 100,
    plugin_name: str = "unknown",
    abort_on_error: bool = False,
) -> None:
    """
    Convenience function to register a hook in the default manager.

    Args:
        hook_type: The type of hook to register for.
        callback: The callback function to execute.
        name: Optional name for this hook registration.
        priority: Execution priority (lower = earlier).
        plugin_name: Name of the plugin registering this hook.
        abort_on_error: If True, abort build if this hook fails.
    """
    get_hook_manager().register(
        hook_type,
        callback,
        name=name,
        priority=priority,
        plugin_name=plugin_name,
        abort_on_error=abort_on_error,
    )


def hook(
    hook_type: Union[HookType, str],
    *,
    name: Optional[str] = None,
    priority: int = 100,
    plugin_name: str = "unknown",
    abort_on_error: bool = False,
) -> Callable[[HookCallback], HookCallback]:
    """
    Decorator for registering hook callbacks.

    Example:
        @hook("pre_validate", plugin_name="my_plugin")
        def my_validator(context: HookContext) -> None:
            if not context.data.get("required_field"):
                context.add_error("Missing required field")

        @hook("pre_compile", plugin_name="critical_plugin", abort_on_error=True)
        def critical_check(context: HookContext) -> None:
            # This hook will abort the build if it raises an exception
            pass

    Args:
        hook_type: The type of hook to register for.
        name: Optional name for this hook.
        priority: Execution priority (lower = earlier).
        plugin_name: Name of the plugin.
        abort_on_error: If True, abort build if this hook fails.

    Returns:
        Decorator function.
    """
    def decorator(callback: HookCallback) -> HookCallback:
        register_hook(
            hook_type,
            callback,
            name=name or callback.__name__,
            priority=priority,
            plugin_name=plugin_name,
            abort_on_error=abort_on_error,
        )
        return callback

    return decorator
