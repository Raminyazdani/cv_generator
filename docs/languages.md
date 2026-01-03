# Language Support

CV Generator supports multilingual CVs with proper text direction and translation.

## Supported Languages

| Code | Language | Direction | Status |
|------|----------|-----------|--------|
| `en` | English | LTR | Canonical (reference) |
| `de` | German | LTR | Fully supported |
| `fa` | Persian | RTL | Fully supported |

## File Naming Conventions

### Flat Structure

Place language-specific files directly in `data/cvs/`:

```
data/cvs/
├── ramin.json       # English (default, no suffix)
├── ramin_de.json    # German
├── ramin_fa.json    # Persian
└── ramin.en.json    # English (alternative naming)
```

### i18n Directory Structure

Organize by person in subdirectories:

```
data/cvs/i18n/
└── ramin/
    ├── cv.en.json   # English
    ├── cv.de.json   # German
    ├── cv.fa.json   # Persian
    └── lang.json    # Translation mapping
```

## Translation Mapping

Skill headings and categories can be translated using a `lang.json` file.

### Location

The mapping file can be placed at:

1. `data/cvs/i18n/<name>/lang.json` (per-person)
2. `data/cvs/lang.json` (shared)
3. `src/cv_generator/lang_engine/lang.json` (default)

### Format

```json
{
  "Technical Skills": {
    "de": "Technische Fähigkeiten",
    "fa": "مهارت‌های فنی"
  },
  "Programming": {
    "de": "Programmierung",
    "fa": "برنامه‌نویسی"
  },
  "Soft Skills": {
    "de": "Soft Skills",
    "fa": "مهارت‌های نرم"
  },
  "Communication": {
    "de": "Kommunikation",
    "fa": "ارتباطات"
  }
}
```

### Usage in Templates

The translation mapping is available as `LANG_MAP`:

```latex
<BLOCK> set translated = LANG_MAP.get(heading, {}).get(LANG, heading) </BLOCK>
{<VAR> translated | latex_escape </VAR>}
```

## RTL (Right-to-Left) Support

Persian (Farsi) is rendered with RTL text direction.

### How It Works

1. The generator sets `IS_RTL = True` for Persian
2. Templates can check this variable:
   ```latex
   <BLOCK> if IS_RTL </BLOCK>
     \setmainlanguage{farsi}
   <BLOCK> endif </BLOCK>
   ```

### Required Packages

For RTL support, ensure these LaTeX packages are installed:

- `polyglossia` — Multilingual support for XeLaTeX
- `bidi` — Bidirectional text
- `xepersian` — Persian typesetting (optional)

### Font Requirements

Use fonts with Persian glyph support:

- **Vazir** — Popular Persian font
- **Sahel** — Modern Persian font
- **XB Fonts** — Traditional Persian fonts

## Building Multilingual CVs

### Build All Languages

```bash
cvgen build --name ramin
```

This generates:
- `output/pdf/ramin/en/ramin_en.pdf`
- `output/pdf/ramin/de/ramin_de.pdf`
- `output/pdf/ramin/fa/ramin_fa.pdf`

### Build Specific Language

Filter by language suffix:

```bash
cvgen build --name ramin_de
```

## Validating Translations

Use `cvgen ensure` to verify consistency across language versions:

```bash
# Check all languages
cvgen ensure --name ramin

# Check specific languages
cvgen ensure --name ramin --langs en,de

# JSON output
cvgen ensure --name ramin --format json
```

### What It Checks

1. **Missing keys** — Fields present in English but missing in other languages
2. **Extra keys** — Fields in other languages not present in English
3. **Schema consistency** — Same structure across all versions
4. **Translation mapping** — All skill headings have translations

### Example Output

```
Found 3 issue(s):

=== Missing Keys/Paths ===
  [de] experiences[2].description (hint: Key 'description' missing in de version)

=== Extra Keys/Paths ===
  [fa] skills.Extra Category (found: Extra Category)

Summary: 2 missing, 1 extra, 0 schema errors, 0 mapping issues
```

## Creating a New Language Version

### Step 1: Copy the English Version

```bash
cp data/cvs/ramin.json data/cvs/ramin_fr.json
```

### Step 2: Translate Content

Edit the new file and translate:
- Job titles and descriptions
- Education details
- Skill descriptions
- Keep schema keys in English (`basics`, `education`, etc.)

### Step 3: Add Translation Mapping

Update `lang.json` with French translations:

```json
{
  "Technical Skills": {
    "de": "Technische Fähigkeiten",
    "fa": "مهارت‌های فنی",
    "fr": "Compétences Techniques"
  }
}
```

### Step 4: Update RTL List (if needed)

For RTL languages, add the code to `src/cv_generator/jinja_env.py`:

```python
RTL_LANGUAGES = {"fa", "ar", "he"}  # Add new RTL language codes
```

### Step 5: Test

```bash
cvgen build --name ramin_fr
cvgen ensure --name ramin --langs en,fr
```

## Best Practices

1. **English as canonical** — Keep English as the reference version
2. **Consistent structure** — All versions should have the same sections
3. **Keep keys in English** — Only translate values, not JSON keys
4. **Run validation** — Use `cvgen ensure` before generating
5. **Translation memory** — Maintain a shared `lang.json` for consistency
