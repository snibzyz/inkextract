"""error_chunker.py — แบ่ง errors เป็นหลาย part เพื่อกัน token limit ของ AI.

Ported from INKIDEA's chapterCheckExport.ts (TypeScript) — same algorithm.

ใช้ตอน export error_trans.txt ขนาดใหญ่ → แบ่งเป็น
  error_trans_001.txt, error_trans_002.txt, ...
แล้วตอน import กลับ จะ scan ทุกไฟล์ที่ตรง pattern อัตโนมัติ
"""
from __future__ import annotations
import re
from typing import List, Sequence, TypeVar

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
