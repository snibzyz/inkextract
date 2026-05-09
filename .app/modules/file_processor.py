import streamlit as st
import re
from pathlib import Path
from typing import List

from modules import paths


class FileProcessor:
    def __init__(self):
        self.input_dir = paths.INPUT_DIR
        self.output_dir = paths.OUTPUT_DIR
        self.fix_dir = paths.FIX_DIR
        self.clean_dir = paths.CLEAN_DIR
        self.merge_dir = paths.MERGE_DIR
        self.separate_dir = paths.SEPARATE_DIR
        paths.ensure_dirs()
    
    def fix_files(self, found_errors: List[dict]):
        """แก้ไขไฟล์และบันทึกลงโฟลเดอร์ fix - ดึงไฟล์ทั้งหมดจาก input และแก้เฉพาะบรรทัดที่มีปัญหา"""
        try:
            # แสดง progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # ดึงไฟล์ทั้งหมดจาก input
            txt_files = list(self.input_dir.glob("*.txt"))
            if not txt_files:
                st.warning("⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ 0-input")
                st.info("💡 กรุณาวางไฟล์ .txt ที่ต้องการแก้ไขไว้ในโฟลเดอร์ 0-input")
                return
            
            # ถ้าไม่มีข้อผิดพลาด ให้คัดลอกไฟล์ทั้งหมดไปยังโฟลเดอร์ fix
            if not found_errors:
                st.info("ℹ️ ไม่พบข้อผิดพลาด - จะคัดลอกไฟล์ทั้งหมดไปยังโฟลเดอร์ 1-fix")
            
            # สร้าง dict สำหรับเก็บข้อผิดพลาดตามไฟล์
            errors_by_file = {}
            for error in found_errors:
                file_path = error['file_path']
                if file_path not in errors_by_file:
                    errors_by_file[file_path] = []
                errors_by_file[file_path].append(error)
            
            # Debug: แสดงข้อมูล found_errors
            st.write(f"🔍 **Debug Fix Process:** พบ {len(found_errors)} รายการทั้งหมด")
            for file_path, errors in errors_by_file.items():
                file_name = Path(file_path).name
                st.write(f"  📁 {file_name}: {len(errors)} รายการ")
                for i, error in enumerate(errors[:2]):  # แสดงแค่ 2 รายการแรก
                    st.write(f"    {i+1}. บรรทัด {error['line_number_B']}: `{error['original_B'][:50]}...`")
                    st.write(f"       แก้ไขแล้ว: {'✅' if error.get('corrected_B', error['original_B']) != error['original_B'] else '❌'}")
            
            total_files = len(txt_files)
            processed_files = 0
            
            # ประมวลผลแต่ละไฟล์
            for file_path in txt_files:
                processed_files += 1
                file_name = file_path.name
                
                # อัปเดต progress
                progress = processed_files / total_files
                progress_bar.progress(progress)
                status_text.text(f"กำลังประมวลผลไฟล์: {file_name} ({processed_files}/{total_files})")
                
                # อ่านไฟล์ต้นฉบับ
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # แก้ไขบรรทัดที่มีปัญหา (ถ้ามี)
                fixed_lines = 0
                file_errors = errors_by_file.get(str(file_path), [])
                for error in file_errors:
                    line_index = error['line_number_B'] - 1
                    if line_index < len(lines):
                        # ใช้ corrected_B ถ้าแก้ไขแล้ว ไม่งั้นใช้ original_B
                        corrected_text = error.get('corrected_B', error['original_B'])
                        
                        # ตรวจสอบว่าได้แก้ไขจริงหรือไม่
                        if corrected_text != error['original_B']:
                            # แก้ไขแล้ว - ใช้ corrected_B
                            lines[line_index] = corrected_text + '\n'
                            fixed_lines += 1
                        else:
                            # ยังไม่ได้แก้ไข - ใช้ original_B (ไม่นับเป็น fixed)
                            lines[line_index] = corrected_text + '\n'
                
                # บันทึกไฟล์ใหม่ในโฟลเดอร์ fix (ทุกไฟล์)
                output_file = self.fix_dir / file_name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                if fixed_lines > 0:
                    status_text.text(f"✅ แก้ไขไฟล์ {file_name} สำเร็จ (แก้ไข {fixed_lines} บรรทัด)")
                else:
                    status_text.text(f"✅ คัดลอกไฟล์ {file_name} สำเร็จ (ไม่มีข้อผิดพลาด)")
                
                # Debug: แสดงข้อมูลการแก้ไข
                if file_errors:
                    st.write(f"🔍 **Debug สำหรับ {file_name}:**")
                    st.write(f"  📊 พบ {len(file_errors)} รายการในไฟล์นี้")
                    for i, error in enumerate(file_errors[:3]):  # แสดงแค่ 3 รายการแรก
                        original = error['original_B']
                        corrected = error.get('corrected_B', original)
                        is_changed = corrected != original
                        st.write(f"  {i+1}. บรรทัด {error['line_number_B']}: {'✅ แก้ไขแล้ว' if is_changed else '❌ ยังไม่ได้แก้ไข'}")
                        st.write(f"     A: `{error['original_A'][:50]}...`")
                        st.write(f"     B เดิม: `{original[:50]}...`")
                        if is_changed:
                            st.write(f"     B ใหม่: `{corrected[:50]}...`")
                    if len(file_errors) > 3:
                        st.write(f"  ... และอีก {len(file_errors) - 3} รายการ")
                else:
                    st.write(f"🔍 **Debug สำหรับ {file_name}:** ไม่พบข้อผิดพลาดในไฟล์นี้")
            
            # เสร็จสิ้น
            progress_bar.progress(1.0)
            status_text.text("🎉 กระบวนการแก้ไขไฟล์เสร็จสิ้น!")
            
            # แสดงรายชื่อไฟล์ที่สร้าง
            for file_path in txt_files:
                file_name = file_path.name
                st.write(f"  ✅ `{file_name}`")
            
            st.info("💡 **หมายเหตุ:** ไฟล์ต้นฉบับในโฟลเดอร์ 0-input และ 1-fix ไม่ถูกแก้ไข สามารถใช้งานซ้ำได้")
        
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการแก้ไขไฟล์: {str(e)}")
            st.exception(e)
    
    def clean_final_files(self):
        """ทำความสะอาดไฟล์จากโฟลเดอร์ fix และบันทึกลงโฟลเดอร์ clean"""
        try:
            # ทำความสะอาดจากไฟล์ใน fix ทุกไฟล์ (ไฟล์ที่แก้ไขแล้ว)
            txt_files = list(self.fix_dir.glob("*.txt"))
            if not txt_files:
                st.warning("⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ 1-fix")
                st.info("💡 จะลองใช้ไฟล์จากโฟลเดอร์ 0-input แทน")
                
                # ลองใช้ไฟล์จาก input แทน
                txt_files = list(self.input_dir.glob("*.txt"))
                if not txt_files:
                    st.error("❌ ไม่พบไฟล์ .txt ในโฟลเดอร์ 0-input และ 1-fix")
                    st.info("💡 กรุณาวางไฟล์ .txt ที่ต้องการทำความสะอาดไว้ในโฟลเดอร์ 0-input หรือ 1-fix")
                    return
                else:
                    st.info(f"ℹ️ พบ {len(txt_files)} ไฟล์ในโฟลเดอร์ 0-input - จะใช้ไฟล์เหล่านี้แทน")
                    source_dir = self.input_dir
            else:
                source_dir = self.fix_dir
            
            # แสดง progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_files = len(txt_files)
            processed_files = 0
            all_vocab = []  # เก็บคำศัพท์ทั้งหมดจากทุกไฟล์
            
            for file_path in txt_files:
                processed_files += 1
                file_name = file_path.name
                
                # อัปเดต progress
                progress = processed_files / total_files
                progress_bar.progress(progress)
                status_text.text(f"กำลังทำความสะอาดไฟล์: {file_name} ({processed_files}/{total_files})")
                
                # ใช้เส้นทางไฟล์ที่ถูกต้องตาม source_dir
                actual_file_path = source_dir / file_name
                with open(actual_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                original_lines = len(lines)
                cleaned_lines = []
                file_vocab = []  # คำศัพท์ในไฟล์นี้
                collect_vocab_section = False  # อยู่ในส่วนคำศัพท์หรือไม่
                
                # ใช้สถานะเพื่อติดตามว่าอยู่ในส่วนไหน
                in_translation_block = False
                
                # ปรับปรุง: วนลูปพร้อม index
                for i, line_content in enumerate(lines):
                    # สำหรับ 3 บรรทัดแรก: เก็บไว้ตามเดิมโดยไม่ strip()
                    if i < 2: # บรรทัดที่ 0, 1, 2
                        cleaned_lines.append(line_content)
                        continue

                    # สำหรับบรรทัดที่ 3 เป็นต้นไป: ใช้ตรรกะ clean แบบเดิม
                    line = line_content.strip()

                    # จัดการส่วนคำศัพท์
                    if line == "ศัพท์ใหม่ภาษาจีน | คำแปลภาษาไทย":
                        collect_vocab_section = True
                        continue  # ไม่เขียนบรรทัดหัวข้อคำศัพท์ลงไฟล์
                    
                    if line == "[จบแล้ว]":
                        # ลบบรรทัด [จบแล้ว]
                        continue
                    
                    # เก็บคำศัพท์รูปแบบ จีน | ไทย ไม่ว่ามีหัวข้อส่วนคำศัพท์หรือไม่
                    if " | " in line and re.search(r'[\u4e00-\u9fff]', line):
                        file_vocab.append(line)
                        continue  # ไม่เขียนบรรทัดคำศัพท์ลงไฟล์หลัก
                    
                    # ถ้าเจอ [A] ให้เริ่มบล็อกแปล
                    if line.startswith('[A]'):
                        in_translation_block = True
                        continue  # ข้ามบรรทัด [A]
                    
                    # ถ้าเจอ [B] ให้จบบล็อกแปลและเก็บเนื้อหา
                    elif line.startswith('[B]'):
                        in_translation_block = False
                        cleaned_line = line[3:].strip()  # ลบ [B] และเว้นวรรค
                        if cleaned_line:  # เฉพาะบรรทัดที่ไม่ว่าง
                            cleaned_lines.append(cleaned_line + '\n')
                    
                    # ถ้าอยู่ในบล็อกแปล (ระหว่าง [A] และ [B]) ให้ข้าม
                    elif in_translation_block:
                        continue  # ข้ามบรรทัดระหว่าง [A] และ [B]
                    
                    # บรรทัดอื่นๆ ที่ไม่อยู่ในบล็อกแปล ให้คงเดิม
                    else:
                        if line:
                            cleaned_lines.append(line + '\n')
                
                # บันทึกไฟล์ที่ทำความสะอาดแล้วไปยังโฟลเดอร์ clean
                output_file = self.clean_dir / file_name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.writelines(cleaned_lines)
                
                cleaned_count = len(cleaned_lines)
                # เพิ่มคำศัพท์จากไฟล์นี้เข้าไปในรายการทั้งหมด
                all_vocab.extend(file_vocab)
                vocab_count = len(file_vocab)
                status_text.text(f"✅ ทำความสะอาดไฟล์ {file_name} สำเร็จ ({original_lines} → {cleaned_count} บรรทัด, พบคำศัพท์ {vocab_count} คำ) → บันทึกที่ clean/{file_name}")
            
            # บันทึกคำศัพท์ทั้งหมดเป็น vocab.txt ในโฟลเดอร์ output
            if all_vocab:
                vocab_file = self.output_dir / "vocab.txt"
                with open(vocab_file, 'w', encoding='utf-8') as f:
                    for vocab in all_vocab:
                        f.write(vocab + '\n')

            # เสร็จสิ้น
            progress_bar.progress(1.0)
            status_text.text("🎉 กระบวนการทำความสะอาดไฟล์เสร็จสิ้น!")
            
            # แสดงผลลัพธ์สรุป
            st.success(f"""
            🎉 **ทำความสะอาดไฟล์สำเร็จ!**
            
            📁 **ไฟล์ที่ทำความสะอาดในโฟลเดอร์ clean:**
            - จำนวนไฟล์: **{total_files}** ไฟล์
            
            📂 **ไฟล์ที่ทำความสะอาด:**
            """)
            
            # แสดงรายชื่อไฟล์ที่ทำความสะอาด
            for file_path in txt_files:
                st.write(f"  `{file_path.name}` → `Clean/{file_path.name}`")
            
            if all_vocab:
                st.write(f"  📚 `vocab.txt` (คำศัพท์ {len(all_vocab)} คำ)")
            
            # ใช้ toast แทน info message
            pass
        
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการทำความสะอาดไฟล์: {str(e)}")
            st.exception(e)
