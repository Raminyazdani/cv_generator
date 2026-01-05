#!/usr/bin/env python3
"""
Script to verify actual output paths and document them correctly.

This script demonstrates the output path structure used by CV Generator
to help ensure documentation stays accurate.

Usage:
    python scripts/verify_output_paths.py
"""

from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cv_generator.paths import ArtifactPaths


def verify_output_paths():
    """Verify and document actual output path behavior."""

    print("=" * 60)
    print("CV Generator Output Path Verification")
    print("=" * 60)

    # Test with typical parameters
    test_cases = [
        {
            'profile': 'ramin',
            'lang': 'en',
            'variant': None,
        },
        {
            'profile': 'ramin',
            'lang': 'de',
            'variant': None,
        },
        {
            'profile': 'ramin',
            'lang': 'en',
            'variant': 'academic',
        },
        {
            'profile': 'john_doe',
            'lang': 'en',
            'variant': 'full',
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Profile: {case['profile']}, Lang: {case['lang']}, Variant: {case['variant']}")
        print("-" * 60)

        # Create ArtifactPaths instance
        paths = ArtifactPaths(
            profile=case['profile'],
            lang=case['lang'],
            variant=case['variant'],
            output_root=Path('output'),
        )

        # Check various path properties
        print(f"  PDF directory:   {paths.pdf_dir}")
        print(f"  PDF named path:  {paths.pdf_named_path}")
        print(f"  LaTeX directory: {paths.latex_dir}")
        print(f"  TeX main file:   {paths.tex_path}")
        print(f"  JSON directory:  {paths.json_dir}")

    print("\n" + "=" * 60)
    print("Summary: Output Path Structure")
    print("=" * 60)

    print("""
CV Generator organizes outputs as follows:

**Without variant:**
  output/pdf/<profile>/<lang>/<profile>_<lang>.pdf
  output/latex/<profile>/<lang>/main.tex
  output/json/<profile>/<lang>/cv.json

**With variant:**
  output/pdf/<profile>/<variant>/<lang>/<profile>_<lang>.pdf
  output/latex/<profile>/<variant>/<lang>/main.tex
  output/json/<profile>/<variant>/<lang>/cv.json

**Example:**
  cvgen build --name ramin --lang en
  → output/pdf/ramin/en/ramin_en.pdf

  cvgen build --name ramin --lang en --variant academic
  → output/pdf/ramin/academic/en/ramin_en.pdf
""")


if __name__ == '__main__':
    verify_output_paths()
