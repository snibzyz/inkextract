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
    insert_after_line: int = -1  # index (0-based) ในไฟล์แปล — แทรกบรรทัดที่หาย "หลัง" บรรทัดนี้
                                 # -1 = แทรกที่ต้นไฟล์ (ก่อน [A] บล็อกแรก)


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


def _extract_a_block_spans(translation_lines: Sequence[str]):
    """เหมือน extract_a_blocks แต่คืน "ตำแหน่งบรรทัด" ของแต่ละบล็อกด้วย.

    คืน (spans, first_a_start) โดย:
      - spans = list ของ (normalized_a_text, insert_after_idx, a_start_idx)
        * normalized_a_text = ข้อความ [A] ที่ normalize แล้ว (เหมือน haystack เดิมเป๊ะ)
        * insert_after_idx = index บรรทัด (0-based) ที่ควรแทรก "บรรทัดถัดไป" ต่อท้าย
          = บรรทัด [B] ที่ปิดบล็อกนี้ (ถ้ามี) ไม่งั้น = บรรทัดเนื้อหา [A] สุดท้าย
        * a_start_idx = index บรรทัด [A] ที่เปิดบล็อกนี้ (ใช้แทรก "ก่อน" บล็อกล่าง)
      - first_a_start = index ของบรรทัด [A] แรกสุด (None ถ้าไม่มี [A] เลย)

    การแบ่งบล็อกตรงกับ extract_a_blocks ทุกประการ → haystack ที่ build จาก spans
    เท่ากับ haystack เดิม จึง "ไม่กระทบผลการ detection"
    """
    spans = []
    first_a_start = None
    current: List[str] = []
    current_a_start = None
    last_content_idx = None
    in_a = False

    def _close(insert_after_idx):
        spans.append((normalize('\n'.join(current)), insert_after_idx, current_a_start))

    for idx, raw in enumerate(translation_lines):
        line = raw.rstrip('\n')
        stripped = line.lstrip()
        if stripped.startswith('[A]'):
            if in_a and current:
                _close(last_content_idx)  # บล็อกก่อนไม่มี [B] → แทรกหลังเนื้อหา [A] สุดท้าย
            current = [stripped[3:].lstrip()]
            current_a_start = idx
            last_content_idx = idx
            if first_a_start is None:
                first_a_start = idx
            in_a = True
        elif stripped.startswith('[B]'):
            if in_a and current:
                _close(idx)  # แทรก "หลัง" บรรทัด [B] ที่ปิดบล็อก
                current = []
                in_a = False
            # [B] ที่ไม่มี [A] นำหน้า → ไม่ถือเป็นบล็อก (เหมือน extract_a_blocks)
        elif in_a:
            current.append(line)
            last_content_idx = idx

    if in_a and current:
        _close(last_content_idx)

    return spans, first_a_start


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
    spans, first_a_start = _extract_a_block_spans(translation_lines)
    # haystack เท่ากับเวอร์ชันเดิม (build จาก [A] บล็อกเดียวกัน) → detection ไม่เปลี่ยน
    haystack = ''.join(s[0] for s in spans)

    # anchor เริ่มต้น = "ก่อน" [A] บล็อกแรก → บรรทัดที่หายช่วงต้น (เช่น ชื่อตอน) ไปอยู่หัวไฟล์
    # ถ้าไม่มี [A] เลย → ต่อท้ายไฟล์
    if first_a_start is not None:
        top_anchor = first_a_start - 1
    else:
        top_anchor = len(translation_lines) - 1

    # ---------- Pass 1: จัดสถานะแต่ละบรรทัด raw + หาว่าบรรทัด "ที่มีอยู่" ตรงกับบล็อกไหน ----------
    # เป้าหมาย: เพื่อให้บรรทัดที่หาย "คร่อม" ระหว่างบรรทัดที่มีอยู่ทั้งบนและล่าง (ตามที่ user ต้องการ)
    # block_of[i] = index บล็อก [A] ที่บรรทัด raw i ตรง (None ถ้า skip/missing/หาไม่เจอ)
    # การตัดสิน present/missing เหมือนเดิมเป๊ะ (needle in haystack หรือ fuzzy ≥ min_ratio) → detection ไม่เปลี่ยน
    n = len(raw_entries)
    kinds: List[str] = []          # 'present' | 'missing' | 'skip'
    block_of: List = []            # block index หรือ None
    ratios: List[float] = []       # best_ratio (สำหรับ missing)
    cursor = 0                     # ตัวชี้บล็อกถัดไป (เดินหน้า — กัน match ซ้ำผิดตัวเมื่อมีบรรทัดซ้ำ)

    for entry in raw_entries:
        _, _, line = entry
        if len(line) < MIN_LINE_LENGTH or (require_cjk and not has_cjk(line)):
            kinds.append('skip'); block_of.append(None); ratios.append(0.0)
            continue
        needle = normalize(line)
        if len(needle) < MIN_LINE_LENGTH:
            kinds.append('skip'); block_of.append(None); ratios.append(0.0)
            continue

        if needle in haystack:
            # exact present → หา block (เดินหน้าก่อน, ไม่เจอค่อยถอยหา — เผื่อบรรทัดซ้ำ/สลับ)
            blk = None
            for j in range(cursor, len(spans)):
                if needle in spans[j][0]:
                    blk = j; cursor = j + 1; break
            if blk is None:
                for j in range(0, min(cursor, len(spans))):
                    if needle in spans[j][0]:
                        blk = j; break
            kinds.append('present'); block_of.append(blk); ratios.append(1.0)
            continue

        ratio = fuzzy_substring_max_ratio(needle, haystack)
        if ratio >= min_ratio:
            # fuzzy present → หา block ที่ใกล้สุด (เดินหน้า) เพื่อเลื่อน cursor ด้วย
            blk = None; best_r = 0.0
            for j in range(cursor, len(spans)):
                r = fuzzy_substring_max_ratio(needle, spans[j][0])
                if r > best_r:
                    best_r = r; blk = j
            if blk is not None and best_r >= min_ratio:
                cursor = blk + 1
            else:
                blk = None  # หา block ชัดๆ ไม่ได้ → ไม่ผูกตำแหน่ง
            kinds.append('present'); block_of.append(blk); ratios.append(1.0)
            continue

        kinds.append('missing'); block_of.append(None); ratios.append(ratio)

    # ---------- Pass 2: บรรทัดที่หาย → คร่อมระหว่างบรรทัดที่มีอยู่ "บน" และ "ล่าง" ----------
    missing: List[MissingLine] = []
    for raw_index in range(n):
        if kinds[raw_index] != 'missing':
            continue

        # บรรทัดที่มีอยู่ใกล้สุด "ด้านบน" (ที่ผูกบล็อกได้)
        prev_blk = None
        for k in range(raw_index - 1, -1, -1):
            if kinds[k] == 'present' and block_of[k] is not None:
                prev_blk = block_of[k]; break
        # บรรทัดที่มีอยู่ใกล้สุด "ด้านล่าง"
        next_blk = None
        for k in range(raw_index + 1, n):
            if kinds[k] == 'present' and block_of[k] is not None:
                next_blk = block_of[k]; break

        if prev_blk is not None:
            insert_after = spans[prev_blk][1]          # แทรก "หลัง" [B] ของบล็อกบน
        elif next_blk is not None:
            insert_after = spans[next_blk][2] - 1      # แทรก "ก่อน" [A] ของบล็อกล่าง
        else:
            insert_after = top_anchor                  # ไม่มีเพื่อนทั้งบน-ล่าง → หัว/ท้ายไฟล์

        chapter_number, chapter_path, line = raw_entries[raw_index]
        missing.append(MissingLine(
            raw_line_index=raw_index,
            chapter_number=chapter_number,
            chapter_path=str(chapter_path),
            text=line,
            best_ratio=ratios[raw_index],
            insert_after_line=insert_after,
        ))

    return missing
