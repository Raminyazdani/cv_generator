---
applyTo: "templates/**/*.tex"
---

# UI Rendering Instructions (LaTeX Templates)

## Overview

These templates use Jinja2 with custom delimiters for LaTeX compatibility.

## Jinja2 Delimiters

- **Blocks**: `<BLOCK> ... </BLOCK>` (instead of `{% %}`)
- **Variables**: `<VAR> ... </VAR>` (instead of `{{ }}`)
- **Comments**: `/*/*/* ... */*/*/`

## Essential Filters

- `| latex_escape` - Escape LaTeX special characters (ALWAYS use for user content)
- `| default('')` - Provide fallback for missing values
- `| debug` - Print value to console for debugging
- `| cmt` - Emit LaTeX comment (gated by SHOW_COMMENTS)

## Preventing Undefined/Empty Sections

### Check Before Rendering
```latex
<BLOCK> if education|length > 0 </BLOCK>
\cvsection{Education}
% render education items
<BLOCK> endif </BLOCK>
```

### Always Use Default Filter
```latex
<VAR> basics[0].get('summary', '') | latex_escape </VAR>
```

### Handle Optional Nested Data
```latex
<BLOCK> if profile.get('uuid') </BLOCK>
\googlescholar{<VAR> profile.uuid </VAR>}{<VAR> profile.username </VAR>}
<BLOCK> endif </BLOCK>
```

## Common Issues and Fixes

### Issue: "undefined" Appears in Output
**Cause**: Template references non-existent key
**Fix**: Add `| default('')` or check existence with `<BLOCK> if key </BLOCK>`

### Issue: Empty Section Heading Appears
**Cause**: Section renders heading but no content
**Fix**: Wrap entire section in length check

### Issue: LaTeX Compilation Error
**Cause**: Special characters not escaped
**Fix**: Apply `| latex_escape` to all user-generated content

## Section Template Structure

Each section template should follow this pattern:
```latex
<BLOCK> if section_data|length > 0 </BLOCK>
\cvsection{Section Title}
<BLOCK> for item in section_data </BLOCK>
% render item safely with escape filters
<BLOCK> endfor </BLOCK>
<BLOCK> endif </BLOCK>
```
