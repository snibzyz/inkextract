"""ทดสอบว่า module ทุกอันใน app import ได้ — ครอบคลุม syntax + dependency"""
import sys
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_app_py_syntax_valid():
    src = (ROOT / 'app.py').read_text(encoding='utf-8')
    ast.parse(src)


def test_all_module_files_parse():
    failures = []
    for p in (ROOT / 'modules').rglob('*.py'):
        try:
            ast.parse(p.read_text(encoding='utf-8'))
        except SyntaxError as e:
            failures.append((p.name, str(e)))
    assert not failures, f"syntax errors: {failures}"


def test_critical_imports_work():
    """ตรวจว่า import แต่ละ module ทำงานได้จริง (ไม่ใช่แค่ parse)"""
    from modules import paths, ui, manuscript_checker  # noqa
    from modules.config import regex_patterns, app_config  # noqa
    from modules.core import FileAnalyzer, TextClassifier, ErrorExporter  # noqa
    from modules.proofreader import NovelProofreader  # noqa
    from modules.vocab_processor import VocabProcessor, parse_vocab_text  # noqa
    from modules.format_checker import FormatChecker  # noqa
    from modules.tabs import manuscript as tab_ms  # noqa


def test_manuscript_tab_render_function_exists():
    from modules.tabs import manuscript
    assert callable(manuscript.render)


def test_app_renders_without_exception():
    """รัน app.py ผ่าน Streamlit AppTest — จับ NameError, ImportError ตอน render"""
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        # Streamlit เก่ากว่า 1.27 → skip
        return
    at = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=30)
    at.run()
    assert not at.exception, f"render exception: {at.exception}"
    # ต้องมี tabs หลัก + sub-tabs
    assert len(at.tabs) >= 4, f"too few tabs: {len(at.tabs)}"


def test_no_module_exceeds_threshold():
    """ตรวจว่าไม่มี module ใหญ่กว่า 2000 บรรทัด (เป็น warning soft limit)"""
    over = []
    for p in (ROOT / 'modules').rglob('*.py'):
        n = sum(1 for _ in p.read_text(encoding='utf-8').splitlines())
        if n > 2000:
            over.append((p.name, n))
    # ถ้ามี ให้รายงาน แต่ไม่ fail (soft limit)
    if over:
        print(f'  ⚠️ modules over 2000 lines: {over}')
    # hard limit: 3000
    hard = [(n, l) for n, l in over if l > 3000]
    assert not hard, f"hard limit exceeded: {hard}"


if __name__ == '__main__':
    import inspect
    tests = [(n, f) for n, f in inspect.getmembers(sys.modules[__name__])
             if n.startswith('test_') and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  ✓ {name}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗ {name}: {e}')
            failed += 1
        except Exception as e:
            print(f'  💥 {name}: {type(e).__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
