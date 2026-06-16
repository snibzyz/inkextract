import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from . import paths
from .config import app_config, regex_patterns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(paths.LOG_FILE), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurityValidator:
    """Handle security validation for file operations"""
    
    @staticmethod
    def validate_file_path(path: str, base_dir: Path) -> bool:
        """Validate that file path is within allowed directory"""
        try:
            resolved_path = Path(path).resolve()
            base_resolved = base_dir.resolve()
            return resolved_path.is_relative_to(base_resolved)
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def validate_file_size(file_path: Path) -> bool:
        """Validate file size is within limits"""
        try:
            size = file_path.stat().st_size
            return size <= app_config.max_file_size
        except OSError:
            return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized

class TextClassifier:
    """Handle text classification and analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TextClassifier")
    
    def classify_text(self, text: str, skip_ab_markers: bool = True) -> Dict[str, bool]:
        """Classify text content for different character types"""
        if skip_ab_markers and (text.startswith('[A]') or text.startswith('[B]')):
            return {'foreign': False, 'english': False, 'numbers': False}

        # บรรทัดที่มีแต่ filler มองไม่เห็น (เช่น ㅤ U+3164) = ว่าง → ไม่นับเป็นภาษาต่างประเทศ
        if regex_patterns.is_effectively_blank(text):
            return {'foreign': False, 'english': False, 'numbers': False}

        cleaned_text = regex_patterns.clean_text(text)
        
        has_english = bool(regex_patterns.english_pattern.search(cleaned_text))
        has_numbers = bool(regex_patterns.numbers_pattern.search(cleaned_text))
        
        # ใช้ฟังก์ชันตรวจจับภาษาต่างประเทศที่ปรับปรุงแล้ว
        has_foreign = regex_patterns.detect_foreign_chars(cleaned_text)

        return {
            'foreign': has_foreign,
            'english': has_english,
            'numbers': has_numbers
        }
    
    def should_flag(self, flags: Dict[str, bool], check_foreign: bool, 
                   check_english: bool, check_numbers: bool) -> bool:
        """Determine if text should be flagged based on settings"""
        return (
            (check_foreign and flags.get('foreign', False)) or
            (check_english and flags.get('english', False)) or
            (check_numbers and flags.get('numbers', False))
        )
    
    def get_category_labels(self, flags: Dict[str, bool], check_foreign: bool,
                          check_english: bool, check_numbers: bool) -> List[str]:
        """Get human-readable category labels"""
        categories = []
        if check_foreign and flags.get('foreign'):
            categories.append('ภาษาต่างประเทศ')
        if check_english and flags.get('english'):
            categories.append('ภาษาอังกฤษ')
        if check_numbers and flags.get('numbers'):
            categories.append('ตัวเลข')
        return categories

class FileAnalyzer:
    """Handle file analysis operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FileAnalyzer")
        self.classifier = TextClassifier()
        self.validator = SecurityValidator()
    
    def analyze_file_content(self, file_path: Path, check_foreign: bool, 
                           check_english: bool, check_numbers: bool,
                           skip_ab_markers: bool = True) -> List[Dict[str, Any]]:
        """Analyze single file content"""
        errors = []
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return errors

        if not self.validator.validate_file_size(file_path):
            self.logger.warning(
                f"File exceeds max_file_size ({app_config.max_file_size} bytes) — scanning anyway: {file_path}"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if len(lines) > app_config.max_lines_per_file:
                self.logger.warning(
                    f"File exceeds max_lines_per_file ({app_config.max_lines_per_file}) — scanning anyway: {file_path}"
                )
            
            for idx, raw_line in enumerate(lines):
                line_content = raw_line.rstrip('\n')
                stripped_line = line_content.strip()
                
                if not stripped_line:
                    continue
                
                flags = self.classifier.classify_text(stripped_line, skip_ab_markers)
                
                if self.classifier.should_flag(flags, check_foreign, check_english, check_numbers):
                    categories = self.classifier.get_category_labels(
                        flags, check_foreign, check_english, check_numbers
                    )
                    
                    error_data = {
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'line_number': idx + 1,
                        'line_content': line_content,
                        'categories': categories,
                        'flags': flags
                    }
                    errors.append(error_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_path}: {str(e)}")
        
        return errors
    
    def analyze_ab_mode(self, file_path: Path, check_foreign: bool, 
                       check_english: bool, check_numbers: bool) -> List[Dict[str, Any]]:
        """Analyze file in AB mode (look for [A]/[B] patterns)"""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                if line.startswith('[B]'):
                    b_content = line[3:].strip()
                    flags = self.classifier.classify_text(b_content, skip_ab_markers=False)
                    
                    if self.classifier.should_flag(flags, check_foreign, check_english, check_numbers):
                        # Find corresponding [A] line
                        prev_a_line = ""
                        for j in range(i-1, -1, -1):
                            if lines[j].strip().startswith('[A]'):
                                prev_a_line = lines[j].strip()
                                break
                        
                        categories = self.classifier.get_category_labels(
                            flags, check_foreign, check_english, check_numbers
                        )
                        
                        error_data = {
                            'file_path': str(file_path),
                            'line_number_B': i + 1,
                            'original_A': prev_a_line,
                            'original_B': line,
                            'corrected_B': line,
                            'categories': categories,
                            'flags': flags
                        }
                        errors.append(error_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing AB mode file {file_path}: {str(e)}")
        
        return errors

class ErrorExporter:
    """Handle error export operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ErrorExporter")
    
    def export_normal_mode_errors(self, errors: List[Dict[str, Any]], 
                                output_path: Path) -> bool:
        """Export normal mode errors to file"""
        if not errors:
            self.logger.warning("No errors to export")
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# รายการบรรทัดที่ต้องตรวจสอบ (โหมดทั่วไป)\n")
                f.write("# รูปแบบ: line_number| ข้อความ [ประเภท]\n")
                f.write("# หมายเหตุ: ตรวจสอบและแก้ไขที่ไฟล์ต้นฉบับโดยตรง\n\n")
                
                # Group errors by file
                grouped_errors = {}
                for error in errors:
                    file_path = error['file_path']
                    if file_path not in grouped_errors:
                        grouped_errors[file_path] = []
                    grouped_errors[file_path].append(error)
                
                for file_path_str, file_errors in grouped_errors.items():
                    file_name = Path(file_path_str).name
                    f.write(f"## {file_name}\n")
                    f.write(f"### {file_path_str}\n")
                    
                    for error in file_errors:
                        content = error['line_content'].strip()
                        categories = ', '.join(error.get('categories', []))
                        category_text = f" [{categories}]" if categories else ""
                        f.write(f"{error['line_number']}| {content}{category_text}\n")
                    f.write("\n")
            
            self.logger.info(f"Exported {len(errors)} errors to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting normal mode errors: {str(e)}")
            return False
    
    def export_ab_mode_errors(self, errors: List[Dict[str, Any]], 
                            output_path: Path) -> bool:
        """Export AB mode errors to file"""
        if not errors:
            self.logger.warning("No errors to export")
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# แก้ไขเฉพาะบรรทัด [B] เท่านั้น\n")
                f.write("# รูปแบบ: line_number| แล้วตามด้วย [A] และ [B]\n")
                
                # Group errors by file
                grouped_errors = {}
                for error in errors:
                    file_name = Path(error['file_path']).name
                    if file_name not in grouped_errors:
                        grouped_errors[file_name] = []
                    grouped_errors[file_name].append(error)
                
                for file_name, file_errors in grouped_errors.items():
                    f.write(f"## {file_name}\n")
                    
                    for error in file_errors:
                        f.write(f"{error['line_number_B']}|\n")
                        
                        # Clean and write [A] line
                        original_a = error['original_A']
                        if original_a.startswith('[A] '):
                            original_a = original_a[4:]
                        f.write(f"[A] {original_a}\n")
                        
                        # Clean and write [B] line
                        original_b = error['original_B']
                        if original_b.startswith('[B] '):
                            original_b = original_b[4:]
                        f.write(f"[B] {original_b}\n")
            
            self.logger.info(f"Exported {len(errors)} AB mode errors to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting AB mode errors: {str(e)}")
            return False
