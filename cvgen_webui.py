"""
Local CV JSON Manager (Flask) — for editing cross-language CV content and tags.

Usage (from repo root):
  python cvgen_webui.py

Notes:
  - This runs locally only (127.0.0.1).
  - SQLite DB is stored under data/db/cv_database.db by default.
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from cv_generator.webui import create_app

def main() -> None:
    app = create_app(repo_root=ROOT)
    app.run(host='127.0.0.1', port=5001, debug=False)
if __name__ == '__main__':
    main()
