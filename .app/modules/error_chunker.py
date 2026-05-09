"""error_chunker.py — แบ่ง errors เป็นหลาย part เพื่อกัน token limit ของ AI.

Ported from INKIDEA's chapterCheckExport.ts (TypeScript) — same algorithm.

ใช้ตอน export error_trans.txt ขนาดใหญ่ → แบ่งเป็น
  error_trans_001.txt, error_trans_002.txt, ...
แล้วตอน import กลับ จะ scan ทุกไฟล์ที่ตรง pattern อัตโนมัติ

มี 2 strategy:
  1. split_errors_into_parts() — แบ่งตาม "จำนวน error" (เก่า, ยังใช้ได้)
  2. split_blocks_by_line_count() — แบ่งตาม "จำนวนบรรทัด" target (~500)
     กันการตัดกลาง entry, repeat section/file headers ในทุก chunk
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, TypeVar

T = TypeVar('T')


def split_errors_into_parts(errors: Sequence[T], part_size: int) -> List[List[T]]:
    """แบ่ง errors เป็น chunks ขนาด part_size.

    part_size <= 0 → คืน [list(errors)] (ไม่ split)
    """
    if part_size <= 0 or len(errors) <= part_size:
        return [list(errors)]
    chunks: List[List[T]] = []
    for i in range(0, len(errors), part_size):
        chunks.append(list(errors[i:i + part_size]))
    return chunks


# ============================================================
# Block-based line chunker (เน้นไม่ตัดกลาง entry)
# ============================================================

# Block kinds — ลำดับสำคัญ: section ครอบ file ครอบ entry
BLOCK_SECTION = 'section'      # # ===== ภาษาต่างประเทศ ... =====
BLOCK_FILE = 'file'            # ## chapter01.txt
BLOCK_VOCAB_HINT = 'vocab_hint'  # # แปลไม่ครบ ต้องแก้เป็นคำ ...
BLOCK_ENTRY = 'entry'          # 1 รายการ error (line_number| + [A] + [B] + blank)


@dataclass
class Block:
    """1 บล็อกของ output — atomic unit ที่ห้ามตัดกลาง."""
    kind: str
    lines: List[str] = field(default_factory=list)  # ไม่มี trailing \n ในแต่ละ string

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def render(self) -> str:
        """คืนเนื้อหาเป็น string พร้อม \\n ปิดท้ายแต่ละบรรทัด."""
        return '\n'.join(self.lines) + '\n' if self.lines else ''


def split_blocks_by_line_count(
    blocks: Sequence[Block],
    target_lines: int,
) -> List[List[Block]]:
    """แบ่ง blocks เป็น chunks โดยให้แต่ละ chunk มีบรรทัดประมาณ target_lines.

    กฎ:
      - ห้ามตัดกลาง block (1 entry = 1 unit, ห้ามแบ่งครึ่ง)
      - ขึ้น chunk ใหม่เมื่อ cur_lines + next_block_lines > target_lines
      - Section header และ File header จะถูก repeat ในทุก chunk ใหม่ที่ยังอยู่ใน
        section/file เดิม — เพื่อให้ AI เห็น context ครบ
      - Vocab_hint จะอยู่กับ entry ถัดไปเสมอ (ไม่ตัดเลย — push ไป chunk ถัดไปกับ entry)

    Args:
        blocks: ลำดับ Block ที่ render มาจาก export
        target_lines: เป้าหมายบรรทัดต่อ chunk (≤ 0 = ไม่ split)

    Returns:
        list ของ chunks — แต่ละ chunk = list[Block]
    """
    if target_lines <= 0:
        return [list(blocks)]

    chunks: List[List[Block]] = []
    cur_chunk: List[Block] = []
    cur_lines = 0
    last_section: Optional[Block] = None
    last_file: Optional[Block] = None
    pending_vocab: Optional[Block] = None  # vocab_hint ที่รอ entry ถัดไป

    def push_chunk():
        nonlocal cur_chunk, cur_lines
        if cur_chunk:
            chunks.append(cur_chunk)
        cur_chunk = []
        cur_lines = 0

    def start_new_chunk_with_context():
        """เริ่ม chunk ใหม่พร้อม repeat section + file headers ที่ยัง active."""
        nonlocal cur_chunk, cur_lines
        push_chunk()
        if last_section is not None:
            cur_chunk.append(last_section)
            cur_lines += last_section.line_count
        if last_file is not None:
            cur_chunk.append(last_file)
            cur_lines += last_file.line_count

    for block in blocks:
        # Track context — ใช้สำหรับ repeat ใน chunk ถัดไป
        if block.kind == BLOCK_SECTION:
            last_section = block
            last_file = None  # section ใหม่ → reset file
            pending_vocab = None
        elif block.kind == BLOCK_FILE:
            last_file = block
            pending_vocab = None

        # Vocab hint รอ entry ถัดไป — ไม่นับเข้า chunk ตอนนี้
        if block.kind == BLOCK_VOCAB_HINT:
            pending_vocab = block
            continue

        # คำนวณบรรทัดที่ block นี้ (+ pending_vocab ถ้ามี) ต้องใช้
        adding = block.line_count
        if pending_vocab is not None and block.kind == BLOCK_ENTRY:
            adding += pending_vocab.line_count

        # ถ้าเพิ่มแล้วเกิน + chunk ปัจจุบันมี entry อย่างน้อย 1 อัน → ขึ้น chunk ใหม่
        # (มี entry อย่างน้อย 1 = ไม่ใช่แค่ headers — กัน chunk ที่มีแต่ headers ลอย)
        has_entry = any(b.kind == BLOCK_ENTRY for b in cur_chunk)
        if has_entry and (cur_lines + adding) > target_lines:
            start_new_chunk_with_context()

        # Section/File header เดิมที่เพิ่ง track ไป — ใส่เข้า chunk ปัจจุบัน
        # (skip ถ้าเพิ่งถูก repeat ตอน start_new_chunk_with_context)
        if block.kind in (BLOCK_SECTION, BLOCK_FILE):
            if not cur_chunk or cur_chunk[-1] is not block:
                cur_chunk.append(block)
                cur_lines += block.line_count
            continue

        # Entry: ใส่ vocab_hint ก่อน (ถ้ามี) แล้วใส่ entry
        if pending_vocab is not None:
            cur_chunk.append(pending_vocab)
            cur_lines += pending_vocab.line_count
            pending_vocab = None

        cur_chunk.append(block)
        cur_lines += block.line_count

    push_chunk()
    return chunks if chunks else [[]]


def build_part_filename(base_name: str, part_index: int, total_parts: int) -> str:
    """สร้างชื่อไฟล์ part เช่น 'error_trans.txt' + index 0 + total 3
    → 'error_trans_001.txt'

    total_parts <= 1 → คืนชื่อเดิม (ไม่ใส่ suffix)
    """
    if total_parts <= 1:
        return base_name
    padded = str(part_index + 1).zfill(3)
    dot_idx = base_name.rfind('.')
    if dot_idx <= 0:
        return f"{base_name}_{padded}"
    stem = base_name[:dot_idx]
    ext = base_name[dot_idx:]
    return f"{stem}_{padded}{ext}"


def is_import_part_filename(name: str, import_base_name: str) -> bool:
    """ตรวจว่าชื่อไฟล์ตรง pattern ของ import — รองรับทั้งแบบไม่ split
    ('Import.txt') และแบบ split ('Import_001.txt').
    """
    dot_idx = import_base_name.rfind('.')
    if dot_idx <= 0:
        return name == import_base_name
    stem = re.escape(import_base_name[:dot_idx])
    ext = re.escape(import_base_name[dot_idx:])
    pattern = re.compile(rf'^{stem}(?:_\d{{3}})?{ext}$', re.IGNORECASE)
    return bool(pattern.match(name))


def find_import_parts(directory, import_base_name: str) -> List:
    """Helper: หาไฟล์ทุก part ในโฟลเดอร์ — เรียงตาม part index.

    Args:
        directory: pathlib.Path
        import_base_name: เช่น 'error_trans.txt'

    Returns:
        List of pathlib.Path เรียงตามชื่อ (Errors_001.txt, Errors_002.txt, ...)
    """
    if not directory or not directory.exists():
        return []
    matches = [
        p for p in directory.iterdir()
        if p.is_file() and is_import_part_filename(p.name, import_base_name)
    ]
    matches.sort(key=lambda p: p.name)
    return matches
