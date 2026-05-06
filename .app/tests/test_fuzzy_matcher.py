"""ทดสอบ fuzzy_matcher — bigram similarity + best-error matching"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.fuzzy_matcher import (  # noqa: E402
    bigram_similarity,
    normalize_import_text,
    strip_ab_prefix,
    build_exact_index,
    find_best_error_by_a,
)


# ============================================================
# normalize / strip
# ============================================================

def test_normalize_strips_whitespace_and_lowercases():
    assert normalize_import_text("  Hello World  ") == "helloworld"


def test_normalize_handles_empty():
    assert normalize_import_text("") == ""
    assert normalize_import_text(None) == ""


def test_normalize_collapses_internal_whitespace():
    assert normalize_import_text("a\tb  c\nd") == "abcd"


def test_strip_ab_prefix_a():
    assert strip_ab_prefix("[A] hello world", "A") == "hello world"


def test_strip_ab_prefix_b():
    assert strip_ab_prefix("[B] สวัสดี", "B") == "สวัสดี"


def test_strip_ab_prefix_no_prefix():
    assert strip_ab_prefix("plain text", "A") == "plain text"


def test_strip_ab_prefix_empty():
    assert strip_ab_prefix("", "A") == ""


# ============================================================
# bigram_similarity
# ============================================================

def test_bigram_identical_strings_return_1():
    assert bigram_similarity("hello", "hello") == 1.0


def test_bigram_completely_different_returns_0():
    # No bigrams in common
    assert bigram_similarity("abc", "xyz") == 0.0


def test_bigram_empty_returns_0():
    assert bigram_similarity("", "anything") == 0.0
    assert bigram_similarity("anything", "") == 0.0


def test_bigram_one_char_strings():
    # No bigrams possible — falls back to char eq
    assert bigram_similarity("a", "a") == 1.0
    assert bigram_similarity("a", "b") == 0.0


def test_bigram_high_similarity_for_typo():
    # "the quick brown" vs "the quik brown" (one char missing)
    score = bigram_similarity("thequickbrown", "thequikbrown")
    assert score > 0.85, f"expected >0.85, got {score}"


def test_bigram_thai_text():
    # Same content, identical
    score = bigram_similarity("สวัสดีชาวโลก", "สวัสดีชาวโลก")
    assert score == 1.0


def test_bigram_thai_one_char_diff():
    # ชาวโลก vs ชาวกลก (1 char different)
    score = bigram_similarity("สวัสดีชาวโลก", "สวัสดีชาวกลก")
    assert 0.7 <= score < 1.0, f"expected 0.7..1.0, got {score}"


def test_bigram_chinese_text():
    score = bigram_similarity("不朽的境界", "不朽的境界")
    assert score == 1.0


def test_bigram_partial_overlap():
    # Half common
    score = bigram_similarity("abcdef", "abcxyz")
    # bigrams a: ab,bc,cd,de,ef (5)  b: ab,bc,cx,xy,yz (5)
    # common: ab, bc → 2
    # ratio = 2*2 / (5+5) = 0.4
    assert 0.3 <= score <= 0.5


# ============================================================
# build_exact_index + find_best_error_by_a
# ============================================================

def _make_errors():
    """Sample errors mimicking the proofreader output format."""
    return [
        {
            'original_a': '[A] The quick brown fox jumps',
            'file_name': 'chapter1.txt',
            'file_path': '/data/chapter1.txt',
            'line_number': 10,
        },
        {
            'original_a': '[A] Lazy dog runs fast indeed',
            'file_name': 'chapter1.txt',
            'file_path': '/data/chapter1.txt',
            'line_number': 25,
        },
        {
            'original_a': '[A] Different content entirely here',
            'file_name': 'chapter2.txt',
            'file_path': '/data/chapter2.txt',
            'line_number': 5,
        },
    ]


def test_build_exact_index_keys_by_normalized_a():
    errs = _make_errors()
    idx = build_exact_index(errs)
    assert len(idx) == 3
    assert 'thequickbrownfoxjumps' in idx


def test_find_best_exact_match():
    errs = _make_errors()
    idx = build_exact_index(errs)
    needle = normalize_import_text('[A] The quick brown fox jumps')
    needle = normalize_import_text(strip_ab_prefix(
        '[A] The quick brown fox jumps'))
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='chapter1.txt',
        hint_line_number=10,
    )
    assert res is not None
    assert res['match_type'] == 'exact'
    assert res['ratio'] == 1.0
    assert res['error']['line_number'] == 10


def test_find_best_fuzzy_match_for_typo():
    errs = _make_errors()
    idx = build_exact_index(errs)
    # Same content but with 1-char typo + extra space (would fail exact)
    needle = normalize_import_text(strip_ab_prefix(
        '[A] The quik brown fox jumps'))  # "quick" → "quik"
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='chapter1.txt',
        hint_line_number=10,
        min_ratio=0.85,
    )
    assert res is not None, "should find fuzzy match for 1-char typo"
    assert res['match_type'] == 'fuzzy'
    assert res['ratio'] >= 0.85
    assert res['error']['line_number'] == 10


def test_find_no_match_for_completely_different():
    errs = _make_errors()
    idx = build_exact_index(errs)
    needle = normalize_import_text(strip_ab_prefix(
        '[A] Totally unrelated XYZ content abcdefg'))
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='chapter1.txt',
        hint_line_number=10,
        min_ratio=0.85,
    )
    assert res is None


def test_find_short_needle_skips_fuzzy():
    """needle < fuzzy_min_length (12) → no fuzzy match (avoid false positive)."""
    errs = [
        {'original_a': '[A] short', 'file_name': 'a.txt',
         'file_path': '/a.txt', 'line_number': 1},
    ]
    idx = build_exact_index(errs)
    needle = normalize_import_text('shor')  # 4 chars
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='a.txt',
        hint_line_number=1,
    )
    assert res is None  # too short for fuzzy


def test_exact_match_ranked_by_filename_hint():
    """When 2 exact matches in different files, prefer same-filename hint."""
    errs = [
        {'original_a': '[A] same content', 'file_name': 'a.txt',
         'file_path': '/a.txt', 'line_number': 1},
        {'original_a': '[A] same content', 'file_name': 'b.txt',
         'file_path': '/b.txt', 'line_number': 1},
    ]
    idx = build_exact_index(errs)
    needle = normalize_import_text(strip_ab_prefix('[A] same content'))
    # hint: file b.txt → should pick b.txt
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='b.txt',
        hint_line_number=1,
    )
    assert res is not None
    assert res['error']['file_name'] == 'b.txt'


def test_fuzzy_rejects_ambiguous_top2_different_files():
    """Top-2 too close + different files → return None (don't guess)."""
    errs = [
        {'original_a': '[A] hello world how are you today friend',
         'file_name': 'a.txt', 'file_path': '/a.txt', 'line_number': 1},
        {'original_a': '[A] hello world how are you today friend',
         'file_name': 'b.txt', 'file_path': '/b.txt', 'line_number': 99},
    ]
    idx = build_exact_index(errs)
    # needle nearly identical (one char) — would tie via fuzzy if exact failed
    # but exact will fire first since both = same normalized
    needle = normalize_import_text(strip_ab_prefix(
        '[A] hello world how are you today fiend'))  # 'friend' → 'fiend'
    res = find_best_error_by_a(
        needle_normalized_a=needle,
        exact_index=idx,
        all_errors=errs,
        hint_file_name='unknown.txt',  # neither file matches
        hint_line_number=50,
        min_ratio=0.85,
    )
    # tied 2 candidates from different files with no hint advantage → reject
    assert res is None, "should reject ambiguous tie across different files"


def test_empty_needle_returns_none():
    res = find_best_error_by_a(
        needle_normalized_a='',
        exact_index={},
        all_errors=[],
    )
    assert res is None


def test_no_errors_returns_none():
    res = find_best_error_by_a(
        needle_normalized_a='hello',
        exact_index={},
        all_errors=[],
    )
    assert res is None


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
