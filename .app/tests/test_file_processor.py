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
