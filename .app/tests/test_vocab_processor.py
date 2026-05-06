"""ทดสอบ vocab_processor — parser, frequency, sort, filter, dedup, prefix/suffix"""
import sys
import tempfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.vocab_processor import (  # noqa: E402
    parse_vocab_text,
    _split_vocab_line,
    VocabProcessor,
)


# ============================================================
# Mock uploaded file (mimics streamlit UploadedFile)
# ============================================================

class MockUploadedFile:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self.size = len(content)
        self._buf = io.BytesIO(content)

    def read(self, n=-1):
        return self._buf.read(n) if n != -1 else self._buf.read()

    def seek(self, pos: int):
        self._buf.seek(pos)


def _mock_text(name: str, text: str) -> MockUploadedFile:
    return MockUploadedFile(name, text.encode('utf-8'))


# ============================================================
# _split_vocab_line tests
# ============================================================

def test_split_tab():
    assert _split_vocab_line("你好\tสวัสดี") == ["你好", "สวัสดี"]


def test_split_pipe():
    assert _split_vocab_line("你好|สวัสดี") == ["你好", "สวัสดี"]


def test_split_pipe_with_spaces():
    assert _split_vocab_line("你好 | สวัสดี") == ["你好", "สวัสดี"]


def test_split_three_columns_pipe():
    assert _split_vocab_line("你好 | สวัสดี | greeting") == ["你好", "สวัสดี", "greeting"]


def test_split_three_columns_tab():
    assert _split_vocab_line("你好\tสวัสดี\tgreeting") == ["你好", "สวัสดี", "greeting"]


def test_split_mixed_separators():
    """ในบรรทัดเดียวมีทั้ง TAB และ pipe ก็ต้อง split ได้"""
    assert _split_vocab_line("你好\tสวัสดี | note") == ["你好", "สวัสดี", "note"]


def test_split_empty_line():
    assert _split_vocab_line("") == []


def test_split_strips_whitespace():
    assert _split_vocab_line("  你好  | สวัสดี  ") == ["你好", "สวัสดี"]


# ============================================================
# parse_vocab_text tests
# ============================================================

def test_parse_unified_formats():
    """ตรวจว่า parse ทุก format ในไฟล์เดียวกันได้"""
    text = """你好\tสวัสดี
精血|พลังเลือด
天空 | ท้องฟ้า | บน
强大\tทรงพลัง\tบรรยาย
"""
    records = parse_vocab_text(text, source_file='test.txt')
    assert len(records) == 4
    assert records[0]['cn'] == '你好'
    assert records[0]['th'] == 'สวัสดี'
    assert records[2]['columns'] == ['天空', 'ท้องฟ้า', 'บน']
    assert records[3]['columns'] == ['强大', 'ทรงพลัง', 'บรรยาย']


def test_parse_skips_blank_and_comments():
    text = """# comment
你好\tสวัสดี

# another
精血|พลังเลือด
"""
    records = parse_vocab_text(text)
    assert len(records) == 2


def test_parse_skips_header():
    text = """CN\tTH
你好\tสวัสดี
"""
    records = parse_vocab_text(text)
    assert len(records) == 1
    assert records[0]['cn'] == '你好'


def test_parse_chinese_header():
    text = """中文\t泰文
你好\tสวัสดี
"""
    records = parse_vocab_text(text)
    assert len(records) == 1


def test_parse_skips_invalid_lines():
    text = """only_one_column
你好\tสวัสดี
\t
"""
    records = parse_vocab_text(text)
    assert len(records) == 1


def test_parse_preserves_columns():
    text = "A\tB\tC\tD\nX\tY\tZ"
    records = parse_vocab_text(text)
    assert records[0]['columns'] == ['A', 'B', 'C', 'D']
    assert records[1]['columns'] == ['X', 'Y', 'Z']


def test_parse_empty_text():
    assert parse_vocab_text('') == []
    assert parse_vocab_text('   \n\n  ') == []


# ============================================================
# parse_uploaded_files (txt)
# ============================================================

def test_parse_uploaded_txt_files():
    vp = VocabProcessor()
    f1 = _mock_text('a.txt', "你好\tสวัสดี\n精血|พลังเลือด\n")
    f2 = _mock_text('b.tsv', "天空\tท้องฟ้า\tบน\n")
    records = vp.parse_uploaded_files([f1, f2])
    assert len(records) == 3
    sources = {r['source_file'] for r in records}
    assert sources == {'a.txt', 'b.tsv'}


# ============================================================
# Frequency / sort / filter tests
# ============================================================

def test_get_vocab_frequency():
    vp = VocabProcessor()
    items = [
        {'cn': '你好', 'th': 'สวัสดี'},
        {'cn': '你好', 'th': 'สวัสดี'},
        {'cn': '你好', 'th': 'สวัสดี'},
        {'cn': '精血', 'th': 'พลัง'},
    ]
    freq = vp.get_vocab_frequency(items)
    assert freq[('你好', 'สวัสดี')] == 3
    assert freq[('精血', 'พลัง')] == 1


def test_get_vocab_frequency_empty():
    vp = VocabProcessor()
    assert vp.get_vocab_frequency([]) == {}


def test_sort_vocab_by_length_desc():
    vp = VocabProcessor()
    items = [
        {'cn': '一', 'th': 'หนึ่ง'},
        {'cn': '一二三', 'th': 'หนึ่งสองสาม'},
        {'cn': '一二', 'th': 'หนึ่งสอง'},
    ]
    out = vp.sort_vocab_by_length(items, group_duplicates=False)
    assert [it['cn'] for it in out] == ['一二三', '一二', '一']


def test_sort_vocab_groups_duplicates():
    vp = VocabProcessor()
    items = [
        {'cn': '一', 'th': 'หนึ่ง'},
        {'cn': '一二', 'th': 'A'},
        {'cn': '一', 'th': 'หนึ่ง'},  # duplicate
    ]
    out = vp.sort_vocab_by_length(items, group_duplicates=True)
    # ยาวก่อน: '一二' มาก่อน '一' (× 2)
    assert out[0]['cn'] == '一二'
    assert out[1]['cn'] == '一'
    assert out[2]['cn'] == '一'


def test_sort_vocab_empty():
    vp = VocabProcessor()
    assert vp.sort_vocab_by_length([]) == []


def test_filter_by_frequency_min_2():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'a'},
        {'cn': 'A', 'th': 'a'},  # 2x
        {'cn': 'B', 'th': 'b'},  # 1x
        {'cn': 'C', 'th': 'c'},
        {'cn': 'C', 'th': 'c'},
        {'cn': 'C', 'th': 'c'},  # 3x
    ]
    out = vp.filter_vocab_by_frequency(items, min_frequency=2, include_duplicates=True)
    cns = sorted(it['cn'] for it in out)
    assert cns == ['A', 'A', 'C', 'C', 'C']


def test_filter_by_frequency_no_duplicates():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'a'},
        {'cn': 'A', 'th': 'a'},
        {'cn': 'B', 'th': 'b'},
    ]
    out = vp.filter_vocab_by_frequency(items, min_frequency=2, include_duplicates=False)
    assert len(out) == 1
    assert out[0]['cn'] == 'A'


def test_filter_by_frequency_no_match():
    vp = VocabProcessor()
    items = [{'cn': 'A', 'th': 'a'}]
    out = vp.filter_vocab_by_frequency(items, min_frequency=5)
    assert out == []


# ============================================================
# Sort prefix/suffix
# ============================================================

def test_sort_by_prefix():
    vp = VocabProcessor()
    items = [
        {'cn': '精血', 'th': 'A'},
        {'cn': '精血石', 'th': 'B'},
        {'cn': '精灵', 'th': 'C'},
        {'cn': '其他', 'th': 'D'},
    ]
    out = vp.sort_by_prefix_or_suffix(items, sort_by='prefix')
    assert len(out) == 4
    # ภายในกลุ่ม "精血*" → ยาวก่อน
    cns_in_order = [it['cn'] for it in out]
    # 精血石 ต้องอยู่ก่อน 精血 (ยาวกว่า)
    assert cns_in_order.index('精血石') < cns_in_order.index('精血')


def test_sort_by_suffix():
    vp = VocabProcessor()
    items = [
        {'cn': '红血', 'th': 'A'},
        {'cn': '黑血', 'th': 'B'},
        {'cn': '海水', 'th': 'C'},
        {'cn': '血', 'th': 'D'},
    ]
    out = vp.sort_by_prefix_or_suffix(items, sort_by='suffix')
    assert len(out) == 4


def test_sort_prefix_empty():
    vp = VocabProcessor()
    assert vp.sort_by_prefix_or_suffix([], 'prefix') == []


def test_sort_prefix_complexity_safe_for_large_input():
    """100k items must not blow up — ควรเสร็จไวเพราะ O(n log n)"""
    import time
    vp = VocabProcessor()
    items = [{'cn': f'word{i:05d}', 'th': f'tr{i}'} for i in range(10_000)]
    start = time.time()
    out = vp.sort_by_prefix_or_suffix(items, sort_by='prefix')
    elapsed = time.time() - start
    assert len(out) == 10_000
    assert elapsed < 5.0, f"too slow: {elapsed:.2f}s — should be O(n log n)"


# ============================================================
# Output writers
# ============================================================

def test_create_sort_vocab_output_writes_tab_separated():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': '你好', 'th': 'สวัสดี', 'columns': ['你好', 'สวัสดี']},
            {'cn': '精血', 'th': 'พลัง', 'columns': ['精血', 'พลัง', 'NOTE']},
        ]
        path = vp.create_sort_vocab_output(items, group_duplicates=False)
        text = Path(path).read_text(encoding='utf-8')
        # ต้องเป็น TAB separated และเก็บคอลัมน์ครบ
        lines = text.strip().split('\n')
        assert lines[0].count('\t') == 1   # cn\tth
        assert lines[1].count('\t') == 2   # cn\tth\tNOTE


def test_create_filter_vocab_output_writes_tab():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
            {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
            {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},
        ]
        path = vp.create_filter_vocab_output(items, min_frequency=2)
        text = Path(path).read_text(encoding='utf-8')
        # ต้องเหลือเฉพาะ A
        lines = [l for l in text.strip().split('\n') if l]
        # 2 instances of A (include_duplicates default True)
        for line in lines:
            assert line.startswith('A\t'), f"unexpected: {line}"


def test_duplicate_check_output():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': 'X', 'th': 'first', 'columns': ['X', 'first']},
            {'cn': 'X', 'th': 'second', 'columns': ['X', 'second']},
            {'cn': 'Y', 'th': 'unique', 'columns': ['Y', 'unique']},
        ]
        path = vp.create_duplicate_check_output(items)
        text = Path(path).read_text(encoding='utf-8')
        lines = [l for l in text.strip().split('\n') if l]
        # X duplicates ต้องอยู่ติดกันก่อน Y
        x_lines = [i for i, l in enumerate(lines) if l.startswith('X\t')]
        y_lines = [i for i, l in enumerate(lines) if l.startswith('Y\t')]
        assert len(x_lines) == 2
        assert len(y_lines) == 1
        assert max(x_lines) < min(y_lines), "duplicates should come before uniques"


# ============================================================
# NEW (2026-05-06): dedupe_by_pair / find_exact_duplicates /
# find_conflicting_translations / get_enhanced_statistics
# ============================================================

def test_dedupe_by_pair_keeps_first_of_each_pair():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
        {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},  # dupe
        {'cn': 'A', 'th': 'aa', 'columns': ['A', 'aa']},  # different th — keep
    ]
    result = vp.dedupe_by_pair(items)
    assert len(result) == 3
    assert (result[0]['cn'], result[0]['th']) == ('A', 'a')
    assert (result[1]['cn'], result[1]['th']) == ('B', 'b')
    assert (result[2]['cn'], result[2]['th']) == ('A', 'aa')


def test_dedupe_by_pair_empty():
    vp = VocabProcessor()
    assert vp.dedupe_by_pair([]) == []


def test_find_exact_duplicates_only_returns_pairs_with_count_ge_2():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
        {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},  # unique → excluded
        {'cn': 'C', 'th': 'c', 'columns': ['C', 'c']},
        {'cn': 'C', 'th': 'c', 'columns': ['C', 'c']},
        {'cn': 'C', 'th': 'c', 'columns': ['C', 'c']},
    ]
    result = vp.find_exact_duplicates(items)
    assert len(result) == 5  # 2 A's + 3 C's
    assert all(it['cn'] in ('A', 'C') for it in result)


def test_find_exact_duplicates_empty():
    vp = VocabProcessor()
    assert vp.find_exact_duplicates([]) == []


def test_find_conflicting_translations_returns_only_cn_with_multiple_th():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'one', 'columns': ['A', 'one']},
        {'cn': 'A', 'th': 'two', 'columns': ['A', 'two']},   # conflict
        {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},
        {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},        # same th — not conflict
        {'cn': 'C', 'th': 'first', 'columns': ['C', 'first']},
        {'cn': 'C', 'th': 'second', 'columns': ['C', 'second']},  # conflict
    ]
    result = vp.find_conflicting_translations(items)
    assert set(result.keys()) == {'A', 'C'}
    assert len(result['A']) == 2
    assert len(result['C']) == 2


def test_find_conflicting_translations_empty():
    vp = VocabProcessor()
    assert vp.find_conflicting_translations([]) == {}


def test_get_enhanced_statistics_basic():
    vp = VocabProcessor()
    items = [
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},   # exact dupe
        {'cn': 'A', 'th': 'aa', 'columns': ['A', 'aa']},  # conflict for A
        {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},
    ]
    s = vp.get_enhanced_statistics(items)
    assert s['total'] == 4
    assert s['unique_pairs'] == 3       # (A,a) (A,aa) (B,b)
    assert s['duplicate_entries'] == 1  # one extra (A,a)
    assert s['unique_cn'] == 2          # A and B
    assert s['conflict_cn_count'] == 1  # A has 2 different th's
    assert s['conflict_entries'] == 3   # all 3 entries with cn=A
    assert s['most_common_pair'] == (('A', 'a'), 2)


def test_get_enhanced_statistics_empty():
    vp = VocabProcessor()
    s = vp.get_enhanced_statistics([])
    assert s['total'] == 0
    assert s['unique_pairs'] == 0
    assert s['conflict_cn_count'] == 0
    assert s['most_common_pair'] is None


# ============================================================
# Output writers — sorted_unique / exact_duplicates / conflicts
# ============================================================

def test_create_unique_sorted_output_dedupes_and_sorts_long_first():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': 'X', 'th': 'a', 'columns': ['X', 'a']},
            {'cn': 'XYZ', 'th': 'b', 'columns': ['XYZ', 'b']},
            {'cn': 'X', 'th': 'a', 'columns': ['X', 'a']},  # dupe — drop
            {'cn': 'XY', 'th': 'c', 'columns': ['XY', 'c']},
        ]
        path = vp.create_unique_sorted_output(items)
        assert Path(path).name == 'sorted_unique.txt'
        lines = [l for l in Path(path).read_text(encoding='utf-8').splitlines() if l]
        assert len(lines) == 3, f"got {len(lines)} lines: {lines}"
        # Sorted long → short by CN length
        assert lines[0].startswith('XYZ\t')
        assert lines[1].startswith('XY\t')
        assert lines[2].startswith('X\t')


def test_create_exact_duplicates_output_groups_pairs_together():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
            {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},  # unique — excluded
            {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},
            {'cn': 'A', 'th': 'a', 'columns': ['A', 'a']},  # 3 A,a's
            {'cn': 'C', 'th': 'c', 'columns': ['C', 'c']},
            {'cn': 'C', 'th': 'c', 'columns': ['C', 'c']},  # 2 C,c's
        ]
        path = vp.create_exact_duplicates_output(items)
        assert Path(path).name == 'exact_duplicates.txt'
        lines = [l for l in Path(path).read_text(encoding='utf-8').splitlines() if l]
        assert len(lines) == 5  # excludes B
        # 3 A's first (largest group), then 2 C's
        assert lines[0].startswith('A\t')
        assert lines[1].startswith('A\t')
        assert lines[2].startswith('A\t')
        assert lines[3].startswith('C\t')
        assert lines[4].startswith('C\t')


def test_create_conflicts_output_includes_only_conflicting_cns():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = [
            {'cn': 'A', 'th': 'one', 'columns': ['A', 'one']},
            {'cn': 'A', 'th': 'two', 'columns': ['A', 'two']},
            {'cn': 'B', 'th': 'b', 'columns': ['B', 'b']},  # not conflict — exclude
            {'cn': 'C', 'th': 'first', 'columns': ['C', 'first']},
            {'cn': 'C', 'th': 'second', 'columns': ['C', 'second']},
            {'cn': 'C', 'th': 'third', 'columns': ['C', 'third']},
        ]
        path = vp.create_conflicts_output(items)
        assert Path(path).name == 'conflicts.txt'
        lines = [l for l in Path(path).read_text(encoding='utf-8').splitlines() if l]
        # 5 entries (A: 2 + C: 3); B excluded
        assert len(lines) == 5
        # No B in output
        assert not any(l.startswith('B\t') for l in lines)
        # C group (3 distinct th's) should come before A group (2 distinct th's)
        c_lines = [i for i, l in enumerate(lines) if l.startswith('C\t')]
        a_lines = [i for i, l in enumerate(lines) if l.startswith('A\t')]
        assert max(c_lines) < min(a_lines), \
            "C (more distinct th) should come before A"


# ============================================================
# apply_pipeline — composer (filter + sort)
# ============================================================

def _make_items():
    return [
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a'], 'source_file': 'f1'},
        {'cn': 'A', 'th': 'a', 'columns': ['A', 'a'], 'source_file': 'f2'},  # exact dupe
        {'cn': 'A', 'th': 'aa', 'columns': ['A', 'aa'], 'source_file': 'f1'},  # conflict
        {'cn': 'BBB', 'th': 'b', 'columns': ['BBB', 'b'], 'source_file': 'f1'},
        {'cn': 'CC', 'th': 'c', 'columns': ['CC', 'c'], 'source_file': 'f2'},
        {'cn': 'CC', 'th': 'c', 'columns': ['CC', 'c'], 'source_file': 'f1'},
    ]


def test_apply_pipeline_no_filters_no_sort():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, sort_by='none')
    assert len(result) == len(items)
    # original order preserved
    assert result[0]['cn'] == 'A' and result[0]['th'] == 'a'
    assert result[-1]['cn'] == 'CC'


def test_apply_pipeline_dedupe_only():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='none')
    # 4 unique pairs: (A,a), (A,aa), (BBB,b), (CC,c)
    assert len(result) == 4


def test_apply_pipeline_only_conflicts():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, only_conflicts=True, sort_by='none')
    # All 3 entries with cn=A (only A has multiple th)
    assert len(result) == 3
    assert all(it['cn'] == 'A' for it in result)


def test_apply_pipeline_only_exact_duplicates():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, only_exact_duplicates=True, sort_by='none')
    # (A,a) appears 2x + (CC,c) appears 2x → 4 entries
    assert len(result) == 4
    # No (A,aa) or (BBB,b)
    keys = {(it['cn'], it['th']) for it in result}
    assert keys == {('A', 'a'), ('CC', 'c')}


def test_apply_pipeline_min_frequency():
    vp = VocabProcessor()
    items = _make_items()
    # Only pairs with freq >= 2
    result = vp.apply_pipeline(items, min_frequency=2, sort_by='none')
    assert len(result) == 4
    keys = {(it['cn'], it['th']) for it in result}
    assert keys == {('A', 'a'), ('CC', 'c')}


def test_apply_pipeline_max_frequency():
    vp = VocabProcessor()
    items = _make_items()
    # Only pairs with freq <= 1
    result = vp.apply_pipeline(items, max_frequency=1, sort_by='none')
    # (A,aa) and (BBB,b) appear 1x
    assert len(result) == 2
    keys = {(it['cn'], it['th']) for it in result}
    assert keys == {('A', 'aa'), ('BBB', 'b')}


def test_apply_pipeline_min_cn_length():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, min_cn_length=2, sort_by='none')
    # CN with >= 2 chars: BBB, CC, CC
    assert len(result) == 3
    assert all(len(it['cn']) >= 2 for it in result)


def test_apply_pipeline_max_cn_length():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, max_cn_length=2, sort_by='none')
    # CN with <= 2 chars: A, A, A, CC, CC
    assert len(result) == 5
    assert all(len(it['cn']) <= 2 for it in result)


def test_apply_pipeline_search_text_matches_cn_or_th():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, search_text='aa', sort_by='none')
    # Only (A,aa) matches "aa"
    assert len(result) == 1
    assert result[0]['cn'] == 'A' and result[0]['th'] == 'aa'


def test_apply_pipeline_source_files_filter():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, source_files={'f1'}, sort_by='none')
    assert all(it['source_file'] == 'f1' for it in result)
    assert len(result) == 4


def test_apply_pipeline_limit_after_sort():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, limit=2, sort_by='length_desc')
    # length_desc: BBB (3) first, then CC's (2)
    assert len(result) == 2
    assert result[0]['cn'] == 'BBB'


def test_apply_pipeline_sort_length_desc():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='length_desc')
    # Length: BBB(3), CC(2), A(1) — A first since 2 distinct (A,a) and (A,aa)
    lengths = [len(it['cn']) for it in result]
    assert lengths == sorted(lengths, reverse=True)


def test_apply_pipeline_sort_length_asc():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='length_asc')
    lengths = [len(it['cn']) for it in result]
    assert lengths == sorted(lengths)


def test_apply_pipeline_sort_frequency_desc():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='frequency_desc')
    # (A,a) and (CC,c) both freq=2, others freq=1 — top entries should be freq=2
    top_keys = {(result[0]['cn'], result[0]['th']),
                (result[1]['cn'], result[1]['th'])}
    assert top_keys == {('A', 'a'), ('CC', 'c')}


def test_apply_pipeline_sort_frequency_asc():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='frequency_asc')
    # First two should be freq=1
    bottom_keys = {(result[0]['cn'], result[0]['th']),
                   (result[1]['cn'], result[1]['th'])}
    assert bottom_keys == {('A', 'aa'), ('BBB', 'b')}


def test_apply_pipeline_sort_group_by_cn():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, sort_by='group_by_cn')
    # Group with 3 entries (A) first, then group of 2 (CC), then 1 (BBB)
    assert result[0]['cn'] == result[1]['cn'] == result[2]['cn'] == 'A'
    assert result[3]['cn'] == result[4]['cn'] == 'CC'
    assert result[5]['cn'] == 'BBB'


def test_apply_pipeline_sort_alpha_cn():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='alpha_cn')
    cns = [it['cn'] for it in result]
    assert cns == sorted(cns)


def test_apply_pipeline_sort_alpha_th():
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(items, dedupe_pairs=True, sort_by='alpha_th')
    ths = [it['th'] for it in result]
    assert ths == sorted(ths)


def test_apply_pipeline_combined_filters_and_sort():
    """Combo: only_exact_duplicates + dedupe + sort length_desc."""
    vp = VocabProcessor()
    items = _make_items()
    result = vp.apply_pipeline(
        items,
        only_exact_duplicates=True,
        dedupe_pairs=True,
        sort_by='length_desc',
    )
    # Exact dupes: (A,a) and (CC,c). After dedupe: 2 items. CC longer.
    assert len(result) == 2
    assert result[0]['cn'] == 'CC'
    assert result[1]['cn'] == 'A'


def test_apply_pipeline_empty_input():
    vp = VocabProcessor()
    assert vp.apply_pipeline([]) == []


def test_create_pipeline_output_writes_filename():
    with tempfile.TemporaryDirectory() as td:
        vp = VocabProcessor()
        vp.output_dir = Path(td)
        items = _make_items()
        path = vp.create_pipeline_output(
            items, filename="my_test.tsv",
            dedupe_pairs=True, sort_by='length_desc',
        )
        assert Path(path).name == "my_test.tsv"
        assert Path(path).exists()
        text = Path(path).read_text(encoding='utf-8')
        assert text.startswith('BBB\t'), f"first line should be BBB: {text[:30]}"


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
