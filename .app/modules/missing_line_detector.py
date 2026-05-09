"""missing_line_detector.py — หา raw line ที่ AI ข้ามไม่แปล.

Algorithm 2 ชั้น:
  1. Substring exact: รวมทุก [A] เป็น string เดียว → เช็ค raw line เป็น substring ตรงๆ
  2. Fuzzy sliding window: ถ้าไม่เจอ exact → slide window ขนาด len(raw) ใน [A] ทั้งหมด
     คำนวณ bigram_similarity, max ratio ≥ threshold → matched

ใช้ได้กับภาษาเดียวกันเท่านั้น (raw จีน vs [A] จีน) — ไม่ใช่ raw จีน vs [B] ไทย
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Sequence

from modules.fuzzy_matcher import bigram_similarity


# unicode whitespace + zero-width
_NORMALIZE_RE = re.compile(r'\s+|​|‌|‍|﻿')
# Chinese char range
_CJK_RE = re.compile(r'[一-鿿]')

# ขั้นต่ำของ raw line ที่จะตรวจ — สั้นกว่านี้ถือว่าเป็น noise / punctuation
MIN_LINE_LENGTH = 4
DEFAULT_FUZZY_RATIO = 0.7


@dataclass
class MissingLine:
    raw_line_index: int       # 0-based ใน raw lines list
    chapter_number: int       # เลขตอน
    chapter_path: str         # path ของไฟล์ raw ตอนนั้น
    text: str                 # บรรทัด raw จริง (ไม่ normalize)
    best_ratio: float = 0.0   # ratio ที่ใกล้ที่สุดที่เจอ (debug)


def normalize(text: str) -> str:
    """Strip whitespace ทั้งหมดจาก text — keep characters อื่นไว้."""
    if not text:
        return ''
    return _NORMALIZE_RE.sub('', text)


def has_cjk(text: str) -> bool:
    """เช็คว่ามีตัวอักษรจีนไหม — ใช้กรอง raw line ที่เป็น punctuation/digits ล้วน."""
    return bool(_CJK_RE.search(text))


def extract_a_blocks(translation_lines: Sequence[str]) -> List[str]:
    """ดึงข้อความหลัง [A] ทั้งหมดจากไฟล์แปล — รองรับ multi-line block.

    หนึ่ง [A] block = ข้อความตั้งแต่บรรทัด '[A] ...' จนถึงก่อน '[B]' หรือก่อน [A] ถัดไป
    """
    blocks: List[str] = []
    current: List[str] = []
    in_a = False

    for raw in translation_lines:
        line = raw.rstrip('\n')
        stripped = line.lstrip()
        if stripped.startswith('[A]'):
            if in_a and current:
                blocks.append('\n'.join(current))
            current = [stripped[3:].lstrip()]
            in_a = True
        elif stripped.startswith('[B]'):
            if in_a and current:
                blocks.append('\n'.join(current))
            current = []
            in_a = False
        elif in_a:
            current.append(line)

    if in_a and current:
        blocks.append('\n'.join(current))

    return blocks


def fuzzy_substring_max_ratio(needle: str, haystack: str) -> float:
    """หา max bigram_similarity ของ sliding window ใน haystack ที่ใกล้เคียง needle.

    Window size = len(needle), step = max(1, len(needle) // 4) (overlap ~75%)
    """
    if not needle or not haystack:
        return 0.0
    n = len(needle)
    h = len(haystack)
    if n > h:
        # haystack สั้นกว่า needle → เทียบทั้งก้อน
        return bigram_similarity(needle, haystack)

    step = max(1, n // 4)
    best = 0.0
    for start in range(0, h - n + 1, step):
        window = haystack[start:start + n]
        ratio = bigram_similarity(needle, window)
        if ratio > best:
            best = ratio
            if best >= 0.99:
                return best
    # ตรวจ window สุดท้ายที่ติดขอบขวา (กันพลาดเพราะ step)
    if (h - n) % step != 0:
        window = haystack[h - n:]
        ratio = bigram_similarity(needle, window)
        if ratio > best:
            best = ratio
    return best


def find_missing_lines(
    raw_entries: Sequence,
    translation_lines: Sequence[str],
    *,
    min_ratio: float = DEFAULT_FUZZY_RATIO,
    require_cjk: bool = True,
) -> List[MissingLine]:
    """หา raw line ที่ไม่ปรากฏใน [A] blocks ของไฟล์แปล.

    Args:
        raw_entries: list ของ (chapter_number, chapter_path, line)
                     จาก raw_file_resolver.load_raw_lines()
        translation_lines: บรรทัดทั้งหมดของไฟล์แปล (อ่าน .readlines())
        min_ratio: threshold สำหรับ fuzzy match (ต่ำกว่านี้ = missing)
        require_cjk: True = ข้ามบรรทัด raw ที่ไม่มีตัวอักษรจีน
                     (กัน noise เช่น '......', '———')

    Returns:
        list ของ MissingLine — บรรทัด raw ที่ AI น่าจะข้ามแปล
    """
    a_blocks = extract_a_blocks(translation_lines)
    haystack = ''.join(normalize(b) for b in a_blocks)

    missing: List[MissingLine] = []

    for raw_index, entry in enumerate(raw_entries):
        chapter_number, chapter_path, line = entry
        if len(line) < MIN_LINE_LENGTH:
            continue
        if require_cjk and not has_cjk(line):
            continue

        needle = normalize(line)
        if len(needle) < MIN_LINE_LENGTH:
            continue

        # Phase 1: exact substring
        if needle in haystack:
            continue

        # Phase 2: fuzzy sliding window
        ratio = fuzzy_substring_max_ratio(needle, haystack)
        if ratio >= min_ratio:
            continue

        missing.append(MissingLine(
            raw_line_index=raw_index,
            chapter_number=chapter_number,
            chapter_path=str(chapter_path),
            text=line,
            best_ratio=ratio,
        ))

    return missing
