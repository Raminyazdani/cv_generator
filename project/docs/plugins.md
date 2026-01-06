# Plugin Development Guide

CV Generator supports a plugin system that allows you to extend the CV generation
pipeline without modifying core code. This guide explains how to create and use plugins.

## Overview

Plugins can:

1. **Register custom section adapters** - Add new CV sections or customize existing ones
2. **Register hook callbacks** - Intercept and modify the CV generation process at key points
3. **Extend functionality** - Add custom validation, post-processing, or export features

## Plugin Location

Plugins are loaded from two directories:

1. **Repository plugins**: `<repository>/plugins/` - For project-specific plugins
2. **User plugins**: `~/.cv_generator/plugins/` - For personal plugins

## Creating a Plugin

A plugin is a Python module (`.py` file) that defines a `register` function:

```python
"""
My Custom Plugin for CV Generator.
"""

def register(registry, hook_manager):
    """
    Register plugin components.

    Args:
        registry: The SectionRegistry instance for registering sections.
        hook_manager: The HookManager instance for registering hooks.
    """
    # Your plugin code here
    pass
```

### Optional: Cleanup Function

If your plugin needs to clean up resources when unloaded:

```python
def unregister():
    """Clean up plugin resources."""
    # Cleanup code here
    pass
```

## Registering Custom Sections

### Using GenericSectionAdapter

For simple sections that use a template:

```python
from cv_generator.registry import GenericSectionAdapter

def register(registry, hook_manager):
    adapter = GenericSectionAdapter(
        name="awards",           # Unique section name
        template="awards.tex",   # Template filename
        data_key="awards",       # Key in CV JSON data
        required=False,          # Whether section is required
    )
    registry.register(adapter)
```

### With Custom Validation

```python
from cv_generator.registry import GenericSectionAdapter

def validate_awards(data):
    """Validate awards section."""
    errors = []
    awards = data.get("awards", [])
    for i, award in enumerate(awards):
        if "title" not in award:
            errors.append(f"Award {i+1} missing title")
    return errors

def register(registry, hook_manager):
    adapter = GenericSectionAdapter(
        name="awards",
        template="awards.tex",
        data_key="awards",
        validator=validate_awards,
    )
    registry.register(adapter)
```

### With Priority Ordering

Control where your section appears in the order:

```python
def register(registry, hook_manager):
    adapter = GenericSectionAdapter(
        name="summary",
        template="summary.tex",
    )
    # Priority 0 = first, higher numbers = later
    registry.register(adapter, priority=1)
```

## Registering Hooks

Hooks allow you to intercept the CV generation pipeline at key points.

### Available Hooks

| Hook Type | When Called | Use Cases |
|-----------|-------------|-----------|
| `pre_validate` | Before CV data validation | Add custom validation, modify data |
| `post_render` | After sections are rendered | Modify rendered content |
| `pre_compile` | Before LaTeX compilation | Modify LaTeX, add files |
| `post_export` | After PDF export | Post-processing, notifications |

### Hook Context

Each hook receives a `HookContext` object with:

```python
from cv_generator.hooks import HookContext

# Available properties:
context.cv_name          # CV profile name
context.lang             # Language code (e.g., "en")
context.data             # CV data dictionary
context.rendered_sections  # Dict of rendered section content
context.tex_path         # Path to .tex file (if available)
context.pdf_path         # Path to .pdf file (if available)
context.errors           # List of error messages
context.warnings         # List of warning messages
context.abort            # Whether to abort processing
context.abort_reason     # Reason for abort

# Methods:
context.add_error("Error message")
context.add_warning("Warning message")
context.signal_abort("Reason to stop")
```

### Basic Hook Example

```python
from cv_generator.hooks import HookContext

def register(registry, hook_manager):
    def validate_email(context: HookContext) -> None:
        """Ensure email is provided."""
        basics = context.data.get("basics", [{}])
        if basics and not basics[0].get("email"):
            context.add_warning("No email address provided")

    hook_manager.register(
        "pre_validate",
        validate_email,
        name="validate_email",
        plugin_name="my_plugin",
        priority=50,  # Lower = runs earlier
    )
```

### Hook Priority

Hooks execute in priority order (lower numbers first):

```python
hook_manager.register("pre_validate", early_hook, priority=10)
hook_manager.register("pre_validate", normal_hook, priority=100)  # default
hook_manager.register("pre_validate", late_hook, priority=200)
```

### Aborting Processing

To stop the CV generation:

```python
def critical_check(context: HookContext) -> None:
    if not context.data.get("basics"):
        context.signal_abort("CV missing required basics section")
```

### Error Handling

Hook errors are captured and logged but don't crash the pipeline:

```python
def risky_hook(context: HookContext) -> None:
    try:
        # risky operation
        pass
    except Exception as e:
        context.add_error(f"Plugin error: {e}")
```

## Complete Example Plugin

Here's a complete example plugin that adds a "hobbies" section:

```python
"""
Hobbies Plugin for CV Generator.

Adds a "hobbies" section to CVs and validates the data.
"""

from cv_generator.hooks import HookContext
from cv_generator.registry import GenericSectionAdapter


def register(registry, hook_manager):
    """Register the hobbies section and hooks."""

    # Register the section
    def validate_hobbies(data):
        errors = []
        hobbies = data.get("hobbies", [])
        if hobbies and not isinstance(hobbies, list):
            errors.append("Hobbies must be a list")
        return errors

    adapter = GenericSectionAdapter(
        name="hobbies",
        template="hobbies.tex",
        data_key="hobbies",
        required=False,
        validator=validate_hobbies,
    )
    registry.register(adapter)

    # Register a logging hook
    def log_hobbies_count(context: HookContext) -> None:
        hobbies = context.data.get("hobbies", [])
        if hobbies:
            print(f"Processing CV with {len(hobbies)} hobbies")

    hook_manager.register(
        "pre_validate",
        log_hobbies_count,
        name="log_hobbies",
        plugin_name="hobbies",
    )


def unregister():
    """Clean up plugin resources."""
    print("Hobbies plugin unregistered")
```

## Using the Decorator API

For simpler hook registration:

```python
from cv_generator.hooks import hook, HookContext

@hook("post_render", plugin_name="my_plugin")
def my_post_render(context: HookContext) -> None:
    """Process rendered content."""
    pass
```

## Testing Your Plugin

1. Create your plugin in `plugins/` or `~/.cv_generator/plugins/`
2. Run CV generation with verbose logging:
   ```bash
   cvgen build --verbose
   ```
3. Check for errors in the output

## API Reference

### SectionRegistry

```python
from cv_generator.registry import get_default_registry

registry = get_default_registry()

# List all sections
registry.list()  # Returns: ["header", "education", ...]

# Get a section adapter
adapter = registry.get("education")

# Check if section exists
"education" in registry  # True
```

### HookManager

```python
from cv_generator.hooks import get_hook_manager

hook_manager = get_hook_manager()

# List all registered hooks
hook_manager.list_hooks()

# List hooks for a specific type
hook_manager.list_hooks("pre_validate")

# Clear all hooks (for testing)
hook_manager.clear()
```

### PluginManager

```python
from cv_generator.plugins import get_plugin_manager

plugin_manager = get_plugin_manager()

# List loaded plugins
plugin_manager.list_plugins()

# Get info about a plugin
info = plugin_manager.get_plugin("my_plugin")
print(f"Loaded: {info.loaded}, Path: {info.path}")
```

## Troubleshooting

### Plugin Not Loading

1. Check the file is in the correct directory
2. Ensure the filename doesn't start with `_`
3. Check for syntax errors: `python -m py_compile plugins/my_plugin.py`

### Hook Not Executing

1. Verify the hook type is correct
2. Check the priority isn't too high
3. Enable debug logging to see hook execution

### Section Not Appearing

1. Verify the template file exists
2. Check the data_key matches your CV JSON
3. Ensure no validation errors are blocking rendering
