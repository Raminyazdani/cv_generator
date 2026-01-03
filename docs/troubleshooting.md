# Troubleshooting

Common issues and their solutions when using CV Generator.

## Installation Issues

### XeLaTeX Not Found

**Symptom:**
```
'xelatex' is not recognized as an internal or external command
```

**Solution:**

1. Install a LaTeX distribution:
   - **Windows:** [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/)
   - **macOS:** [MacTeX](https://www.tug.org/mactex/)
   - **Linux:** `sudo apt install texlive-xetex`

2. Add XeLaTeX to your PATH:
   - **Windows:** Add `C:\texlive\2024\bin\windows` or similar to PATH
   - **macOS/Linux:** Usually automatic with package managers

3. Verify installation:
   ```bash
   xelatex --version
   ```

### Python Package Installation Fails

**Symptom:**
```
ERROR: Could not install packages due to an EnvironmentError
```

**Solution:**

1. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

2. Use a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -e .
   ```

3. Or install with user flag:
   ```bash
   pip install --user -e .
   ```

## LaTeX Compilation Issues

### Special Character Errors

**Symptom:**
```
! Missing $ inserted.
! Undefined control sequence.
```

**Cause:** Unescaped special characters in your JSON data (`#`, `%`, `_`, `&`, `$`, `^`, `~`, `{`, `}`, `\`).

**Solution:**

1. Use the `latex_escape` filter in templates:
   ```latex
   <VAR> text | latex_escape </VAR>
   ```

2. Or escape characters in your JSON:
   ```json
   "description": "C\\# programming"
   ```

### Missing Field Errors

**Symptom:**
```
jinja2.exceptions.UndefinedError: 'basics' is undefined
```

**Cause:** Template references a field that doesn't exist in your JSON.

**Solution:**

1. Check that all required fields exist in your CV JSON
2. Use the `default` filter for optional fields:
   ```latex
   <VAR> optional_field | default('') </VAR>
   ```
3. Use conditional blocks:
   ```latex
   <BLOCK> if field is defined </BLOCK>
     ...
   <BLOCK> endif </BLOCK>
   ```

### Font Warnings

**Symptom:**
```
LaTeX Font Warning: Font shape 'TU/Roboto' undefined
```

**Cause:** Fonts used by Awesome-CV are not installed.

**Solution:**

1. Install required fonts:
   - **Roboto** — Download from [Google Fonts](https://fonts.google.com/specimen/Roboto)
   - **Source Sans Pro** — Download from [Google Fonts](https://fonts.google.com/specimen/Source+Sans+Pro)

2. Or modify `layout.tex` to use available fonts:
   ```latex
   \setmainfont{DejaVu Sans}
   ```

### PDF Not Generated

**Symptom:** Command completes but no PDF is created.

**Solution:**

1. Run with verbose mode to see errors:
   ```bash
   cvgen -v build
   ```

2. Check the LaTeX log by keeping sources:
   ```bash
   cvgen build --keep-latex
   ```
   Then examine `output/latex/<name>/<lang>/main.log`.

3. Run dry-run to check template rendering:
   ```bash
   cvgen build --dry-run
   ```

## File System Issues

### Access Denied (Windows)

**Symptom:**
```
PermissionError: [WinError 5] Access is denied
```

**Cause:** File locks from editors, OneDrive, or antivirus.

**Solution:**

1. Close any editors that have output files open
2. Temporarily pause OneDrive sync
3. Exclude the output directory from antivirus real-time scanning
4. The generator has retry logic; try running again

### Profile Picture Not Showing

**Symptom:** CV generates without the photo.

**Cause:** Photo file not found or wrong format.

**Solution:**

1. Place photo at the correct path:
   - CV: `data/cvs/jane.json`
   - Photo: `data/pics/jane.jpg`

2. Ensure file names match exactly (case-sensitive on Linux/macOS)

3. Use JPG format (other formats may not work)

4. Check the `find_pic` filter in verbose mode:
   ```bash
   cvgen -v build
   ```

## Multilingual Issues

### Language File Not Found

**Symptom:**
```
CV file not found for language 'de'
```

**Cause:** Missing language-specific CV file.

**Solution:**

1. Create the language file with proper naming:
   - `data/cvs/jane.json` (English default)
   - `data/cvs/jane_de.json` (German)
   - `data/cvs/jane_fa.json` (Persian)

2. Or use the i18n directory structure:
   - `data/cvs/i18n/jane/cv.en.json`
   - `data/cvs/i18n/jane/cv.de.json`

### RTL Text Not Working

**Symptom:** Persian text displays incorrectly.

**Cause:** RTL packages not properly configured.

**Solution:**

1. Ensure `polyglossia` package is installed with your LaTeX distribution
2. Check that `IS_RTL` is handled in `layout.tex`
3. Use XeLaTeX (not pdfLaTeX) for proper Unicode support

### Translation Mapping Not Applied

**Symptom:** Skill headings not translated.

**Cause:** Missing or incorrect language mapping.

**Solution:**

1. Check `src/cv_generator/lang_engine/lang.json`:
   ```json
   {
     "Technical Skills": {
       "de": "Technische Fähigkeiten",
       "fa": "مهارت‌های فنی"
     }
   }
   ```

2. Or provide a custom mapping:
   ```bash
   cvgen ensure --name jane --lang-map path/to/lang.json
   ```

## Debugging Tips

### Enable Verbose Logging

```bash
cvgen -v build
```

### Enable Debug Logging

```bash
cvgen --debug build
```

### Dry Run

Render templates without compiling:

```bash
cvgen build --dry-run
```

### Keep LaTeX Files

```bash
cvgen build --keep-latex
```

Then inspect `output/latex/<name>/<lang>/`:
- `main.tex` — Combined document
- `sections/*.tex` — Individual sections
- `main.log` — LaTeX compilation log

### Debug Filter

Add to templates to inspect values:

```latex
<VAR> skills | debug </VAR>
```

### Run Validation

Check JSON consistency:

```bash
cvgen ensure --name jane
```

## Getting Help

1. Check the [CLI Reference](cli.md) for command options
2. Review the [JSON Schema](json-schema.md) for data format
3. See [Templates](templates.md) for customization
4. Use `cvgen help <topic>` for extended help
5. Open an issue on GitHub for bugs or feature requests
