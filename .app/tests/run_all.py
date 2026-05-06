"""run_all.py — รัน test ทุก module พร้อมรายงานสรุป"""
import sys
import importlib
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

TEST_MODULES = [
    'test_imports',
    'test_paths_config',
    'test_ui',
    'test_format_checker',
    'test_core',
    'test_manuscript_checker',
    'test_vocab_processor',
    'test_proofreader',
    'test_merge_separate',
    'test_preferences',
    'test_file_processor',
    'test_fuzzy_matcher',
    'test_error_chunker',
]

if __name__ == '__main__':
    total_passed = 0
    total_failed = 0
    failed_tests = []

    for mod_name in TEST_MODULES:
        print(f'\n━━━ {mod_name} ━━━')
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f'  💥 import failed: {e}')
            total_failed += 1
            continue

        tests = [(n, f) for n, f in inspect.getmembers(mod)
                 if n.startswith('test_') and callable(f)]

        for name, fn in tests:
            try:
                fn()
                total_passed += 1
            except AssertionError as e:
                total_failed += 1
                failed_tests.append((mod_name, name, str(e)))
                print(f'  ✗ {name}: {e}')
            except Exception as e:
                total_failed += 1
                failed_tests.append((mod_name, name, f'{type(e).__name__}: {e}'))
                print(f'  💥 {name}: {type(e).__name__}: {e}')

        print(f'  → {len(tests) - sum(1 for f in failed_tests if f[0] == mod_name)} / {len(tests)}')

    print()
    print('=' * 60)
    print(f'TOTAL: {total_passed} passed • {total_failed} failed')
    print('=' * 60)

    if failed_tests:
        print('\nFAILED:')
        for mod, name, err in failed_tests:
            print(f'  {mod}::{name} — {err}')

    sys.exit(0 if total_failed == 0 else 1)
