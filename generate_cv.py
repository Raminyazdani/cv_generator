#!/usr/bin/env python3
"""
CV Generator - Compatibility wrapper script.

This script provides backward compatibility with the original generate_cv.py usage.
It delegates to the cv_generator package CLI.

Usage:
    python generate_cv.py           # Generate all CVs (same as cvgen build)
    python generate_cv.py --help    # Show help

For advanced usage, use the cvgen CLI directly:
    cvgen build --name ramin        # Build only ramin's CV
    cvgen build --dry-run           # Render LaTeX without compilation
"""

import sys
from pathlib import Path

# Add the src directory to the path for development installations
_src_dir = Path(__file__).parent / "src"
if _src_dir.exists():
    sys.path.insert(0, str(_src_dir))

from cv_generator.cli import main

if __name__ == "__main__":
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

    sys.exit(main(args))
