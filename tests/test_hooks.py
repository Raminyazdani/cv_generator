"""
Tests for cv_generator.hooks module.

Tests the plugin hook system, including:
- Hook registration with abort_on_error
- Hook execution and error handling
- Error visibility improvements (F-014)
"""

import pytest

from cv_generator.hooks import (
    HookContext,
    HookManager,
    HookType,
    RegisteredHook,
    get_hook_manager,
    hook,
    register_hook,
    reset_hook_manager,
)


@pytest.fixture(autouse=True)
def reset_hooks():
    """Reset the hook manager before and after each test."""
    reset_hook_manager()
    yield
    reset_hook_manager()


class TestHookContext:
    """Tests for HookContext dataclass."""

    def test_add_error(self):
        """Test adding an error to context."""
        context = HookContext()
        context.add_error("Something went wrong")
        assert "Something went wrong" in context.errors

    def test_add_warning(self):
        """Test adding a warning to context."""
        context = HookContext()
        context.add_warning("Something to note")
        assert "Something to note" in context.warnings

    def test_signal_abort(self):
        """Test signaling abort."""
        context = HookContext()
        context.signal_abort("Critical error occurred")
        assert context.abort is True
        assert context.abort_reason == "Critical error occurred"


class TestRegisteredHook:
    """Tests for RegisteredHook dataclass."""

    def test_registered_hook_defaults(self):
        """Test RegisteredHook default values."""
        hook_info = RegisteredHook(
            callback=lambda ctx: None,
            name="test_hook",
        )
        assert hook_info.priority == 100
        assert hook_info.plugin_name == "unknown"
        assert hook_info.abort_on_error is False

    def test_registered_hook_with_abort_on_error(self):
        """Test RegisteredHook with abort_on_error set."""
        hook_info = RegisteredHook(
            callback=lambda ctx: None,
            name="critical_hook",
            abort_on_error=True,
        )
        assert hook_info.abort_on_error is True


class TestHookManager:
    """Tests for HookManager class."""

    def test_register_hook(self):
        """Test registering a hook."""
        manager = HookManager()

        def my_hook(ctx):
            pass

        manager.register(HookType.PRE_VALIDATE, my_hook, name="my_hook")
        hooks = manager.list_hooks(HookType.PRE_VALIDATE)
        assert "my_hook" in hooks[HookType.PRE_VALIDATE.value]

    def test_register_hook_with_string_type(self):
        """Test registering a hook with string type."""
        manager = HookManager()

        def my_hook(ctx):
            pass

        manager.register("pre_validate", my_hook, name="my_hook")
        hooks = manager.list_hooks("pre_validate")
        assert "my_hook" in hooks["pre_validate"]

    def test_register_hook_invalid_type(self):
        """Test registering a hook with invalid type raises ValueError."""
        manager = HookManager()

        with pytest.raises(ValueError, match="Invalid hook type"):
            manager.register("invalid_type", lambda ctx: None)

    def test_register_hook_with_abort_on_error(self):
        """Test registering a hook with abort_on_error."""
        manager = HookManager()

        def critical_hook(ctx):
            pass

        manager.register(
            HookType.PRE_COMPILE,
            critical_hook,
            name="critical_hook",
            abort_on_error=True,
        )

        # Verify the hook was registered with abort_on_error
        hooks = manager._hooks[HookType.PRE_COMPILE]
        assert len(hooks) == 1
        assert hooks[0].abort_on_error is True

    def test_execute_hooks_success(self):
        """Test executing hooks successfully."""
        manager = HookManager()
        called = []

        def hook1(ctx):
            called.append("hook1")

        def hook2(ctx):
            called.append("hook2")

        manager.register(HookType.PRE_VALIDATE, hook1, name="hook1")
        manager.register(HookType.PRE_VALIDATE, hook2, name="hook2")

        context = HookContext()
        result = manager.execute(HookType.PRE_VALIDATE, context)

        assert called == ["hook1", "hook2"]
        assert not result.errors

    def test_execute_hooks_with_error(self):
        """Test that hook errors are captured."""
        manager = HookManager()

        def failing_hook(ctx):
            raise RuntimeError("Hook failed")

        manager.register(HookType.PRE_VALIDATE, failing_hook, name="failing_hook")

        context = HookContext()
        result = manager.execute(HookType.PRE_VALIDATE, context)

        assert len(result.errors) == 1
        assert "failing_hook" in result.errors[0]
        assert "Hook failed" in result.errors[0]

    def test_execute_hooks_abort_on_error(self):
        """Test that abort_on_error stops execution."""
        manager = HookManager()
        called = []

        def critical_hook(ctx):
            called.append("critical")
            raise RuntimeError("Critical failure")

        def next_hook(ctx):
            called.append("next")

        manager.register(
            HookType.PRE_VALIDATE,
            critical_hook,
            name="critical_hook",
            abort_on_error=True,
            priority=10,
        )
        manager.register(
            HookType.PRE_VALIDATE,
            next_hook,
            name="next_hook",
            priority=20,
        )

        context = HookContext()
        result = manager.execute(HookType.PRE_VALIDATE, context)

        # Critical hook was called and failed
        assert "critical" in called
        # Next hook was NOT called due to abort
        assert "next" not in called
        # Context should be aborted
        assert result.abort is True
        assert "Critical failure" in result.abort_reason

    def test_execute_hooks_continues_without_abort_on_error(self):
        """Test that hooks continue if abort_on_error is False."""
        manager = HookManager()
        called = []

        def failing_hook(ctx):
            called.append("failing")
            raise RuntimeError("Non-critical failure")

        def next_hook(ctx):
            called.append("next")

        manager.register(
            HookType.PRE_VALIDATE,
            failing_hook,
            name="failing_hook",
            abort_on_error=False,  # Default
            priority=10,
        )
        manager.register(
            HookType.PRE_VALIDATE,
            next_hook,
            name="next_hook",
            priority=20,
        )

        context = HookContext()
        result = manager.execute(HookType.PRE_VALIDATE, context)

        # Both hooks were called
        assert "failing" in called
        assert "next" in called
        # Context should NOT be aborted
        assert result.abort is False
        # But error was recorded
        assert len(result.errors) == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_register_hook_function(self):
        """Test register_hook convenience function."""

        def my_hook(ctx):
            pass

        register_hook("pre_validate", my_hook, name="my_hook")
        hooks = get_hook_manager().list_hooks("pre_validate")
        assert "my_hook" in hooks["pre_validate"]

    def test_register_hook_with_abort_on_error(self):
        """Test register_hook with abort_on_error."""

        def critical_hook(ctx):
            pass

        register_hook(
            "pre_compile",
            critical_hook,
            name="critical",
            abort_on_error=True,
        )

        hooks = get_hook_manager()._hooks[HookType.PRE_COMPILE]
        assert len(hooks) == 1
        assert hooks[0].abort_on_error is True


class TestHookDecorator:
    """Tests for hook decorator."""

    def test_hook_decorator_basic(self):
        """Test basic hook decorator usage."""

        @hook("pre_validate", name="decorated_hook")
        def decorated_hook(ctx):
            pass

        hooks = get_hook_manager().list_hooks("pre_validate")
        assert "decorated_hook" in hooks["pre_validate"]

    def test_hook_decorator_with_abort_on_error(self):
        """Test hook decorator with abort_on_error."""

        @hook("post_render", name="critical_render", abort_on_error=True)
        def critical_render(ctx):
            pass

        hooks = get_hook_manager()._hooks[HookType.POST_RENDER]
        assert len(hooks) == 1
        assert hooks[0].abort_on_error is True
        assert hooks[0].name == "critical_render"
