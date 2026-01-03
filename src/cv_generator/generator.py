"""
CV Generator orchestration module.

Provides the main functions for:
- Rendering individual CVs from JSON to LaTeX
- Compiling LaTeX to PDF
- Orchestrating the full CV generation pipeline
- Incremental builds with caching
"""

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2.exceptions import TemplateError as JinjaTemplateError

from .cache import (
    BuildCache,
    compute_input_hashes,
    get_cache_dir,
    needs_rebuild,
)
from .cleanup import cleanup_result_dir
from .errors import TemplateError
from .hooks import HookContext, HookType, get_hook_manager
from .io import discover_cv_files, load_cv_json, load_lang_map, parse_cv_filename, validate_cv_data
from .jinja_env import RTL_LANGUAGES, create_jinja_env
from .latex import cleanup_latex_artifacts, compile_latex, rename_pdf
from .paths import (
    ArtifactPaths,
    get_default_cvs_path,
    get_default_output_path,
    get_default_templates_path,
    get_repo_root,
)

logger = logging.getLogger(__name__)


def _execute_hook(
    hook_type: HookType,
    cv_name: str,
    lang: str,
    data: Dict[str, Any],
    rendered_sections: Optional[Dict[str, str]] = None,
    tex_path: Optional[Path] = None,
    pdf_path: Optional[Path] = None,
) -> HookContext:
    """
    Execute a hook with the given context.

    Args:
        hook_type: The type of hook to execute.
        cv_name: Name of the CV being processed.
        lang: Language code.
        data: CV data dictionary.
        rendered_sections: Rendered section content (for post_render, pre_compile).
        tex_path: Path to .tex file (for pre_compile, post_export).
        pdf_path: Path to .pdf file (for post_export).

    Returns:
        HookContext after hook execution.
    """
    context = HookContext(
        cv_name=cv_name,
        lang=lang,
        data=data,
        rendered_sections=rendered_sections or {},
        tex_path=tex_path,
        pdf_path=pdf_path,
    )

    hook_manager = get_hook_manager()
    return hook_manager.execute(hook_type, context)


class CVGenerationResult:
    """Result of generating a single CV."""

    def __init__(
        self,
        name: str,
        lang: str,
        success: bool,
        pdf_path: Optional[Path] = None,
        tex_path: Optional[Path] = None,
        error: Optional[str] = None,
        skipped: bool = False,
    ):
        self.name = name
        self.lang = lang
        self.success = success
        self.pdf_path = pdf_path
        self.tex_path = tex_path
        self.error = error
        self.skipped = skipped

    def __repr__(self) -> str:
        if self.skipped:
            status = "⏭️"
        elif self.success:
            status = "✅"
        else:
            status = "❌"
        return f"CVGenerationResult({status} {self.name}_{self.lang})"


def render_sections(
    env,
    template_dir: Path,
    data: Dict[str, Any],
    output_dir: Path
) -> Dict[str, str]:
    """
    Render all section templates.

    Args:
        env: Jinja2 environment.
        template_dir: Path to templates directory.
        data: CV data dictionary.
        output_dir: Directory to write section .tex files.

    Returns:
        Dictionary mapping section names to rendered content.

    Raises:
        TemplateError: If a template fails to render.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered_sections = {}
    template_files = list(template_dir.glob('*.tex'))

    for tmpl_path in template_files:
        tmpl_file = tmpl_path.name
        try:
            template = env.get_template(tmpl_file)
            rendered = template.render(data)
        except JinjaTemplateError as e:
            raise TemplateError(f"[Jinja error in {tmpl_file}] {e}") from e

        # Write section file
        section_name = tmpl_path.stem
        output_path = output_dir / f"{section_name}.tex"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        # Store for inline embedding in layout
        rendered_sections[section_name] = rendered

    logger.debug(f"Rendered {len(rendered_sections)} section templates")
    return rendered_sections


def render_layout(
    env,
    data: Dict[str, Any],
    output_path: Path
) -> str:
    """
    Render the main layout template with embedded sections.

    Args:
        env: Jinja2 environment.
        data: CV data dictionary (should include *_section keys).
        output_path: Path to write the combined .tex file.

    Returns:
        The rendered layout content.

    Raises:
        TemplateError: If the layout template fails to render.
    """
    try:
        layout_template = env.get_template("layout.tex")
        rendered_layout = layout_template.render(data)
    except JinjaTemplateError as e:
        raise TemplateError(f"[Jinja error in layout.tex] {e}") from e

    # Collapse accidental double blank lines
    rendered_layout = rendered_layout.replace("\n\n\n", "\n\n")

    # Write the combined file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_layout)

    logger.debug(f"Written combined layout to {output_path}")
    return rendered_layout


def filter_by_variant(data: Dict[str, Any], variant: str) -> Dict[str, Any]:
    """
    Filter CV data entries by variant (type_key).

    This filters list sections (like experiences, education, etc.) to only
    include entries that have a matching type_key. Entries without type_key
    are always included (they are considered "universal").

    Args:
        data: CV data dictionary.
        variant: Variant name to filter by (matched against type_key).

    Returns:
        Filtered CV data dictionary.
    """
    # Sections that contain list of entries with potential type_key
    list_sections = [
        "education", "experiences", "projects", "publications",
        "workshop_and_certifications", "references", "awards", "honors"
    ]

    filtered = copy.deepcopy(data)

    for section in list_sections:
        if section not in filtered:
            continue

        items = filtered[section]
        if not isinstance(items, list):
            continue

        # Filter items: include if no type_key OR type_key matches variant
        filtered_items = []
        for item in items:
            if not isinstance(item, dict):
                filtered_items.append(item)
                continue

            type_key = item.get("type_key")
            if type_key is None:
                # No type_key means include in all variants
                filtered_items.append(item)
            elif isinstance(type_key, list):
                # type_key is a list of variants
                if variant in type_key:
                    filtered_items.append(item)
            elif type_key == variant:
                # type_key matches exactly
                filtered_items.append(item)

        filtered[section] = filtered_items
        if len(filtered_items) < len(items):
            logger.debug(
                f"Filtered {section}: {len(items)} -> {len(filtered_items)} items "
                f"(variant={variant})"
            )

    return filtered


def generate_cv(
    cv_file: Path,
    *,
    templates_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    lang_map: Optional[Dict[str, Dict[str, str]]] = None,
    dry_run: bool = False,
    keep_latex: bool = False,
    variant: Optional[str] = None,
    incremental: bool = False,
    cache: Optional[BuildCache] = None,
) -> CVGenerationResult:
    """
    Generate a PDF CV from a JSON file.

    Args:
        cv_file: Path to the CV JSON file.
        templates_dir: Path to templates directory.
        output_dir: Path to output directory root.
        lang_map: Language translation map (will be loaded if not provided).
        dry_run: If True, render LaTeX but don't compile to PDF.
        keep_latex: If True, keep LaTeX source files in output/latex/.
        variant: If provided, filter entries by type_key matching this variant.
        incremental: If True, skip rebuild if inputs haven't changed.
        cache: BuildCache instance for incremental builds.

    Returns:
        CVGenerationResult with status and paths.
    """
    if templates_dir is None:
        templates_dir = get_default_templates_path()
    if output_dir is None:
        output_dir = get_default_output_path()

    # Parse filename
    base_name, lang = parse_cv_filename(cv_file.name)
    is_rtl = lang in RTL_LANGUAGES

    # Create artifact paths for this CV
    artifact_paths = ArtifactPaths(profile=base_name, lang=lang, output_root=output_dir)

    # Check for incremental build skip
    if incremental and cache is not None:
        # Compute current input hashes
        assets = []
        pic_path = get_repo_root() / "data" / "pics" / f"{base_name}.jpg"
        if pic_path.exists():
            assets.append(pic_path)

        current_hashes = compute_input_hashes(cv_file, templates_dir, assets)
        cached_hashes = cache.get_entry(base_name, lang)

        rebuild_needed, reason = needs_rebuild(cached_hashes, current_hashes)

        if not rebuild_needed:
            # Check if output PDF exists
            expected_pdf = artifact_paths.pdf_dir / f"{base_name}_{lang}.pdf"
            if expected_pdf.exists():
                logger.info(f"⏭️  Skipping {base_name}_{lang}: {reason}")
                return CVGenerationResult(
                    base_name, lang, True,
                    pdf_path=expected_pdf,
                    skipped=True,
                )

        logger.debug(f"Rebuild needed for {base_name}_{lang}: {reason}")

    artifact_paths.ensure_dirs()
    artifact_paths.log_paths()

    logger.info(f"Processing CV: {base_name} ({lang})")

    # Load CV data
    try:
        data = load_cv_json(cv_file)
    except Exception as e:
        return CVGenerationResult(base_name, lang, False, error=str(e))

    # Validate required structure
    if not validate_cv_data(data, cv_file.name):
        return CVGenerationResult(
            base_name, lang, False,
            error="Missing 'basics' key (incompatible schema)"
        )

    # Apply variant filtering if specified
    if variant:
        data = filter_by_variant(data, variant)

    # Execute pre_validate hook
    hook_ctx = _execute_hook(
        HookType.PRE_VALIDATE,
        cv_name=base_name,
        lang=lang,
        data=data,
    )
    if hook_ctx.abort:
        return CVGenerationResult(
            base_name, lang, False,
            error=f"Aborted by plugin: {hook_ctx.abort_reason}"
        )
    # Allow plugins to modify data
    data = hook_ctx.data

    # Load language map if needed
    if lang_map is None:
        lang_map = load_lang_map()

    # Create Jinja environment
    env = create_jinja_env(templates_dir, lang_map, lang)

    # Set up output paths using unified ArtifactPaths
    sections_dir = artifact_paths.sections_dir
    rendered_tex_path = artifact_paths.tex_path

    # Prepare template variables
    data["OPT_NAME"] = base_name
    env.globals["BASE_NAME"] = base_name
    env.globals["IS_RTL"] = is_rtl

    env_vars = {**data}
    env_vars["LANG_MAP"] = lang_map
    env_vars["LANG"] = lang
    env_vars["BASE_NAME"] = base_name
    env_vars["IS_RTL"] = is_rtl

    # Render sections
    try:
        rendered_sections = render_sections(env, templates_dir, env_vars, sections_dir)
    except TemplateError as e:
        return CVGenerationResult(base_name, lang, False, error=str(e))

    # Add sections to env_vars for layout
    for section_name, content in rendered_sections.items():
        env_vars[f"{section_name}_section"] = content

    logger.info(f"✅ Sections rendered to '{sections_dir}'.")

    # Execute post_render hook
    hook_ctx = _execute_hook(
        HookType.POST_RENDER,
        cv_name=base_name,
        lang=lang,
        data=env_vars,
        rendered_sections=rendered_sections,
    )
    if hook_ctx.abort:
        return CVGenerationResult(
            base_name, lang, False,
            error=f"Aborted by plugin: {hook_ctx.abort_reason}"
        )

    # Render layout
    try:
        render_layout(env, env_vars, rendered_tex_path)
    except TemplateError as e:
        return CVGenerationResult(base_name, lang, False, error=str(e))

    logger.info(f"✅ Final LaTeX generated: {rendered_tex_path}")

    if dry_run:
        logger.info(f"➡️  Dry run: would compile with xelatex {rendered_tex_path}")
        return CVGenerationResult(
            base_name, lang, True,
            tex_path=rendered_tex_path
        )

    # Execute pre_compile hook
    hook_ctx = _execute_hook(
        HookType.PRE_COMPILE,
        cv_name=base_name,
        lang=lang,
        data=env_vars,
        rendered_sections=rendered_sections,
        tex_path=rendered_tex_path,
    )
    if hook_ctx.abort:
        return CVGenerationResult(
            base_name, lang, False,
            error=f"Aborted by plugin: {hook_ctx.abort_reason}"
        )

    # Compile LaTeX to PDF directory
    logger.info(f"➡️  Compile with: xelatex {rendered_tex_path}")

    try:
        pdf_path = compile_latex(rendered_tex_path, artifact_paths.pdf_dir)
    except Exception as e:
        logger.error(f"LaTeX compilation failed: {e}")
        pdf_path = None

    if pdf_path is not None:
        # Rename to final name (profile_lang.pdf for backward compatibility)
        pdf_name = f"{base_name}_{lang}"
        final_pdf = rename_pdf(pdf_path, pdf_name, artifact_paths.pdf_dir)

        # Clean up LaTeX artifacts from PDF directory
        cleanup_latex_artifacts(artifact_paths.pdf_dir)

        logger.info(f"✅ PDF generated: {final_pdf}")

        result = CVGenerationResult(
            base_name, lang, True,
            pdf_path=final_pdf,
            tex_path=rendered_tex_path
        )

        # Save cache for incremental builds
        if incremental and cache is not None:
            assets = []
            pic_path = get_repo_root() / "data" / "pics" / f"{base_name}.jpg"
            if pic_path.exists():
                assets.append(pic_path)
            cache_entry = compute_input_hashes(cv_file, templates_dir, assets)
            cache.save_entry(base_name, lang, cache_entry)

        # Execute post_export hook
        _execute_hook(
            HookType.POST_EXPORT,
            cv_name=base_name,
            lang=lang,
            data=env_vars,
            rendered_sections=rendered_sections,
            tex_path=rendered_tex_path,
            pdf_path=final_pdf,
        )
    else:
        result = CVGenerationResult(
            base_name, lang, False,
            tex_path=rendered_tex_path,
            error="LaTeX compilation failed"
        )

    # Clean up LaTeX files if not keeping them
    if not keep_latex:
        cleanup_result_dir(artifact_paths.latex_dir)
    else:
        logger.info(f"📁 LaTeX files kept at: {artifact_paths.latex_dir}")

    return result


def generate_all_cvs(
    *,
    cvs_dir: Optional[Path] = None,
    templates_dir: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    name_filter: Optional[str] = None,
    dry_run: bool = False,
    keep_latex: bool = False,
    variant: Optional[str] = None,
    incremental: bool = False,
) -> List[CVGenerationResult]:
    """
    Generate PDFs for all CV files in a directory.

    Args:
        cvs_dir: Path to directory containing CV JSON files.
        templates_dir: Path to templates directory.
        output_dir: Path to output directory root.
        name_filter: If provided, only generate CVs matching this base name.
        dry_run: If True, render LaTeX but don't compile to PDF.
        keep_latex: If True, keep LaTeX source files in output/latex/.
        variant: If provided, filter entries by type_key matching this variant.
        incremental: If True, skip rebuild if inputs haven't changed.

    Returns:
        List of CVGenerationResult objects.
    """
    if cvs_dir is None:
        cvs_dir = get_default_cvs_path()
    if output_dir is None:
        output_dir = get_default_output_path()
    if templates_dir is None:
        templates_dir = get_default_templates_path()

    # Log output configuration
    logger.info(f"📁 Output root: {output_dir}")
    logger.info(f"   PDFs will be saved to: {output_dir / 'pdf'}")
    if keep_latex:
        logger.info(f"   LaTeX sources will be saved to: {output_dir / 'latex'}")
    if incremental:
        logger.info("   Incremental build enabled")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up build cache if incremental mode is enabled
    cache = None
    if incremental:
        cache_dir = get_cache_dir(output_dir)
        cache = BuildCache(cache_dir)

    # Load language map once for all CVs
    lang_map = load_lang_map()

    # Discover CV files
    cv_files = discover_cv_files(cvs_dir, name_filter)

    if not cv_files:
        if name_filter:
            logger.warning(f"No CV files found matching '{name_filter}'")
        else:
            logger.warning(f"No CV files found in {cvs_dir}")
        return []

    logger.info(f"Found {len(cv_files)} CV file(s) to process")
    if variant:
        logger.info(f"Filtering entries by variant: {variant}")

    results = []
    for cv_file in cv_files:
        result = generate_cv(
            cv_file,
            templates_dir=templates_dir,
            output_dir=output_dir,
            lang_map=lang_map,
            dry_run=dry_run,
            keep_latex=keep_latex,
            variant=variant,
            incremental=incremental,
            cache=cache,
        )
        results.append(result)

    # Summary
    successful = sum(1 for r in results if r.success)
    skipped = sum(1 for r in results if r.skipped)
    if skipped > 0:
        logger.info(f"Generated {successful}/{len(results)} CVs successfully ({skipped} skipped - up to date)")
    else:
        logger.info(f"Generated {successful}/{len(results)} CVs successfully")

    return results
