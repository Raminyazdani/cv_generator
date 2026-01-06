# Templates

CV Generator uses Jinja2 templates with LaTeX to render CVs. This guide explains how templates work and how to customize them.

## Template Location

Templates are stored in the `templates/` directory:

```
templates/
├── layout.tex        # Main document structure
├── header.tex        # Personal info and social links
├── education.tex     # Education section
├── experience.tex    # Work experience
├── skills.tex        # Skills section
├── language.tex      # Language proficiencies
├── projects.tex      # Projects
├── certificates.tex  # Certifications
├── publications.tex  # Publications
└── references.tex    # References
```

## Template Syntax

Templates use custom Jinja2 delimiters to avoid conflicts with LaTeX:

| Jinja2 | Standard | CV Generator |
|--------|----------|--------------|
| Block | `{% %}` | `<BLOCK> </BLOCK>` |
| Variable | `{{ }}` | `<VAR> </VAR>` |
| Comment | `{# #}` | `/*/*/* */*/*/` |

### Example Template

```latex
<BLOCK> if education|length > 0 </BLOCK>
\cvsection{Education}
\begin{cventries}
<BLOCK> for edu in education </BLOCK>
  \cventry
    {<VAR> edu.studyType | latex_escape </VAR> in <VAR> edu.area | latex_escape </VAR>}
    {<VAR> edu.institution | latex_escape </VAR>}
    {<VAR> edu.location | latex_escape </VAR>}
    {<VAR> edu.startDate </VAR> – <VAR> edu.endDate </VAR>}
    {}
<BLOCK> endfor </BLOCK>
\end{cventries}
<BLOCK> endif </BLOCK>
```

## Available Filters

### latex_escape

Escapes LaTeX special characters to prevent compilation errors.

```latex
<VAR> text | latex_escape </VAR>
```

**Characters escaped:** `\`, `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`

### file_exists

Check if a file exists on disk.

```latex
<BLOCK> if "path/to/file.jpg" | file_exists </BLOCK>
  % Include the file
<BLOCK> endif </BLOCK>
```

### find_pic / get_pic

Check for and get profile picture paths.

```latex
<BLOCK> if OPT_NAME | find_pic </BLOCK>
  \photo[circle,noedge,left]{<VAR> OPT_NAME | get_pic </VAR>}
<BLOCK> endif </BLOCK>
```

### debug / types

Print debugging information during rendering.

```latex
<VAR> basics | debug </VAR>   /*/*/* Prints value to console */*/*/
<VAR> skills | types </VAR>   /*/*/* Prints type info */*/*/
```

### cmt / cblock

Emit LaTeX comments (controlled by `SHOW_COMMENTS` setting).

```latex
<VAR> "This is a comment" | cmt </VAR>
```

## Template Variables

### Built-in Variables

| Variable | Description |
|----------|-------------|
| `OPT_NAME` | Base name of the CV file (e.g., "ramin") |
| `BASE_NAME` | Same as OPT_NAME |
| `LANG` | Current language code (en, de, fa) |
| `IS_RTL` | True for RTL languages (fa) |
| `LANG_MAP` | Translation mapping dictionary |

### Data Variables

All top-level JSON keys become template variables:

```latex
<VAR> basics[0]["fname"] </VAR>     /*/*/* First name */*/*/
<VAR> education </VAR>               /*/*/* Education list */*/*/
<VAR> skills </VAR>                  /*/*/* Skills dictionary */*/*/
```

### Section Variables

Rendered sections are available for layout:

```latex
<VAR> header_section | default('') </VAR>
<VAR> education_section | default('') </VAR>
<VAR> experience_section | default('') </VAR>
```

## Main Layout

The `layout.tex` template is the root document:

```latex
\documentclass[11pt, a4paper]{./awesome-cv}

% Header from rendered section
<VAR> header_section | default('') </VAR>

\begin{document}
\makecvheader

% Include all sections
<VAR> education_section | default('') </VAR>
<VAR> experience_section | default('') </VAR>
<VAR> skills_section | default('') </VAR>
% ... more sections

\makecvfooter{\today}{Name~~~·~~~CV}{\thepage}
\end{document}
```

## Creating a New Section

### Step 1: Create the Template

Create `templates/volunteering.tex`:

```latex
<BLOCK> if volunteering is defined and volunteering|length > 0 </BLOCK>
\cvsection{Volunteering}
\begin{cventries}
<BLOCK> for vol in volunteering </BLOCK>
  \cventry
    {<VAR> vol.role | latex_escape </VAR>}
    {<VAR> vol.organization | latex_escape </VAR>}
    {<VAR> vol.location | latex_escape </VAR>}
    {<VAR> vol.duration </VAR>}
    {
      <BLOCK> if vol.description </BLOCK>
      \begin{cvitems}
        \item {<VAR> vol.description | latex_escape </VAR>}
      \end{cvitems}
      <BLOCK> endif </BLOCK>
    }
<BLOCK> endfor </BLOCK>
\end{cventries}
<BLOCK> endif </BLOCK>
```

### Step 2: Add to Layout

Edit `templates/layout.tex` to include the new section:

```latex
<VAR> volunteering_section | default('') </VAR>
```

### Step 3: Add JSON Data

Add the corresponding data to your CV JSON:

```json
{
  "volunteering": [
    {
      "organization": "Local Food Bank",
      "role": "Volunteer Coordinator",
      "location": "San Francisco, CA",
      "duration": "2020 – Present",
      "description": "Organizing weekly food distribution events"
    }
  ]
}
```

## RTL Support

For right-to-left languages (Persian), the `IS_RTL` variable is set to `True`:

```latex
<BLOCK> if IS_RTL </BLOCK>
\usepackage{polyglossia}
\setmainlanguage{farsi}
\setotherlanguage{english}
<BLOCK> endif </BLOCK>
```

## Translation Mapping

Skill headings can be translated using `LANG_MAP`:

```latex
<BLOCK> set heading_translated = LANG_MAP.get(heading, {}).get(LANG, heading) </BLOCK>
<VAR> heading_translated | latex_escape </VAR>
```

The mapping is defined in `project/src/cv_generator/lang_engine/lang.json`:

```json
{
  "Technical Skills": {
    "de": "Technische Fähigkeiten",
    "fa": "مهارت‌های فنی"
  }
}
```

## Debugging Templates

### Use verbose mode

```bash
cvgen -v build --dry-run
```

### Keep LaTeX files

```bash
cvgen build --keep-latex
```

Then inspect `output/latex/<name>/<lang>/main.tex`.

### Use debug filter

```latex
<VAR> skills | debug </VAR>
```

This prints the value to the console during rendering.

## Awesome-CV Reference

CV Generator uses the [Awesome-CV](https://github.com/posquit0/Awesome-CV) LaTeX class. Key macros:

| Macro | Description |
|-------|-------------|
| `\cvsection{Title}` | Section heading |
| `\begin{cventries}` | Entry container |
| `\cventry{...}` | Individual entry |
| `\begin{cvitems}` | Bullet list |
| `\cvskill{Category}{Skills}` | Skill line |
| `\name{First}{Last}` | Name display |
| `\position{Title}` | Job title |
| `\makecvheader` | Render header |
| `\makecvfooter{L}{C}{R}` | Render footer |

See the [Awesome-CV documentation](https://github.com/posquit0/Awesome-CV) for more details.
