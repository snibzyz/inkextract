"""raw_file_resolver.py — จับคู่ไฟล์แปล (อาจรวมหลายตอน) กับไฟล์ raw จีนต้นฉบับ.

รองรับ:
  - ไฟล์แปลเป็นช่วง: 'ติดหนี้สามสิบล้าน 601-603.txt' → ตอน 601, 602, 603
  - ไฟล์แปลตอนเดียว: 'ติดหนี้สามสิบล้าน 601.txt' → ตอน 601
  - Raw folder ที่มี sub folder ซ้อนกันหลายชั้น (search แบบ recursive)
  - ตัวคั่นช่วงหลายแบบ: '-', '–', '~', '_'

Pure module — ไม่พึ่ง Streamlit
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Optional, Tuple


# ตัวคั่นช่วง: hyphen, en-dash, tilde, underscore
_RANGE_RE = re.compile(r'(\d+)\s*[-–~_]\s*(\d+)')
_NUMBER_RE = re.compile(r'\d+')


def parse_chapter_range(filename: str) -> Optional[Tuple[int, int]]:
    """แยกช่วงเลขตอนจากชื่อไฟล์.

    Returns:
        (start, end) — ครอบคลุมทั้ง single และ range
        None ถ้าไม่เจอเลขเลย
    """
    stem = Path(filename).stem
    match = _RANGE_RE.search(stem)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        # กัน user ใส่ผิดทาง (603-601) → swap
        return (min(a, b), max(a, b))

    numbers = _NUMBER_RE.findall(stem)
    if not numbers:
        return None
    # เลือกเลขสุดท้าย (rightmost) — ปกติคือเลขตอน
    last = int(numbers[-1])
    return (last, last)


def extract_chapter_number(filename: str) -> Optional[int]:
    """หาเลขตอนของไฟล์ raw — เลือก rightmost number."""
    stem = Path(filename).stem
    numbers = _NUMBER_RE.findall(stem)
    if not numbers:
        return None
    return int(numbers[-1])


def resolve_raw_files(
    translation_filename: str,
    raw_dir: Path,
    *,
    recursive: bool = True,
) -> List[Path]:
    """หา raw files ที่ตรงกับช่วงตอนของไฟล์แปล — เรียงตามเลขตอน.

    Args:
        translation_filename: เช่น 'ติดหนี้สามสิบล้าน 601-603.txt'
        raw_dir: โฟลเดอร์ที่มีไฟล์ raw (อาจมี sub folder)
        recursive: True = scan ลึกทุก sub folder, False = top-level เท่านั้น

    Returns:
        list ของ Path เรียงตามเลขตอน — empty list ถ้าไม่เจอ
    """
    if not raw_dir.exists() or not raw_dir.is_dir():
        return []

    chapter_range = parse_chapter_range(translation_filename)
    if chapter_range is None:
        return []
    start, end = chapter_range

    pattern = "**/*.txt" if recursive else "*.txt"
    matches: List[Tuple[int, Path]] = []
    seen_chapters: set = set()

    for path in raw_dir.glob(pattern):
        if not path.is_file():
            continue
        chapter = extract_chapter_number(path.name)
        if chapter is None:
            continue
        if not (start <= chapter <= end):
            continue
        # กัน duplicate (ไฟล์ตอน 601 อยู่ทั้ง done/ และ folder หลัก)
        if chapter in seen_chapters:
            continue
        seen_chapters.add(chapter)
        matches.append((chapter, path))

    matches.sort(key=lambda t: t[0])
    return [p for _, p in matches]


def load_raw_lines(raw_files: List[Path]) -> List[Tuple[int, Path, str]]:
    """อ่านไฟล์ raw ทั้งหมด → list ของ (chapter_number, path, line) ตามลำดับ.

    บรรทัดว่างถูกตัดออก (กัน noise)
    """
    out: List[Tuple[int, Path, str]] = []
    for path in raw_files:
        chapter = extract_chapter_number(path.name) or 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if line:
                        out.append((chapter, path, line))
        except OSError:
            continue
    return out
