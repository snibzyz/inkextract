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

# detect 3-4 หลักเป็นเลขตอน
_NUMBER_RE = re.compile(r'(\d{3,4})')
_SERIES_RE = re.compile(r'(.+?)\s*(\d{3,4})')

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
    series_match = _SERIES_RE.search(name)
    if series_match:
        series = series_match.group(1).strip()
        number = int(series_match.group(2))
        padding = len(series_match.group(2))
    else:
        num_match = _NUMBER_RE.search(name)
        series = None
        number = int(num_match.group(1)) if num_match else None
        padding = len(num_match.group(1)) if num_match else None
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return FileEntry(filename=name, path=path, size=size,
                     number=number, padding=padding, series=series)


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
        - padding ใช้ของไฟล์เดิมแต่ละตัว (กัน "Chapter 001" → "Chapter 02" ผิดเพี้ยน)
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
        global_padding = scan.detected_padding

        for i, e in enumerate(kept):
            new_number = start_number + i
            old_filename = e.filename
            # ใช้ padding ของไฟล์เดิมแต่ละตัว — กันชนกรณี mix padding
            old_padding = e.padding or global_padding
            new_name = re.sub(
                r'\d{' + str(old_padding) + r'}',
                str(new_number).zfill(old_padding),
                old_filename,
                count=1,
            )
            try:
                shutil.copy2(e.path, raw_dir / new_name)
                report.renamed.append((old_filename, new_name))
            except Exception as exc:
                report.errors.append(f"copy {old_filename} -> {new_name}: {exc}")

    return report
