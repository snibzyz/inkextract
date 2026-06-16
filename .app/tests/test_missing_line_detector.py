"""ทดสอบ missing_line_detector — โดยเฉพาะการคำนวณ "ตำแหน่งแทรก" (insert_after_line)

ครอบคลุม:
- บรรทัดที่ AI ข้ามแปล (ไม่มีใน [A] blocks) ต้องถูกตรวจเจอ (detection เดิมไม่เปลี่ยน)
- insert_after_line ชี้ตำแหน่งถูก: ต้นไฟล์ (-1), หลังบล็อกก่อนหน้า, หลายบรรทัดติดกันเรียงถูก
- บรรทัดที่มีอยู่จริง (present) ต้องไม่ถูก flag
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.missing_line_detector import find_missing_lines, _extract_a_block_spans, extract_a_blocks, normalize  # noqa: E402


def _raw(*lines):
    """สร้าง raw_entries (chapter, path, line) ตอน 1 ตามลำดับ"""
    return [(1, "raw/0001.txt", ln) for ln in lines]


def test_haystack_identical_to_old_extract():
    """spans ต้องสร้าง haystack เหมือน extract_a_blocks เดิม — กัน detection regression"""
    trans = [
        "[A] 他走进房间里面\n",
        "[B] เขาเดินเข้าไปในห้อง\n",
        "[A] 她笑了笑\n",
        "[B] เธอยิ้มนิดหน่อย\n",
    ]
    spans, _ = _extract_a_block_spans(trans)
    new_hay = ''.join(s[0] for s in spans)
    old_hay = ''.join(normalize(b) for b in extract_a_blocks(trans))
    assert new_hay == old_hay


def test_missing_title_inserts_at_top():
    """ชื่อตอนที่ AI ข้าม (บรรทัดแรก) → แทรกที่หัวไฟล์ (insert_after = -1)"""
    raw = _raw("第1章 测试标题文字", "他走进房间里面")
    trans = [
        "[A] 他走进房间里面\n",
        "[B] เขาเดินเข้าไปในห้อง\n",
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 1
    assert missing[0].text == "第1章 测试标题文字"
    assert missing[0].insert_after_line == -1  # ก่อน [A] บล็อกแรก (index 0) → แทรกที่ต้น


def test_missing_footer_inserts_after_block():
    """บรรทัดท้าย (คำเตือนเว็บจีน) ที่ AI ข้าม → แทรกหลังบล็อก [B] ก่อนหน้า"""
    raw = _raw("他走进房间里面", "记住首发网站域名twkam点com")
    trans = [
        "[A] 他走进房间里面\n",   # index 0
        "[B] เขาเดินเข้าไปในห้อง\n",  # index 1  ← ปิดบล็อก
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 1
    assert "twkam" in missing[0].text
    assert missing[0].insert_after_line == 1  # แทรกหลังบรรทัด [B] (index 1)


def test_present_line_not_flagged():
    """บรรทัดที่แปลครบ (มีใน [A]) ต้องไม่ถูก flag"""
    raw = _raw("他走进房间里面")
    trans = [
        "[A] 他走进房间里面\n",
        "[B] เขาเดินเข้าไปในห้อง\n",
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert missing == []


def test_two_consecutive_missing_share_anchor_in_order():
    """บรรทัดที่หาย 2 บรรทัดติดกัน → anchor เดียวกัน และคงลำดับ raw"""
    raw = _raw("他走进房间里面", "记住网站域名甲乙丙", "请收藏本站丁戊己")
    trans = [
        "[A] 他走进房间里面\n",
        "[B] เขาเดินเข้าไปในห้อง\n",
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 2
    assert missing[0].text == "记住网站域名甲乙丙"
    assert missing[1].text == "请收藏本站丁戊己"
    # ทั้งคู่แทรกหลังบล็อกเดียว (index 1) — ลำดับการแทรกจัดการที่ fix_files
    assert missing[0].insert_after_line == 1
    assert missing[1].insert_after_line == 1


def test_missing_between_two_present_blocks():
    """บรรทัดที่หายอยู่ "ระหว่าง" 2 บล็อกที่แปลครบ → แทรกหลังบล็อกแรก"""
    raw = _raw("他走进房间里面", "记住网站域名甲乙丙", "她笑了笑很开心")
    trans = [
        "[A] 他走进房间里面\n",   # 0
        "[B] เขาเดินเข้าไปในห้อง\n",  # 1 ← anchor สำหรับบรรทัดที่หาย
        "[A] 她笑了笑很开心\n",    # 2
        "[B] เธอยิ้มอย่างมีความสุข\n",  # 3
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 1
    assert "甲乙丙" in missing[0].text
    assert missing[0].insert_after_line == 1


def test_uses_below_neighbor_when_above_also_missing():
    """บน-ล่าง: ถ้าบรรทัดด้านบนก็หายด้วย → คร่อมด้วยบรรทัดด้านล่าง (แทรกก่อน [A] บล็อกล่าง)"""
    # raw: [0] ชื่อตอน(หาย), [1] ชื่อรอง(หาย), [2] มีแปล
    raw = _raw("第1章 标题甲乙丙", "副标题丁戊己庚", "他走进房间里面")
    trans = [
        "[A] 他走进房间里面\n",       # 0  ← ตรงกับ raw[2]
        "[B] เขาเดินเข้าไปในห้อง\n",  # 1
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 2
    # ทั้งคู่ไม่มีเพื่อนด้านบน → ใช้ด้านล่าง (บล็อก [A] index 0) → แทรกก่อนหน้า = -1 (หัวไฟล์)
    assert missing[0].insert_after_line == -1
    assert missing[1].insert_after_line == -1
    # เรียงตาม raw: ชื่อตอนก่อน ชื่อรอง
    assert missing[0].raw_line_index < missing[1].raw_line_index


def test_missing_between_present_anchors_to_above():
    """บน-ล่าง: บรรทัดที่หายอยู่ระหว่าง 2 บรรทัดที่มีแปล → ยึดบรรทัดบน (แทรกหลัง [B] บน)"""
    raw = _raw("他走进房间里面", "记住网站域名甲乙丙", "她笑了笑很开心")
    trans = [
        "[A] 他走进房间里面\n",       # 0
        "[B] เขาเดินเข้าไปในห้อง\n",  # 1  ← ยึดตรงนี้
        "[A] 她笑了笑很开心\n",        # 2
        "[B] เธอยิ้มอย่างมีความสุข\n",  # 3
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 1
    assert missing[0].insert_after_line == 1  # อยู่ระหว่างบล็อก0(จบที่1) กับบล็อก1(เริ่มที่2)


def test_header_lines_before_first_a():
    """ไฟล์มี header ก่อน [A] บล็อกแรก → title ที่หายแทรกหลัง header (ก่อน [A] แรก)"""
    raw = _raw("第1章 标题甲乙丙", "他走进房间里面")
    trans = [
        "ชื่อเรื่อง: ทดสอบ\n",   # 0  header
        "[A] 他走进房间里面\n",   # 1  [A] แรก
        "[B] เขาเดินเข้าไปในห้อง\n",  # 2
    ]
    missing = find_missing_lines(raw, trans, min_ratio=0.7)
    assert len(missing) == 1
    assert missing[0].insert_after_line == 0  # หลัง header (index 0), ก่อน [A] (index 1)


# ============================================================
if __name__ == '__main__':
    import inspect
    tests = [(n, f) for n, f in inspect.getmembers(sys.modules[__name__])
             if n.startswith('test_') and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  PASS {name}')
            passed += 1
        except AssertionError as e:
            print(f'  FAIL {name}: {e}')
            failed += 1
        except Exception as e:
            print(f'  ERR  {name}: {type(e).__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
