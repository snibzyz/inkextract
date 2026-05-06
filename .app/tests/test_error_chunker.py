"""ทดสอบ error_chunker — split errors + filename helpers"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.error_chunker import (  # noqa: E402
    split_errors_into_parts,
    build_part_filename,
    is_import_part_filename,
    find_import_parts,
)


# ============================================================
# split_errors_into_parts
# ============================================================

def test_split_no_partsize_returns_single_chunk():
    errs = [1, 2, 3, 4, 5]
    result = split_errors_into_parts(errs, 0)
    assert result == [[1, 2, 3, 4, 5]]


def test_split_negative_partsize_returns_single_chunk():
    errs = [1, 2, 3]
    result = split_errors_into_parts(errs, -5)
    assert result == [[1, 2, 3]]


def test_split_partsize_larger_than_total_returns_single():
    errs = [1, 2, 3]
    result = split_errors_into_parts(errs, 100)
    assert result == [[1, 2, 3]]


def test_split_evenly_divides():
    errs = list(range(1, 7))  # [1..6]
    result = split_errors_into_parts(errs, 2)
    assert result == [[1, 2], [3, 4], [5, 6]]


def test_split_uneven_last_chunk_smaller():
    errs = list(range(1, 8))  # [1..7]
    result = split_errors_into_parts(errs, 3)
    assert result == [[1, 2, 3], [4, 5, 6], [7]]


def test_split_empty_list():
    assert split_errors_into_parts([], 5) == [[]]


def test_split_preserves_order():
    errs = ['a', 'b', 'c', 'd', 'e']
    result = split_errors_into_parts(errs, 2)
    flat = [x for chunk in result for x in chunk]
    assert flat == errs


# ============================================================
# build_part_filename
# ============================================================

def test_build_filename_single_part_returns_base():
    assert build_part_filename("error_trans.txt", 0, 1) == "error_trans.txt"


def test_build_filename_zero_total_returns_base():
    assert build_part_filename("foo.txt", 0, 0) == "foo.txt"


def test_build_filename_pads_index_to_3_digits():
    assert build_part_filename("error_trans.txt", 0, 5) == "error_trans_001.txt"
    assert build_part_filename("error_trans.txt", 1, 5) == "error_trans_002.txt"
    assert build_part_filename("error_trans.txt", 9, 12) == "error_trans_010.txt"


def test_build_filename_no_extension():
    assert build_part_filename("README", 0, 3) == "README_001"


def test_build_filename_multiple_dots_uses_last():
    assert build_part_filename("data.tar.gz", 0, 3) == "data.tar_001.gz"


def test_build_filename_hidden_file_no_split():
    # leading dot file (.gitignore) — dot at index 0, treat as no extension
    assert build_part_filename(".hidden", 0, 3) == ".hidden_001"


# ============================================================
# is_import_part_filename
# ============================================================

def test_is_part_matches_exact_base():
    assert is_import_part_filename("error_trans.txt", "error_trans.txt") is True


def test_is_part_matches_split_form():
    assert is_import_part_filename("error_trans_001.txt", "error_trans.txt") is True
    assert is_import_part_filename("error_trans_999.txt", "error_trans.txt") is True


def test_is_part_rejects_unrelated_name():
    assert is_import_part_filename("other.txt", "error_trans.txt") is False
    assert is_import_part_filename("error.txt", "error_trans.txt") is False


def test_is_part_rejects_wrong_suffix_length():
    # _01 (2 digits) instead of _001 (3 digits) → reject
    assert is_import_part_filename("error_trans_01.txt", "error_trans.txt") is False
    assert is_import_part_filename("error_trans_0001.txt", "error_trans.txt") is False


def test_is_part_case_insensitive():
    assert is_import_part_filename("ERROR_TRANS.TXT", "error_trans.txt") is True
    assert is_import_part_filename("Error_Trans_001.Txt", "error_trans.txt") is True


def test_is_part_special_chars_in_base():
    assert is_import_part_filename("foo.bar_001.txt", "foo.bar.txt") is True


# ============================================================
# find_import_parts
# ============================================================

def test_find_parts_returns_empty_for_missing_dir():
    result = find_import_parts(Path("/definitely/does/not/exist"), "x.txt")
    assert result == []


def test_find_parts_picks_only_matching_files():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "error_trans.txt").write_text("a")
        (d / "error_trans_001.txt").write_text("b")
        (d / "error_trans_002.txt").write_text("c")
        (d / "other.txt").write_text("ignore me")
        (d / "subdir").mkdir()

        result = find_import_parts(d, "error_trans.txt")
        names = [p.name for p in result]
        assert "error_trans.txt" in names
        assert "error_trans_001.txt" in names
        assert "error_trans_002.txt" in names
        assert "other.txt" not in names


def test_find_parts_returns_sorted():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "x_003.txt").write_text("c")
        (d / "x_001.txt").write_text("a")
        (d / "x_002.txt").write_text("b")
        result = find_import_parts(d, "x.txt")
        names = [p.name for p in result]
        assert names == ["x_001.txt", "x_002.txt", "x_003.txt"]


# ============================================================
# Round-trip: split + build_part + is_part_match
# ============================================================

def test_roundtrip_split_build_match():
    errs = list(range(1, 16))  # 15 items
    chunks = split_errors_into_parts(errs, 5)
    assert len(chunks) == 3
    base = "errors.txt"
    for i, chunk in enumerate(chunks):
        name = build_part_filename(base, i, len(chunks))
        assert is_import_part_filename(name, base), f"{name} should match {base}"


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
