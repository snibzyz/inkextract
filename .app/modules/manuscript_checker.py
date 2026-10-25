"""manuscript_checker.py — ตรวจต้นฉบับ (ported from noveleditor).

ตรวจหาไฟล์นิยายที่ "เล็กผิดปกติ" — มักเป็นบันทึกผู้เขียน ไม่ใช่เนื้อเรื่องจริง
แล้วเสนอให้ลบ + renumber ไฟล์ที่เหลือให้ต่อเนื่อง

ออกแบบเป็น pure module (ไม่พึ่ง Streamlit/Flask) → reuse ได้ทุก UI
"""
from __future__ import annotations
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import List, Dict, Optional, Iterable, Tuple

# เลขตอน = กลุ่มตัวเลขติดกันทั้งกลุ่ม (ห้ามตัดกลางกลุ่ม) · ข้อความก่อนหน้า = prefix — เลือกด้วย _chapter_run
# บั๊กเดิม: (.+?)\s*(\d{3,4}) บังคับ prefix อย่างน้อย 1 ตัว + รับแค่ 3–4 หลัก
#   → '1000.txt' = prefix '1' + ตอน 0 (ตอน 1000 ขึ้นไปเรียงปนกับตอนต้น ๆ) · '0001.txt' padding 3
#   · '12345' เหลือ 4 หลัก · 'ตอนที่ 12.txt' ไม่นับเป็นตอน (ชุดไม่เติม 0 ตอน 1–99 ไม่ถูก renumber)
_RUN_RE = re.compile(r'\d+')
_VERSION_MARK_RE = re.compile(r'(?<![A-Za-z])[vV]$')   # '_v1', ' v2' = เลขเวอร์ชัน ไม่ใช่เลขตอน


def _chapter_run(name: str) -> Optional[re.Match]:
    """กลุ่มตัวเลขที่เป็นเลขตอนของชื่อไฟล์ (ไม่รวมนามสกุล)

    1. มีกลุ่ม 3 หลักขึ้นไป → กลุ่มแรก ('Chapter_0001_v1' = 1 · '0001 ปี 2024' = 1)
    2. มีแต่ 1–2 หลัก → กลุ่มสุดท้าย — เลขเล่ม/ภาคอยู่หน้าเลขตอน ('Vol2 ตอนที่ 5' = 5 · 'เล่ม 12 ตอนที่ 5' = 5)
    ไม่นับเลขที่ติดหลัง v (เลขเวอร์ชัน)
    """
    stem = Path(name).stem
    runs = [m for m in _RUN_RE.finditer(stem) if not _VERSION_MARK_RE.search(stem[:m.start()])]
    if not runs:
        return None
    long_runs = [m for m in runs if len(m.group()) >= 3]
    return long_runs[0] if long_runs else runs[-1]

# threshold default: ไฟล์ที่เล็กกว่า average × THRESHOLD_RATIO ถูก flag
DEFAULT_THRESHOLD_RATIO = 0.3


@dataclass
class FileEntry:
    filename: str
    path: Path
    size: int
    number: Optional[int]
    padding: Optional[int]
    series: Optional[str]
    is_small: bool = False

    def to_dict(self) -> Dict:
        return {
            'filename': self.filename,
            'size': self.size,
            'number': self.number,
            'padding': self.padding,
            'series': self.series,
            'is_small': self.is_small,
        }


@dataclass
class ScanResult:
    files: List[FileEntry] = field(default_factory=list)
    total_files: int = 0
    average_size: float = 0.0
    threshold_size: float = 0.0
    detected_padding: int = 3
    series_groups: Dict[str, List[FileEntry]] = field(default_factory=dict)
    small_files_count: int = 0


def _parse_filename(path: Path) -> FileEntry:
    name = path.name
    m = _chapter_run(name)
    number = int(m.group()) if m else None
    padding = len(m.group()) if m else None
    series = (name[:m.start()].strip() or None) if m else None
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return FileEntry(filename=name, path=path, size=size,
                     number=number, padding=padding, series=series)


def _zero_pad_widths(entries: Iterable[FileEntry]) -> Dict[Optional[str], int]:
    """ความกว้างเลขแบบเติม 0 ของแต่ละ prefix — นับจากไฟล์ที่เลขขึ้นต้นด้วย 0 (ค่าที่เจอบ่อยสุด)

    prefix ที่ไม่มีไฟล์เลขขึ้นต้นด้วย 0 เลย = ชุดไม่เติม 0 (เช่น 'ตอนที่ 998' … 'ตอนที่ 1000') → ไม่อยู่ใน dict
    """
    counts: Dict[Optional[str], Dict[int, int]] = {}
    for e in entries:
        m = _chapter_run(e.filename)
        if m and len(m.group()) > 1 and m.group()[0] == '0':
            c = counts.setdefault(e.series, {})
            c[len(m.group())] = c.get(len(m.group()), 0) + 1
    return {s: max(c.items(), key=lambda kv: (kv[1], kv[0]))[0] for s, c in counts.items()}


def _renumbered_name(e: FileEntry, new_number: int, pad_widths: Dict[Optional[str], int]) -> str:
    """แทนเฉพาะกลุ่มเลขตอนของไฟล์ (ตำแหน่งเดียวกับที่ _parse_filename อ่าน) ด้วยเลขใหม่

    เลขเดิมขึ้นต้นด้วย 0 → คงความกว้างของไฟล์นั้น ('a 0006' ยังเป็น 4 หลัก)
    เลขเดิมไม่ขึ้นต้นด้วย 0 (เช่น 1000) → ใช้ความกว้างของ prefix เดียวกัน ('0001…2000': 1000→999 = '0999'
    · 'ตอนที่ 998…1000' ไม่เติม 0: 1000→999 = '999' ไม่ใช่ '0999')
    """
    m = _chapter_run(e.filename)
    digits = m.group()
    width = len(digits) if digits[0] == '0' else pad_widths.get(e.series, 0)
    return e.filename[:m.start()] + str(new_number).zfill(width) + e.filename[m.end():]


def _detect_padding(entries: Iterable[FileEntry]) -> int:
    counts: Dict[int, int] = {}
    for e in entries:
        if e.padding:
            counts[e.padding] = counts.get(e.padding, 0) + 1
    if not counts:
        return 3
    return max(counts.items(), key=lambda kv: kv[1])[0]


def scan_directory(directory: Path, threshold_ratio: float = DEFAULT_THRESHOLD_RATIO) -> ScanResult:
    """สแกนโฟลเดอร์ — คืน ScanResult ที่พร้อมแสดงในหน้าเว็บ

    threshold_ratio: ไฟล์ที่ size < average × ratio จะถูก flag เป็น 'เล็กผิดปกติ'
    """
    result = ScanResult()
    if not directory.exists():
        return result

    txt_paths = sorted(directory.glob('*.txt'))
    if not txt_paths:
        return result

    entries = [_parse_filename(p) for p in txt_paths]
    sizes = [e.size for e in entries]
    avg = mean(sizes) if sizes else 0.0
    threshold = avg * threshold_ratio

    for e in entries:
        e.is_small = e.size < threshold and e.size > 0

    # group by series name
    groups: Dict[str, List[FileEntry]] = {}
    for e in entries:
        if e.series and e.number is not None:
            groups.setdefault(e.series, []).append(e)
    for g in groups.values():
        g.sort(key=lambda x: (x.number or 0))

    result.files = entries
    result.total_files = len(entries)
    result.average_size = avg
    result.threshold_size = threshold
    result.detected_padding = _detect_padding(entries)
    result.series_groups = groups
    result.small_files_count = sum(1 for e in entries if e.is_small)
    return result


@dataclass
class ProcessReport:
    renamed: List[Tuple[str, str]] = field(default_factory=list)  # (old_name, new_name) ของไฟล์ที่ยังเก็บไว้
    backed_up: List[str] = field(default_factory=list)            # ทุกไฟล์ต้นฉบับที่ copy ไป old/
    deleted: int = 0                                              # จำนวนที่ผู้ใช้เลือกลบ
    errors: List[str] = field(default_factory=list)
    raw_dir: Optional[Path] = None
    old_dir: Optional[Path] = None


def process(scan: ScanResult, files_to_remove: Iterable[str],
            output_dir: Path, *, copy_unmatched: bool = True) -> ProcessReport:
    """ลบไฟล์ที่เลือก + renumber ไฟล์ที่เหลือ — เก็บผลลัพธ์ใน 2 โฟลเดอร์:

        output_dir/raw/        ← ไฟล์ที่ renumber แล้ว (เช่น 278 ไฟล์ จาก 280)
        output_dir/raw/old/    ← ไฟล์ต้นฉบับ "ทั้งหมด" (280 ไฟล์) เป็น backup

    ไฟล์ต้นทาง (ในโฟลเดอร์ที่สแกน) จะ "ไม่ถูกแตะ" — ใช้ copy เท่านั้น

    หลักการ renumber:
        - detect จาก "เลข" อย่างเดียว ไม่สนใจ prefix → ทุกไฟล์ที่มีเลขรวมเป็นกลุ่มเดียว
        - prefix ของแต่ละไฟล์เดิมถูกเก็บไว้ (เปลี่ยนเฉพาะตัวเลข)
        - padding: เลขขึ้นต้นด้วย 0 ใช้ของไฟล์เดิมแต่ละตัว (กัน "Chapter 001" → "Chapter 02")
          · ไม่ขึ้นต้นด้วย 0 (ตอน 1000+) ใช้ของ prefix เดียวกัน — ดู _renumbered_name
        - raw/ และ raw/old/ ถูกล้างทุกครั้งก่อน process — กันไฟล์ค้างจากรอบก่อน
    """
    report = ProcessReport()
    raw_dir = output_dir / "raw"
    old_dir = raw_dir / "old"

    # ล้าง raw/ ก่อนเสมอ — กันไฟล์ค้างจากรอบก่อน (snapshot ของรอบล่าสุด)
    if raw_dir.exists():
        try:
            shutil.rmtree(raw_dir)
        except Exception as exc:
            report.errors.append(f"ล้าง {raw_dir} ไม่สำเร็จ: {exc}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    old_dir.mkdir(parents=True, exist_ok=True)
    report.raw_dir = raw_dir
    report.old_dir = old_dir

    remove_set = {name for name in files_to_remove}
    report.deleted = sum(1 for e in scan.files if e.filename in remove_set)

    # ===== STEP 1: backup ไฟล์ต้นฉบับ "ทุกไฟล์" ไปไว้ raw/old/ =====
    for e in scan.files:
        try:
            shutil.copy2(e.path, old_dir / e.filename)
            report.backed_up.append(e.filename)
        except Exception as exc:
            report.errors.append(f"backup {e.filename}: {exc}")

    # ===== STEP 2: ไฟล์ที่ไม่มีเลข → copy as-is (ถ้าไม่ถูกเลือกลบ) =====
    if copy_unmatched:
        for e in scan.files:
            if e.number is not None or e.filename in remove_set:
                continue
            try:
                shutil.copy2(e.path, raw_dir / e.filename)
            except Exception as exc:
                report.errors.append(f"copy {e.filename}: {exc}")

    # ===== STEP 3: ไฟล์ที่มีเลข → รวมเป็นกลุ่มเดียว เรียงตามเลข renumber ต่อเนื่อง =====
    numbered = [e for e in scan.files if e.number is not None]
    numbered.sort(key=lambda x: x.number)
    kept = [e for e in numbered if e.filename not in remove_set]

    if kept:
        # เริ่มเลขจากเลขแรกสุดของไฟล์เดิมที่เหลือ (รักษาช่วงเลขเดิม)
        start_number = kept[0].number
        pad_widths = _zero_pad_widths(numbered)

        for i, e in enumerate(kept):
            new_number = start_number + i
            old_filename = e.filename
            new_name = _renumbered_name(e, new_number, pad_widths)
            try:
                shutil.copy2(e.path, raw_dir / new_name)
                report.renamed.append((old_filename, new_name))
            except Exception as exc:
                report.errors.append(f"copy {old_filename} -> {new_name}: {exc}")

    return report


# ============================================================
# Explorer paging — แท็บตรวจต้นฉบับ render ทีละหน้า
# ============================================================
# render checkbox + ปุ่มทุกไฟล์ใน Raw หลายพันตอน = element หลายพันชิ้นต่อ rerun
# → Streamlit (Starlette) คิวส่งเต็ม → หน้าเว็บค้าง "Stop" ถาวร (ดู modules/streamlit_compat.py)

EXPLORER_PAGE_SIZE = 50


def page_count(total: int, page_size: int = EXPLORER_PAGE_SIZE) -> int:
    """จำนวนหน้า (อย่างน้อย 1 แม้ไม่มีไฟล์)"""
    return max(1, -(-max(0, total) // page_size))


def page_of_index(index: int, page_size: int = EXPLORER_PAGE_SIZE) -> int:
    """หน้าที่มีรายการลำดับ index (0-based)"""
    return max(0, index) // page_size


def page_bounds(page: int, total: int, page_size: int = EXPLORER_PAGE_SIZE) -> Tuple[int, int]:
    """ช่วง [start, end) ของหน้า page (0-based) — page นอกช่วงถูกบีบให้อยู่ในช่วง"""
    page = min(max(0, page), page_count(total, page_size) - 1)
    start = page * page_size
    return start, min(max(0, total), start + page_size)


def merge_page_selection(selected: Iterable[str], visible: Iterable[str],
                         checked_visible: Iterable[str]) -> set:
    """รวมการเลือก: ไฟล์นอกหน้านี้คงค่าเดิม · ไฟล์ในหน้านี้ใช้ค่าจาก checkbox"""
    visible = set(visible)
    return (set(selected) - visible) | (set(checked_visible) & visible)
