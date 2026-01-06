# Configuration Reference

CV Generator supports an optional TOML configuration file to reduce repetitive CLI flags and configure project-level defaults.

## Config File Location

The configuration file is named `cv_generator.toml` by default. It is searched for in:

1. Current working directory
2. Repository root

You can also specify a custom path with the `--config` flag:

```bash
cvgen --config path/to/config.toml build
```

## Configuration Sections

### [project]

Project-level settings.

| Key           | Type       | Default | Description |
|---------------|------------|---------|-------------|
| `name`        | string     | `""`    | Project name (for reference) |
| `default_lang`| string     | `"en"`  | Default language code |
| `variants`    | list[str]  | `[]`    | Available variant names for filtering |

Example:

```toml
[project]
name = "My CV Project"
default_lang = "en"
variants = ["academic", "industry", "onepage"]
```

### [paths]

Path configuration (all paths are relative to the config file location).

| Key         | Type   | Default        | Description |
|-------------|--------|----------------|-------------|
| `cvs`       | string | `"data/cvs"`   | CV JSON files directory |
| `templates` | string | `"templates"`  | LaTeX templates directory |
| `output`    | string | `"output"`     | Output directory root |
| `db`        | string | `"data/db/cv.db"` | SQLite database path |

Example:

```toml
[paths]
cvs = "data/cvs"
templates = "templates"
output = "output"
db = "data/db/cv.db"
```

### [build]

Build configuration options.

| Key          | Type    | Default     | Description |
|--------------|---------|-------------|-------------|
| `latex_engine` | string | `"xelatex"` | LaTeX engine to use |
| `keep_latex` | boolean | `false`     | Keep LaTeX source files after compilation |
| `dry_run`    | boolean | `false`     | Render LaTeX but don't compile to PDF |

Example:

```toml
[build]
latex_engine = "xelatex"
keep_latex = true
dry_run = false
```

### [logging]

Logging configuration.

| Key       | Type   | Default     | Description |
|-----------|--------|-------------|-------------|
| `level`   | string | `"WARNING"` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `log_file`| string | `null`      | Path to log file (optional) |

Example:

```toml
[logging]
level = "INFO"
log_file = "output/logs/cvgen.log"
```

## Precedence Rules

Configuration values are resolved with the following precedence (highest to lowest):

1. **CLI flags** — Always override config file values
2. **Config file** — Values from `cv_generator.toml`
3. **Internal defaults** — Built-in fallback values

For example, if you have `keep_latex = true` in your config but run:

```bash
cvgen build --keep-latex=false
```

The CLI flag will take precedence and LaTeX files will **not** be kept.

## Complete Example

Here's a complete example `cv_generator.toml`:

```toml
# cv_generator.toml - CV Generator Configuration

[project]
name = "My Resume Project"
default_lang = "en"
variants = ["full", "academic", "industry", "onepage"]

[paths]
cvs = "data/cvs"
templates = "templates"
output = "output"
db = "data/db/cv.db"

[build]
latex_engine = "xelatex"
keep_latex = false
dry_run = false

[logging]
level = "INFO"
log_file = "output/logs/build.log"
```

## Profile Management

CV Generator also supports profile management through the CLI:

```bash
# List available profiles
cvgen profile list

# Set the current profile
cvgen profile use ramin

# Now 'cvgen build' uses ramin by default
cvgen build

# Clear the current profile
cvgen profile clear
```

The current profile is stored in `.cvgen/state.json` (automatically excluded from git).

## Variant Filtering

Use variants to create targeted CV versions without modifying the source JSON:

```bash
# Build with variant filtering (only includes entries with matching type_key)
cvgen build --variant academic
```

Entries with a `type_key` field will be filtered:
- If `type_key` matches the variant → included
- If `type_key` is a list containing the variant → included
- If entry has no `type_key` → always included (considered universal)
