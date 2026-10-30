"""
Legacy entry point for CV Generator.

DEPRECATED: This script is deprecated and will be removed in v3.0.0.
Use the `cvgen` CLI instead.

Migration:
    OLD: python generate_cv.py --name example
    NEW: cvgen build --name example --lang en

See: https://github.com/Raminyazdani/cv_generator/blob/main/docs/MIGRATION.md
"""
import sys
import time
import warnings
from pathlib import Path
_src_dir = Path(__file__).parent / 'src'
if _src_dir.exists():
    sys.path.insert(0, str(_src_dir))

def show_deprecation_warning():
    """Display deprecation warning to user."""
    warning_message = '\n╔════════════════════════════════════════════════════════════════╗\n║                     DEPRECATION WARNING                        ║\n╠════════════════════════════════════════════════════════════════╣\n║                                                                ║\n║  generate_cv.py is DEPRECATED and will be removed in v3.0.0   ║\n║                                                                ║\n║  Please migrate to the new CLI:                                ║\n║                                                                ║\n║    OLD: python generate_cv.py --name example                     ║\n║    NEW: cvgen build --name example --lang en                     ║\n║                                                                ║\n║  The new CLI provides:                                         ║\n║    • Better error messages                                     ║\n║    • More features (variants, caching, etc.)                   ║\n║    • Improved performance                                      ║\n║    • Active development and support                            ║\n║                                                                ║\n║  Migration guide:                                              ║\n║  https://github.com/Raminyazdani/cv_generator/blob/main/docs/  ║\n║  MIGRATION.md                                                  ║\n║                                                                ║\n╚════════════════════════════════════════════════════════════════╝\n'
    print(warning_message, file=sys.stderr)
    warnings.warn("generate_cv.py is deprecated. Use 'cvgen build' instead.", DeprecationWarning, stacklevel=2)
    time.sleep(2)

def main():
    """Legacy entry point with deprecation warning."""
    from cv_generator.cli import main as cli_main
    show_deprecation_warning()
    args = sys.argv[1:]
    if not args:
        args = ['-v', 'build']
    elif args[0] not in ('build', '--help', '-h', '--version', '-v', '--verbose', '--debug'):
        args = ['build'] + args
    elif args[0] in ('-v', '--verbose', '--debug'):
        if 'build' not in args and '--help' not in args and ('-h' not in args):
            idx = 1
            while idx < len(args) and args[idx] in ('-v', '--verbose', '--debug'):
                idx += 1
            args = args[:idx] + ['build'] + args[idx:]
    return cli_main(args)
if __name__ == '__main__':
    sys.exit(main())
