import json
import os
import shutil
import stat
import time
import uuid
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.exceptions import TemplateError

# -------------------------
# Settings
# -------------------------


BASE_DIR = os.path.dirname(__file__)
CVS_PATH = os.path.join(BASE_DIR,"data", 'cvs')
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
RESULT_DIR = os.path.join(BASE_DIR, "result")
if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)

for people in os.listdir(CVS_PATH):
    people_name = people.split('.')[0]
    if not os.path.exists(os.path.join(RESULT_DIR, people_name)):
        os.mkdir(os.path.join(RESULT_DIR, people_name))
    OUTPUT_DIR = os.path.join(RESULT_DIR, people_name, "sections")
    JSON_PATH = os.path.join(CVS_PATH, people)
    RENDERED_OUTPUT = os.path.join(OUTPUT_DIR, "rendered.tex")

    # Toggle whether template-inserted comments are emitted
    SHOW_COMMENTS = True

    # Which templates to render as sections (and also embed into layout)
    # SECTION_TEMPLATES = [
    #     "header.tex",
    #     "education.tex",
    #     "certificates.tex",
    #     "experience.tex",
    #     "language.tex",
    #     "projects.tex",
    #     "publications.tex",
    #     "references.tex",
    #     "skills.tex"
    #     # add more like: "education.tex", "experience.tex", ...
    # ]
    SECTION_TEMPLATES = [
    x for x in os.listdir(TEMPLATE_DIR)
    ]
    # -------------------------
    # Utilities / Filters
    # -------------------------
    def latex_escape(s):
        """Escape LaTeX special chars in plain text."""
        if s is None:
            return ""
        s = str(s)
        # Order matters: backslash first.
        repl = [
            ("\\", r"\textbackslash{}"),
            ("&",  r"\&"),
            ("%",  r"\%"),
            ("$",  r"\$"),
            ("#",  r"\#"),
            ("_",  r"\_"),
            ("{",  r"\{"),
            ("}",  r"\}"),
            ("~",  r"\textasciitilde{}"),
            ("^",  r"\textasciicircum{}"),
        ]
        for k, v in repl:
            s = s.replace(k, v)
        return s

    def file_exists(value):
        if os.path.exists(value):
            return True
        return False

    def debug(value):
        print(value)
        print(type(value))
        return ""  # emit nothing in TeX

    def types(value):
        print(type(value))
        return ""  # emit nothing in TeX

    def cmt(s):
        """Emit a single LaTeX comment line, gated by SHOW_COMMENTS."""
        if not SHOW_COMMENTS or s is None:
            return ""
        return "% " + str(s).replace("\n", " ").strip() + "\n"

    def cblock(s):
        """Emit multi-line LaTeX comment block, gated by SHOW_COMMENTS."""
        if not SHOW_COMMENTS or s is None:
            return ""
        lines = str(s).splitlines() or [str(s)]
        return "".join("% " + line + "\n" for line in lines)

    def find_pic(opt_name):
        if os.path.exists(f"./data/pics/{opt_name}.jpg"):
            return True
        else:
            return False

    def get_pic(opt_name):
        return f"./data/pics/{opt_name}.jpg"


    # -------------------------
    # Load data (no eval, no hacks)
    # -------------------------
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # If you want to pre-escape specific fields globally, do it here (optional).
    # Otherwise use the |latex_escape filter in templates where needed.

    # -------------------------
    # Jinja environment
    # -------------------------
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),  # be explicit with TEMPLATE_DIR
        block_start_string="<BLOCK>",
        block_end_string="</BLOCK>",
        variable_start_string="<VAR>",
        variable_end_string="</VAR>",
        comment_start_string="/*/*/*",
        comment_end_string="*/*/*/",
        autoescape=False,          # LaTeX, so we escape explicitly
        trim_blocks=True,          # nicer LaTeX whitespace
        lstrip_blocks=True,        # remove leading spaces before blocks
        keep_trailing_newline=True,
        undefined=StrictUndefined  # fail loudly on missing vars (better debugging)
    )

    # Filters & globals
    data["OPT_NAME"] = people_name

    env.filters["latex_escape"] = latex_escape
    env.filters["debug"] = debug
    env.filters["types"] = types
    env.filters["cmt"] = cmt
    env.filters["cblock"] = cblock
    env.filters["file_exists"] = file_exists
    env.globals["SHOW_COMMENTS"] = SHOW_COMMENTS
    env.filters["get_pic"] = get_pic
    env.filters["find_pic"] = find_pic

    # Vars available to templates (top-level JSON keys become variables)
    env_vars = {**data}

    # -------------------------
    # Ensure output folder exists
    # -------------------------
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # -------------------------
    # Render sections (write files + stash inline strings)
    # -------------------------
    for tmpl_file in SECTION_TEMPLATES:
        try:
            template = env.get_template(tmpl_file)
            rendered = template.render(env_vars)
        except TemplateError as e:
            raise SystemExit(f"[Jinja error in {tmpl_file}] {e}") from e

        # write section file
        section_name = os.path.splitext(tmpl_file)[0]
        output_path = os.path.join(OUTPUT_DIR, f"{section_name}.tex")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        # also store for inline embedding in layout
        env_vars[f"{section_name}_section"] = rendered

    print("✅ Sections rendered to 'sections/'.")

    # -------------------------
    # Render layout with embedded sections
    # -------------------------
    try:
        layout_template = env.get_template("layout.tex")
        rendered_layout = layout_template.render(env_vars)
    except TemplateError as e:
        raise SystemExit(f"[Jinja error in layout.tex] {e}") from e

    # Optional tiny cleanup: collapse accidental double blank lines
    rendered_layout = rendered_layout.replace("\n\n\n", "\n\n")

    with open(RENDERED_OUTPUT, "w", encoding="utf-8") as f:
        f.write(rendered_layout)

    print(f"✅ Final resume_rendered.tex generated for user {people_name}.")
    print(f"➡️  Compile with: xelatex {RENDERED_OUTPUT}")
    comand = fr"xelatex -enable-etex -enable-installer -enable-mltex -interaction=nonstopmode -file-line-error -synctex=1 -output-directory=.\output {RENDERED_OUTPUT} "

    # run the command to compile the LaTeX file
    os.system(comand)
    for file in os.listdir("./output"):
        if not file.endswith(".pdf"):
            #remove
            os.remove(f"./output/{file}")
        if file.endswith("rendered.pdf"):
            # rename the file to final.pdf
            shutil.move(f"./output/{file}", f"./output/{people_name}.pdf")


def _clear_readonly_windows(root: Path) -> None:
    # Best-effort: remove "Read-only" attribute recursively (Windows)
    if os.name == "nt":
        try:
            # attrib -R "<root>\*" /S /D  (files + dirs)
            subprocess.run(
                ["attrib", "-R", str(root / "*"), "/S", "/D"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,  # helps attrib resolve wildcards reliably on Windows
            )
        except Exception:
            pass


def _make_writable(path: str) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except Exception:
        pass


def rmtree_reliable(path: str | os.PathLike, *, attempts: int = 25) -> None:
    p = Path(path)

    # Nothing to do
    if not p.exists():
        return

    p = p.resolve()

    # Optional: try renaming once to a unique temp name (helps with sync/watchers sometimes)
    try:
        renamed = p.with_name(f"{p.name}.__deleting__{uuid.uuid4().hex}")
        p.rename(renamed)
        p = renamed
    except Exception:
        # If rename fails (locked), continue anyway
        pass

    def onerror(func, failed_path, exc_info):
        # Called by shutil.rmtree when it hits a problem
        _make_writable(failed_path)
        try:
            func(failed_path)
        except Exception:
            # Let outer retry loop handle transient locks
            raise

    # Retry loop (handles transient "Access is denied" due to OneDrive/AV/Explorer)
    for i in range(attempts):
        try:
            _clear_readonly_windows(p)
            shutil.rmtree(p, onerror=onerror)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            # exponential backoff up to ~2s
            time.sleep(min(2.0, 0.05 * (2 ** i)))
        except OSError as e:
            # Some Windows lock errors come as generic OSError
            time.sleep(min(2.0, 0.05 * (2 ** i)))

    # Final attempt (raise if it still fails)
    _clear_readonly_windows(p)
    shutil.rmtree(p, onerror=onerror)

rmtree_reliable(RESULT_DIR)
