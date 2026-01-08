## CV Generator Web UI

A lightweight Flask UI for importing, editing, and exporting multi-language CV JSON data stored in `data/cvs`.

### Prerequisites
- Python 3.10+ recommended
- Install dependencies from the repo root: `pip install -r webui_requirements.txt`

### Running locally
1. From the repo root, run `python cvgen_webui.py`.
2. The app starts at `http://127.0.0.1:5001`.
3. SQLite data is stored at `data/db/cv_database.db` (the directory is created automatically). Tables are created on first request.
4. Run commands from the repository root so relative data paths resolve correctly.

### Importing sample data
- Use the **Import** page in the UI and choose “Import from disk” to load the example JSON files under `data/cvs/`.

### Exporting
- Use the **Export** page to preview or write JSON exports to `output/json/`.

> Note: This UI is intended for local use only; the default secret key is not production-ready.
