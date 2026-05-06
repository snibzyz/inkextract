import streamlit as st
import re
from pathlib import Path
from typing import List

from modules import paths


class MergeProcessor:
    def __init__(self):
        self.clean_dir = paths.CLEAN_DIR
        self.merge_dir = paths.MERGE_DIR
        paths.ensure_dirs()
    
    def merge_output(
        self,
        chapters_per_file: int,
        end_credit: str,
        focus_keyword: str,
        title_prefix: str,
        title_suffix: str,
        chapter_number_padding: int,
        start_number: int,
        source_path: Path = None,
        add_filename_separator: bool = False,
        add_chapter_heading: bool = True,
        output_folder: Path = None,
        selected_files: List[Path] = None
    ) -> List[Path]:
        """รวมไฟล์ในโฟลเดอร์ output เป็นไฟล์เดียวหรือหลายไฟล์ตามจำนวนตอนต่อไฟล์

        - ถ้า chapters_per_file <= 0 จะรวมเป็นไฟล์เดียวชื่อ merged.txt
        - ถ้า chapters_per_file > 0 จะตัดแบ่งตามจำนวนตอนต่อไฟล์ เป็น merged_001.txt, merged_002.txt, ...
        - เพิ่ม end_credit ต่อท้ายตอน ถ้า end_credit ไม่ว่าง
        - คั่นตอนด้วยบรรทัดว่าง 1 บรรทัด
        - หัวบทใช้: "{focus_keyword} {title_prefix}{chapter_no:0{chapter_number_padding}d}{title_suffix}"
        """
        # เรียงไฟล์ตอนตามตัวเลขที่เจอในชื่อไฟล์
        def extract_num(path: Path) -> int:
            name = path.stem
            m = re.search(r"(\d+)", name)
            if not m:
                return 0
            try:
                return int(m.group(1))
            except Exception:
                return 0

        # ใช้ source_path ถ้ามี ไม่งั้นใช้ clean_dir เป็น default
        input_path = source_path if source_path else self.clean_dir
        
        # ถ้ามีการเลือกไฟล์เฉพาะ ให้ใช้ไฟล์ที่เลือก ไม่งั้นใช้ไฟล์ทั้งหมดในโฟลเดอร์
        if selected_files:
            chapter_files = sorted(selected_files, key=extract_num)
        else:
            chapter_files = sorted(input_path.glob("*.txt"), key=extract_num)
        
        if not chapter_files:
            st.warning(f"⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ {input_path}")
            return []
        
        # ใช้ output_folder ถ้ามี ไม่งั้นใช้ merge_dir เป็น default
        output_path = output_folder if output_folder else self.merge_dir
        output_path.mkdir(exist_ok=True)

        created_files: List[Path] = []
        total = len(chapter_files)

        def read_text_keep(content_path: Path) -> str:
            with open(content_path, 'r', encoding='utf-8') as f:
                return f.read().rstrip('\n')

        focus = focus_keyword.strip()
        chap_pad = max(1, int(chapter_number_padding))
        start_number = int(start_number)

        def build_heading(num: int) -> str:
            num_str = str(num).zfill(chap_pad)
            if focus:  # ถ้ามี focus keyword
                return f"{focus} {title_prefix}{num_str}{title_suffix}".rstrip()
            else:  # ถ้าไม่มี focus keyword
                return f"{title_prefix}{num_str}{title_suffix}".rstrip()

        # เตรียมลำดับไฟล์ (เรียงตามชื่อ/ตัวเลขในชื่อ) และจะกำหนดเลขตอนตาม start_number ต่อเนื่อง
        ordered_paths: List[Path] = list(chapter_files)

        # รวมเป็นไฟล์เดียว
        if chapters_per_file <= 0:
            # ตั้งชื่อไฟล์รวมตามช่วงเลขตอนทั้งหมด
            start_n = start_number
            end_n = start_number + total - 1
            start_str = str(start_n).zfill(chap_pad)
            end_str = str(end_n).zfill(chap_pad)
            merged_path = output_path / f"{title_prefix}{start_str}-{end_str}.txt"
            with open(merged_path, 'w', encoding='utf-8') as out:
                for idx, chapter_path in enumerate(ordered_paths):
                    num = start_number + idx
                    
                    # เพิ่มหัวข้อบทใหม่ถ้าเลือกออปชัน
                    if add_chapter_heading:
                        out.write(build_heading(num) + "\n")
                    
                    # เพิ่มชื่อไฟล์เดิมเป็นหัวข้อคั่นถ้าเลือกออปชัน
                    if add_filename_separator:
                        original_filename = chapter_path.stem  # ชื่อไฟล์ไม่รวม .txt
                        out.write(f"--- {original_filename} ---\n\n")
                    
                    out.write(read_text_keep(chapter_path) + "\n")
                    if end_credit.strip():
                        out.write(end_credit.strip() + "\n")
                    if idx != total - 1:
                        out.write("\n")
            created_files.append(merged_path)
            return created_files

        # แบ่งเป็นหลายไฟล์ตามจำนวนตอนต่อไฟล์
        groups = [ordered_paths[i:i+chapters_per_file] for i in range(0, total, chapters_per_file)]
        for group_index, group in enumerate(groups, start=0):
            group_start_num = start_number + group_index * chapters_per_file
            group_end_num = group_start_num + len(group) - 1
            start_str = str(group_start_num).zfill(chap_pad)
            end_str = str(group_end_num).zfill(chap_pad)
            filename = f"{title_prefix}{start_str}-{end_str}.txt"
            merged_path = output_path / filename
            with open(merged_path, 'w', encoding='utf-8') as out:
                for idx, chapter_path in enumerate(group):
                    num = group_start_num + idx
                    
                    # เพิ่มหัวข้อบทใหม่ถ้าเลือกออปชัน
                    if add_chapter_heading:
                        out.write(build_heading(num) + "\n")
                    
                    # เพิ่มชื่อไฟล์เดิมเป็นหัวข้อคั่นถ้าเลือกออปชัน
                    if add_filename_separator:
                        original_filename = chapter_path.stem  # ชื่อไฟล์ไม่รวม .txt
                        out.write(f"--- {original_filename} ---\n\n")
                    
                    out.write(read_text_keep(chapter_path) + "\n")
                    if end_credit.strip():
                        out.write(end_credit.strip() + "\n")
                    if idx != len(group) - 1:
                        out.write("\n")
            created_files.append(merged_path)

        return created_files
    
    def get_available_files(self, source_path: Path = None) -> List[Path]:
        """ดึงรายการไฟล์ .txt ที่พร้อมใช้งานในโฟลเดอร์"""
        input_path = source_path if source_path else self.clean_dir
        if not input_path.exists():
            return []
        
        def extract_num(path: Path) -> int:
            name = path.stem
            m = re.search(r"(\d+)", name)
            if not m:
                return 0
            try:
                return int(m.group(1))
            except Exception:
                return 0
        
        return sorted(input_path.glob("*.txt"), key=extract_num)
