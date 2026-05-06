import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter

from modules import paths


class FormatChecker:
    """ตรวจสอบ format บรรทัดแรกของไฟล์"""

    def __init__(self, clean_dir: Path = None):
        if clean_dir is None:
            clean_dir = paths.CLEAN_DIR
        self.clean_dir = clean_dir
    
    def read_first_line(self, file_path: Path) -> Optional[str]:
        """อ่านบรรทัดแรกของไฟล์ (ไม่ข้ามบรรทัดว่าง)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                # ถ้าบรรทัดแรกว่าง (ไม่มีเนื้อหาหรือมีแค่ whitespace) ให้ return empty string
                return first_line.strip() if first_line else ""
        except Exception as e:
            return None
    
    def detect_format_pattern(self, first_line: str) -> Optional[str]:
        """
        ตรวจสอบรูปแบบของบรรทัดแรก
        
        รูปแบบที่รองรับ:
        1. [ชื่อเรื่อง] [หมายเลข] [ชื่อตอน] - เช่น "ระบบฝึกยุทธ์ออโต้ 001 ข้ามมิติสู่ลัทธิมาร"
        2. [ชื่อเรื่อง] [ตอนที่] [หมายเลข] [ชื่อตอน] - เช่น "รวยขั้นเทพ ช้อนบิตคอย์นตั้งแต่เริ่ม ตอนที่ 002 ตัดสินใจซื้อบิตคอยน์"
        
        Returns:
            'pattern1': [ชื่อเรื่อง] [หมายเลข] [ชื่อตอน]
            'pattern2': [ชื่อเรื่อง] [ตอนที่] [หมายเลข] [ชื่อตอน]
            'unknown': ไม่ตรงกับรูปแบบใดๆ
        """
        if not first_line:
            return 'unknown'
        
        # Pattern 1: [ชื่อเรื่อง] [หมายเลข] [ชื่อตอน]
        # หมายเลขอาจเป็นตัวเลข 3-4 หลัก (001, 0001, 1, 10, 100)
        pattern1 = re.compile(r'^(.+?)\s+(\d{1,4})\s+(.+)$')
        match1 = pattern1.match(first_line)
        if match1:
            title = match1.group(1).strip()
            number = match1.group(2).strip()
            chapter_name = match1.group(3).strip()
            
            # ตรวจสอบว่าไม่ใช่ pattern2 โดยดูว่ามี "ตอนที่" หรือไม่
            if 'ตอนที่' not in first_line:
                return 'pattern1'
        
        # Pattern 2: [ชื่อเรื่อง] [ตอนที่] [หมายเลข] [ชื่อตอน]
        # ต้องมี "ตอนที่" ตามด้วยหมายเลข
        pattern2 = re.compile(r'^(.+?)\s+ตอนที่\s+(\d{1,4})\s+(.+)$')
        match2 = pattern2.match(first_line)
        if match2:
            return 'pattern2'
        
        # ถ้าไม่ตรงกับรูปแบบใดๆ
        return 'unknown'
    
    def check_all_files(self) -> Dict:
        """
        ตรวจสอบไฟล์ทั้งหมดในโฟลเดอร์ 2-clean
        
        Returns:
            dict ที่มี:
                - files: List[Dict] - รายการไฟล์พร้อมสถานะ
                - format_stats: Dict - สถิติรูปแบบ
                - standard_format: str - รูปแบบมาตรฐาน (>70%)
                - total_files: int - จำนวนไฟล์ทั้งหมด
                - valid_files: int - จำนวนไฟล์ที่ format ถูกต้อง
                - invalid_files: int - จำนวนไฟล์ที่ format ไม่ถูกต้อง
        """
        if not self.clean_dir.exists():
            return {
                'files': [],
                'format_stats': {},
                'standard_format': None,
                'total_files': 0,
                'valid_files': 0,
                'invalid_files': 0
            }
        
        # รองรับทั้ง .txt และ .md
        txt_files = sorted(list(self.clean_dir.glob("*.txt")) + list(self.clean_dir.glob("*.md")))
        files_data = []
        format_counter = Counter()
        
        for file_path in txt_files:
            first_line = self.read_first_line(file_path)
            if first_line is None:
                # ไฟล์อ่านไม่ได้
                files_data.append({
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'first_line': '',
                    'format': 'empty',
                    'is_valid': False
                })
                format_counter['empty'] += 1
                continue
            
            # ถ้าบรรทัดแรกว่าง (empty string) ให้ถือว่าผิด
            if first_line == "":
                files_data.append({
                    'filename': file_path.name,
                    'file_path': str(file_path),
                    'first_line': '',
                    'format': 'empty',
                    'is_valid': False
                })
                format_counter['empty'] += 1
                continue
            
            format_pattern = self.detect_format_pattern(first_line)
            files_data.append({
                'filename': file_path.name,
                'file_path': str(file_path),
                'first_line': first_line,
                'format': format_pattern,
                'is_valid': format_pattern != 'unknown'
            })
            format_counter[format_pattern] += 1
        
        # หารูปแบบมาตรฐาน (>70%)
        total_files = len(txt_files)
        standard_format = None
        if total_files > 0:
            for pattern, count in format_counter.most_common():
                percentage = (count / total_files) * 100
                if percentage >= 70 and pattern != 'unknown' and pattern != 'empty':
                    standard_format = pattern
                    break
        
        # นับไฟล์ที่ valid/invalid
        valid_files = sum(1 for f in files_data if f['is_valid'] and f['format'] == standard_format)
        invalid_files = total_files - valid_files
        
        return {
            'files': files_data,
            'format_stats': dict(format_counter),
            'standard_format': standard_format,
            'total_files': total_files,
            'valid_files': valid_files,
            'invalid_files': invalid_files
        }
    
    def get_format_description(self, pattern: str) -> str:
        """แปลงชื่อ pattern เป็นคำอธิบาย"""
        descriptions = {
            'pattern1': '[ชื่อเรื่อง] [หมายเลข] [ชื่อตอน]',
            'pattern2': '[ชื่อเรื่อง] [ตอนที่] [หมายเลข] [ชื่อตอน]',
            'unknown': 'ไม่ตรงกับรูปแบบมาตรฐาน',
            'empty': 'ไฟล์ว่างหรืออ่านไม่ได้'
        }
        return descriptions.get(pattern, pattern)
    
    def export_report(self, output_path: Path, check_result: Dict) -> bool:
        """ส่งออกรายงานเป็นไฟล์ข้อความ"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("รายงานการตรวจสอบรูปแบบบรรทัดแรก\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"โฟลเดอร์ที่ตรวจสอบ: {self.clean_dir}\n")
                f.write(f"จำนวนไฟล์ทั้งหมด: {check_result['total_files']}\n")
                f.write(f"ไฟล์ที่ format ถูกต้อง: {check_result['valid_files']}\n")
                f.write(f"ไฟล์ที่ format ไม่ถูกต้อง: {check_result['invalid_files']}\n\n")
                
                if check_result['standard_format']:
                    f.write(f"รูปแบบมาตรฐาน: {self.get_format_description(check_result['standard_format'])}\n\n")
                
                f.write("สถิติรูปแบบ:\n")
                for pattern, count in check_result['format_stats'].items():
                    percentage = (count / check_result['total_files'] * 100) if check_result['total_files'] > 0 else 0
                    f.write(f"  - {self.get_format_description(pattern)}: {count} ไฟล์ ({percentage:.1f}%)\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("รายละเอียดไฟล์ที่ format ไม่ถูกต้อง:\n")
                f.write("=" * 80 + "\n\n")
                
                invalid_files = [f for f in check_result['files'] 
                                if not f['is_valid'] or (check_result['standard_format'] and f['format'] != check_result['standard_format'])]
                
                if invalid_files:
                    for file_data in invalid_files:
                        f.write(f"ไฟล์: {file_data['filename']}\n")
                        f.write(f"  Format: {self.get_format_description(file_data['format'])}\n")
                        f.write(f"  บรรทัดแรก: {file_data['first_line']}\n")
                        f.write("\n")
                else:
                    f.write("ไม่พบไฟล์ที่ format ไม่ถูกต้อง\n")
            
            return True
        except Exception as e:
            return False

