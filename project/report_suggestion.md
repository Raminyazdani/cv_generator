# report_suggestion.md

## Executive Summary

This report provides a comprehensive analysis and actionable strategies for implementing a robust multilingual workflow in your CV/PDF generator repository. The repository currently maintains CV data in JSON files across three languages (English, German, Farsi) with differing key structures, creating synchronization and maintenance challenges.

**Key Challenges Identified:**
1. **Sync Issues**: Changes to `ramin.json` (English) must be manually replicated to `ramin_de.json` and `ramin_fa.json`
2. **Key Translation**: German and Farsi versions use translated keys (e.g., `grunddaten` vs `basics`), breaking template compatibility
3. **Hardcoded PDF Strings**: Templates contain hardcoded English labels like `\cvsection{Education}`
4. **Template/Schema Management**: Need for `empty.json` and `minimal.json` as schema templates
5. **Script Issues**: `make_translate_csv.py` exists but doesn't fully support the multilingual workflow

**Core Recommendation:**
Adopt a **single-source-of-truth** approach with English keys and overlay-based value translation. This provides the best balance of maintainability, template compatibility, and localization flexibility. Ten distinct strategies are presented below, ranging from quick stabilization to full automation.

**Extensibility Principle:**
All strategies are designed to be **language-agnostic and scalable**. Adding a new language (e.g., Italian, Spanish, French) should require only:
- Adding new locale files / translation overlays / mapping tables
- No template modifications
- No structural changes to the source JSON
- Automated validation to ensure completeness

---

## What I Understand About Your Repo and Problems

### Repository Structure
- **CV Data**: `data/cvs/*.json` containing structured CV data
  - `ramin.json` — English (main source)
  - `ramin_de.json` — German (translated keys + values)
  - `ramin_fa.json` — Farsi/Persian (translated keys + values, RTL language)
  - `mahsa.json` — Another English CV
  
- **Templates**: `templates/*.tex` (Jinja2-based LaTeX templates)
  - Using custom Jinja2 delimiters (`<VAR>`, `<BLOCK>`)
  - Templates reference English keys like `basics`, `education`, `skills`
  - Section headings are hardcoded in English (e.g., `\cvsection{Education}`)

- **Generation Script**: `generate_cv.py`
  - Iterates over all JSON files in `data/cvs/`
  - Uses Jinja2 with StrictUndefined for template rendering
  - Compiles LaTeX via XeLaTeX

- **Helper Script**: `scripts/make_translate_csv.py`
  - Intended for generating `empty.json` and `minimal.json`
  - Contains logic for anonymizing/trimming but not for translation management

### Current Pain Points

1. **Translated Keys Break Templates**
   - German version uses `grunddaten` instead of `basics`, `ausbildung` instead of `education`
   - Farsi version uses `اطلاعات_پایه` instead of `basics`, `تحصیلات` instead of `education`
   - Templates only recognize English keys, causing render failures

2. **Manual Sync Burden**
   - Adding a new job/project to `ramin.json` requires manual addition to DE/FA versions
   - Risk of versions drifting out of sync
   - No tooling to detect or report sync drift

3. **Hardcoded English in PDFs**
   - Template section titles: `\cvsection{Education}`, `\cvsection{Skills}`
   - Footer text: `Curriculum Vitae`
   - These render in English regardless of JSON language

4. **Missing Schema Artifacts**
   - `empty.json` and `minimal.json` in `example/` exist but may not reflect current schema
   - No automated schema validation

5. **RTL Support for Farsi**
   - XeLaTeX needs specific configuration for RTL languages
   - Font selection critical for Persian text rendering

---

## Success Criteria (What "Good" Looks Like)

A successful multilingual workflow should achieve:

1. **Single Source of Truth**: Changes made once, propagated automatically or semi-automatically
2. **Template Compatibility**: All language variants work with the same templates
3. **Localized Output**: PDFs display correctly translated section headers, labels, and content
4. **Minimal Manual Effort**: Translation updates are isolated, not requiring full re-entry
5. **Change Tracking**: Ability to detect when source EN content has changed vs. translations
6. **Schema Consistency**: `empty.json` and `minimal.json` auto-generated from source
7. **RTL/Font Support**: Farsi PDFs render correctly with proper direction and fonts
8. **Validation**: CI/CD checks that all language files are structurally valid
9. **Extensibility**: Easy to add new languages (e.g., French, Spanish, Italian) with minimal effort
10. **Developer Experience**: Clear documentation on how to update content and translations
11. **Language-Agnostic Design**: Adding a 4th, 5th, or Nth language requires only new locale files—no template or schema changes

---

## Core Decision: Should JSON Keys Be Translated?

### The Tradeoff

| Approach | Pros | Cons |
|----------|------|------|
| **Keep Keys in English** | Templates work universally; merging/diff is trivial; tooling is simpler | Harder for non-English maintainers to read JSON directly |
| **Translate Keys** | JSON files are "native" to each language; feels complete | Templates must be duplicated or mapped; sync is complex; merge conflicts in keys |

### Recommendation: Keep Keys in English

For a technical workflow where JSON is processed by code (not directly shown to end users), English keys provide:
- Consistent template compatibility
- Easier programmatic access
- Standard tooling (JSON Schema, linters)
- Simpler sync/diff workflows

### If Keys MUST Be Translated (Fallback Approach)

Use a **key mapping table** at export/render time:

```python
KEY_MAP = {
    "de": {
        "basics": "grunddaten",
        "education": "ausbildung",
        "skills": "faehigkeiten",
        ...
    },
    "fa": {
        "basics": "اطلاعات_پایه",
        "education": "تحصیلات",
        ...
    }
}
```

At generation time:
1. Load source JSON with English keys
2. Apply key mapping to produce language-specific keys
3. Export the transformed JSON (for archival if needed)
4. Templates still use English keys internally

This provides the "translated keys" aesthetic while maintaining template compatibility.

---

## 10 Practical Strategies (Implementation-Ready)

### Strategy 1: Canonical English Keys with Value Overlays

**Idea**

Maintain a single `ramin.json` with English keys and values. Create lightweight overlay files (`ramin.de.values.json`, `ramin.fa.values.json`) that contain only translated values, keyed by a unique path or ID.

**How it Works (Step-by-step)**

1. Define a stable ID or JSONPath for each translatable string in the source
2. Create overlay files structured as `{ "path.to.field": "translated value" }`
3. At generation time, merge base + overlay to produce translated content
4. Templates receive English keys with translated values

**How it Handles Value Translation**

Overlay files contain only translatable strings, making translation updates isolated and diff-friendly.

**How it Handles Key Translation**

Keys remain in English everywhere. If translated key export is needed, apply key mapping as a final step.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

- Add a `version` or `lastModified` field to source JSON
- Script compares overlay timestamps to source
- Report which translations are stale

**How it Impacts empty.json & minimal.json**

Generate from source `ramin.json` automatically:
- `empty.json`: Replace all leaf strings with `""`
- `minimal.json`: Keep first item in arrays, apply anonymization

**How it Fixes Hardcoded English in PDFs**

Create a `ui_strings.json` per language:
```json
{
  "section_education": "Bildung",
  "section_skills": "Fähigkeiten",
  "footer_cv": "Lebenslauf"
}
```
Templates use: `<VAR> ui.section_education </VAR>`

**Pros**

- Minimal structural change to existing workflow
- Clear separation of concerns
- Translations can be delegated to non-technical translators

**Cons / Risks**

- Requires building a merge script
- Paths may change if JSON structure evolves

**When to Choose This**

Best for teams wanting to minimize refactoring while gaining sync benefits.

**Acceptance Checks (How to verify it works)**

- [ ] Overlays merge correctly with base
- [ ] German PDF shows German content
- [ ] Adding new field to source flags overlay as outdated
- [ ] Templates render without StrictUndefined errors

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Create `ramin.it.values.json` overlay file with Italian translations |
| **UI Strings** | Add `it` section to `ui_strings.json` |
| **Key Map** | None needed—keys remain English |
| **Templates** | No changes required—templates are language-agnostic |
| **Schema** | No changes—schema validates structure, not language |
| **Generator** | Add `"it"` to `SUPPORTED_LANGUAGES` list (one-line change) |

**Completeness Checks for New Language**
- Schema parity: Overlay must have entries for all translatable paths in source
- Missing translations: `translation_diff.py --lang it` reports gaps
- Template token coverage: All `<VAR> ui.* </VAR>` tokens have Italian values

---

### Strategy 2: Monolingual JSONs with Key Normalization Script

**Idea**

Keep current separate JSON files (`ramin_de.json`, `ramin_fa.json`) but add a normalization layer that translates keys to English before template rendering.

**How it Works (Step-by-step)**

1. Create `key_map.json` defining language-specific keys → English keys
2. Pre-process each JSON through a `normalize_keys.py` script
3. Output normalized JSON with English keys
4. Feed normalized JSON to existing templates

**How it Handles Value Translation**

Values stay as-is (already translated in source files).

**How it Handles Key Translation**

Key mapping is explicit and centralized. Script recursively walks JSON and renames keys.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

- Manual sync still required for values
- Can add a `diff_structures.py` script to compare shape of EN vs DE/FA

**How it Impacts empty.json & minimal.json**

Generate from English source, then optionally produce localized key versions.

**How it Fixes Hardcoded English in PDFs**

Same as Strategy 1: introduce `ui_strings.json` loaded into template context.

**Pros**

- Minimal change to existing translated JSONs
- Keeps translated keys for "native" readability

**Cons / Risks**

- Key map must be maintained manually
- Sync of values still manual

**When to Choose This**

Good if you've already invested heavily in translated-key JSONs and don't want to restructure.

**Acceptance Checks (How to verify it works)**

- [ ] Normalized DE/FA JSONs pass template rendering
- [ ] Key map covers all nested keys
- [ ] No StrictUndefined errors

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Create `ramin_it.json` with Italian content (translated keys allowed) |
| **Key Map** | Add `"it": { "basics": "dati_base", ... }` to `key_map.json` |
| **UI Strings** | Add Italian UI strings section |
| **Templates** | No changes—normalization handles key translation |
| **Schema** | No changes—validates post-normalization structure |
| **Generator** | Detect `_it.json` suffix, apply Italian key map |

**Completeness Checks for New Language**
- Key map completeness: All keys in source have Italian mappings (or use English fallback)
- Structure validation: Normalized Italian JSON matches schema
- Missing keys: Diff tool compares Italian structure to English source

---

### Strategy 3: i18n-Style Value Extraction

**Idea**

Extract all translatable strings into a classic i18n structure (like gettext `.po` files or JSON message catalogs), keeping the source JSON as a skeleton with translation keys.

**How it Works (Step-by-step)**

1. Define translation keys for all user-visible strings: `"edu.0.institution": "t:edu_0_institution"`
2. Create `messages/en.json`, `messages/de.json`, `messages/fa.json` with:
   ```json
   { "edu_0_institution": "University of Tehran" }
   ```
3. At render time, resolve translation keys to values based on target language
4. Templates receive fully resolved data

**How it Handles Value Translation**

All values are externalized to message catalogs. Professional translation tools (Crowdin, Phrase, Lokalise) can ingest these directly.

**How it Handles Key Translation**

Keys in skeleton JSON are always English. Output keys can be mapped if needed.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Adding a new entry to skeleton requires adding corresponding keys to all message catalogs. CI can validate completeness.

**How it Impacts empty.json & minimal.json**

- `empty.json`: Skeleton with translation keys
- `minimal.json`: Skeleton with first-item arrays and translation keys

**How it Fixes Hardcoded English in PDFs**

UI strings live in message catalogs too: `"ui.section_education": "Bildung"`

**Pros**

- Industry-standard approach
- Professional translation tooling integration
- Clear separation of structure and content

**Cons / Risks**

- Major refactor of existing JSON structure
- More complex build pipeline
- Loss of "readable" JSON without tool support

**When to Choose This**

Best for teams planning to scale to many languages or integrate with professional translation services.

**Acceptance Checks (How to verify it works)**

- [ ] Skeleton + messages produce valid CV
- [ ] Missing translation keys cause clear errors
- [ ] Translation tool can import/export catalogs

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Create `messages/it.json` with all translation keys |
| **Skeleton** | No changes—skeleton uses translation key references |
| **Templates** | No changes—templates are language-agnostic |
| **Schema** | No changes—schema defines skeleton structure |
| **Generator** | Add `"it"` to language list; message loader handles automatically |
| **Translation Tools** | Export `it.json` to Crowdin/Phrase for professional translation |

**Completeness Checks for New Language**
- Key completeness: `it.json` must have every key present in `en.json`
- CI validation: `check_messages.py --lang it` fails if keys missing
- Format validation: Ensure placeholders (`{name}`, `{date}`) are preserved

---

### Strategy 4: Per-Field Language Embedding

**Idea**

Embed all translations inline within each field:
```json
{
  "institution": {
    "en": "University of Tehran",
    "de": "Universität Teheran",
    "fa": "دانشگاه تهران"
  }
}
```

**How it Works (Step-by-step)**

1. Restructure JSON so every translatable field is an object with language keys
2. Generator selects appropriate language at render time
3. Non-translatable fields (URLs, dates) remain simple values

**How it Handles Value Translation**

All translations live together, making it clear what's translated.

**How it Handles Key Translation**

Keys remain in English. Language selection is value-level only.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Single file contains all languages—adding new content requires adding all translations immediately.

**How it Impacts empty.json & minimal.json**

- `empty.json`: `{ "en": "", "de": "", "fa": "" }` for each field
- `minimal.json`: All languages present with minimal content

**How it Fixes Hardcoded English in PDFs**

Section titles follow same pattern:
```json
{
  "ui": {
    "section_education": { "en": "Education", "de": "Bildung", "fa": "تحصیلات" }
  }
}
```

**Pros**

- All languages in one file—impossible to miss a translation
- No external files to coordinate

**Cons / Risks**

- JSON becomes verbose (3x content)
- Harder to delegate translation to non-technical users
- Merge conflicts more likely

**When to Choose This**

Good for small teams where one person maintains all languages and wants single-file simplicity.

**Acceptance Checks (How to verify it works)**

- [ ] Generator correctly extracts target language
- [ ] Missing language gracefully falls back to EN
- [ ] JSON remains valid and readable

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | None—add `"it": "..."` to each field in existing JSON |
| **Templates** | No changes—generator passes selected language value |
| **Schema** | Update to require/allow `it` key in language objects |
| **Generator** | Add `"it"` to `SUPPORTED_LANGUAGES`; extraction logic unchanged |
| **Fallback** | Define fallback chain: `it` → `en` if Italian missing |

**Completeness Checks for New Language**
- Field coverage: Script scans all translatable fields for `it` key
- Fallback report: List which fields are using English fallback
- Schema validation: Ensure `it` key is valid per updated schema

**Scalability Note**
This strategy becomes unwieldy beyond 4-5 languages as JSON size grows proportionally. Consider migration to Strategy 1 or 3 at that point.

---

### Strategy 5: Modular Section Files with Language Suffixes

**Idea**

Split monolithic JSON into section files: `education.en.json`, `education.de.json`, `skills.en.json`, etc. Assemble at generation time.

**How it Works (Step-by-step)**

1. Create `data/sections/{section}.{lang}.json` for each section and language
2. Loader script collects all sections for target language
3. Merge into unified data object for templates
4. Source of truth: `.en.json` files; translations: `.de.json`, `.fa.json`

**How it Handles Value Translation**

Each section file contains translated values. Translators can work on isolated files.

**How it Handles Key Translation**

All section files use English keys. Language is encoded in filename, not keys.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

- Compare `.en.json` structure to `.de.json`, `.fa.json` for each section
- Report missing or extra keys

**How it Impacts empty.json & minimal.json**

Generate from assembled English sections.

**How it Fixes Hardcoded English in PDFs**

Add `ui.en.json`, `ui.de.json` for template strings.

**Pros**

- Parallelizable translation work
- Small, focused files
- Clear ownership per section

**Cons / Risks**

- More files to manage
- Assembly logic adds complexity

**When to Choose This**

Good for larger CVs or multi-person teams wanting to parallelize.

**Acceptance Checks (How to verify it works)**

- [ ] Assembly produces complete CV
- [ ] Missing section file causes clear error
- [ ] Adding new section requires only new files

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Create `*.it.json` for each section: `education.it.json`, `skills.it.json`, etc. |
| **UI Strings** | Add `ui.it.json` for template labels |
| **Templates** | No changes—templates are language-agnostic |
| **Schema** | No changes—each section file validates against section schema |
| **Generator** | Language detection from filename suffix; assembly logic unchanged |
| **Directory** | Consider `data/sections/it/` subdirectory for organization |

**Completeness Checks for New Language**
- File parity: Every `.en.json` section must have corresponding `.it.json`
- Structure match: Italian section files have same keys as English
- CI check: `check_sections.py --lang it` reports missing section files

---

### Strategy 6: Git Submodule for Translations

**Idea**

Store translations in a separate Git repository, imported as a submodule. Source remains in main repo.

**How it Works (Step-by-step)**

1. Create `cv_translations` repo with overlay/message files
2. Add as submodule: `git submodule add ... translations/`
3. CI/build merges `translations/` with source data
4. Translators work in dedicated repo with their own branch/PR workflow

**How it Handles Value Translation**

Translation repo contains only translated values (overlays or message catalogs).

**How it Handles Key Translation**

Not affected—keys live in main repo, always English.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

- Main repo: bump version on schema changes
- Translation repo: CI validates compatibility with main repo version

**How it Impacts empty.json & minimal.json**

Generated in main repo from source schema.

**How it Fixes Hardcoded English in PDFs**

UI strings live in translation repo.

**Pros**

- Clean separation of concerns
- Translation team can have independent review process
- Main repo stays small

**Cons / Risks**

- Submodule complexity
- Must coordinate version dependencies

**When to Choose This**

Best for organizations with dedicated translation teams or multi-repo workflows.

**Acceptance Checks (How to verify it works)**

- [ ] Submodule update pulls latest translations
- [ ] Build fails gracefully if submodule missing
- [ ] Translation repo can be updated independently

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Add `it/` directory in translation submodule with overlays/messages |
| **Main Repo** | No changes—submodule contains all language files |
| **Templates** | No changes—templates are language-agnostic |
| **Schema** | No changes—lives in main repo |
| **Translation Repo** | Add Italian translator to repo contributors |
| **CI** | Version compatibility check includes Italian |

**Completeness Checks for New Language**
- Directory structure: `translations/it/` exists with required files
- Version compatibility: Italian files match main repo schema version
- PR validation: Translation repo CI validates Italian completeness

---

### Strategy 7: JSON Schema + Validation Pipeline

**Idea**

Define a JSON Schema for CV structure. Use schema to auto-generate `empty.json`, validate all language variants, and detect drift.

**How it Works (Step-by-step)**

1. Create `cv_schema.json` defining all required/optional fields, types
2. Use `jsonschema` Python package or `ajv` CLI for validation
3. `empty.json`: Generate from schema with empty values
4. `minimal.json`: Generate from schema with `examples` field data
5. CI validates all CVs against schema

**How it Handles Value Translation**

Schema doesn't translate—it validates structure. Values come from overlays or inline.

**How it Handles Key Translation**

Schema defines canonical (English) keys. Validation ensures all variants match.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Schema evolution triggers validation failures if language files don't match.

**How it Impacts empty.json & minimal.json**

Auto-generated from schema—always current.

**How it Fixes Hardcoded English in PDFs**

Schema can include `ui` section with required keys for section titles.

**Pros**

- Single source of truth for structure
- Auto-generated artifacts
- CI-enforced consistency

**Cons / Risks**

- Initial effort to create comprehensive schema
- Schema maintenance overhead

**When to Choose This**

Essential for any serious implementation—combine with other strategies.

**Acceptance Checks (How to verify it works)**

- [ ] Schema validates current `ramin.json`
- [ ] Invalid JSON produces clear schema errors
- [ ] `empty.json` regenerates correctly

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | None for schema itself; Italian translation files per chosen strategy |
| **Schema** | No changes—schema is language-agnostic (defines structure, not content) |
| **Templates** | No changes—schema doesn't affect templates |
| **Validation** | Add Italian files to validation target list |
| **empty.json** | No changes—generated from schema |
| **minimal.json** | No changes—generated from schema |

**Completeness Checks for New Language**
- Schema validation: Italian CV JSON passes schema validation
- Structure parity: Italian has same required fields as schema demands
- UI schema: If UI strings have schema, Italian must satisfy it

**Extensibility Design Principle**
Schema should define:
- Required vs optional fields
- Field types and formats
- No language-specific content (that goes in overlays/messages)

---

### Strategy 8: Template-Level Language Switching

**Idea**

Make templates language-aware: pass language code and let templates select appropriate strings from a lookup table embedded in the template or passed in context.

**How it Works (Step-by-step)**

1. Define `UI_STRINGS` dict in generator script per language
2. Pass `lang` and `ui` variables to template context
3. Templates use: `\cvsection{<VAR> ui.education </VAR>}`
4. No changes to JSON structure required

**How it Handles Value Translation**

JSON values still need translation via overlay or separate files.

**How it Handles Key Translation**

Not applicable—templates use UI lookup.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Doesn't address data sync directly—only UI strings.

**How it Impacts empty.json & minimal.json**

No direct impact.

**How it Fixes Hardcoded English in PDFs**

Primary purpose—moves all hardcoded strings to configurable lookups.

**Pros**

- Quick win for PDF localization
- Minimal structural change

**Cons / Risks**

- Only solves UI strings, not data sync

**When to Choose This**

Immediate fix for hardcoded English while planning broader strategy.

**Acceptance Checks (How to verify it works)**

- [ ] German PDF shows "Bildung" instead of "Education"
- [ ] Adding new UI string is straightforward
- [ ] Missing UI key causes clear error

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | Add `"it": { "education": "Istruzione", ... }` to `ui_strings.json` |
| **Templates** | No changes—templates use `<VAR> ui.{key} </VAR>` pattern |
| **Generator** | Language selection already parameterized; works automatically |
| **Schema** | Optionally validate that `ui_strings.json` has all required keys per language |

**Completeness Checks for New Language**
- Key coverage: Italian section has every key present in English section
- Template scan: All `<VAR> ui.* </VAR>` tokens have Italian values
- Runtime check: Generator fails fast if UI key missing for target language

**UI Strings Structure (Language-Agnostic)**
```json
{
  "en": { "education": "Education", "skills": "Skills", ... },
  "de": { "education": "Bildung", "skills": "Fähigkeiten", ... },
  "fa": { "education": "تحصیلات", "skills": "مهارت‌ها", ... },
  "it": { "education": "Istruzione", "skills": "Competenze", ... }
}
```
Adding a language = adding one new object with all keys.

---

### Strategy 9: Automated Translation Diff Tool

**Idea**

Build a CLI tool that compares source JSON structure to translation files and generates a diff/report of what needs translation.

**How it Works (Step-by-step)**

1. `python scripts/translation_diff.py --source ramin.json --target ramin_de.json`
2. Tool walks both JSONs, comparing structure and optionally content hashes
3. Output: list of missing keys, new keys, changed values
4. Can generate stub overlay file for missing translations

**How it Handles Value Translation**

Identifies which values are missing or stale.

**How it Handles Key Translation**

If using key normalization, runs after normalization.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Core purpose—provides visibility into sync status.

**How it Impacts empty.json & minimal.json**

Can verify these match current schema.

**How it Fixes Hardcoded English in PDFs**

Include UI strings in diff check.

**Pros**

- Visibility without mandating specific structure
- Works with existing files
- Gradual adoption

**Cons / Risks**

- Manual action still required to fix diffs
- Doesn't prevent drift, only detects it

**When to Choose This**

Good first step before larger refactoring.

**Acceptance Checks (How to verify it works)**

- [ ] Tool correctly identifies missing translations
- [ ] Changed source values flagged as needing update
- [ ] CI can fail on unaddressed diffs

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **New Artifacts** | None for the tool itself |
| **Tool Usage** | `python scripts/translation_diff.py --lang it` |
| **Config** | Add `it` to `SUPPORTED_LANGUAGES` in diff tool config |
| **Templates** | No changes—tool operates on data files |
| **Output** | Generate stub Italian translation file from diff output |

**Completeness Checks for New Language**
- Run diff against empty Italian file to get full translation task list
- Track percentage complete: `--lang it --summary` shows 0/N translated
- Generate stub: `--lang it --generate-stub` creates placeholder file

**Tool Design for Scalability**
```bash
# Check all languages at once
python translation_diff.py --all

# Output format includes language code
[de] Missing: education[2].description
[fa] Missing: education[2].description  
[it] Missing: education[0].institution (and 847 more)
```

---

### Strategy 10: CI/CD-Enforced Translation Workflow

**Idea**

Integrate translation validation into CI pipeline. PRs that modify source JSON must include translation updates or be flagged.

**How it Works (Step-by-step)**

1. Add GitHub Action / GitLab CI step: `validate-translations`
2. On PR: detect changes to `ramin.json`
3. Run translation diff tool against DE/FA files
4. If diff exists without corresponding translation updates, mark check as failed
5. Provide clear instructions in check output

**How it Handles Value Translation**

Enforces that translations stay current.

**How it Handles Key Translation**

Works with whatever key strategy is chosen.

**How it Solves Sync/Change Tracking (ramin.json → de/fa)**

Prevents merging out-of-sync PRs.

**How it Impacts empty.json & minimal.json**

Can include schema generation and validation in CI.

**How it Fixes Hardcoded English in PDFs**

UI string completeness can be part of CI check.

**Pros**

- Systematic enforcement
- Shift-left—catch issues before merge
- Clear feedback loop

**Cons / Risks**

- Blocks PRs—may slow development
- Requires good diff tooling

**When to Choose This**

After establishing translation workflow, add CI enforcement for discipline.

**Acceptance Checks (How to verify it works)**

- [ ] PR with source changes but no translations fails CI
- [ ] PR with complete translations passes
- [ ] Error messages guide user to fix

**Adding a 4th Language (e.g., Italian)**

| Aspect | What to Do |
|--------|------------|
| **CI Config** | Add `it` to `REQUIRED_LANGUAGES` in workflow file |
| **New Artifacts** | Create initial Italian translation files (can be stubs) |
| **Templates** | No changes—CI validates data, not templates |
| **Workflow** | Same PR validation applies to Italian |
| **Exceptions** | Optional: Allow `[skip-it]` in commit message during bootstrap |

**Completeness Checks for New Language**
- CI matrix includes Italian in validation languages
- Bootstrap process: Initial commit with stub Italian files
- Graduation: Remove stub allowance once Italian is complete

**Scalable CI Design**
```yaml
# .github/workflows/validate-translations.yml
jobs:
  validate:
    strategy:
      matrix:
        lang: [de, fa, it, es, fr]  # Easy to extend
    steps:
      - run: python scripts/translation_diff.py --lang ${{ matrix.lang }} --fail-on-missing
```

Adding a language = one line in the matrix + initial translation files.

---

## Recommended Path (A Doable Plan)

### Extensibility-First Design Principles

Before implementing any phase, ensure these design principles are followed:

1. **Language as Parameter**: Never hardcode language-specific logic; use configuration/data files
2. **Convention over Configuration**: Establish naming patterns (e.g., `*.{lang}.json`) that scale automatically
3. **Single Registration Point**: Adding a language should require updating only one config file/list
4. **Graceful Degradation**: Missing translations should fall back to English, not crash
5. **Self-Documenting**: Config files should list all supported languages with metadata

### Phase 1: Quick Stabilization (1-2 weeks)

**Goal**: Get current templates working with all three language files.

1. **Implement Key Normalization (Strategy 2)**
   - Create `key_map.json` for DE and FA
   - Add `normalize_keys.py` script
   - Modify `generate_cv.py` to normalize before rendering

2. **Implement Template UI Strings (Strategy 8)**
   - Create `ui_strings.json` for EN/DE/FA
   - Update templates to use `<VAR> ui.section_name </VAR>`
   - Add `ui` to template context

3. **Fix Farsi RTL/Fonts**
   - Add XeLaTeX RTL package configuration for FA
   - Test with appropriate Persian fonts

**Deliverables**: All three CVs render correctly in PDF.

### Phase 2: Proper Multilingual Workflow (2-4 weeks)

**Goal**: Establish sustainable sync mechanism.

1. **Define JSON Schema (Strategy 7)**
   - Create `cv_schema.json` from current structure
   - Validate all existing JSONs against schema
   - Auto-generate `empty.json` and `minimal.json`

2. **Implement Value Overlays (Strategy 1)**
   - Restructure to single `ramin.json` source
   - Create `ramin.de.overlay.json` and `ramin.fa.overlay.json`
   - Build merge script in `generate_cv.py`

3. **Build Translation Diff Tool (Strategy 9)**
   - Create `scripts/translation_diff.py`
   - Document workflow for updating translations

**Deliverables**: Single source of truth with overlay-based translations; schema-validated structure.

### Phase 3: Automation/CI Hardening (2-3 weeks)

**Goal**: Prevent drift and automate validation.

1. **Add CI Translation Checks (Strategy 10)**
   - GitHub Action to validate translation completeness
   - Fail PR if source changes without translation updates

2. **Auto-generate Schema Artifacts**
   - CI generates `empty.json`, `minimal.json` on source changes
   - Commit back to repo or publish as release artifacts

3. **Documentation**
   - Write CONTRIBUTING.md section on translation workflow
   - Create translation guide for non-technical contributors

**Deliverables**: Fully automated validation pipeline; documented workflow.

### Adding a New Language: Standard Procedure

Once the recommended workflow is implemented, adding a new language (e.g., Italian) follows this procedure:

**Step 1: Register the Language (5 minutes)**
```python
# config/languages.json
{
  "supported": ["en", "de", "fa", "it"],  # Add "it"
  "default": "en",
  "rtl": ["fa", "ar", "he"],  # RTL languages for future
  "metadata": {
    "it": {
      "name": "Italian",
      "native_name": "Italiano",
      "font_family": "default",
      "date_format": "DD/MM/YYYY"
    }
  }
}
```

**Step 2: Create Translation Artifacts (Translation Team)**
- `ramin.it.overlay.json` — Value translations for CV content
- `ui_strings.json` — Add Italian section with all UI keys

**Step 3: Validation (Automatic)**
- CI runs translation diff tool
- Reports missing translations
- Generates completeness percentage

**Step 4: PDF Configuration (If Special Needs)**
- For RTL languages: Add to `rtl` list
- For special fonts: Specify in metadata
- For special date formats: Configure in metadata

**What Does NOT Change**
- Templates (zero modifications)
- Schema (structure-only, language-agnostic)
- Generator core logic (parameterized by language)
- Source `ramin.json` (single source of truth)
- Other language files (isolated by design)

**Estimated Effort to Add a Language**
| Task | Time | Who |
|------|------|-----|
| Register language | 5 min | Developer |
| Create overlay stub | 10 min | Developer |
| Add UI strings | 30 min | Developer |
| Translate CV content | 2-4 hours | Translator |
| Review & test PDF | 30 min | Developer |
| **Total** | **3-5 hours** | |

### Minimum Changes for Quick Value

If time is very limited, do only:
1. **UI Strings (Strategy 8)** - 2-4 hours
2. **Key Normalization (Strategy 2)** - 4-8 hours

This gets PDFs rendering in all languages with minimal structural change.

---

## Common Gotchas (German + Farsi + PDF)

### RTL (Right-to-Left) for Farsi

- **XeLaTeX Packages**: Use `polyglossia` with `\setmainlanguage{persian}` or `bidi` package
- **Font Selection**: Farsi requires fonts with Persian glyphs (e.g., Vazir, IranSans, XB Zar)
- **Mixed Content**: When mixing English and Farsi, use `\LR{...}` and `\RL{...}` macros
- **Text Direction**: Ensure `\begin{RTL}` wrapping for Farsi sections

### Fonts for German

- **Umlauts**: Ensure font supports ä, ö, ü, ß (most modern fonts do)
- **XeLaTeX**: Use `fontspec` package with Unicode fonts
- **Fallback**: Always test with actual German content (umlauts, eszett)

### Date Formats

| Language | Format | Example |
|----------|--------|---------|
| English | YYYY-MM-DD or "Month YYYY" | "2024-09-15" or "September 2024" |
| German | DD.MM.YYYY or "Monat YYYY" | "15.09.2024" or "September 2024" |
| Farsi | YYYY/MM/DD (Solar Hijri) | "1403/06/25" |

Consider adding a date formatter filter in templates.

### Unicode and Encoding

- **JSON**: Always use UTF-8 encoding with `encoding="utf-8"` in Python file ops
- **LaTeX**: Use `\usepackage[utf8]{inputenc}` (pdflatex) or ensure XeLaTeX (handles UTF-8 natively)
- **Special Characters**: Test with actual content including RTL markers, zero-width joiners

### Template Alignment

- **Column Widths**: RTL text may affect table column calculations
- **Photo Position**: May need mirroring for RTL layout
- **Headers/Footers**: Ensure language-appropriate ordering

### Hyphenation

- **German**: Use `\hyphenation{Deut-sche}` or `babel`/`polyglossia` for automatic hyphenation
- **Farsi**: Persian hyphenation is complex; consider `nohyphenation` for some sections

### PDF Metadata

- Update `\hypersetup{pdftitle={...}, pdfauthor={...}}` with localized values

---

## Unknowns / Assumptions

### Unknowns (Cannot Determine Without Direct File Access)

1. **Exact Template Errors**: Which specific templates fail when processing DE/FA JSONs
2. **Current `make_translate_csv.py` Issues**: What specifically isn't working
3. **LaTeX Compilation**: Whether XeLaTeX is installed and configured in target environment
4. **Font Availability**: Which fonts are available for Persian rendering
5. **CI/CD Setup**: Whether GitHub Actions or other CI is already configured

### Assumptions Made

1. **English is Primary**: `ramin.json` is the authoritative source for content
2. **Keys Should Be English**: Based on template analysis, templates expect English keys
3. **XeLaTeX Available**: For proper Unicode and font support
4. **No Real-time Translation**: Translations are prepared offline, not generated dynamically
5. **Maintainer is Technical**: Comfortable with Python scripting and JSON editing
6. **Three Languages Sufficient**: EN/DE/FA are the target set for now

### Clarifications That Would Help

1. Is there a preference for keeping translated keys in the long term?
2. What is the deployment target (local, CI, web service)?
3. Are there external translation tools/services in use?
4. What is the expected update frequency for CV content?
5. Are there additional CVs beyond Ramin and Mahsa that need multilingual support?

---

## Self-audit Against Constraints

| Constraint | Status | Notes |
|------------|--------|-------|
| **Produced a report only** | ✅ | No code implemented, no files modified |
| **Did not implement or modify code** | ✅ | All content is strategic recommendations |
| **Proposed 10 distinct strategies** | ✅ | Strategies 1-10 cover different approaches |
| **Addressed sync between EN/DE/FA** | ✅ | Strategies 1, 2, 4, 5, 9, 10 |
| **Addressed value translation** | ✅ | Strategies 1, 3, 4, 5, 6 |
| **Addressed key translation** | ✅ | Core Decision section + Strategies 2, 4 |
| **Addressed empty.json & minimal.json** | ✅ | Strategies 1, 7, and Phase 2 plan |
| **Addressed PDF hardcoded strings** | ✅ | Strategy 8 + all "How it Fixes..." sections |
| **Language-agnostic & scalable design** | ✅ | Each strategy includes "Adding a 4th Language" section |
| **4th language addition explained** | ✅ | Artifacts, unchanged components, and checks specified per strategy |
| **Completeness checks defined** | ✅ | Schema parity, missing translations, template token coverage per strategy |

### Extensibility Compliance Summary

Every strategy now explicitly documents:
1. ✅ **What new artifacts are created** for a 4th language
2. ✅ **What does NOT need to change** (templates, schema, other languages)
3. ✅ **Completeness checks** including:
   - Schema/structure parity validation
   - Missing translation detection
   - Template token coverage verification
4. ✅ **Scalability notes** where applicable (e.g., Strategy 4 scalability limits)

This report provides a complete, actionable, and **extensible** framework for implementing multilingual support in your CV generator repository.
