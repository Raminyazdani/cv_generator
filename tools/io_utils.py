from pathlib import Path
import json

def read_json(path: Path):
    # TODO: add schema validation and friendly error messages
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_text(path: Path, text: str):
    # TODO: ensure consistent newlines/encoding; maybe backup old file
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
