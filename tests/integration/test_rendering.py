"""
Integration tests for JSON → LaTeX rendering pipeline.

Tests the full rendering flow from CV JSON data to LaTeX output,
including snapshot testing to detect unintended changes.
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from cv_generator.generator import render_layout, render_sections
from cv_generator.io import load_lang_map
from cv_generator.jinja_env import create_jinja_env
from cv_generator.paths import get_default_templates_path
from tests.conftest import (
    FIXTURES_MULTILANG_DIR,
    FIXTURES_VALID_DIR,
    load_json_fixture,
)
from tests.snapshot_utils import assert_snapshot_tex


def setup_template_vars(
    cv_data: Dict[str, Any],
    name: str,
    lang: str,
    lang_map: Dict[str, Dict[str, str]],
    is_rtl: bool = False,
) -> Dict[str, Any]:
    """
    Set up required template variables for CV data.

    Args:
        cv_data: The CV data dictionary to modify.
        name: The OPT_NAME/BASE_NAME value.
        lang: The language code.
        lang_map: The language translation map.
        is_rtl: Whether this is a right-to-left language.

    Returns:
        The modified cv_data dictionary.
    """
    cv_data["OPT_NAME"] = name
    cv_data["BASE_NAME"] = name
    cv_data["IS_RTL"] = is_rtl
    cv_data["LANG"] = lang
    cv_data["LANG_MAP"] = lang_map
    return cv_data


class TestJsonToLatexRendering:
    """Tests for the JSON to LaTeX rendering pipeline."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        """Return the default templates directory."""
        return get_default_templates_path()

    @pytest.fixture
    def default_lang_map(self) -> dict:
        """Return a minimal language map for testing."""
        return load_lang_map()

    @pytest.fixture
    def multilang_lang_map(self) -> dict:
        """Return the language map from multilang fixtures."""
        return load_json_fixture(FIXTURES_MULTILANG_DIR / "lang.json")

    def test_render_minimal_cv_produces_valid_latex(self, tmp_path, templates_dir, default_lang_map):
        """Test that minimal CV data produces valid LaTeX output."""
        cv_data = load_json_fixture(FIXTURES_VALID_DIR / "minimal.json")
        output_dir = tmp_path / "output"

        # Create environment with lang_map so t() is available
        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="en")

        # Set up required template variables
        setup_template_vars(cv_data, "minimal", "en", default_lang_map)

        sections = render_sections(env, templates_dir, cv_data, output_dir)

        # Check that sections were rendered
        assert len(sections) > 0
        # Header should be present
        assert "header" in sections
        # Header should contain the name
        assert "Test" in sections["header"] or "User" in sections["header"]

    def test_render_complete_cv_produces_all_sections(self, tmp_path, templates_dir, default_lang_map):
        """Test that complete CV data produces all expected sections."""
        cv_data = load_json_fixture(FIXTURES_VALID_DIR / "complete.json")
        output_dir = tmp_path / "output"

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="en")

        # Set up required template variables
        setup_template_vars(cv_data, "complete", "en", default_lang_map)

        sections = render_sections(env, templates_dir, cv_data, output_dir)

        # Check expected sections are rendered
        expected_sections = ["header", "education", "experience", "skills", "projects"]
        for section in expected_sections:
            assert section in sections, f"Section '{section}' should be rendered"

        # Check content is present
        assert "Complete" in sections["header"]
        assert "Technical University" in sections["education"]

    def test_render_layout_combines_sections(self, tmp_path, templates_dir, default_lang_map):
        """Test that layout template combines all sections."""
        cv_data = load_json_fixture(FIXTURES_VALID_DIR / "minimal.json")
        sections_dir = tmp_path / "sections"
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="en")

        # Set up required template variables
        setup_template_vars(cv_data, "minimal", "en", default_lang_map)

        # Render sections first
        sections = render_sections(env, templates_dir, cv_data, sections_dir)

        # Add sections to data for layout
        for section_name, content in sections.items():
            cv_data[f"{section_name}_section"] = content

        # Render layout
        tex_path = output_dir / "layout.tex"
        layout_content = render_layout(env, cv_data, tex_path)

        # Check that layout file was created
        assert tex_path.exists()

        # Check layout contains documentclass
        assert "\\documentclass" in layout_content or "documentclass" in layout_content.lower()

    def test_render_english_cv_with_snapshot(self, tmp_path, templates_dir, default_lang_map):
        """Test rendering English CV and compare with snapshot."""
        cv_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.en.json")
        sections_dir = tmp_path / "sections"

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="en")

        # Set up required template variables
        setup_template_vars(cv_data, "test", "en", default_lang_map)

        sections = render_sections(env, templates_dir, cv_data, sections_dir)

        # Snapshot test the header section
        assert_snapshot_tex(sections["header"], "integration_header_en")

    def test_render_german_cv_with_snapshot(self, tmp_path, templates_dir, default_lang_map):
        """Test rendering German CV and compare with snapshot."""
        cv_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.de.json")
        sections_dir = tmp_path / "sections"

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="de")

        # Set up required template variables
        setup_template_vars(cv_data, "test", "de", default_lang_map)

        sections = render_sections(env, templates_dir, cv_data, sections_dir)

        # Snapshot test the header section
        assert_snapshot_tex(sections["header"], "integration_header_de")


class TestMultilangParity:
    """Tests for multilingual CV structural parity."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        """Return the default templates directory."""
        return get_default_templates_path()

    @pytest.fixture
    def default_lang_map(self) -> dict:
        """Return a minimal language map for testing."""
        return load_lang_map()

    def test_en_de_structural_parity(self, tmp_path, templates_dir):
        """Test that English and German CVs have same structure."""
        en_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.en.json")
        de_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.de.json")

        # Both should have same top-level keys
        en_keys = set(en_data.keys())
        de_keys = set(de_data.keys())
        assert en_keys == de_keys, "English and German CVs should have same structure"

        # Both should have same number of education entries
        assert len(en_data.get("education", [])) == len(de_data.get("education", []))

        # Both should have same number of projects
        assert len(en_data.get("projects", [])) == len(de_data.get("projects", []))

    def test_en_fa_structural_parity(self, tmp_path, templates_dir):
        """Test that English and Persian CVs have same structure."""
        en_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.en.json")
        fa_data = load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.fa.json")

        # Both should have same top-level keys
        en_keys = set(en_data.keys())
        fa_keys = set(fa_data.keys())
        assert en_keys == fa_keys, "English and Persian CVs should have same structure"

        # Both should have same number of education entries
        assert len(en_data.get("education", [])) == len(fa_data.get("education", []))

    def test_multilang_all_render_successfully(self, tmp_path, templates_dir, default_lang_map):
        """Test that all language variants render without errors."""
        languages = ["en", "de", "fa"]
        rtl_langs = {"fa"}

        for lang in languages:
            cv_data = load_json_fixture(FIXTURES_MULTILANG_DIR / f"cv.{lang}.json")
            output_dir = tmp_path / f"output_{lang}"

            is_rtl = lang in rtl_langs
            env = create_jinja_env(
                template_dir=templates_dir,
                lang_map=default_lang_map,
                lang=lang
            )

            # Set up required template variables
            setup_template_vars(cv_data, "test", lang, default_lang_map, is_rtl)

            # This should not raise any exceptions
            sections = render_sections(env, templates_dir, cv_data, output_dir)
            assert len(sections) > 0, f"Language {lang} should produce sections"


class TestEdgeCaseRendering:
    """Tests for edge case CV data rendering."""

    @pytest.fixture
    def templates_dir(self) -> Path:
        """Return the default templates directory."""
        return get_default_templates_path()

    @pytest.fixture
    def default_lang_map(self) -> dict:
        """Return a minimal language map for testing."""
        return load_lang_map()

    def test_unicode_heavy_cv_renders_correctly(self, tmp_path, templates_dir, default_lang_map, unicode_heavy_data):
        """Test that Unicode-heavy (Persian) CV renders correctly."""
        output_dir = tmp_path / "output"

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="fa")

        # Set up required template variables
        setup_template_vars(unicode_heavy_data, "unicode", "fa", default_lang_map, is_rtl=True)

        sections = render_sections(env, templates_dir, unicode_heavy_data, output_dir)

        # Should render without errors
        assert len(sections) > 0
        # Header should contain Persian text
        assert "header" in sections

    def test_long_text_fields_render_correctly(self, tmp_path, templates_dir, default_lang_map, long_text_data):
        """Test that CVs with very long text fields render correctly."""
        output_dir = tmp_path / "output"

        env = create_jinja_env(template_dir=templates_dir, lang_map=default_lang_map, lang="en")

        # Set up required template variables
        setup_template_vars(long_text_data, "long", "en", default_lang_map)

        sections = render_sections(env, templates_dir, long_text_data, output_dir)

        # Should render without errors
        assert len(sections) > 0
        # Content should include the long name
        assert "VeryLongFirstName" in sections.get("header", "")
