"""
Custom Section Plugin for CV Generator.

This plugin demonstrates how to add a custom "awards" section to CVs.
It shows how to:
1. Create a custom section adapter with validation
2. Register the section with the registry
3. Use hooks to log processing information

To use this plugin:
1. Place in <repository>/plugins/ or ~/.cv_generator/plugins/
2. Create a matching template: templates/awards.tex
3. Add "awards" data to your CV JSON

Example CV JSON structure:
{
    "awards": [
        {
            "title": "Best Paper Award",
            "organization": "IEEE Conference",
            "date": "2025",
            "description": "Awarded for research on machine learning"
        },
        {
            "title": "Dean's List",
            "organization": "University of Technology",
            "date": "2024"
        }
    ]
}

Example template (templates/awards.tex):
<BLOCK> if awards and awards|length > 0 </BLOCK>
\\cvsection{Awards \\& Honors}
\\begin{cventries}
<BLOCK> for award in awards </BLOCK>
  \\cventry
    {<VAR> award.title | latex_escape </VAR>}
    {<VAR> award.organization | latex_escape </VAR>}
    {}
    {<VAR> award.date | latex_escape </VAR>}
    {
<BLOCK> if award.description </BLOCK>
      \\begin{cvitems}
        \\item {<VAR> award.description | latex_escape </VAR>}
      \\end{cvitems}
<BLOCK> endif </BLOCK>
    }
<BLOCK> endfor </BLOCK>
\\end{cventries}
<BLOCK> endif </BLOCK>
"""

import logging
from typing import Any, Dict, List

from cv_generator.hooks import HookContext, HookType
from cv_generator.registry import GenericSectionAdapter

logger = logging.getLogger(__name__)


def validate_awards(data: Dict[str, Any]) -> List[str]:
    """
    Validate awards section data.

    Checks that each award has required fields.

    Args:
        data: The CV data dictionary.

    Returns:
        List of validation error messages.
    """
    errors = []
    awards = data.get("awards", [])

    if not isinstance(awards, list):
        errors.append("Awards must be a list")
        return errors

    for i, award in enumerate(awards):
        if not isinstance(award, dict):
            errors.append(f"Award {i + 1}: must be a dictionary")
            continue

        if "title" not in award:
            errors.append(f"Award {i + 1}: missing required 'title' field")

        if "organization" not in award:
            errors.append(f"Award {i + 1}: missing required 'organization' field")

    return errors


def normalize_awards(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize awards data before rendering.

    - Ensures date field exists (defaults to empty string)
    - Ensures description field exists (defaults to empty string)

    Args:
        data: The CV data dictionary.

    Returns:
        Normalized data dictionary.
    """
    awards = data.get("awards", [])

    for award in awards:
        if isinstance(award, dict):
            # Set defaults for optional fields
            award.setdefault("date", "")
            award.setdefault("description", "")

    return data


def register(registry, hook_manager):
    """
    Register the awards section and hooks.

    This function is called when the plugin is loaded by CV Generator.

    Args:
        registry: The SectionRegistry instance for registering sections.
        hook_manager: The HookManager instance for registering hooks.
    """
    logger.info("Custom Section Plugin: Loading awards section...")

    # Create and register the awards section adapter
    awards_adapter = GenericSectionAdapter(
        name="awards",
        template="awards.tex",
        data_key="awards",
        required=False,  # Awards are optional
        validator=validate_awards,
        normalizer=normalize_awards,
    )

    # Register with a high priority value to place after built-in sections.
    # Priority is position-based: lower values appear earlier in the CV.
    registry.register(awards_adapter, priority=7)

    logger.info("Custom Section Plugin: Registered 'awards' section")

    # Register a hook to log awards count during validation
    def log_awards_count(context: HookContext) -> None:
        """Log the number of awards being processed."""
        awards = context.data.get("awards", [])
        if awards:
            logger.debug(
                f"Processing {len(awards)} award(s) for "
                f"{context.cv_name} ({context.lang})"
            )

    hook_manager.register(
        HookType.PRE_VALIDATE,
        log_awards_count,
        name="awards_count_logger",
        plugin_name="custom_section",
        priority=50,  # Run early in the validation phase
    )

    # Register a hook to verify awards were rendered
    def verify_awards_rendered(context: HookContext) -> None:
        """Verify awards section was rendered if data exists."""
        awards = context.data.get("awards", [])
        rendered = context.rendered_sections

        if awards and "awards_section" not in rendered:
            context.add_warning(
                "Awards data exists but section was not rendered. "
                "Ensure templates/awards.tex exists."
            )

    hook_manager.register(
        HookType.POST_RENDER,
        verify_awards_rendered,
        name="awards_render_verifier",
        plugin_name="custom_section",
        priority=100,
    )


def unregister():
    """
    Clean up plugin resources.

    This function is called when the plugin is unloaded.
    """
    logger.info("Custom Section Plugin: Unloaded")
