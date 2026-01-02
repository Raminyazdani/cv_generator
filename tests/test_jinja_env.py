"""
Unit tests for cv_generator.jinja_env module.

Tests Jinja2 environment creation and custom filters.
"""

import pytest

from cv_generator.jinja_env import (
    latex_escape,
    file_exists,
    cmt,
    cblock,
    find_pic,
    get_pic,
    make_translate_func,
    create_jinja_env
)


class TestLatexEscape:
    """Tests for latex_escape function."""
    
    def test_escape_ampersand(self):
        """Test escaping ampersand."""
        assert latex_escape("A & B") == r"A \& B"
    
    def test_escape_percent(self):
        """Test escaping percent sign."""
        assert latex_escape("100%") == r"100\%"
    
    def test_escape_dollar(self):
        """Test escaping dollar sign."""
        assert latex_escape("$100") == r"\$100"
    
    def test_escape_hash(self):
        """Test escaping hash sign."""
        assert latex_escape("#1") == r"\#1"
    
    def test_escape_underscore(self):
        """Test escaping underscore."""
        assert latex_escape("first_name") == r"first\_name"
    
    def test_escape_braces(self):
        """Test escaping curly braces."""
        assert latex_escape("{test}") == r"\{test\}"
    
    def test_escape_backslash(self):
        """Test escaping backslash."""
        # Backslash is replaced with \textbackslash{}, and the braces are also escaped
        result = latex_escape("path\\to")
        assert "textbackslash" in result
    
    def test_escape_tilde(self):
        """Test escaping tilde."""
        assert latex_escape("~user") == r"\textasciitilde{}user"
    
    def test_escape_caret(self):
        """Test escaping caret."""
        assert latex_escape("x^2") == r"x\textasciicircum{}2"
    
    def test_none_value(self):
        """Test that None returns empty string."""
        assert latex_escape(None) == ""
    
    def test_numeric_value(self):
        """Test that numeric values are converted."""
        assert latex_escape(123) == "123"


class TestCommentFilters:
    """Tests for cmt and cblock filters."""
    
    def test_cmt_simple(self):
        """Test simple comment."""
        result = cmt("This is a comment")
        assert result == "% This is a comment\n"
    
    def test_cmt_multiline_collapsed(self):
        """Test that multiline is collapsed to single line."""
        result = cmt("Line 1\nLine 2")
        assert result == "% Line 1 Line 2\n"
    
    def test_cmt_none(self):
        """Test that None returns empty string."""
        assert cmt(None) == ""
    
    def test_cblock_multiline(self):
        """Test multi-line comment block."""
        result = cblock("Line 1\nLine 2")
        assert "% Line 1\n" in result
        assert "% Line 2\n" in result
    
    def test_cblock_none(self):
        """Test that None returns empty string."""
        assert cblock(None) == ""


class TestTranslateFunc:
    """Tests for translation function creation."""
    
    def test_translate_existing_key(self):
        """Test translating an existing key."""
        lang_map = {"education": {"en": "Education", "de": "Ausbildung"}}
        t = make_translate_func(lang_map, "de")
        
        result = t("education")
        assert result == "Ausbildung"
    
    def test_translate_fallback_to_english(self):
        """Test fallback to English when target lang not available."""
        lang_map = {"education": {"en": "Education"}}
        t = make_translate_func(lang_map, "de")
        
        result = t("education")
        assert result == "Education"
    
    def test_translate_fallback_to_key(self):
        """Test fallback to key when no translation available."""
        lang_map = {}
        t = make_translate_func(lang_map, "en")
        
        # By default, the result is LaTeX-escaped
        result = t("unknown_key")
        assert result == r"unknown\_key"
    
    def test_translate_with_default(self):
        """Test translation with default value."""
        lang_map = {}
        t = make_translate_func(lang_map, "en")
        
        result = t("unknown_key", default="Default Value")
        assert result == "Default Value"
    
    def test_translate_no_escape(self):
        """Test translation without LaTeX escaping."""
        lang_map = {"key": {"en": "Test & Value"}}
        t = make_translate_func(lang_map, "en")
        
        result = t("key", escape=False)
        assert result == "Test & Value"
    
    def test_translate_with_escape(self):
        """Test translation with LaTeX escaping."""
        lang_map = {"key": {"en": "Test & Value"}}
        t = make_translate_func(lang_map, "en")
        
        result = t("key", escape=True)
        assert result == r"Test \& Value"


class TestCreateJinjaEnv:
    """Tests for create_jinja_env function."""
    
    def test_create_env_with_defaults(self, tmp_path):
        """Test creating environment with default settings."""
        # Create a minimal template file
        (tmp_path / "test.tex").write_text("<VAR> name </VAR>")
        
        env = create_jinja_env(template_dir=tmp_path)
        
        assert env is not None
        assert "latex_escape" in env.filters
        assert "debug" in env.filters
        assert "cmt" in env.filters
    
    def test_create_env_with_lang_map(self, tmp_path):
        """Test creating environment with language map."""
        (tmp_path / "test.tex").write_text("<VAR> name </VAR>")
        lang_map = {"key": {"en": "Value"}}
        
        env = create_jinja_env(template_dir=tmp_path, lang_map=lang_map, lang="en")
        
        assert "tr" in env.filters
        assert "tr_raw" in env.filters
        assert env.globals.get("LANG") == "en"
    
    def test_env_renders_template(self, tmp_path):
        """Test that created environment can render templates."""
        (tmp_path / "test.tex").write_text("<VAR> name | latex_escape </VAR>")
        
        env = create_jinja_env(template_dir=tmp_path)
        template = env.get_template("test.tex")
        result = template.render(name="Test & User")
        
        assert result == r"Test \& User"
