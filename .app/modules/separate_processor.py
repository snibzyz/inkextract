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
    
    def separate_files(self, uploaded_files, focus_keyword: str, title_prefix: str, title_suffix: str, 
                      chapter_number_padding: int, start_number: int, strip_end_credit: bool, end_credit_text: str = "จบตอน") -> List[dict]:
        """แยกไฟล์หลายไฟล์พร้อมการตั้งค่าขั้นสูง"""
        results = []
        current_chapter = start_number
        
        # เรียงไฟล์ตามชื่อ
        sorted_files = sorted(uploaded_files, key=lambda x: x.name)
        
        for uploaded_file in sorted_files:
            try:
                # อ่านเนื้อหาไฟล์
                content = uploaded_file.read().decode('utf-8')
                
                # แยกตามหัวข้อ
                sections = self._separate_by_keyword(
                    content, focus_keyword, title_prefix, title_suffix,
                    chapter_number_padding, current_chapter, strip_end_credit, end_credit_text
                )
                
                # อัปเดตหมายเลขบทถัดไป
                current_chapter += len(sections)
                
                results.append({
                    'filename': uploaded_file.name,
                    'sections': len(sections),
                    'created_files': sections
                })
                
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผล {uploaded_file.name}: {str(e)}")
        
        return results
    
    def _separate_by_keyword(self, content: str, focus_keyword: str, title_prefix: str, 
                           title_suffix: str, chapter_padding: int, start_number: int, 
                           strip_end_credit: bool, end_credit_text: str = "จบตอน") -> List[Path]:
        """แยกเนื้อหาตาม focus keyword และสร้างไฟล์"""
        lines = content.splitlines()
        created_files = []
        current_section = []
        section_count = 0
        
        for line in lines:
            line = line.rstrip()
            
            # ตรวจสอบว่าเป็นหัวข้อใหม่หรือไม่
            if line.startswith(focus_keyword):
                # บันทึกส่วนก่อนหน้า (ถ้ามี)
                if current_section:
                    file_path = self._save_section(
                        current_section, title_prefix, title_suffix, 
                        chapter_padding, start_number + section_count, strip_end_credit, end_credit_text
                    )
                    if file_path:
                        created_files.append(file_path)
                    section_count += 1
                    current_section = []
                
                # เริ่มส่วนใหม่
                current_section = [line]
            else:
                # เพิ่มบรรทัดในส่วนปัจจุบัน
                current_section.append(line)
        
        # บันทึกส่วนสุดท้าย
        if current_section:
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
