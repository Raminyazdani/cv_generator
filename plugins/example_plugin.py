"""
Example Plugin for CV Generator.

This is a sample plugin that demonstrates how to:
1. Register a custom section
2. Register hook callbacks
3. Interact with the CV generation pipeline

To use this plugin, ensure it's in one of the plugin directories:
- <repository>/plugins/
- ~/.cv_generator/plugins/
"""

import logging

logger = logging.getLogger(__name__)


def register(registry, hook_manager):
    """
    Register plugin components.

    This function is called when the plugin is loaded.

    Args:
        registry: The SectionRegistry instance.
        hook_manager: The HookManager instance.
    """
    logger.info("Example plugin registered")

    # Example: Register a hook that logs when validation starts
    from cv_generator.hooks import HookContext

    def log_pre_validate(context: HookContext) -> None:
        """Log when CV validation begins."""
        logger.debug(f"Validating CV: {context.cv_name} ({context.lang})")

    hook_manager.register(
        "pre_validate",
        log_pre_validate,
        name="example_log_validate",
        plugin_name="example",
        priority=50,  # Run early
    )

    # Example: Register a hook that logs after rendering
    def log_post_render(context: HookContext) -> None:
        """Log rendering statistics."""
        section_count = len(context.rendered_sections)
        logger.debug(f"Rendered {section_count} sections for {context.cv_name}")

    hook_manager.register(
        "post_render",
        log_post_render,
        name="example_log_render",
        plugin_name="example",
    )


def unregister():
    """
    Clean up plugin resources.

    This function is called when the plugin is unloaded.
    """
    logger.info("Example plugin unregistered")
