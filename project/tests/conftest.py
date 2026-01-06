"""Test configuration and fixtures for CV Generator tests."""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for development testing
_src_dir = Path(__file__).parent.parent / "src"
if _src_dir.exists():
    sys.path.insert(0, str(_src_dir))


# ==============================================================================
# Fixture paths
# ==============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_VALID_DIR = FIXTURES_DIR / "valid"
FIXTURES_INVALID_DIR = FIXTURES_DIR / "invalid"
FIXTURES_MULTILANG_DIR = FIXTURES_DIR / "multilang"
FIXTURES_LINT_DIR = FIXTURES_DIR / "lint"
FIXTURES_RAMIN_DIR = FIXTURES_DIR / "ramin"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


# ==============================================================================
# JSON fixture helpers
# ==============================================================================

def load_json_fixture(fixture_path: Path) -> dict:
    """Load a JSON fixture file."""
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# Shared pytest fixtures
# ==============================================================================

@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def valid_fixtures_dir() -> Path:
    """Return the path to the valid fixtures directory."""
    return FIXTURES_VALID_DIR


@pytest.fixture
def invalid_fixtures_dir() -> Path:
    """Return the path to the invalid fixtures directory."""
    return FIXTURES_INVALID_DIR


@pytest.fixture
def multilang_fixtures_dir() -> Path:
    """Return the path to the multilang fixtures directory."""
    return FIXTURES_MULTILANG_DIR


@pytest.fixture
def snapshots_dir() -> Path:
    """Return the path to the snapshots directory."""
    return SNAPSHOTS_DIR


@pytest.fixture
def minimal_cv_data() -> dict:
    """Return minimal valid CV data fixture."""
    return load_json_fixture(FIXTURES_VALID_DIR / "minimal.json")


@pytest.fixture
def complete_cv_data() -> dict:
    """Return complete CV data fixture."""
    return load_json_fixture(FIXTURES_VALID_DIR / "complete.json")


@pytest.fixture
def multilang_en_data() -> dict:
    """Return English CV data from multilang fixtures."""
    return load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.en.json")


@pytest.fixture
def multilang_de_data() -> dict:
    """Return German CV data from multilang fixtures."""
    return load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.de.json")


@pytest.fixture
def multilang_fa_data() -> dict:
    """Return Persian (Farsi) CV data from multilang fixtures."""
    return load_json_fixture(FIXTURES_MULTILANG_DIR / "cv.fa.json")


@pytest.fixture
def multilang_lang_map() -> dict:
    """Return language translation map from multilang fixtures."""
    return load_json_fixture(FIXTURES_MULTILANG_DIR / "lang.json")


@pytest.fixture
def unicode_heavy_data() -> dict:
    """Return Unicode-heavy CV data fixture (Persian text)."""
    return load_json_fixture(FIXTURES_INVALID_DIR / "unicode_heavy.json")


@pytest.fixture
def long_text_data() -> dict:
    """Return CV data with long text fields fixture."""
    return load_json_fixture(FIXTURES_INVALID_DIR / "long_text_fields.json")
