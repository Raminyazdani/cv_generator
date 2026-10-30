# CV generator — separate local code variant

Preserved code is the selected local variant only. Depending on this variant, entry points are the packaged `src/cv_generator/cli.py`/`generate_cv.py` or `cvgen_webui.py` with `src/cv_generator/webui/`. Source manifests and HTML/LaTeX code templates are retained where available. No variant is selected as canonical based on dates or commit counts.

Install dependencies from the retained `pyproject.toml` or supplied `requirements.txt` in an isolated environment after review. Flask UI variants run locally; hardcoded development session keys were replaced with `CVGEN_SECRET_KEY` or a per-process ephemeral key, and development debug startup was disabled. The application can create a fresh private local SQLite database when explicitly started. No original database is included or opened during preparation.

Supply your own reviewed CV input and language/configuration resources. Original JSON records and output PDFs are deliberately absent. Packaged CLI/PDF/translation features may require owner-supplied language maps, templates/fonts or external LaTeX tools as documented by their code; no end-to-end rendering or server run was performed. Static validation and unresolved resource/import details appear in the external receipt.

## Publication boundary and history

This is a current-tree, code-only publication copy prepared at the time recorded in `PUBLICATION_PROVENANCE.md`. Original local data and Git repositories are unchanged. Real CVs, contacts, databases, `.env` files, outreach results, browser profiles, personal fixtures and logs were excluded. Synthetic configuration examples contain no real credentials or CV facts.

For owned-repository variants, the proposed branch starts from the recorded existing remote parent. **Old remote Git history may still contain CV/private/runtime data. This change only replaces the new current tree; it does not purge history, rotate credentials, change visibility or make old data safe.** No local source-history commits are imported. Source HEAD and per-file SHA-256 document this code import; no historical commit dates or fake development history are created.

No sender, browser, login, production database or network API was executed during preparation. Validation scope is recorded in the external receipt. Dependencies and full runtime behavior are not claimed verified. Ignore rules do not protect already tracked or historical secrets.

## Dependency metadata audit

See [DEPENDENCY_AUDIT.md](DEPENDENCY_AUDIT.md) and `constraints-audited-py312-windows.txt` for the actual2026-10-30 resolver/advisory scope. This is a Python3.12/Windows package-metadata snapshot, not proof of complete runtime compatibility or coverage of LaTeX/browser/system tools.
