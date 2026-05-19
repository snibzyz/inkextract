"""ทดสอบ TextClassifier + RegexPatterns — เคารพ checkbox semantics

ครอบคลุม:
- digits ทุก script (ASCII / fullwidth / Arabic-Indic / Thai / Devanagari) ต้องไปหมวด "ตัวเลข" ไม่ตก foreign
- letters Latin (ASCII / fullwidth) ต้องไปหมวด "ภาษาอังกฤษ" ไม่ตก foreign
- foreign scripts (CJK / Cyrillic / Korean / Arabic letters / Greek) ต้องตก "ภาษาต่างประเทศ"
- fullwidth punctuation (！？) = foreign (CJK typography artifact)
- invisible/format chars (ZWSP/ZWNJ/ZWJ/LRM/RLM/bidi) ต้องตก foreign
- [A]/[B] markers ต้อง skip
- should_flag / get_category_labels เคารพ checkbox
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.core import TextClassifier  # noqa: E402


# ============================================================
# Digits — ทุก script ต้องไปหมวด "ตัวเลข" ไม่ตก foreign
# ============================================================

def test_ascii_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 12 ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


def test_fullwidth_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี １２ ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


def test_arabic_indic_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี ١٢ ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


def test_thai_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี ๑๒ ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


def test_persian_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี ۱۲ ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


def test_devanagari_digits_go_to_numbers_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี १२ ตัว", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': True}


# ============================================================
# Letters — Latin ทุก variant ต้องไปหมวด "ภาษาอังกฤษ"
# ============================================================

def test_ascii_latin_go_to_english_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก OK", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': True, 'numbers': False}


def test_fullwidth_latin_go_to_english_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก ＯＫ", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': True, 'numbers': False}


def test_fullwidth_lowercase_go_to_english_only():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก ｈｅｌｌｏ", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': True, 'numbers': False}


# ============================================================
# Foreign scripts — ตก "ภาษาต่างประเทศ"
# ============================================================

def test_chinese_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก 你好", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_japanese_hiragana_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก こんにちは", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_japanese_katakana_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก カタカナ", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_halfwidth_katakana_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก ｱｲｳ ครับ", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_korean_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก 안녕", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_russian_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก Привет", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_arabic_letters_flag_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก أبجد", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_greek_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("ค่า α + β", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_hebrew_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก שלום", skip_ab_markers=False)
    assert flags['foreign'] is True


# ============================================================
# Fullwidth punctuation = CJK typography artifact = foreign
# ============================================================

def test_fullwidth_exclamation_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก！ครับ", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_fullwidth_question_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขาถาม？", skip_ab_markers=False)
    assert flags['foreign'] is True


def test_fullwidth_comma_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี，สอง", skip_ab_markers=False)
    assert flags['foreign'] is True


# ============================================================
# Invisible / format chars — ZWSP / ZWNJ / ZWJ / LRM / RLM / bidi
# ============================================================

def test_zwsp_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา​เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "ZWSP (U+200B) ต้องตรวจเจอ"


def test_zwnj_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา‌เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "ZWNJ (U+200C) ต้องตรวจเจอ"


def test_zwj_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา‍เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "ZWJ (U+200D) ต้องตรวจเจอ"


def test_lrm_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา‎เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "LRM (U+200E) ต้องตรวจเจอ"


def test_rlm_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา‏เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "RLM (U+200F) ต้องตรวจเจอ"


def test_word_joiner_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา⁠เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "WORD JOINER (U+2060) ต้องตรวจเจอ"


def test_bom_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("﻿เขาเดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "BOM/ZWNBSP (U+FEFF) ต้องตรวจเจอ"


def test_soft_hyphen_flags_foreign():
    tc = TextClassifier()
    flags = tc.classify_text("เขา­เดิน", skip_ab_markers=False)
    assert flags['foreign'] is True, "SOFT HYPHEN (U+00AD) ต้องตรวจเจอ"


# ============================================================
# Clean Thai text — ไม่ flag อะไรเลย
# ============================================================

def test_clean_thai_no_flags():
    tc = TextClassifier()
    flags = tc.classify_text("เขาเดินไปตลาดซื้อของกินกลับบ้าน", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


def test_thai_with_punctuation_no_flags():
    tc = TextClassifier()
    flags = tc.classify_text("เขาถาม: \"คุณสบายดีไหม?\" — \"สบายดี\".", skip_ab_markers=False)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


# ============================================================
# Mixed — flags ที่ทับซ้อนกัน
# ============================================================

def test_chinese_and_digits_flag_both():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 你好 5 ตัว", skip_ab_markers=False)
    assert flags['foreign'] is True
    assert flags['numbers'] is True
    assert flags['english'] is False


def test_arabic_letters_and_arabic_digits():
    """อักษรอาหรับ → foreign, ตัวเลขอาหรับ → numbers (แยกหมวด)"""
    tc = TextClassifier()
    flags = tc.classify_text("เขามี ١٢ أبجد", skip_ab_markers=False)
    assert flags['foreign'] is True
    assert flags['numbers'] is True


# ============================================================
# [A] / [B] markers — skip
# ============================================================

def test_skip_a_marker_with_chinese():
    tc = TextClassifier()
    flags = tc.classify_text("[A] 这是中文", skip_ab_markers=True)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


def test_skip_b_marker_with_english():
    tc = TextClassifier()
    flags = tc.classify_text("[B] this is english", skip_ab_markers=True)
    assert flags == {'foreign': False, 'english': False, 'numbers': False}


def test_no_skip_when_disabled():
    """ถ้า skip_ab_markers=False ต้องตรวจปกติ"""
    tc = TextClassifier()
    flags = tc.classify_text("[A] 这是中文", skip_ab_markers=False)
    assert flags['foreign'] is True


# ============================================================
# should_flag — เคารพ checkbox
# ============================================================

def test_should_flag_foreign_only_ticked_excludes_numbers():
    """ถ้าติ๊กแค่ foreign บรรทัดที่มีแค่ตัวเลข ASCII ต้อง NOT flag"""
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 12 ตัว", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is False


def test_should_flag_foreign_only_ticked_excludes_fullwidth_digits():
    """user rule: ตัวเลข fullwidth ไม่ตก foreign"""
    tc = TextClassifier()
    flags = tc.classify_text("เขามี １２ ตัว", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is False


def test_should_flag_foreign_only_ticked_excludes_arabic_indic_digits():
    """user rule: ตัวเลขทุก script ไม่ตก foreign"""
    tc = TextClassifier()
    flags = tc.classify_text("เขามี ١٢ ตัว", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is False


def test_should_flag_foreign_only_ticked_excludes_english():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก OK", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is False


def test_should_flag_foreign_only_ticked_excludes_fullwidth_latin():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก ＯＫ", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is False


def test_should_flag_foreign_only_ticked_catches_chinese():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก 你好", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=True, check_english=False, check_numbers=False) is True


def test_should_flag_numbers_only_ticked_catches_fullwidth_digits():
    """ติ๊กแค่ numbers — fullwidth digits ต้อง flag"""
    tc = TextClassifier()
    flags = tc.classify_text("เขามี １２ ตัว", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=False, check_english=False, check_numbers=True) is True


def test_should_flag_english_only_ticked_catches_fullwidth_latin():
    tc = TextClassifier()
    flags = tc.classify_text("เขาบอก ＯＫ", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=False, check_english=True, check_numbers=False) is True


def test_should_flag_nothing_ticked_returns_false():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 你好 12", skip_ab_markers=False)
    assert tc.should_flag(flags, check_foreign=False, check_english=False, check_numbers=False) is False


# ============================================================
# get_category_labels — เคารพ checkbox
# ============================================================

def test_labels_only_for_ticked_categories():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 你好 12 OK", skip_ab_markers=False)
    # ติ๊กทั้งหมด
    labels = tc.get_category_labels(flags, True, True, True)
    assert 'ภาษาต่างประเทศ' in labels
    assert 'ภาษาอังกฤษ' in labels
    assert 'ตัวเลข' in labels


def test_labels_skip_unticked_categories():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 你好 12 OK", skip_ab_markers=False)
    # ติ๊กแค่ foreign
    labels = tc.get_category_labels(flags, True, False, False)
    assert labels == ['ภาษาต่างประเทศ']


def test_labels_empty_when_nothing_ticked():
    tc = TextClassifier()
    flags = tc.classify_text("เขามี 你好 12 OK", skip_ab_markers=False)
    labels = tc.get_category_labels(flags, False, False, False)
    assert labels == []


# ============================================================
# FileAnalyzer — oversize / too-many-lines warn but scan anyway
# ============================================================

def test_oversize_file_scanned_with_warning(tmp_path=None):
    """ไฟล์เกิน max_file_size ต้องสแกนต่อ (ไม่ silent-skip)"""
    import tempfile
    from modules.core import FileAnalyzer
    from modules.config import app_config

    saved = app_config.max_file_size
    app_config.max_file_size = 100  # 100 bytes
    try:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "big.txt"
            # >100 bytes with foreign content
            p.write_text("เขาเดิน\nเขาบอก 你好\n" * 20, encoding='utf-8')
            fa = FileAnalyzer()
            errs = fa.analyze_file_content(p, check_foreign=True, check_english=False, check_numbers=False)
            assert len(errs) > 0, "ต้องสแกนต่อแม้ไฟล์เกิน limit"
    finally:
        app_config.max_file_size = saved


def test_too_many_lines_scanned_with_warning():
    """ไฟล์เกิน max_lines_per_file ต้องสแกนต่อ (ไม่ silent-skip)"""
    import tempfile
    from modules.core import FileAnalyzer
    from modules.config import app_config

    saved = app_config.max_lines_per_file
    app_config.max_lines_per_file = 5
    try:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "many.txt"
            p.write_text("เขาบอก 你好\n" * 10, encoding='utf-8')  # 10 lines
            fa = FileAnalyzer()
            errs = fa.analyze_file_content(p, check_foreign=True, check_english=False, check_numbers=False)
            assert len(errs) == 10, "ต้องสแกนทั้ง 10 บรรทัด แม้เกิน limit"
    finally:
        app_config.max_lines_per_file = saved


# ============================================================
if __name__ == '__main__':
    import inspect
    tests = [(n, f) for n, f in inspect.getmembers(sys.modules[__name__])
             if n.startswith('test_') and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  PASS {name}')
            passed += 1
        except AssertionError as e:
            print(f'  FAIL {name}: {e}')
            failed += 1
        except Exception as e:
            print(f'  ERR  {name}: {type(e).__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
