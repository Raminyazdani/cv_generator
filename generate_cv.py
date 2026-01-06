#!/usr/bin/env python3
"""
Legacy entry point for CV Generator.

DEPRECATED: This script is deprecated and will be removed in v3.0.0.
Use the `cvgen` CLI instead.

Migration:
    OLD: python generate_cv.py --name ramin
    NEW: cvgen build --name ramin --lang en

See: https://github.com/Raminyazdani/cv_generator/blob/main/docs/MIGRATION.md
"""

import sys
import time
import warnings
from pathlib import Path

# Add the src directory to the path for development installations
_src_dir = Path(__file__).parent / "src"
if _src_dir.exists():
    sys.path.insert(0, str(_src_dir))


def show_deprecation_warning():
    """Display deprecation warning to user."""
    warning_message = """
╔════════════════════════════════════════════════════════════════╗
║                     DEPRECATION WARNING                        ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  generate_cv.py is DEPRECATED and will be removed in v3.0.0   ║
║                                                                ║
║  Please migrate to the new CLI:                                ║
║                                                                ║
║    OLD: python generate_cv.py --name ramin                     ║
║    NEW: cvgen build --name ramin --lang en                     ║
║                                                                ║
║  The new CLI provides:                                         ║
║    • Better error messages                                     ║
║    • More features (variants, caching, etc.)                   ║
║    • Improved performance                                      ║
║    • Active development and support                            ║
║                                                                ║
║  Migration guide:                                              ║
║  https://github.com/Raminyazdani/cv_generator/docs/MIGRATION.md║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
"""

    print(warning_message, file=sys.stderr)

    # Also issue Python warning for programmatic detection
    warnings.warn(
        "generate_cv.py is deprecated. Use 'cvgen build' instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Give user time to read
    time.sleep(2)


def main():
    """Legacy entry point with deprecation warning."""
    from cv_generator.cli import main as cli_main

    # Show deprecation warning
    show_deprecation_warning()

    # Default to 'build' command if no command specified
    # and no help flags are present
    args = sys.argv[1:]

    # If no arguments, run build command with verbose output
    if not args:
        args = ["-v", "build"]
    elif args[0] not in ("build", "--help", "-h", "--version", "-v", "--verbose", "--debug"):
        # If first arg is not a command, flag, or help flag, prepend build
        args = ["build"] + args
    elif args[0] in ("-v", "--verbose", "--debug"):
        # Flag is already there, just ensure build command is added if missing
        if "build" not in args and "--help" not in args and "-h" not in args:
            # Insert build after the flag
            idx = 1
            while idx < len(args) and args[idx] in ("-v", "--verbose", "--debug"):
                idx += 1
            args = args[:idx] + ["build"] + args[idx:]

    return cli_main(args)


if __name__ == "__main__":
    sys.exit(main())
