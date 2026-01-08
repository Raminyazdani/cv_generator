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

### Tag Management

The **Tags** page allows you to manage tags that categorize CV entries. Tags support multiple languages and can be used to filter and group entries.

#### Removing Tags
- Navigate to the **Tags** page.
- Each tag card has a **🗑️ Delete Tag** button at the bottom.
- Clicking delete will remove the tag along with all its translations, aliases, and associations with CV entries.
- A confirmation dialog will appear before deletion.

#### Linking/Grouping Translation-Equivalent Tags
When importing CVs in multiple languages, tags may be imported as separate entries even if they represent the same concept (e.g., "bioinformatic" in English, "بیوانفورماتیک" in Farsi, "bioinformatik" in German).

To link these translation-equivalent tags:
1. Navigate to the **Tags** page.
2. The **Merge / Link Tags** section appears when you have 2 or more tags.
3. Select the **Target Tag** (the tag you want to keep).
4. Select one or more **Source Tags** (tags to merge into the target).
5. Click **🔗 Merge Tags**.

After merging:
- All entity associations from source tags are transferred to the target tag.
- Translations from source tags are added to the target (if not already present).
- Aliases from source tags are transferred (if no conflict).
- Source tags are deleted.

**Example workflow:**
1. Import English CV with tag "bioinformatic"
2. Import German CV with tag "bioinformatik"  
3. Go to Tags page, merge "bioinformatik" into "bioinformatic"
4. Add German translation "Bioinformatik" to the merged tag
5. Now both language CVs share the same tag concept

> Note: This UI is intended for local use only; the default secret key is not production-ready.
