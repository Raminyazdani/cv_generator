"""
Tests for the Section Registry and Plugin Hooks system.

Tests cover:
- SectionRegistry registration and lookup
- GenericSectionAdapter functionality
- HookManager registration and execution
- Plugin discovery and loading
"""

import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from cv_generator.hooks import (
    HookContext,
    HookManager,
    HookType,
    get_hook_manager,
    register_hook,
    reset_hook_manager,
)
from cv_generator.plugins import (
    PluginManager,
    discover_and_load_plugins,
    get_plugin_manager,
    reset_plugin_manager,
)
from cv_generator.registry import (
    GenericSectionAdapter,
    SectionRegistry,
    create_default_registry,
    get_default_registry,
    register_section,
    reset_default_registry,
)


class TestGenericSectionAdapter:
    """Tests for GenericSectionAdapter class."""

    def test_adapter_properties(self):
        """Test adapter property accessors."""
        adapter = GenericSectionAdapter(
            name="education",
            template="education.tex",
            data_key="education",
            required=True,
        )

        assert adapter.name == "education"
        assert adapter.template == "education.tex"
        assert adapter.data_key == "education"
        assert adapter.required is True

    def test_adapter_default_data_key(self):
        """Test that data_key defaults to name."""
        adapter = GenericSectionAdapter(
            name="skills",
            template="skills.tex",
        )

        assert adapter.data_key == "skills"
        assert adapter.required is False

    def test_validate_required_missing(self):
        """Test validation when required section is missing."""
        adapter = GenericSectionAdapter(
            name="basics",
            template="header.tex",
            data_key="basics",
            required=True,
        )

        errors = adapter.validate({})
        assert len(errors) == 1
        assert "basics" in errors[0].lower()

    def test_validate_required_present(self):
        """Test validation when required section is present."""
        adapter = GenericSectionAdapter(
            name="basics",
            template="header.tex",
            data_key="basics",
            required=True,
        )

        errors = adapter.validate({"basics": {"name": "Test"}})
        assert len(errors) == 0

    def test_validate_custom_validator(self):
        """Test custom validator function."""
        def custom_validator(data: Dict[str, Any]) -> list:
            if "email" not in data.get("basics", {}):
                return ["Email is required"]
            return []

        adapter = GenericSectionAdapter(
            name="basics",
            template="header.tex",
            validator=custom_validator,
        )

        errors = adapter.validate({"basics": {}})
        assert "Email is required" in errors

    def test_normalize_default(self):
        """Test default normalize returns data unchanged."""
        adapter = GenericSectionAdapter(
            name="test",
            template="test.tex",
        )

        data = {"key": "value"}
        result = adapter.normalize(data)
        assert result == data

    def test_normalize_custom(self):
        """Test custom normalizer function."""
        def normalizer(data: Dict[str, Any]) -> Dict[str, Any]:
            data["normalized"] = True
            return data

        adapter = GenericSectionAdapter(
            name="test",
            template="test.tex",
            normalizer=normalizer,
        )

        data = {"key": "value"}
        result = adapter.normalize(data)
        assert result["normalized"] is True


class TestSectionRegistry:
    """Tests for SectionRegistry class."""

    def test_register_adapter(self):
        """Test registering an adapter."""
        registry = SectionRegistry()
        adapter = GenericSectionAdapter("test", "test.tex")

        registry.register(adapter)

        assert "test" in registry
        assert len(registry) == 1
        assert registry.get("test") == adapter

    def test_register_duplicate_raises(self):
        """Test that registering duplicate adapter raises error."""
        registry = SectionRegistry()
        adapter1 = GenericSectionAdapter("test", "test.tex")
        adapter2 = GenericSectionAdapter("test", "other.tex")

        registry.register(adapter1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(adapter2)

    def test_unregister_adapter(self):
        """Test unregistering an adapter."""
        registry = SectionRegistry()
        adapter = GenericSectionAdapter("test", "test.tex")

        registry.register(adapter)
        result = registry.unregister("test")

        assert result is True
        assert "test" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent adapter."""
        registry = SectionRegistry()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_list_order(self):
        """Test that list maintains registration order."""
        registry = SectionRegistry()
        registry.register(GenericSectionAdapter("first", "first.tex"))
        registry.register(GenericSectionAdapter("second", "second.tex"))
        registry.register(GenericSectionAdapter("third", "third.tex"))

        assert registry.list() == ["first", "second", "third"]

    def test_register_with_priority(self):
        """Test registration with priority ordering."""
        registry = SectionRegistry()
        registry.register(GenericSectionAdapter("third", "third.tex"))
        registry.register(
            GenericSectionAdapter("first", "first.tex"),
            priority=0,
        )
        registry.register(
            GenericSectionAdapter("second", "second.tex"),
            priority=1,
        )

        assert registry.list() == ["first", "second", "third"]

    def test_list_adapters(self):
        """Test listing adapter objects."""
        registry = SectionRegistry()
        adapter1 = GenericSectionAdapter("first", "first.tex")
        adapter2 = GenericSectionAdapter("second", "second.tex")

        registry.register(adapter1)
        registry.register(adapter2)

        adapters = registry.list_adapters()
        assert adapters == [adapter1, adapter2]

    def test_clear(self):
        """Test clearing all adapters."""
        registry = SectionRegistry()
        registry.register(GenericSectionAdapter("test", "test.tex"))
        registry.register(GenericSectionAdapter("other", "other.tex"))

        registry.clear()

        assert len(registry) == 0
        assert registry.list() == []

    def test_iteration(self):
        """Test iterating over registry."""
        registry = SectionRegistry()
        registry.register(GenericSectionAdapter("first", "first.tex"))
        registry.register(GenericSectionAdapter("second", "second.tex"))

        names = list(registry)
        assert names == ["first", "second"]


class TestDefaultRegistry:
    """Tests for default registry functions."""

    def setup_method(self):
        """Reset default registry before each test."""
        reset_default_registry()

    def teardown_method(self):
        """Clean up after tests."""
        reset_default_registry()

    def test_create_default_registry(self):
        """Test creating default registry with built-in sections."""
        registry = create_default_registry()

        # Check that default sections are registered
        assert "header" in registry
        assert "education" in registry
        assert "experience" in registry
        assert "skills" in registry

    def test_get_default_registry_singleton(self):
        """Test that get_default_registry returns same instance."""
        registry1 = get_default_registry()
        registry2 = get_default_registry()

        assert registry1 is registry2

    def test_register_section_convenience(self):
        """Test register_section convenience function."""
        adapter = register_section(
            name="custom",
            template="custom.tex",
            data_key="custom_data",
        )

        registry = get_default_registry()
        assert "custom" in registry
        assert registry.get("custom") == adapter


class TestHookManager:
    """Tests for HookManager class."""

    def test_register_hook(self):
        """Test registering a hook callback."""
        manager = HookManager()

        def callback(context):
            pass

        manager.register(HookType.PRE_VALIDATE, callback, name="test_hook")

        hooks = manager.list_hooks(HookType.PRE_VALIDATE)
        assert "test_hook" in hooks[HookType.PRE_VALIDATE.value]

    def test_register_hook_string_type(self):
        """Test registering hook with string type."""
        manager = HookManager()

        def callback(context):
            pass

        manager.register("pre_validate", callback, name="test_hook")

        assert len(manager) == 1

    def test_register_invalid_hook_type(self):
        """Test registering with invalid hook type raises error."""
        manager = HookManager()

        with pytest.raises(ValueError, match="Invalid hook type"):
            manager.register("invalid_type", lambda ctx: None)

    def test_execute_hooks(self):
        """Test executing registered hooks."""
        manager = HookManager()
        called = []

        def hook1(context):
            called.append("hook1")

        def hook2(context):
            called.append("hook2")

        manager.register(HookType.PRE_VALIDATE, hook1, priority=1)
        manager.register(HookType.PRE_VALIDATE, hook2, priority=2)

        context = HookContext(cv_name="test")
        manager.execute(HookType.PRE_VALIDATE, context)

        assert called == ["hook1", "hook2"]

    def test_execute_hooks_priority_order(self):
        """Test hooks execute in priority order."""
        manager = HookManager()
        order = []

        def high_priority(ctx):
            order.append("high")

        def low_priority(ctx):
            order.append("low")

        manager.register(HookType.POST_RENDER, low_priority, priority=100)
        manager.register(HookType.POST_RENDER, high_priority, priority=10)

        manager.execute(HookType.POST_RENDER, HookContext())

        assert order == ["high", "low"]

    def test_hook_context_abort(self):
        """Test that aborted context stops execution."""
        manager = HookManager()
        called = []

        def hook1(context):
            called.append("hook1")
            context.signal_abort("Test abort")

        def hook2(context):
            called.append("hook2")

        manager.register(HookType.PRE_COMPILE, hook1, priority=1)
        manager.register(HookType.PRE_COMPILE, hook2, priority=2)

        context = HookContext()
        manager.execute(HookType.PRE_COMPILE, context)

        assert called == ["hook1"]
        assert context.abort is True
        assert context.abort_reason == "Test abort"

    def test_hook_error_handling(self):
        """Test that hook errors are captured without crashing."""
        manager = HookManager()

        def failing_hook(context):
            raise ValueError("Test error")

        manager.register(HookType.POST_EXPORT, failing_hook, name="failing")

        context = HookContext()
        manager.execute(HookType.POST_EXPORT, context)

        # Error should be captured in context
        assert len(context.errors) == 1
        assert "Test error" in context.errors[0]

    def test_unregister_hook(self):
        """Test unregistering hooks."""
        manager = HookManager()

        def callback(ctx):
            pass

        manager.register(HookType.PRE_VALIDATE, callback, name="test")
        removed = manager.unregister(HookType.PRE_VALIDATE, name="test")

        assert removed == 1
        assert len(manager) == 0

    def test_clear_hooks(self):
        """Test clearing all hooks."""
        manager = HookManager()
        manager.register(HookType.PRE_VALIDATE, lambda ctx: None)
        manager.register(HookType.POST_RENDER, lambda ctx: None)

        manager.clear()

        assert len(manager) == 0


class TestHookContext:
    """Tests for HookContext class."""

    def test_context_defaults(self):
        """Test default context values."""
        context = HookContext()

        assert context.cv_name == ""
        assert context.lang == "en"
        assert context.data == {}
        assert context.errors == []
        assert context.abort is False

    def test_add_error(self):
        """Test adding errors to context."""
        context = HookContext()
        context.add_error("Test error")

        assert "Test error" in context.errors

    def test_add_warning(self):
        """Test adding warnings to context."""
        context = HookContext()
        context.add_warning("Test warning")

        assert "Test warning" in context.warnings

    def test_signal_abort(self):
        """Test signaling abort."""
        context = HookContext()
        context.signal_abort("Abort reason")

        assert context.abort is True
        assert context.abort_reason == "Abort reason"


class TestDefaultHookManager:
    """Tests for default hook manager functions."""

    def setup_method(self):
        """Reset hook manager before each test."""
        reset_hook_manager()

    def teardown_method(self):
        """Clean up after tests."""
        reset_hook_manager()

    def test_get_hook_manager_singleton(self):
        """Test that get_hook_manager returns same instance."""
        manager1 = get_hook_manager()
        manager2 = get_hook_manager()

        assert manager1 is manager2

    def test_register_hook_convenience(self):
        """Test register_hook convenience function."""
        def callback(ctx):
            pass

        register_hook("pre_validate", callback, name="test", plugin_name="test_plugin")

        manager = get_hook_manager()
        hooks = manager.list_hooks("pre_validate")
        assert "test" in hooks["pre_validate"]


class TestPluginManager:
    """Tests for PluginManager class."""

    def test_add_plugin_directory(self):
        """Test adding plugin directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager()
            manager.add_plugin_directory(Path(tmpdir))

            assert Path(tmpdir) in manager._plugin_dirs

    def test_discover_plugins(self):
        """Test discovering plugin files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            # Create some plugin files
            (plugin_dir / "plugin1.py").write_text("# Plugin 1")
            (plugin_dir / "plugin2.py").write_text("# Plugin 2")
            (plugin_dir / "_private.py").write_text("# Private")
            (plugin_dir / "__init__.py").write_text("# Init")

            manager = PluginManager()
            manager.add_plugin_directory(plugin_dir)

            discovered = manager.discover_plugins()

            # Should find plugin1 and plugin2, not _private or __init__
            names = [p.stem for p in discovered]
            assert "plugin1" in names
            assert "plugin2" in names
            assert "_private" not in names
            assert "__init__" not in names

    def test_load_plugin(self):
        """Test loading a plugin file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "test_plugin.py"
            plugin_path.write_text("""
def register(registry, hook_manager):
    pass
""")

            manager = PluginManager()
            info = manager.load_plugin(plugin_path)

            assert info.loaded is True
            assert info.name == "test_plugin"
            assert info.error is None

    def test_load_plugin_with_error(self):
        """Test loading a plugin with syntax error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "bad_plugin.py"
            plugin_path.write_text("this is not valid python {{{")

            manager = PluginManager()
            info = manager.load_plugin(plugin_path)

            assert info.loaded is False
            assert info.error is not None

    def test_list_plugins(self):
        """Test listing loaded plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "test_plugin.py"
            plugin_path.write_text("def register(registry, hook_manager): pass")

            manager = PluginManager()
            manager.load_plugin(plugin_path)

            plugins = manager.list_plugins()
            assert len(plugins) == 1
            assert plugins[0].name == "test_plugin"

    def test_unload_plugin(self):
        """Test unloading a plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "test_plugin.py"
            plugin_path.write_text("def register(registry, hook_manager): pass")

            manager = PluginManager()
            manager.load_plugin(plugin_path)

            result = manager.unload_plugin("test_plugin")

            assert result is True
            assert manager.get_plugin("test_plugin") is None


class TestPluginIntegration:
    """Integration tests for plugin system."""

    def setup_method(self):
        """Reset all managers before each test."""
        reset_default_registry()
        reset_hook_manager()
        reset_plugin_manager()

    def teardown_method(self):
        """Clean up after tests."""
        reset_default_registry()
        reset_hook_manager()
        reset_plugin_manager()

    def test_plugin_registers_hook(self):
        """Test that a plugin can register hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "hook_plugin.py"
            plugin_path.write_text("""
def register(registry, hook_manager):
    def my_hook(context):
        context.data["plugin_ran"] = True

    hook_manager.register(
        "pre_validate",
        my_hook,
        name="my_hook",
        plugin_name="hook_plugin",
    )
""")

            manager = PluginManager()
            manager.load_plugin(plugin_path)

            hook_manager = get_hook_manager()
            context = HookContext(data={})
            hook_manager.execute("pre_validate", context)

            assert context.data.get("plugin_ran") is True

    def test_plugin_registers_section(self):
        """Test that a plugin can register sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "section_plugin.py"
            plugin_path.write_text("""
from cv_generator.registry import GenericSectionAdapter

def register(registry, hook_manager):
    adapter = GenericSectionAdapter(
        name="custom_section",
        template="custom.tex",
    )
    registry.register(adapter)
""")

            # Create a fresh registry for this test
            registry = SectionRegistry()

            manager = PluginManager()

            # Patch get_default_registry to return our test registry
            with patch("cv_generator.plugins.get_default_registry", return_value=registry):
                manager.load_plugin(plugin_path)

            assert "custom_section" in registry


class TestHooksInGenerator:
    """Test that hooks fire correctly during CV generation."""

    def setup_method(self):
        """Reset hook manager before each test."""
        reset_hook_manager()

    def teardown_method(self):
        """Clean up after tests."""
        reset_hook_manager()

    def test_hooks_fire_during_generate_cv(self, tmp_path):
        """Test that hooks fire during CV generation."""
        import json
        from cv_generator.generator import generate_cv
        from cv_generator.io import load_lang_map
        from cv_generator.paths import get_default_templates_path

        # Track which hooks were called
        hooks_called = []

        def pre_validate_hook(ctx: HookContext) -> None:
            hooks_called.append("pre_validate")

        def post_render_hook(ctx: HookContext) -> None:
            hooks_called.append("post_render")

        hook_manager = get_hook_manager()
        hook_manager.register("pre_validate", pre_validate_hook, name="test_pre")
        hook_manager.register("post_render", post_render_hook, name="test_post")

        # Create a sample CV with all expected sections
        cv_data = {
            "basics": [{
                "fname": "Test",
                "lname": "User",
                "email": "test@example.com",
                "label": ["Software Engineer"],
                "location": [{
                    "city": "Berlin",
                    "country": "Germany"
                }],
                "phone": {"formatted": "+49 123 456789"}
            }],
            "profiles": [],
            "education": [],
            "experiences": [],
            "skills": {},
            "languages": [],
            "projects": [],
            "publications": [],
            "references": [],
            "workshop_and_certifications": []
        }
        cv_file = tmp_path / "test.json"
        cv_file.write_text(json.dumps(cv_data))

        # Create lang map
        lang_dir = tmp_path / "lang_engine"
        lang_dir.mkdir()
        (lang_dir / "lang.json").write_text(json.dumps({}))

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("cv_generator.paths.get_lang_engine_path", return_value=lang_dir):
            lang_map = load_lang_map(lang_dir)
            result = generate_cv(
                cv_file,
                templates_dir=get_default_templates_path(),
                output_dir=output_dir,
                lang_map=lang_map,
                dry_run=True,
                keep_latex=True,
            )

        # Check result
        assert result.success is True, f"Generation failed: {result.error}"
        assert "pre_validate" in hooks_called
        assert "post_render" in hooks_called

    def test_hook_abort_stops_generation(self, tmp_path):
        """Test that aborting in a hook stops CV generation."""
        import json
        from cv_generator.generator import generate_cv
        from cv_generator.io import load_lang_map
        from cv_generator.paths import get_default_templates_path

        def abort_hook(ctx: HookContext) -> None:
            ctx.signal_abort("Test abort")

        hook_manager = get_hook_manager()
        hook_manager.register("pre_validate", abort_hook, name="abort_test")

        # Create a sample CV
        cv_data = {
            "basics": [{
                "fname": "Test",
                "lname": "User",
                "email": "test@example.com",
            }],
        }
        cv_file = tmp_path / "test.json"
        cv_file.write_text(json.dumps(cv_data))

        # Create lang map
        lang_dir = tmp_path / "lang_engine"
        lang_dir.mkdir()
        (lang_dir / "lang.json").write_text(json.dumps({}))

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch("cv_generator.paths.get_lang_engine_path", return_value=lang_dir):
            lang_map = load_lang_map(lang_dir)
            result = generate_cv(
                cv_file,
                templates_dir=get_default_templates_path(),
                output_dir=output_dir,
                lang_map=lang_map,
                dry_run=True,
            )

        assert result.success is False
        assert "Aborted by plugin" in result.error
        assert "Test abort" in result.error
