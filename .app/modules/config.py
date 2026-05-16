# Configuration for Novel Proofreader
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
import re

from modules import paths

@dataclass
class AppConfig:
    """Application configuration settings"""
    input_dir: Path = field(default_factory=lambda: paths.INPUT_DIR)
    output_dir: Path = field(default_factory=lambda: paths.OUTPUT_DIR)
    fix_dir: Path = field(default_factory=lambda: paths.FIX_DIR)
    clean_dir: Path = field(default_factory=lambda: paths.CLEAN_DIR)
    merge_dir: Path = field(default_factory=lambda: paths.MERGE_DIR)
    separate_dir: Path = field(default_factory=lambda: paths.SEPARATE_DIR)
    md_dir: Path = field(default_factory=lambda: paths.CLEAN_DIR)  # ยุบเข้า 2-clean
    exclude_file: Path = field(default_factory=lambda: paths.EXCLUDE_FILE)

    max_file_size: int = 10 * 1024 * 1024
    max_files_per_batch: int = 1000
    max_lines_per_file: int = 50000

    default_check_foreign: bool = True
    default_check_english: bool = False
    default_check_numbers: bool = False

    progress_update_interval: int = 10
    preview_lines_limit: int = 20

    def __post_init__(self):
        paths.ensure_dirs()

    def reload_paths(self) -> None:
        """Re-resolve all path attributes from current paths.* module state.

        Call after switching active project (project_manager.set_active_project)
        so that this singleton points at the new project's folders.
        """
        self.input_dir = paths.INPUT_DIR
        self.output_dir = paths.OUTPUT_DIR
        self.fix_dir = paths.FIX_DIR
        self.clean_dir = paths.CLEAN_DIR
        self.merge_dir = paths.MERGE_DIR
        self.separate_dir = paths.SEPARATE_DIR
        self.md_dir = paths.CLEAN_DIR
        self.exclude_file = paths.EXCLUDE_FILE
        paths.ensure_dirs()

def load_exclude_patterns() -> List[str]:
    """โหลด exclude patterns จากไฟล์ exclude.txt"""
    patterns = []
    if paths.EXCLUDE_FILE.exists():
        try:
            with open(paths.EXCLUDE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception as e:
            print(f"⚠️ ไม่สามารถอ่านไฟล์ exclude.txt: {e}")
    return patterns

def get_exclude_file_mtime() -> float:
    """ดึงเวลาแก้ไขล่าสุดของไฟล์ exclude.txt"""
    if paths.EXCLUDE_FILE.exists():
        try:
            return paths.EXCLUDE_FILE.stat().st_mtime
        except Exception:
            return 0.0
    return 0.0

class RegexPatterns:
    """Compiled regex patterns - optimized for hub-scale workloads"""

    def __init__(self):
        self._exclude_file_mtime = 0.0
        self._load_patterns()

        # Main patterns - อนุญาตเฉพาะภาษาไทย เครื่องหมายวรรคตอน และตัวเลข
        # รวม CJK punctuation + fullwidth forms (、。！？，：；、) - punctuation
        # CJK letters (zh/jp/ko) caught by foreign_combined in step 1 ก่อนเสมอ
        self.allowed_chars = re.compile(r'[฀-๿\s\n\r\t.,!?;:()\[\]{}\'"ๆ\-–—/%@#*+=<>|~`^&$฿ -⁯0-9　-〿＀-｟￠-￯]')
        self.vocab_pattern = re.compile(r'[一-鿿].*\|.*[฀-๿]')
        self.numbers_pattern = re.compile(r'[0-9]')
        self.english_pattern = re.compile(r'[A-Za-z]')
        self.chinese_pattern = re.compile(r'[一-鿿]')

        self._init_foreign_patterns()

    def _load_patterns(self):
        """โหลด ignore patterns และคอมไพล์เป็น regex ก้อนเดียว"""
        base_patterns = [
            r'【.*?】',
            r'【',
            r'】',
            r'・',
            r'（.*?）',
            r'（',
            r'）',
            r'「.*?」',
            r'『.*?』',
        ]

        user_patterns = load_exclude_patterns()
        self._exclude_file_mtime = get_exclude_file_mtime()
        all_patterns = base_patterns + user_patterns

        self.ignore_patterns = []
        self.ignore_patterns_raw = all_patterns
        valid_patterns: List[str] = []
        for pattern in all_patterns:
            try:
                if not pattern.strip():
                    continue
                self.ignore_patterns.append(re.compile(pattern))
                valid_patterns.append(pattern)
            except re.error as e:
                import sys
                print(f"⚠️ Pattern ไม่ถูกต้อง '{pattern}': {e}", file=sys.stderr)

        # ✨ รวม ignore patterns ทั้งหมดเป็น regex ก้อนเดียว → sub() ครั้งเดียวต่อบรรทัด
        if valid_patterns:
            try:
                self.ignore_combined = re.compile('|'.join(f'(?:{p})' for p in valid_patterns))
            except re.error:
                self.ignore_combined = None
        else:
            self.ignore_combined = None

    def check_and_reload(self) -> bool:
        current_mtime = get_exclude_file_mtime()
        if current_mtime > self._exclude_file_mtime:
            self._load_patterns()
            return True
        return False

    def reload_patterns(self):
        self._load_patterns()

    def _init_foreign_patterns(self):
        """รวมทุก Unicode block ของอักษรต่างประเทศเป็น regex เดียว (ไม่รวมไทย)"""
        # หมายเหตุ: ไม่รวมไทย (฀-๿) และไม่รวม ASCII English
        foreign_class = (
            r'一-鿿㐀-䶿豈-﫿'   # CJK
            r'぀-ゟ゠-ヿ'                 # Hiragana / Katakana
            r'؀-ۿݐ-ݿࢠ-ࣿ'    # Arabic
            r'ﭐ-﷿ﹰ-﻿'                 # Arabic forms
            r'Ѐ-ӿԀ-ԯ'                 # Cyrillic
            r'ᄀ-ᇿ가-힯'                 # Hangul
            r'㄰-㆏ꥠ-꥿ힰ-퟿'    # Hangul ext
            r'Ͱ-Ͽ'                              # Greek
            r'ऀ-ॿঀ-৿'                 # Devanagari / Bengali
            r'਀-੿઀-૿'                 # Gurmukhi / Gujarati
            r'଀-୿஀-௿'                 # Oriya / Tamil
            r'ఀ-౿ಀ-೿'                 # Telugu / Kannada
            r'ഀ-ൿ'                              # Malayalam
            r'຀-໿'                              # Lao
            r'က-႟Ⴀ-ჿ'                 # Myanmar / Georgian
            r'ሀ-፿ក-៿᠀-᢯'    # Ethiopic / Khmer / Mongolian
            r'԰-֏֐-׿יִ-ﭏ'    # Armenian / Hebrew
        )
        self.foreign_combined = re.compile(f'[{foreign_class}]')
        # legacy field — เก็บไว้ในกรณีที่ external code อ้างอิง
        self.foreign_patterns = [self.foreign_combined]

    def clean_text(self, text: str) -> str:
        """ลบ ignore patterns ในการเรียก sub() ครั้งเดียว"""
        if self.ignore_combined is None:
            return text
        return self.ignore_combined.sub('', text)

    def detect_foreign_chars(self, text: str) -> bool:
        """ตรวจจับอักษรต่างประเทศแบบ single-pass"""
        # 1) regex รวมอักษรต่างประเทศก้อนเดียว — ครอบคลุม 99% ของกรณี
        if self.foreign_combined.search(text):
            return True
        # 2) Fallback กันอักษรประหลาดอื่นที่ไม่ใช่ allowed/English
        leftover = self.allowed_chars.sub('', text)
        leftover = self.english_pattern.sub('', leftover)
        for ch in leftover:
            if ord(ch) >= 32:
                return True
        return False

# Global instances
app_config = AppConfig()
regex_patterns = RegexPatterns()

# Legacy compatibility
IGNORE_PATTERNS = [p.pattern for p in regex_patterns.ignore_patterns]
ALLOWED_CHARS_PATTERN = regex_patterns.allowed_chars.pattern
VOCAB_PATTERN = regex_patterns.vocab_pattern.pattern
NUMBERS_PATTERN = regex_patterns.numbers_pattern.pattern
