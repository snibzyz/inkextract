"""ทดสอบ manuscript_checker — ครอบคลุมทุก function ที่มี"""
import sys
import tempfile
from pathlib import Path

# allow running from .app/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import manuscript_checker as mc  # noqa: E402


# ============================================================
# Helpers สำหรับ test
# ============================================================

def _make_files(directory: Path, spec: dict[str, int]):
    """spec = {filename: size_in_bytes}"""
    for name, size in spec.items():
        (directory / name).write_text('x' * size, encoding='utf-8')


# ============================================================
# Tests
# ============================================================

def test_scan_empty_directory():
    with tempfile.TemporaryDirectory() as td:
        result = mc.scan_directory(Path(td))
        assert result.total_files == 0
        assert result.files == []
        assert result.average_size == 0.0
        assert result.small_files_count == 0


def test_scan_nonexistent_directory():
    result = mc.scan_directory(Path("/nonexistent_path_xyz_12345"))
    assert result.total_files == 0


def test_scan_basic():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _make_files(base, {
            'novel 001.txt': 2048,
            'novel 002.txt': 2048,
            'novel 003.txt': 200,   # small
            'novel 004.txt': 2048,
        })
        result = mc.scan_directory(base, threshold_ratio=0.3)
        assert result.total_files == 4
        assert result.detected_padding == 3
        assert result.small_files_count == 1
        small_names = [e.filename for e in result.files if e.is_small]
        assert small_names == ['novel 003.txt']


def test_scan_padding_4_digits():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _make_files(base, {f'epic 0{i:03d}.txt': 1000 for i in range(1, 11)})
        result = mc.scan_directory(base)
        assert result.detected_padding == 4


def test_scan_mixed_padding_picks_majority():
    """ถ้ามีไฟล์ padding ผสม ให้เลือกที่มากกว่า"""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # 7 files padding 3 + 2 files padding 4
        _make_files(base, {
            **{f'a {i:03d}.txt': 1000 for i in range(1, 8)},
            **{f'b 0{i:03d}.txt': 1000 for i in range(1, 3)},
        })
        result = mc.scan_directory(base)
        assert result.detected_padding == 3, "majority padding wins"


def test_scan_unmatched_files_no_number():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _make_files(base, {
            'novel 001.txt': 1000,
            'README.txt': 1000,  # ไม่มีเลข
        })
        result = mc.scan_directory(base)
        assert result.total_files == 2
        readme_entry = next(e for e in result.files if e.filename == 'README.txt')
        assert readme_entry.number is None
        assert readme_entry.series is None


def test_process_no_deletions_preserves_all_files():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {f'novel {i:03d}.txt': 1000 for i in range(1, 11)})

        scan = mc.scan_directory(src)
        report = mc.process(scan, [], out)

        raw = out / 'raw'
        old = raw / 'old'
        assert len(list(raw.glob('*.txt'))) == 10
        assert len(list(old.glob('*.txt'))) == 10
        assert report.deleted == 0


def test_process_deletes_and_renumbers_continuous():
    """280 ไฟล์ ลบ 2 → ต้องเหลือ 278 ไฟล์เลข 001..278 ต่อเนื่อง"""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        spec = {}
        small_files = []
        for i in range(1, 281):
            name = f'นิยาย {i:03d} ตอน {i}.txt'
            if i in (23, 156):
                spec[name] = 200
                small_files.append(name)
            else:
                spec[name] = 2048
        _make_files(src, spec)

        scan = mc.scan_directory(src)
        report = mc.process(scan, small_files, out)

        raw = out / 'raw'
        old = raw / 'old'

        raw_files = sorted(p.name for p in raw.glob('*.txt'))
        old_files = sorted(p.name for p in old.glob('*.txt'))

        assert len(raw_files) == 278, f"raw count {len(raw_files)}"
        assert len(old_files) == 280, f"old count {len(old_files)}"

        # numbers ต่อเนื่อง 001..278 (no gaps)
        import re
        nums = sorted(int(re.search(r'(\d{3})', n).group(1)) for n in raw_files)
        assert nums == list(range(1, 279)), "numbers not sequential"

        # mapping ตรวจตัวอย่าง
        rename_map = dict(report.renamed)
        # ไฟล์ 022 → 022 (ก่อนไฟล์ที่ลบ)
        assert rename_map['นิยาย 022 ตอน 22.txt'] == 'นิยาย 022 ตอน 22.txt'
        # ไฟล์ 024 → 023 (หลังลบ 023)
        assert rename_map['นิยาย 024 ตอน 24.txt'] == 'นิยาย 023 ตอน 24.txt'
        # ไฟล์ 280 → 278 (สุดท้าย หลังลบ 2 ไฟล์)
        assert rename_map['นิยาย 280 ตอน 280.txt'] == 'นิยาย 278 ตอน 280.txt'


def test_process_unmatched_files_copied_to_raw():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {
            'novel 001.txt': 2048,
            'novel 002.txt': 200,  # small
            'novel 003.txt': 2048,
            'README.txt': 2048,    # no number, should still be copied
        })
        scan = mc.scan_directory(src)
        report = mc.process(scan, ['novel 002.txt'], out)

        raw_files = sorted(p.name for p in (out / 'raw').glob('*.txt'))
        # README ต้องอยู่ + 001 ตามเดิม + 003 → 002
        assert 'README.txt' in raw_files
        assert 'novel 001.txt' in raw_files
        assert 'novel 002.txt' in raw_files  # was 003
        assert len(raw_files) == 3


def test_process_preserves_starting_number():
    """ถ้าเริ่มที่ 011 → ผลลัพธ์ต้องเริ่มที่ 011 ไม่ใช่ 001"""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {f'novel {i:03d}.txt': 1000 for i in range(11, 21)})
        scan = mc.scan_directory(src)
        report = mc.process(scan, [], out)
        raw_files = sorted(p.name for p in (out / 'raw').glob('*.txt'))
        # ต้องเริ่มที่ 011 (รักษาช่วงเลขเดิม)
        assert raw_files[0] == 'novel 011.txt'
        assert raw_files[-1] == 'novel 020.txt'


def test_process_creates_directories_if_missing():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'deep' / 'nested' / 'output'
        _make_files(src, {'novel 001.txt': 1000})
        scan = mc.scan_directory(src)
        report = mc.process(scan, [], out)
        assert (out / 'raw').exists()
        assert (out / 'raw' / 'old').exists()


def test_process_backup_preserves_originals_unchanged():
    """ไฟล์ใน raw/old/ ต้องเหมือนต้นฉบับเป๊ะ"""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'

        original_content = "เนื้อหาต้นฉบับสำคัญ\nบรรทัดที่ 2\n"
        (src / 'novel 001.txt').write_text(original_content, encoding='utf-8')
        (src / 'novel 002.txt').write_text('small', encoding='utf-8')

        scan = mc.scan_directory(src)
        mc.process(scan, ['novel 002.txt'], out)

        backup_text = (out / 'raw' / 'old' / 'novel 001.txt').read_text(encoding='utf-8')
        assert backup_text == original_content
        # ไฟล์ต้นทางต้องไม่ถูกแตะ
        assert (src / 'novel 001.txt').read_text(encoding='utf-8') == original_content


def test_process_report_fields():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {f'a {i:03d}.txt': 1000 for i in range(1, 6)})
        scan = mc.scan_directory(src)
        report = mc.process(scan, ['a 003.txt'], out)
        assert report.deleted == 1
        assert len(report.renamed) == 4
        assert len(report.backed_up) == 5
        assert report.raw_dir == out / 'raw'
        assert report.old_dir == out / 'raw' / 'old'
        assert report.errors == []


def test_process_handles_no_prefix_files():
    """ไฟล์ '001.txt', '002.txt' (ไม่มี prefix) ต้องถูก renumber ปกติ
    (บั๊กเดิม: _SERIES_RE ต้อง match prefix → no-prefix ถูกข้าม)
    """
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {f'{i:03d}.txt': 1000 for i in range(1, 11)})

        scan = mc.scan_directory(src)
        # ลบ 003, 006
        report = mc.process(scan, ['003.txt', '006.txt'], out)

        raw_files = sorted(p.name for p in (out / 'raw').glob('*.txt') if p.is_file())
        # คาด: 001..008 (8 ไฟล์)
        assert raw_files == [f'{i:03d}.txt' for i in range(1, 9)], f"got: {raw_files}"
        assert len(raw_files) == 8

        # ตรวจ content alignment: 004 เดิม → ใหม่ 003
        original_004 = (src / '004.txt').read_bytes()
        new_003 = (out / 'raw' / '003.txt').read_bytes()
        assert original_004 == new_003, "เดิม 004 ต้องเท่า ใหม่ 003"


def test_process_clears_residual_from_previous_run():
    """รัน process 2 รอบติด ด้วย selection ต่างกัน — รอบ 2 ห้ามมี ghost files จากรอบ 1
    (บั๊กเดิม: raw/ ไม่ถูกล้าง → ดูเหมือน 'ไม่ลบ' / save ซ้ำซ้อน)
    """
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        _make_files(src, {f'novel {i:03d}.txt': 1000 for i in range(1, 11)})

        # Round 1: ลบ 5 ไฟล์ → เหลือ 5
        scan1 = mc.scan_directory(src)
        mc.process(scan1, [f'novel {i:03d}.txt' for i in [2, 4, 6, 8, 10]], out)
        round1_files = sorted(p.name for p in (out / 'raw').glob('*.txt') if p.is_file())
        assert len(round1_files) == 5, f"round1: {len(round1_files)}"

        # Round 2: ลบเฉพาะ 003 → ต้องเหลือ 9 (ไม่ใช่ 9 + ghost จาก round1)
        scan2 = mc.scan_directory(src)
        mc.process(scan2, ['novel 003.txt'], out)
        round2_files = sorted(p.name for p in (out / 'raw').glob('*.txt') if p.is_file())
        assert len(round2_files) == 9, f"round2 ghost! got {len(round2_files)}: {round2_files}"


def test_process_mixed_prefix_detect_by_number():
    """mixed prefix — บางไฟล์มี prefix บางไฟล์ไม่มี ต้องเรียงตามเลขรวมเป็นกลุ่มเดียว
    (ตามคำสั่งผู้ใช้: detect แค่เลข prefix ใดก็ได้)
    """
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        # 001 (no prefix), 002 (no), Chapter 003, Chapter 004, 005 (no)
        for name in ['001.txt', '002.txt', 'Chapter 003.txt', 'Chapter 004.txt', '005.txt']:
            (src / name).write_text('x' * 1000, encoding='utf-8')

        scan = mc.scan_directory(src)
        # ลบ Chapter 003
        report = mc.process(scan, ['Chapter 003.txt'], out)

        raw_files = sorted(p.name for p in (out / 'raw').glob('*.txt') if p.is_file())
        # คาด: 001, 002, Chapter 003 (เคย 004), 004 (เคย 005)
        # — prefix ของแต่ละไฟล์ถูกเก็บไว้
        assert '001.txt' in raw_files
        assert '002.txt' in raw_files
        assert 'Chapter 003.txt' in raw_files, "Chapter 004 ต้องเป็น Chapter 003"
        assert '004.txt' in raw_files, "005 ต้องเป็น 004"
        assert len(raw_files) == 4


def test_process_per_file_padding_preserved():
    """ไฟล์ padding ผสม (3 + 4 digits) — แต่ละไฟล์ใช้ padding ของตัวเอง
    (บั๊กเดิม: ใช้ global padding → 'Chapter 0001' (4) อาจกลายเป็น 'Chapter <new>1' ผิด)
    """
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        src = base / 'src'
        src.mkdir()
        out = base / 'out'
        # majority padding 3, but one file with padding 4
        for i in range(1, 6):
            (src / f'a {i:03d}.txt').write_text('x' * 1000, encoding='utf-8')
        (src / 'a 0006.txt').write_text('x' * 1000, encoding='utf-8')  # padding 4

        scan = mc.scan_directory(src)
        assert scan.detected_padding == 3  # majority

        report = mc.process(scan, [], out)
        raw_files = sorted(p.name for p in (out / 'raw').glob('*.txt') if p.is_file())

        # ไฟล์ padding 4 ต้องถูกแทนแค่ 4 หลัก ไม่ใช่ 3 หลัก
        assert 'a 0006.txt' in raw_files, f"padding-4 ต้องคงเป็น 0006 — got: {raw_files}"


# ============================================================
# Test runner
# ============================================================

if __name__ == '__main__':
    import inspect

    tests = [
        (name, fn) for name, fn in inspect.getmembers(sys.modules[__name__])
        if name.startswith('test_') and callable(fn)
    ]
    passed = 0
    failed = 0
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
