import streamlit as st
import re
from pathlib import Path
from typing import List

from modules import paths


class SeparateProcessor:
    def __init__(self):
        self.separate_dir = paths.SEPARATE_DIR
        paths.ensure_dirs()
    
    def separate_uploaded(self, content: str, focus_keyword: str, strip_end_credit: str) -> List[Path]:
        """แยกไฟล์ merged ตามหัวข้อที่ขึ้นต้นด้วย focus_keyword เก็บเป็นไฟล์ใน separate/ โดยใช้ชื่อหลังหัวข้อเป็นชื่อไฟล์

        - ตัวแบ่งตอน: บรรทัดที่ขึ้นต้นด้วย f"{focus_keyword} "
        - ส่วนที่เหลือของบรรทัดจะถูกใช้เป็นชื่อไฟล์ (เติม .txt)
        - ถ้า strip_end_credit ไม่ว่าง จะลบบรรทัดที่เท่ากับค่านั้นออกจากตอน
        """
        lines = content.splitlines()
        focus = focus_keyword.strip()
        created: List[Path] = []
        current_title: str = ""
        buffer: List[str] = []

        def flush():
            nonlocal buffer, current_title
            if not current_title:
                return
            safe_name = re.sub(r"[\\/:*?\"<>|]", "_", current_title).strip()
            if not safe_name:
                return
            out_path = self.separate_dir / f"{safe_name}.txt"
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(buffer).rstrip('\n') + "\n")
            created.append(out_path)
            current_title = ""
            buffer = []

        for raw in lines:
            line = raw.rstrip('\n')
            if line.startswith(focus + " "):
                # เจอหัวข้อใหม่ → flush ก่อนหน้า
                flush()
                current_title = line[len(focus) + 1:].strip()
                continue
            # เก็บเนื้อหาในตอน
            if strip_end_credit and line.strip() == strip_end_credit.strip():
                continue
            buffer.append(line)

        # flush ตอนสุดท้าย
        flush()
        return created
    
    # โหมดจัดการบรรทัดหัวตอน (ตัวแยก) ในไฟล์ที่แยกออกมา
    HEADER_MODES = ("keep", "drop_line", "strip_marker")

    @staticmethod
    def _transform_header(line: str, focus_keyword: str, header_mode: str):
        """แปลงบรรทัดหัวตอนตามโหมด — คืนค่าที่จะเก็บไว้ในไฟล์ตอน หรือ None ถ้าให้ตัดทั้งบรรทัด

        - keep         : เก็บบรรทัดหัวตอนไว้ตามเดิม
        - drop_line    : ตัดทั้งบรรทัดหัวตอน (คืน None)
        - strip_marker : ตัดเฉพาะเครื่องหมาย focus_keyword ออก เก็บข้อความที่เหลือ
        """
        if header_mode == "drop_line":
            return None
        if header_mode == "strip_marker":
            stripped = line.lstrip()[len(focus_keyword):].lstrip()
            return stripped or None
        return line  # keep

    def separate_files(self, uploaded_files, focus_keyword: str, title_prefix: str, title_suffix: str,
                      chapter_number_padding: int, start_number: int, strip_end_credit: bool,
                      end_credit_text: str = "จบตอน", header_mode: str = "keep") -> dict:
        """แยกไฟล์หลายไฟล์ — รวมทุกไฟล์เป็น stream เดียวก่อน แล้วค่อยหั่นเป็นตอน

        หลักการ "รวมก่อนหั่น" (merge-then-split):
          ตอนหนึ่งอาจถูกตัดคร่อมขอบไฟล์ — จบไฟล์ A กลางตอน เนื้อหาไปต่อหัวไฟล์ B
          ถ้าหั่นทีละไฟล์ ตอนที่คร่อมไฟล์จะกลายเป็น 2 ไฟล์ (ท้ายขาด + หัวขาด)
          และเนื้อหาก่อน focus_keyword ตัวแรกของแต่ละไฟล์จะถูกนับเป็นตอนซ้ำซ้อน
          การรวมทุกไฟล์เป็น stream เดียวก่อนหั่น ทำให้ตอนที่คร่อมไฟล์ยังครบในไฟล์เดียว
          และเลขตอนเรียงต่อเนื่องถูกต้องทั้งชุด

        Args:
            header_mode: จัดการบรรทัดหัวตอน — "keep" / "drop_line" / "strip_marker"

        Returns:
            dict: {'source_files': [ชื่อไฟล์ต้นทาง...], 'sections': N, 'created_files': [Path...]}
        """
        empty = {'source_files': [], 'sections': 0, 'created_files': []}
        if not uploaded_files:
            return empty

        # เรียงไฟล์ตามชื่อ — ลำดับชื่อไฟล์คือลำดับเนื้อเรื่อง
        sorted_files = sorted(uploaded_files, key=lambda x: x.name)

        # ── รวมทุกไฟล์เป็น stream เดียว (merge เข้า buffer) ──
        merged_parts: List[str] = []
        source_names: List[str] = []
        for uploaded_file in sorted_files:
            try:
                content = uploaded_file.read().decode('utf-8')
            except Exception as e:
                st.error(f"อ่านไฟล์ {uploaded_file.name} ไม่ได้: {str(e)}")
                continue
            # rstrip กันบรรทัดว่างท้ายไฟล์ทำให้เกิดช่องว่างเกินตอนเชื่อม
            merged_parts.append(content.rstrip('\n'))
            source_names.append(uploaded_file.name)

        if not merged_parts:
            return empty

        # คั่นแต่ละไฟล์ด้วยขึ้นบรรทัดใหม่ — กันบรรทัดท้ายไฟล์ A ติดกับบรรทัดหัวไฟล์ B
        merged_content = "\n".join(merged_parts)

        # ── หั่นตอนจาก stream ที่รวมแล้ว (ครั้งเดียว) ──
        created_files = self._separate_by_keyword(
            merged_content, focus_keyword, title_prefix, title_suffix,
            chapter_number_padding, start_number, strip_end_credit, end_credit_text,
            header_mode=header_mode,
        )

        return {
            'source_files': source_names,
            'sections': len(created_files),
            'created_files': created_files,
        }
    
    def _separate_by_keyword(self, content: str, focus_keyword: str, title_prefix: str,
                           title_suffix: str, chapter_padding: int, start_number: int,
                           strip_end_credit: bool, end_credit_text: str = "จบตอน",
                           header_mode: str = "keep") -> List[Path]:
        """แยกเนื้อหาตาม focus keyword และสร้างไฟล์

        section_started = เจอบรรทัดหัวตอนแล้วอย่างน้อย 1 ครั้ง — ใช้แยกกรณี
        "section ที่หัวตอนถูกตัดทิ้ง (drop_line) จนยังว่าง" ออกจาก "ยังไม่เริ่ม section"
        เพื่อให้เลขตอนเรียงตรงไม่ว่าจะเลือก header_mode ใด
        """
        lines = content.splitlines()
        created_files = []
        current_section: List[str] = []
        section_started = False
        section_count = 0

        for line in lines:
            line = line.rstrip()

            # ตรวจสอบว่าเป็นหัวข้อใหม่หรือไม่
            if line.startswith(focus_keyword):
                # บันทึกส่วนก่อนหน้า (preamble หรือตอนที่เริ่มไปแล้ว)
                if section_started or current_section:
                    file_path = self._save_section(
                        current_section, title_prefix, title_suffix,
                        chapter_padding, start_number + section_count, strip_end_credit, end_credit_text
                    )
                    if file_path:
                        created_files.append(file_path)
                    section_count += 1

                # เริ่มส่วนใหม่ — จัดการบรรทัดหัวตอนตาม header_mode
                section_started = True
                head = self._transform_header(line, focus_keyword, header_mode)
                current_section = [head] if head is not None else []
            else:
                # เพิ่มบรรทัดในส่วนปัจจุบัน
                current_section.append(line)

        # บันทึกส่วนสุดท้าย
        if section_started or current_section:
            file_path = self._save_section(
                current_section, title_prefix, title_suffix,
                chapter_padding, start_number + section_count, strip_end_credit, end_credit_text
            )
            if file_path:
                created_files.append(file_path)

        return created_files
    
    def _save_section(self, section_lines: List[str], title_prefix: str, title_suffix: str,
                     chapter_padding: int, chapter_number: int, strip_end_credit: bool, end_credit_text: str = "จบตอน") -> Path:
        """บันทึกส่วนเป็นไฟล์"""
        if not section_lines:
            return None
        
        # สร้างชื่อไฟล์
        chapter_str = str(chapter_number).zfill(chapter_padding)
        filename = f"{title_prefix}{chapter_str}{title_suffix}.txt"
        file_path = self.separate_dir / filename
        
        # กรองเนื้อหา
        filtered_lines = []
        for line in section_lines:
            # ลบ end credit ถ้าตั้งค่าไว้
            if strip_end_credit and line.strip() in [end_credit_text.strip(), '[จบแล้ว]', 'จบแล้ว']:
                continue
            filtered_lines.append(line)
        
        # เพิ่ม end credit ถ้าไม่ได้ลบและมีเนื้อหา
        if not strip_end_credit and end_credit_text.strip() and filtered_lines:
            filtered_lines.append(end_credit_text.strip())
        
        # บันทึกไฟล์
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(filtered_lines))
            
            return file_path
        except Exception as e:
            st.error(f"❌ ไม่สามารถบันทึกไฟล์ {filename}: {str(e)}")
            return None
