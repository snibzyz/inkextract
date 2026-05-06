"""ทดสอบ core: SecurityValidator + ErrorExporter (ไม่ครอบใน test_proofreader)"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.core import SecurityValidator, ErrorExporter  # noqa: E402


# ============================================================
# SecurityValidator
# ============================================================

def test_validate_file_path_within_base():
    sv = SecurityValidator()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        good = base / 'sub' / 'a.txt'
        good.parent.mkdir()
        good.touch()
        assert sv.validate_file_path(str(good), base) is True


def test_validate_file_path_outside_base():
    sv = SecurityValidator()
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        base = Path(td1)
        outside = Path(td2) / 'evil.txt'
        outside.touch()
        assert sv.validate_file_path(str(outside), base) is False


def test_validate_file_size_under_limit():
    sv = SecurityValidator()
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / 'small.txt'
        f.write_text('x' * 100, encoding='utf-8')
        assert sv.validate_file_size(f) is True


def test_validate_file_size_nonexistent():
    sv = SecurityValidator()
    assert sv.validate_file_size(Path('/nonexistent/xyz.txt')) is False


def test_sanitize_filename_removes_dangerous_chars():
    sv = SecurityValidator()
    assert '/' not in sv.sanitize_filename('a/b.txt')
    assert '\\' not in sv.sanitize_filename('a\\b.txt')
    assert '..' not in sv.sanitize_filename('../../etc')
    assert ':' not in sv.sanitize_filename('C:file')
    for ch in ['*', '?', '"', '<', '>', '|']:
        assert ch not in sv.sanitize_filename(f'a{ch}b')


def test_sanitize_filename_keeps_safe_chars():
    sv = SecurityValidator()
    out = sv.sanitize_filename('normal name.txt')
    assert 'normal name.txt' == out


# ============================================================
# ErrorExporter
# ============================================================

def test_export_normal_mode_errors_empty_returns_false():
    ee = ErrorExporter()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'errors.txt'
        assert ee.export_normal_mode_errors([], out) is False


def test_export_normal_mode_errors_writes_file():
    ee = ErrorExporter()
    errors = [
        {
            'file_path': '/path/to/file1.txt',
            'file_name': 'file1.txt',
            'line_number': 5,
            'line_content': 'มีจีน 你好',
            'categories': ['ภาษาต่างประเทศ'],
            'flags': {'foreign': True},
        },
        {
            'file_path': '/path/to/file1.txt',
            'file_name': 'file1.txt',
            'line_number': 10,
            'line_content': 'test 123',
            'categories': ['ภาษาอังกฤษ'],
            'flags': {'english': True},
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'errors.txt'
        result = ee.export_normal_mode_errors(errors, out)
        assert result is True
        text = out.read_text(encoding='utf-8')
        assert 'file1.txt' in text
        assert '5|' in text
        assert '10|' in text
        assert 'ภาษาต่างประเทศ' in text


def test_export_ab_mode_errors_empty_returns_false():
    ee = ErrorExporter()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'ab.txt'
        assert ee.export_ab_mode_errors([], out) is False


def test_export_ab_mode_errors_writes_file():
    ee = ErrorExporter()
    errors = [
        {
            'file_path': '/path/to/sample.txt',
            'line_number_B': 4,
            'original_A': '[A] 你好',
            'original_B': '[B] สวัสดี test',
            'corrected_B': '[B] สวัสดี test',
            'categories': ['ภาษาอังกฤษ'],
            'flags': {'english': True},
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'ab.txt'
        result = ee.export_ab_mode_errors(errors, out)
        assert result is True
        text = out.read_text(encoding='utf-8')
        assert 'sample.txt' in text
        assert '[A] 你好' in text or '你好' in text
        assert 'สวัสดี' in text


# ============================================================
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
