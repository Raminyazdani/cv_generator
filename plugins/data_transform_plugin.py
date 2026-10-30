"""
Data Transformation Plugin for CV Generator.

This plugin demonstrates how to use hooks to transform CV data
during the generation pipeline. It shows how to:
1. Modify CV data before validation (pre_validate hook)
2. Post-process rendered content (post_render hook)
3. Intercept compilation (pre_compile hook)
4. React to export completion (post_export hook)

Use cases demonstrated:
- Add computed fields (years of experience)
- Anonymize sensitive data
- Add watermarks to rendered content
- Log pipeline statistics

To use this plugin:
1. Place in <repository>/plugins/ or ~/.cv_generator/plugins/
2. Run CV generation normally - transformations apply automatically

Configuration via environment variables:
- CVGEN_ANONYMIZE=1: Anonymize contact information
- CVGEN_WATERMARK=1: Add watermark to LaTeX output
"""
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List
from cv_generator.hooks import HookContext, HookType
logger = logging.getLogger(__name__)

def calculate_years_of_experience(experiences: List[Dict[str, Any]]) -> int:
    """
    Calculate total years of work experience.

    Parses duration strings like "2020 – Present" or "2018 - 2020"
    to compute total years.

    Args:
        experiences: List of experience entries.

    Returns:
        Total years of experience.
    """
    current_year = datetime.now().year
    total_months = 0
    for exp in experiences:
        duration = exp.get('duration', '')
        if not duration:
            continue
        match = re.search('(\\d{4})\\s*[-–—]\\s*(\\d{4}|[Pp]resent|[Cc]urrent)', duration)
        if match:
            start_year = int(match.group(1))
            end_str = match.group(2)
            if end_str.lower() in ('present', 'current'):
                end_year = current_year
            else:
                end_year = int(end_str)
            years = end_year - start_year
            total_months += years * 12
    return total_months // 12

def anonymize_email(email: str) -> str:
    """
    Anonymize an email address.

    Example: operator@example.invalid -> j***@c***.com

    Args:
        email: Email address to anonymize.

    Returns:
        Anonymized email address.
    """
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    domain_parts = domain.rsplit('.', 1)
    local_anon = local[0] + '***' if local else '***'
    domain_anon = domain_parts[0][0] + '***' if domain_parts[0] else '***'
    tld = domain_parts[1] if len(domain_parts) > 1 else 'com'
    return f'{local_anon}@{domain_anon}.{tld}'

def anonymize_phone(phone: str) -> str:
    """
    Anonymize a phone number.

    Example: +49 123 456789 -> +49 *** ***789

    Args:
        phone: Phone number to anonymize.

    Returns:
        Anonymized phone number.
    """
    if not phone:
        return phone
    digits = re.findall('\\d', phone)
    if len(digits) < 4:
        return '*** ***'
    country = ''.join(digits[:3]) if len(digits) >= 6 else ''.join(digits[:2])
    last = ''.join(digits[-3:])
    return f'+{country} *** ***{last}'

def add_latex_watermark(content: str, text: str='DRAFT') -> str:
    """
    Add a watermark to LaTeX content.

    Inserts a draftwatermark package usage after documentclass.

    Args:
        content: LaTeX content.
        text: Watermark text.

    Returns:
        LaTeX content with watermark.
    """
    if 'draftwatermark' in content:
        return content
    watermark_code = f'\n% Watermark added by data_transform_plugin\n\\usepackage{{draftwatermark}}\n\\SetWatermarkText{{{text}}}\n\\SetWatermarkScale{{0.5}}\n\\SetWatermarkColor[gray]{{0.9}}\n'
    match = re.search('(\\\\documentclass\\[.*?\\]\\{.*?\\})', content)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + watermark_code + content[insert_pos:]
    return content
_stats: Dict[str, Any] = {'cvs_processed': 0, 'total_experience_years': 0, 'sections_rendered': 0, 'anonymizations': 0}

def pre_validate_handler(context: HookContext) -> None:
    """
    Pre-validation hook handler.

    Performs the following transformations:
    1. Adds computed fields (years_of_experience)
    2. Anonymizes data if CVGEN_ANONYMIZE=1

    Args:
        context: Hook context with CV data.
    """
    logger.debug(f'Data Transform: pre_validate for {context.cv_name}')
    experiences = context.data.get('experiences', [])
    years = calculate_years_of_experience(experiences)
    context.data['computed'] = context.data.get('computed', {})
    context.data['computed']['years_of_experience'] = years
    _stats['total_experience_years'] += years
    if os.environ.get('CVGEN_ANONYMIZE', '').lower() in ('1', 'true', 'yes'):
        logger.info('Data Transform: Anonymizing contact information')
        basics = context.data.get('basics', [])
        if not isinstance(basics, list):
            basics = [basics] if isinstance(basics, dict) else []
        for basic in basics:
            if not isinstance(basic, dict):
                continue
            if 'email' in basic:
                basic['email'] = anonymize_email(basic['email'])
                _stats['anonymizations'] += 1
            if 'phone' in basic:
                phone = basic['phone']
                if isinstance(phone, dict) and 'formatted' in phone:
                    phone['formatted'] = anonymize_phone(phone['formatted'])
                elif isinstance(phone, str):
                    basic['phone'] = anonymize_phone(phone)
                _stats['anonymizations'] += 1

def post_render_handler(context: HookContext) -> None:
    """
    Post-render hook handler.

    Logs rendering statistics and optionally adds watermark.

    Args:
        context: Hook context with rendered sections.
    """
    sections = context.rendered_sections
    section_count = len(sections)
    logger.debug(f'Data Transform: Rendered {section_count} sections for {context.cv_name} ({context.lang})')
    _stats['sections_rendered'] += section_count
    if os.environ.get('CVGEN_WATERMARK', '').lower() in ('1', 'true', 'yes'):
        logger.info('Data Transform: Adding watermark to output')
        if 'layout_section' in sections:
            sections['layout_section'] = add_latex_watermark(sections['layout_section'], text='DRAFT')

def pre_compile_handler(context: HookContext) -> None:
    """
    Pre-compile hook handler.

    Validates that the LaTeX file exists and is ready for compilation.

    Args:
        context: Hook context with tex_path.
    """
    if context.tex_path and context.tex_path.exists():
        size = context.tex_path.stat().st_size
        logger.debug(f'Data Transform: LaTeX file ready for compilation ({size} bytes)')
    else:
        context.add_warning('LaTeX file not found before compilation')

def post_export_handler(context: HookContext) -> None:
    """
    Post-export hook handler.

    Logs export completion and final statistics.

    Args:
        context: Hook context with pdf_path.
    """
    _stats['cvs_processed'] += 1
    if context.pdf_path and context.pdf_path.exists():
        size = context.pdf_path.stat().st_size
        logger.info(f'Data Transform: Export complete - {context.cv_name}_{context.lang}.pdf ({size / 1024:.1f} KB)')
    if _stats['cvs_processed'] % 5 == 0:
        logger.info(f"Data Transform Stats: {_stats['cvs_processed']} CVs processed, {_stats['sections_rendered']} sections rendered")

def register(registry, hook_manager):
    """
    Register plugin components.

    Registers hooks at all four hook points to demonstrate
    the complete pipeline lifecycle.

    Args:
        registry: The SectionRegistry instance (not used here).
        hook_manager: The HookManager instance for registering hooks.
    """
    logger.info('Data Transform Plugin: Loading...')
    hook_manager.register(HookType.PRE_VALIDATE, pre_validate_handler, name='data_transform_pre_validate', plugin_name='data_transform', priority=10)
    hook_manager.register(HookType.POST_RENDER, post_render_handler, name='data_transform_post_render', plugin_name='data_transform', priority=100)
    hook_manager.register(HookType.PRE_COMPILE, pre_compile_handler, name='data_transform_pre_compile', plugin_name='data_transform', priority=100)
    hook_manager.register(HookType.POST_EXPORT, post_export_handler, name='data_transform_post_export', plugin_name='data_transform', priority=100)
    logger.info('Data Transform Plugin: Registered 4 hooks')
    logger.info('  - Set CVGEN_ANONYMIZE=1 to anonymize contact info')
    logger.info('  - Set CVGEN_WATERMARK=1 to add draft watermark')

def unregister():
    """
    Clean up plugin resources.

    Logs final statistics when the plugin is unloaded.
    """
    logger.info(f"Data Transform Plugin: Final stats - {_stats['cvs_processed']} CVs, {_stats['total_experience_years']} total years of experience, {_stats['anonymizations']} fields anonymized")
