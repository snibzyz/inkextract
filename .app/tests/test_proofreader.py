"""ทดสอบ proofreader + regex patterns + AB analysis"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.config import regex_patterns  # noqa: E402
from modules.proofreader import NovelProofreader  # noqa: E402
from modules.core import FileAnalyzer, TextClassifier  # noqa: E402


# ============================================================
# RegexPatterns tests
# ============================================================

def test_detect_foreign_thai_only():
    assert regex_patterns.detect_foreign_chars('สวัสดีครับ') is False


def test_detect_foreign_chinese():
    assert regex_patterns.detect_foreign_chars('你好世界') is True


def test_detect_foreign_japanese_hiragana():
    assert regex_patterns.detect_foreign_chars('こんにちは') is True


def test_detect_foreign_japanese_katakana():
    assert regex_patterns.detect_foreign_chars('カタカナ') is True


def test_detect_foreign_korean():
    assert regex_patterns.detect_foreign_chars('안녕하세요') is True


def test_detect_foreign_arabic():
    assert regex_patterns.detect_foreign_chars('السلام') is True


def test_detect_foreign_cyrillic():
    assert regex_patterns.detect_foreign_chars('Привет') is True


def test_detect_foreign_mixed_thai_english_passes():
    """ไทย+อังกฤษ → ไม่นับว่ามีต่างประเทศ (อังกฤษเช็คด้วย flag แยก)"""
    assert regex_patterns.detect_foreign_chars('สวัสดี hello') is False


def test_detect_foreign_thai_with_chinese_fails():
    assert regex_patterns.detect_foreign_chars('สวัสดี你好') is True


def test_clean_text_removes_japanese_brackets():
    out = regex_patterns.clean_text('สวัสดี【note】test')
    assert '【' not in out and '】' not in out
    assert 'test' in out


def test_clean_text_removes_chinese_parens():
    out = regex_patterns.clean_text('สวัสดี（note）test')
    assert '（' not in out and '）' not in out


def test_clean_text_idempotent():
    text = 'สวัสดีปกติ ไม่มี pattern'
    assert regex_patterns.clean_text(text) == text


def test_clean_text_keeps_content_inside_cjk_brackets():
    """Regression: ห้ามกลืนเนื้อหาข้างใน 【…】/（…） — โน้ตจีนของผู้แต่งต้องรอดไปถึงขั้นตรวจ"""
    assert '时间比例' in regex_patterns.clean_text('【时间比例：一比十。】')
    assert '凤溪国国号为汉' in regex_patterns.clean_text('（凤溪国国号为汉。）')


def test_detect_foreign_chinese_inside_brackets_flagged():
    """Regression: บรรทัดจีน (ตัวย่อ) ที่ครอบวงเล็บ CJK ทั้งบรรทัด ต้องถูก flag เป็น foreign"""
    for line in (
        '【道果：大日帝主（六司）、酆都天曹（八极）、金乌仙体（七元）……】',
        '（进士只是储官，授官要经吏部关试。例如韩愈，虽中了进士。）',
        '（凤溪国国号为汉。）',
        '【龍鳳呈祥】',  # ตัวเต็มในวงเล็บก็ต้องโดนเหมือนกัน
    ):
        assert regex_patterns.detect_foreign_chars(regex_patterns.clean_text(line)) is True


def test_detect_foreign_thai_inside_brackets_passes():
    """ไทยล้วนในวงเล็บ CJK (แปลแล้ว) — ไม่ flag"""
    cleaned = regex_patterns.clean_text('【ลิขิตเซียน: กายาราชามนุษย์】')
    assert regex_patterns.detect_foreign_chars(cleaned) is False


def test_english_pattern():
    assert regex_patterns.english_pattern.search('hello123')
    assert not regex_patterns.english_pattern.search('สวัสดี你好')


def test_numbers_pattern():
    assert regex_patterns.numbers_pattern.search('test123')
    assert not regex_patterns.numbers_pattern.search('test')


def test_chinese_pattern():
    assert regex_patterns.chinese_pattern.search('你好')
    assert not regex_patterns.chinese_pattern.search('สวัสดี')


def test_reload_patterns_does_not_throw():
    regex_patterns.reload_patterns()
    assert regex_patterns.ignore_combined is not None or len(regex_patterns.ignore_patterns_raw) == 0


# ============================================================
# TextClassifier tests
# ============================================================

def test_classifier_skip_ab_markers_default():
    tc = TextClassifier()
    flags = tc.classify_text('[A] 你好', skip_ab_markers=True)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


def test_classifier_no_skip_ab_markers():
    tc = TextClassifier()
    flags = tc.classify_text('[A] 你好', skip_ab_markers=False)
    # นับ [A] เลย — มี chinese
    assert flags['foreign'] is True


def test_classifier_thai_clean():
    tc = TextClassifier()
    flags = tc.classify_text('สวัสดีครับ', skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


def test_should_flag_logic():
    tc = TextClassifier()
    flags = {'foreign': True, 'english': False, 'numbers': False}
    assert tc.should_flag(flags, check_foreign=True, check_english=True, check_numbers=True)
    assert not tc.should_flag(flags, check_foreign=False, check_english=True, check_numbers=True)


def test_category_labels():
    tc = TextClassifier()
    flags = {'foreign': True, 'english': True, 'numbers': False}
    cats = tc.get_category_labels(flags, check_foreign=True, check_english=True, check_numbers=False)
    assert 'ภาษาต่างประเทศ' in cats
    assert 'ภาษาอังกฤษ' in cats
    assert 'ตัวเลข' not in cats


# ============================================================
# FileAnalyzer (normal mode)
# ============================================================

def test_analyze_normal_mode_finds_chinese_lines():
    fa = FileAnalyzer()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'test.txt'
        fp.write_text(
            "สวัสดีปกติ\n"
            "มีจีน 你好 หลงเหลือ\n"
            "test123 ไทย\n",
            encoding='utf-8',
        )
        errors = fa.analyze_file_content(fp, True, False, False, skip_ab_markers=False)
        assert len(errors) == 1
        assert errors[0]['line_number'] == 2


def test_analyze_normal_mode_with_english_check():
    fa = FileAnalyzer()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'test.txt'
        fp.write_text("ปกติ\nhas hello\n", encoding='utf-8')
        errors = fa.analyze_file_content(fp, False, True, False, skip_ab_markers=False)
        assert len(errors) == 1
        assert 'ภาษาอังกฤษ' in errors[0]['categories']


def test_analyze_normal_mode_skips_blank_lines():
    fa = FileAnalyzer()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'test.txt'
        fp.write_text("ปกติ\n\n\nบรรทัดอื่น\n", encoding='utf-8')
        errors = fa.analyze_file_content(fp, True, True, True, skip_ab_markers=False)
        assert errors == []


def test_analyze_normal_mode_nonexistent_file():
    fa = FileAnalyzer()
    errors = fa.analyze_file_content(Path('/nonexistent/file.txt'), True, True, True)
    assert errors == []


# ============================================================
# AB mode
# ============================================================

def test_ab_mode_basic():
    pr = NovelProofreader()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'sample.txt'
        fp.write_text(
            "[A] 你好世界\n"
            "[B] สวัสดีโลก\n"
            "[A] 我是测试\n"
            "[B] ฉันคือทดสอบ test123\n"
            "[A] 中文\n"
            "[B] ไทย 测试 หลงเหลือ\n",
            encoding='utf-8',
        )
        errors = pr._analyze_ab_file(fp, True, True, True)
        assert len(errors) == 2
        # บรรทัด [B] บนสุด (4) มี english+numbers
        line4 = next(e for e in errors if e['line_number_B'] == 4)
        assert 'ภาษาอังกฤษ' in line4['categories']
        # บรรทัด [B] ล่าง (6) มี chinese
        line6 = next(e for e in errors if e['line_number_B'] == 6)
        assert 'ภาษาต่างประเทศ' in line6['categories']


def test_ab_mode_clean_no_errors():
    pr = NovelProofreader()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'clean.txt'
        fp.write_text(
            "[A] 你好\n"
            "[B] สวัสดี\n"
            "[A] 谢谢\n"
            "[B] ขอบคุณ\n",
            encoding='utf-8',
        )
        errors = pr._analyze_ab_file(fp, True, True, True)
        assert errors == []


def test_ab_mode_links_correct_a_to_b():
    """ตรวจว่า [A] ที่ผูกกับ [B] เป็นบรรทัด [A] ล่าสุดก่อนหน้า"""
    pr = NovelProofreader()
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / 'multi.txt'
        fp.write_text(
            "[A] AAAA\n"
            "comment line\n"
            "[A] BBBB\n"
            "[B] ทดสอบ test\n",  # ต้องผูกกับ BBBB
            encoding='utf-8',
        )
        errors = pr._analyze_ab_file(fp, True, True, True)
        assert len(errors) == 1
        assert errors[0]['original_A'] == '[A] BBBB'


def test_ab_signature_consistent():
    """signature ของไฟล์ควรเท่ากันถ้า [B] เนื้อหาเหมือนกัน (whitespace insensitive)"""
    pr = NovelProofreader()
    lines1 = "[A] 1\n[B] hello\n[A] 2\n[B] world\n".splitlines()
    lines2 = "[A] x\n[B]   hello   \n[A] y\n[B] world\n".splitlines()
    # different [A], same [B] (whitespace normalized) → same signature
    sig1 = pr._signature_from_lines(lines1)
    sig2 = pr._signature_from_lines(lines2)
    assert sig1 == sig2 and sig1 != ''


def test_ab_signature_different_when_b_differs():
    pr = NovelProofreader()
    sig1 = pr._signature_from_lines("[B] a\n[B] b\n".splitlines())
    sig2 = pr._signature_from_lines("[B] a\n[B] c\n".splitlines())
    assert sig1 != sig2


def test_ab_signature_empty_returns_empty():
    pr = NovelProofreader()
    assert pr._signature_from_lines([]) == ''


# ============================================================
# Vocab matching (for AB vocab check)
# ============================================================

def test_count_chinese_characters():
    pr = NovelProofreader()
    assert pr._count_chinese_characters('你好世界') == 4
    assert pr._count_chinese_characters('hello สวัสดี') == 0
    assert pr._count_chinese_characters('') == 0


def test_normalize_vocab_text_strips_ws():
    pr = NovelProofreader()
    assert pr._normalize_vocab_text('  你 好  ') == '你好'


def test_strip_ab_prefix():
    pr = NovelProofreader()
    assert pr._strip_ab_prefix('[A] hello', 'A') == 'hello'
    assert pr._strip_ab_prefix('[B] world', 'B') == 'world'
    assert pr._strip_ab_prefix('plain text', 'A') == 'plain text'


# ============================================================
# Test runner
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
