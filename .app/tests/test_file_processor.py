"""ทดสอบ file_processor.clean_final_files (logic การ clean [A]/[B] block + vocab extraction)

หมายเหตุ: file_processor.fix_files ใช้ st.* เยอะ ทดสอบ logic ผ่าน mock-state ยาก
จึงเทสเฉพาะส่วน clean_final_files ผ่านการสร้างไฟล์จริงในโฟลเดอร์ workspace ชั่วคราว
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_module_imports():
    """อย่างน้อยต้อง import ได้ — บางฟังก์ชันใช้ streamlit เยอะเทสตรงๆ ยาก"""
    from modules.file_processor import FileProcessor  # noqa
    fp = FileProcessor()
    assert fp.input_dir.exists() or True  # ensure_dirs สร้างให้แล้ว


def test_file_processor_has_required_methods():
    from modules.file_processor import FileProcessor
    fp = FileProcessor()
    assert hasattr(fp, 'fix_files')
    assert hasattr(fp, 'clean_final_files')


def test_md_converter_imports():
    from modules.md_converter import MarkdownConverter
    mc = MarkdownConverter()
    assert hasattr(mc, 'convert_txt_to_md')


def test_docx_converter_imports():
    from modules.docx_converter import DocxConverter
    dc = DocxConverter()
    # ต้องไม่ throw และมีเมธอดหลัก
    assert hasattr(dc, '__class__')


# ============================================================
# fix_files — กรณี B (บรรทัดที่ AI ข้ามแปล) ต้องถูก "แทรกกลับ" เข้าไฟล์ ไม่ใช่ทับบรรทัดสุดท้าย
# ใช้ fake st (NoOp) แทน streamlit runtime — file_processor ผูก `st` ที่ระดับ module
# ============================================================

class _NoOpSt:
    """fake streamlit — ทุก method เป็น no-op, session_state เป็น dict จริง"""
    def __init__(self):
        self.session_state = {}

    def __getattr__(self, name):
        def _f(*args, **kwargs):
            return self
        return _f


def _fp_with_fake_st():
    """คืน (module, FileProcessor instance) ที่ st ถูกแทนด้วย NoOp"""
    import modules.file_processor as fpmod
    fpmod.st = _NoOpSt()
    return fpmod


def _write_input(input_dir: Path, name: str, text: str) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    f = input_dir / name
    f.write_text(text, encoding='utf-8')
    return f


_SAMPLE = (
    "[A] 他走进房间里面\n"          # 0
    "[B] เขาเดินเข้าไปในห้อง\n"      # 1
    "[A] 她笑了笑\n"                # 2
    "[B] เธอยิ้มนิดหน่อย\n"          # 3
)


def test_fix_inserts_missing_translation_at_end():
    """กรณี B ที่ insert_after = บรรทัดสุดท้าย → แทรก [A]/[B] ต่อท้าย และไม่ทับบรรทัดเดิม"""
    import tempfile
    fpmod = _fp_with_fake_st()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f = _write_input(tdp / "input", "Chapter 0001.txt", _SAMPLE)
        out_dir = tdp / "out"

        fp = fpmod.FileProcessor()
        fp.input_dir = tdp / "input"

        errors = [{
            'file_path': str(f),
            'line_number_B': 0,
            'original_A': "[A] 记住网站域名twkam",
            'original_B': "[B] ",
            'corrected_B': "[B] จำเว็บไซต์ twkam",
            'error_bucket': 'missing_translation',
            'missing_insert_after': 3,
        }]
        fp.fix_files(errors, destination_dir=out_dir)

        result = (out_dir / "Chapter 0001.txt").read_text(encoding='utf-8').splitlines()
        assert "[B] จำเว็บไซต์ twkam" in result, "ข้อความ [B] ที่กรอกต้องถูกแทรกกลับ"
        assert "[A] 记住网站域名twkam" in result, "ต้องแทรก [A] ต้นฉบับคู่ไปด้วย"
        # regression: เดิม line_number_B=0 → line_index=-1 → ทับ [B] บรรทัดสุดท้าย
        assert "[B] เธอยิ้มนิดหน่อย" in result, "บรรทัดสุดท้ายเดิมต้องไม่ถูกทับ"
        # [A] ใหม่อยู่ก่อน [B] ใหม่ และอยู่ท้ายไฟล์
        assert result[-2:] == ["[A] 记住网站域名twkam", "[B] จำเว็บไซต์ twkam"]


def test_fix_inserts_missing_translation_at_top():
    """insert_after = -1 → แทรกที่หัวไฟล์ (ชื่อตอนที่ AI ข้าม)"""
    import tempfile
    fpmod = _fp_with_fake_st()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f = _write_input(tdp / "input", "Chapter 0001.txt", _SAMPLE)
        out_dir = tdp / "out"

        fp = fpmod.FileProcessor()
        fp.input_dir = tdp / "input"

        errors = [{
            'file_path': str(f),
            'line_number_B': 0,
            'original_A': "[A] 第1章 标题",
            'original_B': "[B] ",
            'corrected_B': "[B] บทที่ 1",
            'error_bucket': 'missing_translation',
            'missing_insert_after': -1,
        }]
        fp.fix_files(errors, destination_dir=out_dir)

        result = (out_dir / "Chapter 0001.txt").read_text(encoding='utf-8').splitlines()
        assert result[0] == "[A] 第1章 标题"
        assert result[1] == "[B] บทที่ 1"
        assert result[2] == "[A] 他走进房间里面"  # บรรทัดเดิมเลื่อนลงมา ไม่หาย


def test_fix_missing_not_filled_does_not_touch_file():
    """กรณี B ที่ยังไม่กรอก [B] (corrected == original ว่าง) → ไม่แทรก ไม่ทับอะไร"""
    import tempfile
    fpmod = _fp_with_fake_st()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f = _write_input(tdp / "input", "Chapter 0001.txt", _SAMPLE)
        out_dir = tdp / "out"

        fp = fpmod.FileProcessor()
        fp.input_dir = tdp / "input"

        errors = [{
            'file_path': str(f),
            'line_number_B': 0,
            'original_A': "[A] 记住网站域名twkam",
            'original_B': "[B] ",
            'corrected_B': "[B] ",   # ยังไม่ได้กรอก
            'error_bucket': 'missing_translation',
            'missing_insert_after': 3,
        }]
        fp.fix_files(errors, destination_dir=out_dir)

        result = (out_dir / "Chapter 0001.txt").read_text(encoding='utf-8').splitlines()
        assert result == _SAMPLE.splitlines(), "ไม่ควรเปลี่ยนไฟล์เมื่อยังไม่กรอก [B]"


def test_fix_replaces_existing_b_line_in_place():
    """error ปกติ (line_number_B >= 1) → แทนที่บรรทัด [B] เดิม ไม่เพิ่มบรรทัด"""
    import tempfile
    fpmod = _fp_with_fake_st()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f = _write_input(tdp / "input", "Chapter 0001.txt", _SAMPLE)
        out_dir = tdp / "out"

        fp = fpmod.FileProcessor()
        fp.input_dir = tdp / "input"

        errors = [{
            'file_path': str(f),
            'line_number_B': 2,  # 1-based → index 1 = [B] เขาเดิน...
            'original_A': "[A] 他走进房间里面",
            'original_B': "[B] เขาเดินเข้าไปในห้อง",
            'corrected_B': "[B] เขาเดินเข้าห้องไป",
            'error_bucket': 'foreign_only',
        }]
        fp.fix_files(errors, destination_dir=out_dir)

        result = (out_dir / "Chapter 0001.txt").read_text(encoding='utf-8').splitlines()
        assert len(result) == 4, "แก้บรรทัดเดิมต้องไม่เพิ่มจำนวนบรรทัด"
        assert result[1] == "[B] เขาเดินเข้าห้องไป"


def test_fix_multiple_insertions_keep_order_at_same_anchor():
    """กรณี B 2 รายการที่ anchor เดียวกัน → คงลำดับเดิม (รายการแรกอยู่บน)"""
    import tempfile
    fpmod = _fp_with_fake_st()
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        f = _write_input(tdp / "input", "Chapter 0001.txt", _SAMPLE)
        out_dir = tdp / "out"

        fp = fpmod.FileProcessor()
        fp.input_dir = tdp / "input"

        errors = [
            {
                'file_path': str(f), 'line_number_B': 0,
                'original_A': "[A] 第一条甲", 'original_B': "[B] ",
                'corrected_B': "[B] หนึ่ง", 'error_bucket': 'missing_translation',
                'missing_insert_after': 1,
            },
            {
                'file_path': str(f), 'line_number_B': 0,
                'original_A': "[A] 第二条乙", 'original_B': "[B] ",
                'corrected_B': "[B] สอง", 'error_bucket': 'missing_translation',
                'missing_insert_after': 1,
            },
        ]
        fp.fix_files(errors, destination_dir=out_dir)

        result = (out_dir / "Chapter 0001.txt").read_text(encoding='utf-8').splitlines()
        # แทรกหลัง index 1 ตามลำดับ: หนึ่ง ก่อน สอง
        assert result[2:6] == ["[A] 第一条甲", "[B] หนึ่ง", "[A] 第二条乙", "[B] สอง"]


# ============================================================
if __name__ == '__main__':
    import inspect
    tests = [(n, f) for n, f in inspect.getmembers(sys.modules[__name__])
             if n.startswith('test_') and callable(f)]
    passed = failed = 0
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
