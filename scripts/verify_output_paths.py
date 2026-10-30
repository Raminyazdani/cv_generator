"""
Script to verify actual output paths and document them correctly.

This script demonstrates the output path structure used by CV Generator
to help ensure documentation stays accurate.

Usage:
    python scripts/verify_output_paths.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from cv_generator.paths import ArtifactPaths

def verify_output_paths():
    """Verify and document actual output path behavior."""
    print('=' * 60)
    print('CV Generator Output Path Verification')
    print('=' * 60)
    test_cases = [{'profile': 'example', 'lang': 'en', 'variant': None}, {'profile': 'example', 'lang': 'de', 'variant': None}, {'profile': 'example', 'lang': 'en', 'variant': 'academic'}, {'profile': 'john_doe', 'lang': 'en', 'variant': 'full'}]
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Profile: {case['profile']}, Lang: {case['lang']}, Variant: {case['variant']}")
        print('-' * 60)
        paths = ArtifactPaths(profile=case['profile'], lang=case['lang'], variant=case['variant'], output_root=Path('output'))
        print(f'  PDF directory:   {paths.pdf_dir}')
        print(f'  PDF named path:  {paths.pdf_named_path}')
        print(f'  LaTeX directory: {paths.latex_dir}')
        print(f'  TeX main file:   {paths.tex_path}')
        print(f'  JSON directory:  {paths.json_dir}')
    print('\n' + '=' * 60)
    print('Summary: Output Path Structure')
    print('=' * 60)
    print('\nCV Generator organizes outputs as follows:\n\n**Without variant:**\n  output/pdf/<profile>/<lang>/<profile>_<lang>.pdf\n  output/latex/<profile>/<lang>/main.tex\n  output/json/<profile>/<lang>/cv.json\n\n**With variant:**\n  output/pdf/<profile>/<variant>/<lang>/<profile>_<lang>.pdf\n  output/latex/<profile>/<variant>/<lang>/main.tex\n  output/json/<profile>/<variant>/<lang>/cv.json\n\n**Example:**\n  cvgen build --name example --lang en\n  → output/pdf/example/en/example_en.pdf\n\n  cvgen build --name example --lang en --variant academic\n  → output/pdf/example/academic/en/example_en.pdf\n')
if __name__ == '__main__':
    verify_output_paths()
