# CV Generator – Web UI for CV Data Management

A lightweight web interface for managing CV data stored in JSON and SQLite. Browse, edit, and organize your CV information through an intuitive local web UI.

## Features

- **Web-based UI** – Browse and edit CV data through a local web interface
- **SQLite storage** – Store CV data in a queryable database  
- **Tag management** – Organize entries with tags for easy filtering
- **Multi-language** – Support for English, German, and Persian
- **Import/Export** – Import from JSON files and export back

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator

# Install the package
pip install -e .

# Initialize the database
cvgen db init

# Import your CV JSON files
cvgen db import

# Start the web UI
cvgen web
# Opens at http://127.0.0.1:5000
```

## Installation

### Requirements

- Python 3.9 or higher
- pip (Python package manager)

### Install from Source

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install the package
pip install -e .

# Verify installation
cvgen --version
```

### Developer Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -q
```

## Usage

### Start the Web UI

```bash
cvgen web
```

This starts a local web server at `http://127.0.0.1:5000`. Open this URL in your browser to access the CV Manager.

Options:
- `--port 8080` – Use a different port
- `--debug` – Enable Flask debug mode

### Database Commands

```bash
# Initialize the database
cvgen db init

# Import CV JSON files into the database
cvgen db import --input-dir data/cvs

# Export database to JSON files
cvgen db export --output-dir output/cvs

# List persons in the database
cvgen db list --what persons

# List tags in the database
cvgen db list --what tags
```

## Web UI Features

The web interface provides:

### Browse & Navigate
- View all persons and their CV sections
- Navigate through education, experience, skills, etc.
- Switch between languages (EN/DE/FA)

### Edit Entries
- View and edit individual entries
- Add new entries
- Delete entries with confirmation

### Tag Management
- Create, rename, and delete tags
- Assign tags to entries
- Filter entries by tag

### Export
- Preview export before saving
- Export CVs with tag updates
- Choose language for export

## Project Structure

```
cv_generator/
├── src/cv_generator/         # Python package
│   ├── cli.py               # Command-line interface
│   ├── web.py               # Flask web application
│   ├── db.py                # Database operations
│   ├── templates/           # HTML templates
│   └── ...
├── data/
│   ├── cvs/                 # CV JSON files
│   └── db/                  # SQLite database
├── tests/                   # Test suite
├── pyproject.toml          # Package configuration
└── README.md               # This file
```

## CV JSON Format

CV data uses a simple JSON structure:

```json
{
  "basics": [{
    "fname": "Jane",
    "lname": "Doe",
    "email": "jane@example.com"
  }],
  "education": [
    {
      "institution": "University",
      "area": "Computer Science",
      "studyType": "B.Sc.",
      "startDate": "2018",
      "endDate": "2022"
    }
  ],
  "experiences": [
    {
      "institution": "Tech Company",
      "role": "Developer",
      "duration": "2022 - Present"
    }
  ]
}
```

## Configuration

Create a `cv_generator.toml` file for configuration:

```toml
[project]
name = "My CV Project"
default_lang = "en"

[paths]
cvs = "data/cvs"
db = "data/db/cv.db"

[web]
host = "127.0.0.1"
port = 5000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

MIT License – see [LICENSE](LICENSE) for details.
