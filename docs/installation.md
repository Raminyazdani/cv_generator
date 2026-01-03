# Installation

## Requirements

### Python

- Python 3.9 or higher
- pip (Python package manager)

### LaTeX

You must have XeLaTeX installed. The generator uses XeLaTeX to compile LaTeX documents to PDF.

**Windows:**
- [MiKTeX](https://miktex.org/) (recommended for Windows)
- [TeX Live](https://www.tug.org/texlive/)

**macOS:**
- [MacTeX](https://www.tug.org/mactex/)
- Homebrew: `brew install --cask mactex`

**Linux:**
- Ubuntu/Debian: `sudo apt install texlive-xetex texlive-fonts-recommended`
- Fedora: `sudo dnf install texlive-xetex`
- Arch: `sudo pacman -S texlive-core`

Verify XeLaTeX is installed:

```bash
xelatex --version
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Raminyazdani/cv_generator.git
cd cv_generator
```

### 2. Create a Virtual Environment (Recommended)

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install the Package

**Basic installation:**
```bash
pip install -e .
```

**With development dependencies:**
```bash
pip install -e ".[dev]"
```

### 4. Verify Installation

```bash
cvgen --version
cvgen --help
```

## Fonts

Awesome-CV uses specific fonts for optimal appearance:

- **Roboto** — Main text font
- **Source Sans Pro** — Alternative font

If fonts are not installed, XeLaTeX will substitute system fonts, which may affect appearance.

**Installing fonts:**

- **Windows:** Download and install from Google Fonts
- **macOS:** Download and install from Google Fonts
- **Linux:** `sudo apt install fonts-roboto` or download from Google Fonts

## Troubleshooting Installation

### XeLaTeX not found

Ensure XeLaTeX is in your PATH:

```bash
which xelatex  # Linux/macOS
where xelatex  # Windows
```

If not found, add the TeX distribution bin directory to your PATH.

### Package installation fails

Try upgrading pip:

```bash
pip install --upgrade pip
pip install -e .
```

### Permission errors

Use a virtual environment (recommended) or install with `--user`:

```bash
pip install --user -e .
```
