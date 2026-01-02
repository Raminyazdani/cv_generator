"""Test configuration and fixtures for CV Generator tests."""

import sys
from pathlib import Path

# Add src to path for development testing
_src_dir = Path(__file__).parent.parent / "src"
if _src_dir.exists():
    sys.path.insert(0, str(_src_dir))
