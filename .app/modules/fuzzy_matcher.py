"""fuzzy_matcher.py — bigram similarity + best-error matcher.

Ported from INKIDEA's chapterCheckLogic.ts (TypeScript) — same algorithm.

ใช้ตอน import ไฟล์ error_trans.txt กลับมา เพื่อจับคู่บรรทัดที่ user/AI แก้ไข
กับ error ที่สแกนไว้ — ทนต่อ:
  - บรรทัดเลขผิด (line number drift)
  - ชื่อไฟล์ผิดเล็กน้อย
  - text [A] ขาดหรือเกินบางคำ
  - whitespace/case ต่างกัน
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Sequence, Tuple


# ============================================================
# Normalization
# ============================================================

_WS_RE = re.compile(r'\s+')
_AB_PREFIX_RE = re.compile(r'^\s*\[([AB])\]\s*', re.IGNORECASE)


def normalize_import_text(text: str) -> str:
    """Normalize for similarity comparison: strip whitespace + lowercase.

    ตรงกับ TS: text.replace(/\\s+/gu, '').trim().toLowerCase()
    """
    if not text:
        return ''
    return _WS_RE.sub('', text).strip().lower()


def strip_ab_prefix(text: str, kind: str = 'A') -> str:
    """ตัด `[A]` หรือ `[B]` prefix ออก — return ที่เหลือไม่มี whitespace ขอบ"""
    if not text:
        return ''
    return _AB_PREFIX_RE.sub('', text, count=1).strip()


# ============================================================
# Bigram (Sørensen–Dice) similarity
# ============================================================

def bigram_similarity(a: str, b: str) -> float:
    """Sørensen–Dice bigram similarity — 0.0..1.0 (1.0 = identical).

    O(n+m). Fast enough for thousands of comparisons per import.

    Args:
        a, b: pre-normalized strings (call normalize_import_text first for fairness)

    Returns:
        2 * common_bigrams / (bigrams_in_a + bigrams_in_b)
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) < 2 or len(b) < 2:
        # No bigrams possible — fall back to char equality
        return 1.0 if a == b else 0.0

    a_grams: Dict[str, int] = {}
    for i in range(len(a) - 1):
        g = a[i:i + 2]
        a_grams[g] = a_grams.get(g, 0) + 1

    common = 0
    b_gram_count = 0
    for i in range(len(b) - 1):
        g = b[i:i + 2]
        b_gram_count += 1
        left = a_grams.get(g, 0)
        if left > 0:
            common += 1
            a_grams[g] = left - 1

    total = (len(a) - 1) + b_gram_count
    if total == 0:
        return 0.0
    return (2.0 * common) / total


# ============================================================
# Best-match: combine exact lookup + fuzzy fallback
# ============================================================

def build_exact_index(errors: Sequence[Dict]) -> Dict[str, List[Dict]]:
    """สร้าง index normalize([A]) → [errors...] เพื่อ exact lookup ตอน import.

    Each error must have keys: 'original_a' (str), 'file_name' (str),
    'line_number' (int), 'file_path' (str — for disambiguation across same name)
    """
    out: Dict[str, List[Dict]] = {}
    for err in errors:
        clean = strip_ab_prefix(err.get('original_a', ''), 'A')
        key = normalize_import_text(clean)
        if not key:
            continue
        out.setdefault(key, []).append(err)
    return out


def find_best_error_by_a(
    *,
    needle_normalized_a: str,
    exact_index: Dict[str, List[Dict]],
    all_errors: Sequence[Dict],
    hint_file_name: str = '',
    hint_line_number: int = 0,
    min_ratio: float = 0.9,
    fuzzy_min_length: int = 12,
) -> Optional[Dict]:
    """จับคู่ entry จาก import file → error ที่สแกนไว้.

    Two-phase:
      1. Exact: lookup ใน hash index ตาม normalize([A])
      2. Fuzzy: scan ทุก candidate ด้วย bigram similarity, threshold ≥ min_ratio

    Anti-false-match guard:
      - ถ้า top-2 ใกล้กันมาก (Δratio < 0.02) และมาคนละไฟล์ → return None
      - ถ้า [A] สั้นเกิน (< fuzzy_min_length) → ไม่ทำ fuzzy

    Returns:
        {'error': dict, 'ratio': float, 'match_type': 'exact' | 'fuzzy'} or None
    """
    if not needle_normalized_a:
        return None

    # ===== Phase 1: exact =====
    exact_candidates = exact_index.get(needle_normalized_a, [])
    if exact_candidates:
        # rank: same file first → closest line
        ranked = sorted(
            exact_candidates,
            key=lambda e: (
                0 if e.get('file_name') == hint_file_name else 1,
                abs(int(e.get('line_number', 0)) - hint_line_number),
            ),
        )
        best = ranked[0]
        # reject ambiguous tie across different files
        if len(ranked) >= 2:
            second = ranked[1]
            same_rank = (
                ((best.get('file_name') == hint_file_name) ==
                 (second.get('file_name') == hint_file_name))
                and (abs(int(best.get('line_number', 0)) - hint_line_number) ==
                     abs(int(second.get('line_number', 0)) - hint_line_number))
            )
            if same_rank and best.get('file_path') != second.get('file_path'):
                return None
        return {'error': best, 'ratio': 1.0, 'match_type': 'exact'}

    # ===== Phase 2: fuzzy fallback =====
    if len(needle_normalized_a) < fuzzy_min_length:
        return None

    scored: List[Tuple[float, int, int, Dict]] = []  # (ratio, sameFile, lineDist, error)
    for err in all_errors:
        cand_norm = normalize_import_text(strip_ab_prefix(err.get('original_a', ''), 'A'))
        if not cand_norm:
            continue
        # length pruning — skip candidates with very different length
        len_delta = abs(len(needle_normalized_a) - len(cand_norm))
        allowed = max(6, len(needle_normalized_a) // 5)  # 20% tolerance
        if len_delta > allowed:
            continue

        ratio = bigram_similarity(needle_normalized_a, cand_norm)
        if ratio < min_ratio:
            continue

        scored.append((
            ratio,
            0 if err.get('file_name') == hint_file_name else 1,
            abs(int(err.get('line_number', 0)) - hint_line_number),
            err,
        ))

    if not scored:
        return None

    # Sort: highest ratio → same file → closest line
    scored.sort(key=lambda x: (-x[0], x[1], x[2]))
    best = scored[0]

    # reject if top-2 close + different files (avoid wrong guess)
    if len(scored) >= 2:
        second = scored[1]
        if (best[0] - second[0]) < 0.02 and best[3].get('file_path') != second[3].get('file_path'):
            return None

    return {'error': best[3], 'ratio': best[0], 'match_type': 'fuzzy'}
