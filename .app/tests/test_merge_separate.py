"""ทดสอบ merge_processor + separate_processor"""
import sys
import tempfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.merge_processor import MergeProcessor  # noqa: E402
from modules.separate_processor import SeparateProcessor  # noqa: E402


# ============================================================
# Mock UploadedFile
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


# ============================================================
# MergeProcessor tests
# ============================================================

def test_merge_into_single_file():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'; src.mkdir()
        out = base / 'out'; out.mkdir()
        for i in range(1, 6):
            (src / f'ch {i:03d}.txt').write_text(f'content {i}', encoding='utf-8')

        mp = MergeProcessor()
        files = mp.merge_output(
            chapters_per_file=0,  # all in one
            end_credit='จบตอน',
            focus_keyword='ตอนที่',
            title_prefix='Chapter ',
            title_suffix='',
            chapter_number_padding=3,
            start_number=1,
            source_path=src,
            output_folder=out,
        )
        assert len(files) == 1
        text = files[0].read_text(encoding='utf-8')
        # ทุกตอนต้องมีในไฟล์
        for i in range(1, 6):
            assert f'content {i}' in text
        # มี end credit
        assert 'จบตอน' in text


def test_merge_split_by_chapters_per_file():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'; src.mkdir()
        out = base / 'out'; out.mkdir()
        for i in range(1, 11):
            (src / f'ch {i:03d}.txt').write_text(f'c{i}', encoding='utf-8')

        mp = MergeProcessor()
        files = mp.merge_output(
            chapters_per_file=3,
            end_credit='',
            focus_keyword='',
            title_prefix='Chapter ',
            title_suffix='',
            chapter_number_padding=3,
            start_number=1,
            source_path=src,
            output_folder=out,
        )
        # 10 ตอน / 3 ต่อไฟล์ = 4 ไฟล์ (3,3,3,1)
        assert len(files) == 4


def test_merge_no_files():
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 'empty'; src.mkdir()
        out = Path(td) / 'out'; out.mkdir()
        mp = MergeProcessor()
        files = mp.merge_output(0, '', 'ตอนที่', 'C ', '', 3, 1, source_path=src, output_folder=out)
        assert files == []


def test_merge_with_chapter_heading():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); src = base / 's'; src.mkdir(); out = base / 'o'; out.mkdir()
        (src / 'a 001.txt').write_text('body', encoding='utf-8')
        mp = MergeProcessor()
        files = mp.merge_output(
            0, '', 'นิยาย', 'ตอนที่ ', '',
            3, 5, source_path=src, output_folder=out,
            add_chapter_heading=True,
        )
        text = files[0].read_text(encoding='utf-8')
        # heading: "นิยาย ตอนที่ 005"
        assert 'นิยาย ตอนที่ 005' in text


def test_merge_get_available_files_sorted():
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 's'; src.mkdir()
        # สร้างไฟล์ไม่เรียง
        for i in [3, 1, 10, 2]:
            (src / f'ch {i:03d}.txt').write_text('x', encoding='utf-8')
        mp = MergeProcessor()
        files = mp.get_available_files(source_path=src)
        nums = [int(f.stem.split()[-1]) for f in files]
        assert nums == [1, 2, 3, 10]


def test_merge_with_selected_files():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td); src = base / 's'; src.mkdir(); out = base / 'o'; out.mkdir()
        for i in range(1, 6):
            (src / f'ch {i:03d}.txt').write_text(f'c{i}', encoding='utf-8')
        # เลือกแค่ 1, 3, 5
        selected = [src / 'ch 001.txt', src / 'ch 003.txt', src / 'ch 005.txt']
        mp = MergeProcessor()
        files = mp.merge_output(
            0, '', '', 'M ', '', 3, 1,
            source_path=src, output_folder=out, selected_files=selected,
        )
        text = files[0].read_text(encoding='utf-8')
        assert 'c1' in text and 'c3' in text and 'c5' in text
        assert 'c2' not in text and 'c4' not in text


# ============================================================
# SeparateProcessor tests
# ============================================================

def test_separate_uploaded_basic():
    with tempfile.TemporaryDirectory() as td:
        sp = SeparateProcessor()
        sp.separate_dir = Path(td)

        content = (
            "บทที่ 001 ชื่อเรื่อง 1\n"
            "เนื้อหา 1\n"
            "เนื้อหา 1.1\n"
            "บทที่ 002 ชื่อเรื่อง 2\n"
            "เนื้อหา 2\n"
        )
        files = sp.separate_uploaded(content, focus_keyword='บทที่', strip_end_credit='')
        assert len(files) == 2
        # ตรวจชื่อไฟล์ใช้ส่วนหลัง keyword
        names = [f.name for f in files]
        assert any('001' in n for n in names)
        assert any('002' in n for n in names)


def test_separate_uploaded_strips_end_credit():
    with tempfile.TemporaryDirectory() as td:
        sp = SeparateProcessor()
        sp.separate_dir = Path(td)
        content = (
            "บท 1\n"
            "content\n"
            "จบตอน\n"
        )
        files = sp.separate_uploaded(content, focus_keyword='บท', strip_end_credit='จบตอน')
        # อ่านเนื้อหาแล้วต้องไม่มี "จบตอน"
        text = files[0].read_text(encoding='utf-8')
        assert 'จบตอน' not in text


def test_separate_uploaded_no_keyword_match():
    with tempfile.TemporaryDirectory() as td:
        sp = SeparateProcessor()
        sp.separate_dir = Path(td)
        content = "เนื้อหาที่ไม่มี keyword\n"
        files = sp.separate_uploaded(content, focus_keyword='ตอนที่', strip_end_credit='')
        assert files == []


def test_separate_uploaded_sanitizes_filename():
    with tempfile.TemporaryDirectory() as td:
        sp = SeparateProcessor()
        sp.separate_dir = Path(td)
        # title มีอักขระอันตราย
        content = "บท bad/name:test*\ncontent\n"
        files = sp.separate_uploaded(content, focus_keyword='บท', strip_end_credit='')
        assert len(files) == 1
        # ไม่ควรมีอักขระต้องห้ามในชื่อ
        for ch in '/:*?"<>|':
            assert ch not in files[0].name


def test_separate_files_with_multiple_uploads():
    with tempfile.TemporaryDirectory() as td:
        sp = SeparateProcessor()
        sp.separate_dir = Path(td)
        f1 = MockUploadedFile('1.txt', "บท 1\ncontent A\nบท 2\ncontent B".encode('utf-8'))
        results = sp.separate_files(
            [f1], focus_keyword='บท', title_prefix='Ch ', title_suffix='',
            chapter_number_padding=3, start_number=1, strip_end_credit=False,
            end_credit_text='',
        )
        assert len(results) == 1
        assert results[0]['sections'] == 2


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
