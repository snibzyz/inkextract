"""ทดสอบ format_checker — first-line format detection"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.format_checker import FormatChecker  # noqa: E402


def test_detect_pattern1_with_3_digit_number():
    fc = FormatChecker()
    assert fc.detect_format_pattern("ระบบฝึกยุทธ์ 001 ข้ามมิติ") == 'pattern1'


def test_detect_pattern1_with_4_digit_number():
    fc = FormatChecker()
    assert fc.detect_format_pattern("เรื่อง 0001 ตอนแรก") == 'pattern1'


def test_detect_pattern2_with_ตอนที่():
    fc = FormatChecker()
    assert fc.detect_format_pattern("รวยขั้นเทพ ตอนที่ 002 ตัดสินใจ") == 'pattern2'


def test_detect_unknown_format():
    fc = FormatChecker()
    assert fc.detect_format_pattern("สวัสดีครับ") == 'unknown'


def test_detect_empty_line():
    fc = FormatChecker()
    assert fc.detect_format_pattern("") == 'unknown'


def test_read_first_line():
    fc = FormatChecker()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'test.txt'
        fp.write_text("first line\nsecond\nthird\n", encoding='utf-8')
        assert fc.read_first_line(fp) == "first line"


def test_read_first_line_empty_file():
    fc = FormatChecker()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'empty.txt'
        fp.write_text("", encoding='utf-8')
        assert fc.read_first_line(fp) == ""


def test_check_all_files():
    fc = FormatChecker()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # 3 ไฟล์ pattern1, 1 ไฟล์ unknown
        for i, line in enumerate([
            "นิยาย 001 ตอน1",
            "นิยาย 002 ตอน2",
            "นิยาย 003 ตอน3",
            "บรรทัดมั่วๆ",
        ]):
            (base / f'f{i}.txt').write_text(line + "\n", encoding='utf-8')
        fc.clean_dir = base
        result = fc.check_all_files()
        assert result['total_files'] == 4
        assert result['standard_format'] == 'pattern1'
        assert result['valid_files'] == 3
        assert result['invalid_files'] == 1


def test_check_all_files_empty_dir():
    fc = FormatChecker()
    with tempfile.TemporaryDirectory() as td:
        fc.clean_dir = Path(td)
        result = fc.check_all_files()
        assert result['total_files'] == 0
        assert result['files'] == []


def test_format_description():
    fc = FormatChecker()
    assert 'หมายเลข' in fc.get_format_description('pattern1')
    assert 'ตอนที่' in fc.get_format_description('pattern2')
    assert 'ไม่ตรง' in fc.get_format_description('unknown')


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
