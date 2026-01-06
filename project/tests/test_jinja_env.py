"""
Unit tests for cv_generator.jinja_env module.

Tests Jinja2 environment creation and custom filters.
"""

import pytest

from cv_generator.jinja_env import (
    cblock,
    cmt,
    create_jinja_env,
    file_exists,
    find_pic,
    get_pic,
    latex_escape,
    latex_raw,
    make_translate_func,
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


class TestLatexEscapeComprehensive:
    """Comprehensive parameterized tests for latex_escape function."""

    @pytest.mark.parametrize("input_str,expected", [
        # Basic special characters
        ("%", r"\%"),
        ("$", r"\$"),
        ("&", r"\&"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
        # Newlines and tabs
        ("\n", r"\newline{}"),
        ("\t", r"\hspace{1em}"),
        # Combined special chars
        ("100%", r"100\%"),
        ("$100", r"\$100"),
        ("C#", r"C\#"),
        ("A & B", r"A \& B"),
        ("first_name", r"first\_name"),
        ("{test}", r"\{test\}"),
        ("x^2", r"x\textasciicircum{}2"),
        ("~user", r"\textasciitilde{}user"),
    ])
    def test_escape_special_characters(self, input_str, expected):
        """Test escaping of individual special characters."""
        assert latex_escape(input_str) == expected

    @pytest.mark.parametrize("input_str,expected", [
        # Persian text with Latin punctuation
        ("سلام & خداحافظ", r"سلام \& خداحافظ"),
        ("قیمت: $100", r"قیمت: \$100"),
        ("بخش #1", r"بخش \#1"),
        ("زیر_خط", r"زیر\_خط"),
        ("درصد: 50%", r"درصد: 50\%"),
        # German text with special chars
        ("Prüfung & Test", r"Prüfung \& Test"),
        ("Größe: 100%", r"Größe: 100\%"),
        ("Schüler_innen", r"Schüler\_innen"),
        # Pure Unicode (should pass through)
        ("مرحبا", "مرحبا"),
        ("日本語", "日本語"),
        ("Ελληνικά", "Ελληνικά"),
    ])
    def test_escape_multilingual(self, input_str, expected):
        """Test escaping with mixed-language content."""
        assert latex_escape(input_str) == expected

    @pytest.mark.parametrize("input_str,expected", [
        # Multiple newlines
        ("Line1\nLine2\nLine3", r"Line1\newline{}Line2\newline{}Line3"),
        # Newline at start and end
        ("\nText\n", r"\newline{}Text\newline{}"),
        # Multiple tabs
        ("Col1\tCol2\tCol3", r"Col1\hspace{1em}Col2\hspace{1em}Col3"),
        # Mixed newlines and tabs
        ("A\nB\tC", r"A\newline{}B\hspace{1em}C"),
        # Windows-style line endings - \r passes through unchanged, \n becomes \newline{}
        ("A\r\nB", "A\r\\newline{}B"),
    ])
    def test_escape_whitespace(self, input_str, expected):
        """Test escaping of whitespace characters."""
        assert latex_escape(input_str) == expected

    @pytest.mark.parametrize("input_str", [
        # Backslash combinations
        "path\\to\\file",
        "\\section{Title}",
        "\\textbf{bold}",
        "C:\\Users\\name",
    ])
    def test_escape_backslash_patterns(self, input_str):
        """Test escaping backslash in various contexts."""
        result = latex_escape(input_str)
        assert "textbackslash" in result
        # Ensure no raw backslashes remain (except in escaped sequences)
        # Backslashes should all be converted

    @pytest.mark.parametrize("input_str,expected", [
        # All special chars in one string
        ("%$&#_{}~^", r"\%\$\&\#\_\{\}\textasciitilde{}\textasciicircum{}"),
        # Real-world CV content
        ("100% completion rate", r"100\% completion rate"),
        ("C# & .NET development", r"C\# \& .NET development"),
        ("email_address@example.com", r"email\_address@example.com"),
        ("Project #1: Revenue $1M", r"Project \#1: Revenue \$1M"),
    ])
    def test_escape_real_world_content(self, input_str, expected):
        """Test escaping with realistic CV content."""
        assert latex_escape(input_str) == expected

    @pytest.mark.parametrize("input_val", [
        None,
        "",
        0,
        123,
        3.14,
        True,
        False,
    ])
    def test_escape_non_string_values(self, input_val):
        """Test that non-string values are handled correctly."""
        result = latex_escape(input_val)
        assert isinstance(result, str)
        if input_val is None:
            assert result == ""
        else:
            assert result == str(input_val)

    def test_escape_deterministic(self):
        """Test that escaping is deterministic (same input -> same output)."""
        test_str = "Complex: $100 & 50% (test_data) #1 {item}^2"
        result1 = latex_escape(test_str)
        result2 = latex_escape(test_str)
        assert result1 == result2

    def test_escape_empty_string(self):
        """Test escaping empty string."""
        assert latex_escape("") == ""

    def test_escape_long_text(self):
        """Test escaping longer text with multiple special chars."""
        long_text = """
        Company & Co. is hiring!
        Job #123: Developer
        Salary: $100k+
        Skills: C#, Python (100% required)
        Contact: user_name@example.com
        """
        result = latex_escape(long_text)
        # Verify key escapes
        assert r"\&" in result
        assert r"\#" in result
        assert r"\$" in result
        assert r"\%" in result
        assert r"\_" in result
        assert r"\newline{}" in result


class TestLatexRaw:
    """Tests for latex_raw function."""

    def test_raw_passthrough(self):
        """Test that latex_raw passes through text unchanged."""
        input_str = r"\textbf{bold} & \textit{italic}"
        assert latex_raw(input_str) == input_str

    def test_raw_none(self):
        """Test that None returns empty string."""
        assert latex_raw(None) == ""

    def test_raw_numeric(self):
        """Test that numeric values are converted to string."""
        assert latex_raw(123) == "123"
        assert latex_raw(3.14) == "3.14"

    def test_raw_special_chars_unchanged(self):
        """Test that special chars pass through without escaping."""
        input_str = "% $ & # _ { } ~ ^"
        assert latex_raw(input_str) == input_str


class TestLatexEscapeRegisteredInEnv:
    """Tests verifying latex_escape and latex_raw are registered in Jinja env."""

    def test_latex_escape_filter_registered(self, tmp_path):
        """Test that latex_escape filter is available in environment."""
        (tmp_path / "test.tex").write_text("<VAR> text | latex_escape </VAR>")
        env = create_jinja_env(template_dir=tmp_path)

        template = env.get_template("test.tex")
        result = template.render(text="100% & $50")

        assert result == r"100\% \& \$50"

    def test_latex_raw_filter_registered(self, tmp_path):
        """Test that latex_raw filter is available in environment."""
        (tmp_path / "test.tex").write_text("<VAR> text | latex_raw </VAR>")
        env = create_jinja_env(template_dir=tmp_path)

        template = env.get_template("test.tex")
        result = template.render(text=r"\textbf{bold}")

        assert result == r"\textbf{bold}"

    def test_escape_and_raw_different(self, tmp_path):
        """Test that escape and raw produce different results for special chars."""
        (tmp_path / "escaped.tex").write_text("<VAR> text | latex_escape </VAR>")
        (tmp_path / "raw.tex").write_text("<VAR> text | latex_raw </VAR>")
        env = create_jinja_env(template_dir=tmp_path)

        test_input = "100% complete"

        escaped = env.get_template("escaped.tex").render(text=test_input)
        raw = env.get_template("raw.tex").render(text=test_input)

        assert escaped != raw
        assert escaped == r"100\% complete"
        assert raw == "100% complete"
