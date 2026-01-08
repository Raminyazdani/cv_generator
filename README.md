<div align="center">

# 📋 CV Generator Web UI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-lightgrey.svg)](https://flask.palletsprojects.com/)

**A lightweight Flask-based web interface for importing, editing, and exporting multi-language CV JSON data.**

Easily manage your CV content in multiple languages (English, German, Farsi, and more), organize entries with tags, and export polished JSON files for use with LaTeX templates or other CV generators.

</div>

---

## ✨ Features

- 🌐 **Multi-language Support** — Manage CV content in English, German, Farsi, and more
- 📥 **Easy Import** — Import CV data from JSON files via drag-and-drop or quick disk import
- 📤 **Flexible Export** — Export single variants or batch export all language versions
- 🏷️ **Tag Management** — Organize CV entries with tags, merge translation-equivalent tags across languages
- 👤 **Person Dashboard** — View and edit all CV sections (education, skills, experience, etc.)
- 🔄 **Cross-Language Editor** — Edit multiple language versions side-by-side
- 💾 **SQLite Storage** — Lightweight database with automatic table creation

---

## 📸 Screenshots

### Home Page
<img src="https://github.com/user-attachments/assets/06b81e6a-bed5-4c9b-8c42-f0415b310a8b" alt="Home Page - CV Generator" width="800">

*View all persons in the database with their available language variants.*

### Person Dashboard
<img src="https://github.com/user-attachments/assets/33f899ee-4847-4d08-87bc-b26baf88dc5c" alt="Person Dashboard" width="800">

*Navigate through CV sections like Basics, Education, Skills, Experience, and more.*

### Import Page
<img src="https://github.com/user-attachments/assets/67f49460-605d-463b-b7ee-a6201252be24" alt="Import Page" width="800">

*Import CV JSON files via drag-and-drop or use Quick Import from disk.*

### Export Page
<img src="https://github.com/user-attachments/assets/b4822d48-f26f-41dd-8937-572bbb6bbb66" alt="Export Page" width="800">

*Export individual CV variants or batch export multiple persons at once.*

### Tags Management
<img src="https://github.com/user-attachments/assets/3afdbc52-c531-41c4-8806-33583ea23a07" alt="Tags Page" width="800">

*Create, manage, and merge tags with multi-language translations.*

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (recommended)
- **pip** (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Raminyazdani/cv_generator.git
   cd cv_generator
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r webui_requirements.txt
   ```

### Running the Application

1. **Start the server**
   ```bash
   python cvgen_webui.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5001
   ```

3. **Import sample data** (optional):
   - Go to the **Import** page
   - Click **⚡ Import from Disk** to load example JSON files from `data/cvs/`

> **Note:** Run commands from the repository root so relative data paths resolve correctly.

---

## 📖 Usage Guide

### Importing CV Data

You can import CV data in two ways:

1. **Upload Files**: Drag and drop JSON files or click to select files
2. **Quick Import**: Click **⚡ Import from Disk** to import all JSON files from `data/cvs/`

**Import Modes:**
- **Merge** — Add new data while keeping existing entries
- **Overwrite** — Replace existing data for matching persons

### Exporting CV Data

Navigate to the **Export** page to:

- **Single Export**: Select a person and language, then click **📤 Export**
- **Batch Export**: Select multiple persons and export all their language variants
- **Preview**: Click **👁️ Preview** to view the JSON before exporting

Exported files are saved to `output/json/` with timestamps to prevent overwriting.

### Managing Tags

Tags help categorize CV entries and support multiple languages:

**Creating Tags:**
1. Navigate to the **Tags** page
2. Enter a tag label and click **➕ Create**

**Merging Translation-Equivalent Tags:**

When importing CVs in multiple languages, tags may be created separately even if they represent the same concept (e.g., "bioinformatics" in English, "Bioinformatik" in German).

To merge these tags:
1. Go to the **Tags** page
2. Select the **Target Tag** (the one to keep)
3. Select one or more **Source Tags** (to merge into target)
4. Click **🔗 Merge Tags**

After merging:
- All entity associations transfer to the target tag
- Translations from source tags are added to the target
- Aliases are transferred (if no conflict)
- Source tags are deleted

**Deleting Tags:**
- Each tag card has a **🗑️ Delete Tag** button
- A confirmation dialog appears before deletion

---

## 📁 Project Structure

```
cv_generator/
├── cvgen_webui.py          # Main Flask application entry point
├── webui_requirements.txt  # Python dependencies
├── data/
│   ├── cvs/                # Sample CV JSON files
│   ├── assets/             # Configuration assets
│   └── pics/               # Profile pictures
├── src/
│   └── cv_generator/
│       ├── webui/          # Flask routes and models
│       ├── templates/      # HTML templates
│       └── lang_engine/    # Language processing
└── output/
    └── json/               # Exported JSON files
```

---

## ⚙️ Configuration

### Database Location

SQLite database is stored at `data/db/cv_database.db`. The directory and tables are created automatically on first request.

### Sample CV Data Format

CV JSON files follow this structure:

```json
{
  "config": {
    "lang": "en",
    "ID": "person_id"
  },
  "basics": [{ "fname": "John", "lname": "Doe", ... }],
  "education": [...],
  "skills": {...},
  "experiences": [...],
  "projects": [...],
  "publications": [...],
  "references": [...]
}
```

See `data/cvs/ramin.json` for a complete example.

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** and commit them
   ```bash
   git commit -m "Add your feature description"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**

### Reporting Issues

Found a bug or have a feature request? Please [open an issue](https://github.com/Raminyazdani/cv_generator/issues) with:
- A clear description of the problem or feature
- Steps to reproduce (for bugs)
- Expected vs. actual behavior

---

## ⚠️ Notes

- This UI is intended for **local use only**; the default secret key is not production-ready.
- No automated tests are currently included in the repository.
- Data must be imported from sample JSON files manually on first use.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [Ramin Yazdani](https://github.com/Raminyazdani)**

</div>
