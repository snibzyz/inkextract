import streamlit as st
from pathlib import Path
from typing import List, Dict
import re

from modules import paths


class MarkdownConverter:
    def __init__(self):
        self.clean_dir = paths.CLEAN_DIR
        # alias เพื่อ backward compat — ทั้งคู่ชี้ที่ 2-clean ตอนนี้
        self.md_dir = paths.CLEAN_DIR
        self.output_dir = paths.OUTPUT_DIR
        paths.ensure_dirs()
    
    def convert_txt_to_md(self, source_dir: Path = None, target_dir: Path = None, in_place: bool = True) -> Dict:
        """
        เปลี่ยนนามสกุลไฟล์จาก .txt เป็น .md (แปลงใน-place ที่ 2-clean)
        
        Args:
            source_dir: โฟลเดอร์ต้นทาง (default: 2-clean)
            target_dir: โฟลเดอร์ปลายทาง (ไม่ใช้ถ้า in_place=True)
            in_place: ถ้า True จะเปลี่ยนนามสกุลไฟล์โดยตรงในโฟลเดอร์เดิม (default: True)
        
        Returns:
            Dict: ผลลัพธ์การแปลง
        """
        if source_dir is None:
            source_dir = self.clean_dir
        if target_dir is None:
            target_dir = self.md_dir
        
        try:
            # ตรวจสอบโฟลเดอร์ต้นทาง
            if not source_dir.exists():
                return {
                    'success': False,
                    'error': f"โฟลเดอร์ {source_dir} ไม่มีอยู่",
                    'files_processed': 0
                }
            
            # ค้นหาไฟล์ .txt ทั้งหมด
            txt_files = list(source_dir.glob("*.txt"))
            if not txt_files:
                return {
                    'success': False,
                    'error': f"ไม่พบไฟล์ .txt ในโฟลเดอร์ {source_dir}",
                    'files_processed': 0
                }
            
            # แสดง progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            converted_files = []
            errors = []
            total_files = len(txt_files)
            
            for i, txt_file in enumerate(txt_files):
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"กำลังแปลง: {txt_file.name} ({i+1}/{total_files})")
                
                try:
                    if in_place:
                        # แปลงใน-place: เปลี่ยนนามสกุลไฟล์โดยตรงในโฟลเดอร์เดิม
                        md_file = source_dir / f"{txt_file.stem}.md"
                        
                        # อ่านไฟล์ .txt
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # แก้ปัญหาบรรทัดติดกัน - แยกบรรทัดและใส่ line break ที่ถูกต้อง
                        lines = content.split('\n')
                        fixed_content = []
                        
                        for line in lines:
                            # ตรวจสอบว่าบรรทัดนี้มีเนื้อหาหรือไม่
                            if line.strip():  # มีเนื้อหา
                                fixed_content.append(line)
                            else:  # บรรทัดว่าง
                                fixed_content.append('')
                        
                        # รวมบรรทัดด้วย \n
                        fixed_content_str = '\n'.join(fixed_content)
                        
                        # เขียนไฟล์ .md ใหม่
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content_str)
                        
                        # ลบไฟล์ .txt เดิม
                        txt_file.unlink()
                        
                        converted_files.append(md_file.name)
                    else:
                        # แบบเดิม: คัดลอกไปยัง target_dir
                        # อ่านไฟล์ .txt
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # แก้ปัญหาบรรทัดติดกัน - แยกบรรทัดและใส่ line break ที่ถูกต้อง
                        lines = content.split('\n')
                        fixed_content = []
                        
                        for line in lines:
                            # ตรวจสอบว่าบรรทัดนี้มีเนื้อหาหรือไม่
                            if line.strip():  # มีเนื้อหา
                                fixed_content.append(line)
                            else:  # บรรทัดว่าง
                                fixed_content.append('')
                        
                        # รวมบรรทัดด้วย \n
                        fixed_content_str = '\n'.join(fixed_content)
                        
                        # สร้างไฟล์ .md (แค่เปลี่ยนนามสกุล)
                        md_file = target_dir / f"{txt_file.stem}.md"
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content_str)
                        
                        converted_files.append(md_file.name)
                    
                except Exception as e:
                    errors.append(f"❌ ไม่สามารถแปลง {txt_file.name}: {str(e)}")
            
            # เสร็จสิ้น
            progress_bar.progress(1.0)
            status_text.text("🎉 การแปลงเสร็จสิ้น!")
            
            return {
                'success': True,
                'files_processed': len(converted_files),
                'converted_files': converted_files,
                'errors': errors,
                'source_dir': str(source_dir),
                'target_dir': str(source_dir) if in_place else str(target_dir),
                'in_place': in_place
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"เกิดข้อผิดพลาด: {str(e)}",
                'files_processed': 0
            }
    
    def convert_md_to_txt(self, source_dir: Path = None, target_dir: Path = None, in_place: bool = True) -> Dict:
        """
        เปลี่ยนนามสกุลไฟล์จาก .md เป็น .txt (แปลงใน-place ที่ 2-clean)
        
        Args:
            source_dir: โฟลเดอร์ต้นทาง (default: 2-clean)
            target_dir: โฟลเดอร์ปลายทาง (ไม่ใช้ถ้า in_place=True)
            in_place: ถ้า True จะเปลี่ยนนามสกุลไฟล์โดยตรงในโฟลเดอร์เดิม (default: True)
        
        Returns:
            Dict: ผลลัพธ์การแปลง
        """
        if source_dir is None:
            source_dir = self.clean_dir
        if target_dir is None:
            target_dir = self.md_dir
        
        try:
            # ตรวจสอบโฟลเดอร์ต้นทาง
            if not source_dir.exists():
                return {
                    'success': False,
                    'error': f"โฟลเดอร์ {source_dir} ไม่มีอยู่",
                    'files_processed': 0
                }
            
            # ค้นหาไฟล์ .md ทั้งหมด
            md_files = list(source_dir.glob("*.md"))
            if not md_files:
                return {
                    'success': False,
                    'error': f"ไม่พบไฟล์ .md ในโฟลเดอร์ {source_dir}",
                    'files_processed': 0
                }
            
            # แสดง progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            converted_files = []
            errors = []
            total_files = len(md_files)
            
            for i, md_file in enumerate(md_files):
                progress = (i + 1) / total_files
                progress_bar.progress(progress)
                status_text.text(f"กำลังแปลง: {md_file.name} ({i+1}/{total_files})")
                
                try:
                    if in_place:
                        # แปลงใน-place: เปลี่ยนนามสกุลไฟล์โดยตรงในโฟลเดอร์เดิม
                        txt_file = source_dir / f"{md_file.stem}.txt"
                        
                        # อ่านไฟล์ .md
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # แก้ปัญหาบรรทัดติดกัน - แยกบรรทัดและใส่ line break ที่ถูกต้อง
                        lines = content.split('\n')
                        fixed_content = []
                        
                        for line in lines:
                            # ตรวจสอบว่าบรรทัดนี้มีเนื้อหาหรือไม่
                            if line.strip():  # มีเนื้อหา
                                fixed_content.append(line)
                            else:  # บรรทัดว่าง
                                fixed_content.append('')
                        
                        # รวมบรรทัดด้วย \n
                        fixed_content_str = '\n'.join(fixed_content)
                        
                        # เขียนไฟล์ .txt ใหม่
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content_str)
                        
                        # ลบไฟล์ .md เดิม
                        md_file.unlink()
                        
                        converted_files.append(txt_file.name)
                    else:
                        # แบบเดิม: คัดลอกไปยัง target_dir
                        # อ่านไฟล์ .md
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # แก้ปัญหาบรรทัดติดกัน - แยกบรรทัดและใส่ line break ที่ถูกต้อง
                        lines = content.split('\n')
                        fixed_content = []
                        
                        for line in lines:
                            # ตรวจสอบว่าบรรทัดนี้มีเนื้อหาหรือไม่
                            if line.strip():  # มีเนื้อหา
                                fixed_content.append(line)
                            else:  # บรรทัดว่าง
                                fixed_content.append('')
                        
                        # รวมบรรทัดด้วย \n
                        fixed_content_str = '\n'.join(fixed_content)
                        
                        # สร้างไฟล์ .txt (แค่เปลี่ยนนามสกุล)
                        txt_file = target_dir / f"{md_file.stem}.txt"
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(fixed_content_str)
                        
                        converted_files.append(txt_file.name)
                    
                except Exception as e:
                    errors.append(f"❌ ไม่สามารถแปลง {md_file.name}: {str(e)}")
            
            # เสร็จสิ้น
            progress_bar.progress(1.0)
            status_text.text("🎉 การแปลงเสร็จสิ้น!")
            
            return {
                'success': True,
                'files_processed': len(converted_files),
                'converted_files': converted_files,
                'errors': errors,
                'source_dir': str(source_dir),
                'target_dir': str(source_dir) if in_place else str(target_dir),
                'in_place': in_place
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"เกิดข้อผิดพลาด: {str(e)}",
                'files_processed': 0
            }
    
    
    def get_file_stats(self) -> Dict:
        """
        ดึงสถิติไฟล์ในโฟลเดอร์ต่างๆ
        
        Returns:
            Dict: สถิติไฟล์
        """
        stats = {
            'clean_files': 0,
            'md_files': 0,
            'clean_size': 0,
            'md_size': 0
        }
        
        # นับไฟล์ .txt ใน 2-clean
        if self.clean_dir.exists():
            txt_files = list(self.clean_dir.glob("*.txt"))
            stats['clean_files'] = len(txt_files)
            for f in txt_files:
                stats['clean_size'] += f.stat().st_size
            
            # นับไฟล์ .md ใน 2-clean (สำหรับ in-place conversion)
            md_files = list(self.clean_dir.glob("*.md"))
            stats['md_files'] = len(md_files)
            for f in md_files:
                stats['md_size'] += f.stat().st_size

        return stats
    
    def preview_conversion(self, source_dir: Path, preview_lines: int = 10, file_extension: str = None) -> Dict:
        """
        แสดงตัวอย่างการแปลง
        
        Args:
            source_dir: โฟลเดอร์ที่ต้องการดูตัวอย่าง
            preview_lines: จำนวนบรรทัดที่แสดง
            file_extension: นามสกุลไฟล์ที่ต้องการดู ("txt", "md", หรือ None สำหรับดูทั้งหมด)
        
        Returns:
            Dict: ข้อมูลตัวอย่าง
        """
        if not source_dir.exists():
            return {'error': f"โฟลเดอร์ {source_dir} ไม่มีอยู่"}
        
        files = []
        if file_extension:
            file_pattern = f"*.{file_extension}"
            file_type = file_extension.upper()
        elif source_dir == self.clean_dir:
            # สำหรับ in-place conversion ให้ดูทั้ง .txt และ .md
            file_pattern = ["*.txt", "*.md"]
            file_type = "TXT/MD"
        else:
            file_pattern = "*.md"
            file_type = "Markdown"
        
        # รองรับทั้ง pattern เดียวและหลาย pattern
        if isinstance(file_pattern, list):
            source_files = []
            for pattern in file_pattern:
                source_files.extend(list(source_dir.glob(pattern)))
        else:
            source_files = list(source_dir.glob(file_pattern))
        
        for file_path in source_files[:3]:  # แสดงแค่ 3 ไฟล์แรก
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')[:preview_lines]
                
                # กำหนดประเภทไฟล์จากนามสกุลจริง
                actual_type = "TXT" if file_path.suffix == ".txt" else "MD" if file_path.suffix == ".md" else file_type
                
                files.append({
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'preview': '\n'.join(lines),
                    'type': actual_type
                })
            except Exception as e:
                files.append({
                    'name': file_path.name,
                    'error': str(e)
                })
        
        return {
            'files': files,
            'total_files': len(source_files),
            'directory': str(source_dir)
        }
