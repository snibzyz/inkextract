import streamlit as st
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from . import paths
from .config import app_config, regex_patterns, IGNORE_PATTERNS, NUMBERS_PATTERN, ALLOWED_CHARS_PATTERN, VOCAB_PATTERN
from .core import FileAnalyzer, ErrorExporter, SecurityValidator
import logging
import hashlib
import re
import unicodedata
from collections import defaultdict

logger = logging.getLogger(__name__)

class NovelProofreader:
    """Main proofreader class with improved architecture"""
    
    def __init__(self):
        self.base_dir = paths.ROOT
        self.found_errors: List[Dict[str, Any]] = []
        self.normal_mode_errors: List[Dict[str, Any]] = []
        self.normal_mode_stats: Dict[str, int] = {
            'files': 0,
            'errors': 0,
            'lines': 0,
            'foreign': 0,
            'english': 0,
            'numbers': 0
        }

        # Multi-folder mode data
        self.multi_folder_results: Dict[str, Dict[str, Any]] = {}
        self.multi_folder_settings: Dict[str, bool] = {
            'check_foreign_languages': app_config.default_check_foreign,
            'check_english': app_config.default_check_english,
            'check_numbers': app_config.default_check_numbers
        }

        # Override สำหรับ normal_mode_source (UI ตั้ง path เองได้)
        # ปล่อย None = ใช้ paths.CLEAN_DIR ของ project ปัจจุบัน
        self._normal_mode_source_override: Optional[Path] = None
        
        # Settings
        self.normal_mode_settings: Dict[str, bool] = {
            'check_foreign_languages': app_config.default_check_foreign,
            'check_english': app_config.default_check_english,
            'check_numbers': app_config.default_check_numbers
        }
        self.ab_settings: Dict[str, bool] = {
            'check_foreign_languages': app_config.default_check_foreign,
            'check_english': app_config.default_check_english,
            'check_numbers': app_config.default_check_numbers
        }
        self.ab_check_translation_vocab = False
        self.ab_vocab_file: Optional[Path] = None
        self.ab_vocab_entries: List[Dict[str, str]] = []
        self.ab_vocab_min_cn_length = 2
        # Duplicate content (between files) detected in AB mode
        self.ab_duplicate_content_groups: List[List[str]] = []
        
        # Core components
        self.file_analyzer = FileAnalyzer()
        self.error_exporter = ErrorExporter()
        self.validator = SecurityValidator()

    # ── Dynamic path properties — resolve ต่อ project ปัจจุบันทุกครั้ง ──
    # อย่า snapshot เป็น attribute ตรงๆ เพราะตอนสลับ project ค่าจะค้าง
    # ทำให้ output ไปลง workspace เดิม (bug ที่ user เจอ)
    @property
    def input_dir(self) -> Path:
        return paths.INPUT_DIR

    @property
    def output_dir(self) -> Path:
        return paths.OUTPUT_DIR

    @property
    def normal_mode_source(self) -> Path:
        return self._normal_mode_source_override or paths.CLEAN_DIR

    @normal_mode_source.setter
    def normal_mode_source(self, value) -> None:
        self._normal_mode_source_override = Path(value) if value else None

    def classify_text(self, text: str, skip_ab_markers: bool = True) -> Dict[str, bool]:
        """จำแนกประเภทของอักขระที่ต้องการตรวจในข้อความ"""
        if skip_ab_markers and (text.startswith('[A]') or text.startswith('[B]')):
            return {'foreign': False, 'english': False, 'numbers': False}

        # ใช้ regex_patterns จาก config
        from .config import regex_patterns
        
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

    @staticmethod
    def _should_flag(flags: Dict[str, bool], check_foreign_languages: bool, check_english: bool, check_numbers: bool) -> bool:
        return (
            (check_foreign_languages and flags.get('foreign', False)) or
            (check_english and flags.get('english', False)) or
            (check_numbers and flags.get('numbers', False))
        )

    @staticmethod
    def _get_category_labels(flags: Dict[str, bool], check_foreign_languages: bool, check_english: bool, check_numbers: bool) -> List[str]:
        categories: List[str] = []
        if check_foreign_languages and flags.get('foreign'):
            categories.append('ภาษาต่างประเทศ')
        if check_english and flags.get('english'):
            categories.append('ภาษาอังกฤษ')
        if check_numbers and flags.get('numbers'):
            categories.append('ตัวเลข')
        return categories

    def detect_characters(
        self,
        text: str,
        check_foreign_languages: bool,
        check_numbers: bool,
        skip_ab_markers: bool = True,
        check_english: bool = False
    ) -> Dict[str, Any]:
        """ตรวจสอบและระบุประเภทอักขระที่ต้องการ"""
        flags = self.classify_text(text, skip_ab_markers=skip_ab_markers)
        should_flag = self._should_flag(flags, check_foreign_languages, check_english, check_numbers)
        categories = self._get_category_labels(flags, check_foreign_languages, check_english, check_numbers)
        return {
            'should_flag': should_flag,
            'categories': categories,
            'flags': flags
        }

    @staticmethod
    def _strip_ab_prefix(text: str, marker: str) -> str:
        prefix = f'[{marker}]'
        if isinstance(text, str) and text.startswith(prefix):
            return text[len(prefix):].lstrip()
        return text if isinstance(text, str) else ''

    @staticmethod
    def _normalize_import_filename(file_name: str) -> str:
        if not isinstance(file_name, str):
            return ''
        normalized = unicodedata.normalize('NFKC', file_name).strip()
        return re.sub(r'\s+', ' ', normalized)

    @staticmethod
    def _normalize_import_text(text: str) -> str:
        if not isinstance(text, str):
            return ''
        normalized = unicodedata.normalize('NFKC', text).strip()
        return re.sub(r'\s+', '', normalized)

    @staticmethod
    def _parse_import_file_header(line: str) -> str:
        if not isinstance(line, str):
            return ''

        match = re.match(r'^##\s+(.+?\.txt)\s*$', line)
        if not match:
            return ''

        return match.group(1).strip()

    @staticmethod
    def _parse_import_line_number(line: str) -> Optional[int]:
        if not isinstance(line, str):
            return None

        match = re.match(r'^(\d+)\s*\|\s*$', line)
        if not match:
            return None

        return int(match.group(1))

    def _find_import_target(
        self,
        current_file: str,
        line_number: int,
        imported_a: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        normalized_file = self._normalize_import_filename(current_file)
        candidates = [
            error for error in self.found_errors
            if self._normalize_import_filename(Path(error['file_path']).name) == normalized_file
            and error.get('line_number_B') == line_number
        ]

        if not candidates:
            return self._bootstrap_import_target(current_file, line_number, imported_a)

        if len(candidates) == 1:
            candidate = candidates[0]
            original_a = self._strip_ab_prefix(candidate.get('original_A', ''), 'A')
            if imported_a and original_a == imported_a:
                return candidate, 'exact'
            if imported_a and self._normalize_import_text(original_a) == self._normalize_import_text(imported_a):
                return candidate, 'normalized'
            return candidate, 'line_only'

        if imported_a:
            exact_matches = [
                error for error in candidates
                if self._strip_ab_prefix(error.get('original_A', ''), 'A') == imported_a
            ]
            if len(exact_matches) == 1:
                return exact_matches[0], 'exact'

            normalized_imported_a = self._normalize_import_text(imported_a)
            normalized_matches = [
                error for error in candidates
                if self._normalize_import_text(self._strip_ab_prefix(error.get('original_A', ''), 'A')) == normalized_imported_a
            ]
            if len(normalized_matches) == 1:
                return normalized_matches[0], 'normalized'

        # ===== Fuzzy fallback (2026-05-06) =====
        # ลำดับก่อนหน้านี้ match แบบ strict: ต้องตรง file+line ด้วย exact/normalized
        # ถ้ายังจับคู่ไม่ได้ (line number เพี้ยน, ชื่อไฟล์ผิด, [A] ขาดบางคำ) →
        # ลอง bigram similarity ทั่วทุก error
        fuzzy_target = self._fuzzy_find_import_target(current_file, line_number, imported_a)
        if fuzzy_target is not None:
            return fuzzy_target, 'fuzzy'

        return self._bootstrap_import_target(current_file, line_number, imported_a)

    def _fuzzy_find_import_target(
        self,
        current_file: str,
        line_number: int,
        imported_a: str,
    ) -> Optional[Dict[str, Any]]:
        """Fuzzy match — bigram similarity ≥ 0.85 across all errors.

        ใช้เมื่อ exact/normalized match ไม่ได้ — เช่น user แก้บรรทัดเลขใหม่,
        ชื่อไฟล์ผิด, หรือ AI ตัด [A] ทิ้งบางส่วน
        """
        if not imported_a or not self.found_errors:
            return None
        try:
            from modules.fuzzy_matcher import (
                build_exact_index, find_best_error_by_a,
                normalize_import_text, strip_ab_prefix,
            )
        except Exception:
            return None

        # แปลง self.found_errors → format ที่ fuzzy_matcher ใช้
        candidates = []
        for err in self.found_errors:
            candidates.append({
                'original_a': err.get('original_A', ''),
                'file_name': Path(err.get('file_path', '')).name,
                'file_path': err.get('file_path', ''),
                'line_number': err.get('line_number_B', 0),
                '_orig_ref': err,  # reference back to original dict
            })

        idx = build_exact_index(candidates)
        needle = normalize_import_text(strip_ab_prefix(imported_a, 'A'))

        # ใช้ threshold จาก grab_and_import_file ถ้าตั้งไว้, default 0.95 (แม่น)
        min_ratio = getattr(self, '_import_fuzzy_min_ratio', 0.95)

        result = find_best_error_by_a(
            needle_normalized_a=needle,
            exact_index=idx,
            all_errors=candidates,
            hint_file_name=current_file,
            hint_line_number=line_number,
            min_ratio=min_ratio,
        )
        if result is None:
            return None
        return result['error']['_orig_ref']

    def _find_input_file_by_name(self, file_name: str) -> Optional[Path]:
        normalized_target = self._normalize_import_filename(file_name)
        if not normalized_target or not self.input_dir.exists():
            return None

        for file_path in self.input_dir.glob('*.txt'):
            if self._normalize_import_filename(file_path.name) == normalized_target:
                return file_path

        return None

    def _find_source_line_index(
        self,
        lines: List[str],
        expected_line_number: int,
        imported_a: str
    ) -> Optional[int]:
        candidate_index = expected_line_number - 1
        if 0 <= candidate_index < len(lines) and lines[candidate_index].strip().startswith('[B]'):
            return candidate_index

        normalized_imported_a = self._normalize_import_text(imported_a)
        matched_indexes: List[int] = []

        if normalized_imported_a:
            previous_a_line = ''
            for index, raw_line in enumerate(lines):
                stripped_line = raw_line.strip()
                if stripped_line.startswith('[A]'):
                    previous_a_line = self._strip_ab_prefix(stripped_line, 'A')
                    continue

                if not stripped_line.startswith('[B]'):
                    continue

                if self._normalize_import_text(previous_a_line) == normalized_imported_a:
                    matched_indexes.append(index)

        if matched_indexes:
            return min(matched_indexes, key=lambda index: abs(index - candidate_index))

        if 0 <= candidate_index < len(lines):
            for offset in range(1, 4):
                for nearby_index in (candidate_index - offset, candidate_index + offset):
                    if 0 <= nearby_index < len(lines) and lines[nearby_index].strip().startswith('[B]'):
                        return nearby_index

        return None

    def _build_import_error_entry(
        self,
        file_path: Path,
        line_number_b: int,
        original_a: str,
        original_b: str
    ) -> Dict[str, Any]:
        detection = self.detect_characters(
            self._strip_ab_prefix(original_b, 'B'),
            self.ab_settings.get('check_foreign_languages', app_config.default_check_foreign),
            self.ab_settings.get('check_numbers', app_config.default_check_numbers),
            skip_ab_markers=False,
            check_english=self.ab_settings.get('check_english', app_config.default_check_english)
        )
        vocab_matches = self._find_missing_translation_vocab(
            self._strip_ab_prefix(original_a, 'A'),
            self._strip_ab_prefix(original_b, 'B')
        )

        error_data = self._build_ab_error(
            file_path=file_path,
            line_number_b=line_number_b,
            original_a=original_a,
            original_b=original_b,
            detection=detection,
            vocab_matches=vocab_matches
        )
        if error_data is not None:
            return error_data

        return {
            'file_path': str(file_path),
            'line_number_B': line_number_b,
            'original_A': original_a,
            'original_B': original_b,
            'corrected_B': original_b,
            'categories': [],
            'flags': detection.get('flags', {}),
            'has_char_issue': False,
            'has_vocab_issue': False,
            'matched_vocab_pairs': vocab_matches.get('matched', []),
            'missing_vocab_pairs': vocab_matches.get('missing', []),
            'error_bucket': 'import_only'
        }

    def _bootstrap_import_target(
        self,
        current_file: str,
        line_number: int,
        imported_a: str
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        source_file = self._find_input_file_by_name(current_file)
        if source_file is None:
            return None, 'source_file_missing'

        try:
            with open(source_file, 'r', encoding='utf-8') as source_handle:
                lines = source_handle.readlines()
        except Exception:
            return None, 'source_file_error'

        source_line_index = self._find_source_line_index(lines, line_number, imported_a)
        if source_line_index is None:
            return None, 'source_line_missing'

        resolved_line_number = source_line_index + 1
        normalized_file = self._normalize_import_filename(source_file.name)
        for existing_error in self.found_errors:
            if (
                self._normalize_import_filename(Path(existing_error['file_path']).name) == normalized_file
                and existing_error.get('line_number_B') == resolved_line_number
            ):
                return existing_error, 'line_only'

        original_b = lines[source_line_index].strip()
        if not original_b.startswith('[B]'):
            return None, 'source_line_missing'

        original_a = ''
        for search_index in range(source_line_index - 1, -1, -1):
            candidate = lines[search_index].strip()
            if candidate.startswith('[A]'):
                original_a = candidate
                break

        error_entry = self._build_import_error_entry(
            file_path=source_file,
            line_number_b=resolved_line_number,
            original_a=original_a,
            original_b=original_b
        )
        self.found_errors.append(error_entry)

        if resolved_line_number == line_number:
            return error_entry, 'bootstrapped_line'

        return error_entry, 'bootstrapped_shifted'

    @staticmethod
    def _normalize_vocab_text(text: str) -> str:
        if not text:
            return ''
        return re.sub(r'\s+', '', text.strip())

    @staticmethod
    def _count_chinese_characters(text: str) -> int:
        if not text:
            return 0
        return len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]', text))

    def get_available_vocab_files(self) -> List[Path]:
        vocab_dir = paths.VOCAB_DIR
        if not vocab_dir.exists():
            return []
        return sorted(vocab_dir.glob('*.txt'), key=lambda path: path.name.lower())

    def load_vocab_entries(self, vocab_file: Optional[Path]) -> List[Dict[str, str]]:
        if vocab_file is None or not vocab_file.exists():
            return []

        vocab_map: Dict[Tuple[str, str], Dict[str, str]] = {}

        try:
            with open(vocab_file, 'r', encoding='utf-8') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = [part.strip() for part in line.split('\t') if part.strip()]
                    if len(parts) < 2:
                        continue

                    cn_word = parts[0]
                    th_word = parts[1]
                    cn_normalized = self._normalize_vocab_text(cn_word)
                    th_normalized = self._normalize_vocab_text(th_word)

                    if self._count_chinese_characters(cn_normalized) < self.ab_vocab_min_cn_length:
                        continue

                    key = (cn_word, th_word)

                    if key not in vocab_map:
                        vocab_map[key] = {
                            'cn': cn_word,
                            'th': th_word,
                            'cn_normalized': cn_normalized,
                            'th_normalized': th_normalized
                        }
        except Exception as e:
            st.error(f"❌ ไม่สามารถอ่านไฟล์คำศัพท์ `{vocab_file.name}` ได้: {str(e)}")
            return []

        return sorted(
            vocab_map.values(),
            key=lambda item: (
                len(item['cn_normalized']),
                len(item['th_normalized']),
                item['cn_normalized'],
                item['th_normalized']
            ),
            reverse=True
        )

    def _find_missing_translation_vocab(self, source_text: str, translated_text: str) -> Dict[str, List[Dict[str, str]]]:
        if not self.ab_check_translation_vocab or not self.ab_vocab_entries:
            return {'matched': [], 'missing': []}

        normalized_source = self._normalize_vocab_text(source_text)
        normalized_translated = self._normalize_vocab_text(translated_text)

        matched_entries: List[Dict[str, str]] = []
        missing_entries: List[Dict[str, str]] = []
        seen_pairs = set()
        consumed_source_ranges: List[Tuple[int, int]] = []

        for entry in self.ab_vocab_entries:
            cn_normalized = entry.get('cn_normalized', '')
            th_normalized = entry.get('th_normalized', '')
            pair_key = (entry['cn'], entry['th'])

            if not cn_normalized or pair_key in seen_pairs:
                continue

            start_index = 0
            found_unconsumed_match = False

            while True:
                match_index = normalized_source.find(cn_normalized, start_index)
                if match_index == -1:
                    break

                match_end = match_index + len(cn_normalized)
                overlaps_existing_match = any(
                    match_index < consumed_end and match_end > consumed_start
                    for consumed_start, consumed_end in consumed_source_ranges
                )

                if not overlaps_existing_match:
                    consumed_source_ranges.append((match_index, match_end))
                    found_unconsumed_match = True
                    break

                start_index = match_index + 1

            if found_unconsumed_match:
                seen_pairs.add(pair_key)
                matched_entry = {'cn': entry['cn'], 'th': entry['th']}
                matched_entries.append(matched_entry)

                if not th_normalized or th_normalized not in normalized_translated:
                    missing_entries.append(matched_entry)

        return {
            'matched': matched_entries,
            'missing': missing_entries
        }

    def _build_ab_error(
        self,
        file_path: Path,
        line_number_b: int,
        original_a: str,
        original_b: str,
        detection: Dict[str, Any],
        vocab_matches: Dict[str, List[Dict[str, str]]]
    ) -> Optional[Dict[str, Any]]:
        has_char_issue = detection.get('should_flag', False)
        missing_vocab = vocab_matches.get('missing', [])
        has_vocab_issue = bool(missing_vocab)

        if not has_char_issue and not has_vocab_issue:
            return None

        categories = list(detection.get('categories', []))
        if has_vocab_issue:
            categories.append('ศัพท์ไม่ตรง วิเคราะห์เพิ่ม')

        if has_char_issue and has_vocab_issue:
            error_bucket = 'foreign_and_vocab'
        elif has_char_issue:
            error_bucket = 'foreign_only'
        else:
            error_bucket = 'vocab_only'

        return {
            'file_path': str(file_path),
            'line_number_B': line_number_b,
            'original_A': original_a,
            'original_B': original_b,
            'corrected_B': original_b,
            'categories': categories,
            'flags': detection.get('flags', {}),
            'has_char_issue': has_char_issue,
            'has_vocab_issue': has_vocab_issue,
            'matched_vocab_pairs': vocab_matches.get('matched', []),
            'missing_vocab_pairs': missing_vocab,
            'error_bucket': error_bucket
        }

    def _analyze_ab_file(
        self,
        file_path: Path,
        check_foreign_languages: bool,
        check_numbers: bool,
        check_english: bool,
        lines: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """วิเคราะห์ AB file แบบ single-pass:
        - ไม่อ่านไฟล์ซ้ำ ถ้า caller ส่ง `lines` มา
        - ติดตาม [A] บรรทัดล่าสุดแบบ forward (ไม่ย้อนกลับ)
        """
        errors: List[Dict[str, Any]] = []

        try:
            if lines is None:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

            last_a_line = ''  # เก็บ [A] ล่าสุดที่เจอ — ไม่ต้องย้อนหลัง

            for i, raw_line in enumerate(lines):
                stripped_line = raw_line.strip()
                if not stripped_line:
                    continue

                if stripped_line.startswith('[A]'):
                    last_a_line = stripped_line
                    continue

                if not stripped_line.startswith('[B]'):
                    continue

                b_content = self._strip_ab_prefix(stripped_line, 'B')
                a_content = self._strip_ab_prefix(last_a_line, 'A')

                detection = self.detect_characters(
                    b_content,
                    check_foreign_languages,
                    check_numbers,
                    skip_ab_markers=False,
                    check_english=check_english
                )
                vocab_matches = self._find_missing_translation_vocab(a_content, b_content)
                error_data = self._build_ab_error(
                    file_path=file_path,
                    line_number_b=i + 1,
                    original_a=last_a_line,
                    original_b=stripped_line,
                    detection=detection,
                    vocab_matches=vocab_matches
                )

                if error_data:
                    errors.append(error_data)

        except Exception as e:
            logger.error(f"Error analyzing AB mode file {file_path}: {str(e)}")

        return errors
    
    @staticmethod
    def _normalize_lines_for_signature(lines: List[str]) -> str:
        """Normalize lines for duplicate detection (whitespace-insensitive)."""
        cleaned: List[str] = []
        for line in lines:
            line = (line or "").strip()
            if not line:
                continue
            # collapse whitespace inside a line
            line = re.sub(r'\s+', ' ', line)
            cleaned.append(line)
        return '\n'.join(cleaned)

    def _compute_ab_duplicate_signature(self, file_path: Path) -> str:
        """ใช้สำหรับ external callers — ไฟล์จะถูกอ่านครั้งเดียว"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_lines = f.read().splitlines()
            return self._signature_from_lines(raw_lines)
        except Exception as e:
            logger.error(f"Error computing duplicate signature for {file_path}: {str(e)}")
            return ''

    def _signature_from_lines(self, raw_lines: List[str]) -> str:
        """สร้าง signature จาก lines ที่อ่านมาแล้ว (ไม่อ่านไฟล์ซ้ำ)"""
        b_contents: List[str] = []
        for raw_line in raw_lines:
            stripped_line = raw_line.strip()
            if stripped_line.startswith('[B]'):
                b_contents.append(self._strip_ab_prefix(stripped_line, 'B'))

        content_lines = b_contents if b_contents else [ln.strip() for ln in raw_lines if ln.strip()]
        normalized_text = self._normalize_lines_for_signature(content_lines)
        if not normalized_text:
            return ''
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    def scan_missing_translations(
        self,
        raw_dir: Path,
        *,
        min_ratio: float = 0.7,
        recursive: bool = True,
    ) -> int:
        """ตรวจหาบรรทัดที่ AI ข้ามแปล โดยเทียบกับไฟล์ raw ต้นฉบับ.

        วน 0-input/*.txt → resolve raw files (ตามช่วงเลขตอนในชื่อไฟล์) →
        smart matching หาบรรทัด raw ที่ไม่มีใน [A] blocks → append เข้า found_errors
        ด้วย bucket 'missing_translation'

        Args:
            raw_dir: โฟลเดอร์ raw ต้นฉบับจีน (อาจมี sub folder)
            min_ratio: threshold สำหรับ fuzzy match (ต่ำกว่านี้ = missing)
            recursive: True = scan ลึกใน sub folders

        Returns:
            จำนวน missing line ที่เจอทั้งหมด
        """
        from modules.raw_file_resolver import resolve_raw_files, load_raw_lines
        from modules.missing_line_detector import find_missing_lines

        if not raw_dir or not raw_dir.exists():
            st.error(f"❌ ไม่พบโฟลเดอร์ raw: `{raw_dir}`")
            return 0
        if not self.input_dir.exists():
            st.error("❌ ไม่พบโฟลเดอร์ 0-input")
            return 0

        txt_files = list(self.input_dir.glob("*.txt"))
        if not txt_files:
            st.warning("⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ 0-input")
            return 0

        progress_bar = st.progress(0)
        status_text = st.empty()
        total_files = len(txt_files)
        unresolved_files: List[str] = []
        total_missing = 0

        for idx, trans_path in enumerate(txt_files, start=1):
            status_text.text(f"กำลังเทียบ raw: {trans_path.name} ({idx}/{total_files})")
            progress_bar.progress(idx / total_files)

            raw_files = resolve_raw_files(trans_path.name, raw_dir, recursive=recursive)
            if not raw_files:
                unresolved_files.append(trans_path.name)
                continue

            raw_entries = load_raw_lines(raw_files)
            if not raw_entries:
                continue

            try:
                with open(trans_path, 'r', encoding='utf-8') as f:
                    trans_lines = f.readlines()
            except Exception as e:
                logger.error(f"Read translation failed {trans_path}: {e}")
                continue

            missing = find_missing_lines(raw_entries, trans_lines, min_ratio=min_ratio)
            for m in missing:
                self.found_errors.append({
                    'file_path': str(trans_path),
                    'line_number_B': 0,  # 0 = sentinel (ยังไม่มีในไฟล์)
                    'original_A': f"[A] {m.text}",
                    'original_B': '[B] ',
                    'corrected_B': '[B] ',
                    'categories': ['บรรทัดที่ AI ข้ามแปล'],
                    'flags': {},
                    'has_char_issue': False,
                    'has_vocab_issue': False,
                    'matched_vocab_pairs': [],
                    'missing_vocab_pairs': [],
                    'error_bucket': 'missing_translation',
                    'missing_chapter': m.chapter_number,
                    'missing_raw_line': m.raw_line_index + 1,  # 1-based
                    'missing_chapter_path': m.chapter_path,
                    'missing_best_ratio': m.best_ratio,
                })
            total_missing += len(missing)

        progress_bar.progress(1.0)
        status_text.text("🎉 เทียบ raw เสร็จสิ้น!")

        if unresolved_files:
            st.warning(
                f"⚠️ ไม่เจอ raw สำหรับ {len(unresolved_files)} ไฟล์: "
                f"{', '.join(unresolved_files[:5])}"
                + (f" และอีก {len(unresolved_files) - 5}" if len(unresolved_files) > 5 else "")
            )

        return total_missing

    def analyze_files(
        self,
        check_foreign_languages: bool,
        check_numbers: bool,
        check_english: bool,
        check_translation_vocab: bool = False,
        vocab_file: Optional[Path] = None,
        min_vocab_cn_length: int = 2,
        check_duplicate_content: bool = True
    ):
        """Analyze files in AB mode with improved performance"""
        # 🔄 Auto-reload exclude patterns ถ้าไฟล์เปลี่ยน
        if regex_patterns.check_and_reload():
            st.info(f"🔄 ตรวจพบการเปลี่ยนแปลง exclude.txt โหลด patterns ใหม่แล้ว ({len(regex_patterns.ignore_patterns)} patterns)")
        
        self.found_errors = []
        self.ab_settings = {
            'check_foreign_languages': check_foreign_languages,
            'check_numbers': check_numbers,
            'check_english': check_english
        }
        self.ab_vocab_min_cn_length = max(1, int(min_vocab_cn_length))
        self.ab_check_translation_vocab = check_translation_vocab
        self.ab_vocab_file = vocab_file if check_translation_vocab else None
        self.ab_vocab_entries = self.load_vocab_entries(vocab_file) if check_translation_vocab else []
        self.ab_duplicate_content_groups = []
        duplicate_hash_to_files: Dict[str, List[Path]] = defaultdict(list)

        if check_translation_vocab and vocab_file and not self.ab_vocab_entries:
            st.warning(f"⚠️ ไม่พบรายการคำศัพท์ที่ใช้งานได้ในไฟล์ `{vocab_file.name}`")
        
        if not self.input_dir.exists():
            st.error("❌ ไม่พบโฟลเดอร์ 0-input")
            st.info("💡 กรุณาสร้างโฟลเดอร์ 0-input และวางไฟล์ .txt ที่ต้องการตรวจสอบ")
            return
        
        txt_files = list(self.input_dir.glob("*.txt"))
        if not txt_files:
            st.warning("⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ 0-input")
            st.info("💡 กรุณาวางไฟล์ .txt ที่ต้องการตรวจสอบในโฟลเดอร์ 0-input")
            return
        
        # Limit files for performance
        if len(txt_files) > app_config.max_files_per_batch:
            st.warning(f"⚠️ พบไฟล์ {len(txt_files)} ไฟล์ จำกัดการประมวลผลที่ {app_config.max_files_per_batch} ไฟล์ (เพื่อประสิทธิภาพ)")
            st.info(f"💡 กำลังประมวลผล {app_config.max_files_per_batch} ไฟล์แรก หากต้องการประมวลผลทั้งหมด สามารถแบ่งไฟล์ออกเป็นหลาย batch ได้")
            txt_files = txt_files[:app_config.max_files_per_batch]
        else:
            st.success(f"✅ พบไฟล์ทั้งหมด {len(txt_files)} ไฟล์ กำลังประมวลผลทั้งหมด...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(txt_files)
        processed_files = 0
        
        logger.info(f"Starting AB mode analysis of {total_files} files")

        # ⚡ อ่านไฟล์ครั้งเดียวแบบขนาน (I/O bound) แล้วประมวลผลแบบ vectorized
        from concurrent.futures import ThreadPoolExecutor

        def _read_file(file_path: Path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return file_path, f.readlines()
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                return file_path, None

        # ใช้ thread pool ขนาดพอเหมาะ — Windows มักได้ผลดีที่ 8-16
        max_workers = min(16, max(4, total_files))
        update_every = max(1, total_files // 50)  # อัปเดต progress ~50 ครั้ง พอ

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for file_path, lines in pool.map(_read_file, txt_files):
                processed_files += 1
                if lines is None:
                    continue

                # คำนวณ signature สำหรับ duplicate detection จาก lines เดิม (ไม่อ่านซ้ำ)
                if check_duplicate_content:
                    signature = self._signature_from_lines(lines)
                    if signature:
                        duplicate_hash_to_files[signature].append(file_path)

                file_errors = self._analyze_ab_file(
                    file_path,
                    check_foreign_languages,
                    check_numbers,
                    check_english,
                    lines=lines,
                )
                self.found_errors.extend(file_errors)

                # Throttle Streamlit progress updates — UI rerun is expensive
                if processed_files == total_files or processed_files % update_every == 0:
                    progress_bar.progress(processed_files / total_files)
                    status_text.text(f"กำลังวิเคราะห์ไฟล์: {file_path.name} ({processed_files}/{total_files})")

                if processed_files % app_config.progress_update_interval == 0:
                    logger.info(f"Processed {processed_files}/{total_files} files")
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("🎉 กระบวนการวิเคราะห์เสร็จสิ้น!")
        
        logger.info(f"AB mode analysis completed. Found {len(self.found_errors)} errors")
        vocab_issue_count = sum(1 for error in self.found_errors if error.get('has_vocab_issue'))
        char_issue_count = sum(1 for error in self.found_errors if error.get('has_char_issue'))

        # Build duplicate groups after processing all files
        if check_duplicate_content and duplicate_hash_to_files:
            groups = [files for files in duplicate_hash_to_files.values() if len(files) > 1]
            # deterministic ordering (by size desc, then lowest filename)
            groups.sort(key=lambda g: (-len(g), sorted([p.name for p in g])[0].lower()))
            self.ab_duplicate_content_groups = [[str(p) for p in group] for group in groups]
        
        # Show results
        if self.found_errors:
            vocab_summary = ""
            if check_translation_vocab:
                vocab_name = self.ab_vocab_file.name if self.ab_vocab_file else '-'
                vocab_summary = f"\n            - จำนวนบรรทัดที่พบศัพท์ไม่ตรง: **{vocab_issue_count}** รายการ\n            - ไฟล์ vocab ที่ใช้เทียบ: **{vocab_name}**"

            st.success(f"""
            🔍 **การวิเคราะห์เสร็จสิ้น!**
            
            📊 **ผลลัพธ์:**
            - จำนวนไฟล์ที่วิเคราะห์: **{total_files}** ไฟล์
            - จำนวนข้อผิดพลาดที่พบ: **{len(self.found_errors)}** รายการ
            - จำนวนบรรทัดที่พบภาษาต่างประเทศ/อังกฤษ/เลข: **{char_issue_count}** รายการ{vocab_summary}
            
            💡 **ขั้นตอนต่อไป:** กดปุ่ม "Export for AI" เพื่อส่งออกข้อผิดพลาดไปแก้ไข
            """)
        else:
            st.success(f"""
            ✅ **การวิเคราะห์เสร็จสิ้น!**
            
            📊 **ผลลัพธ์:**
            - จำนวนไฟล์ที่วิเคราะห์: **{total_files}** ไฟล์
            - จำนวนข้อผิดพลาดที่พบ: **0** รายการ
            
            🎉 **ยินดีด้วย!** ไม่พบข้อผิดพลาดตามเงื่อนไขที่เลือก
            """)

        # Show duplicate warnings (separately from char/vocab errors)
        if check_duplicate_content and self.ab_duplicate_content_groups:
            total_groups = len(self.ab_duplicate_content_groups)
            st.warning(f"⚠️ พบไฟล์เนื้อหาซ้ำ (อิงจากบรรทัด `[B]`) จำนวน {total_groups} กลุ่ม")

            max_groups_to_show = 20
            for group in self.ab_duplicate_content_groups[:max_groups_to_show]:
                file_names = [Path(p).name for p in group]
                st.info(f"ซ้ำกัน: {', '.join(file_names)}")

            if total_groups > max_groups_to_show:
                st.caption(f"... และอีก {total_groups - max_groups_to_show} กลุ่ม")

    def analyze_normal_mode(self, input_directory: Path, check_foreign_languages: bool, 
                          check_numbers: bool, check_english: bool):
        """Analyze files in normal mode with improved performance"""
        # 🔄 Auto-reload exclude patterns ถ้าไฟล์เปลี่ยน
        if regex_patterns.check_and_reload():
            st.info(f"🔄 ตรวจพบการเปลี่ยนแปลง exclude.txt โหลด patterns ใหม่แล้ว ({len(regex_patterns.ignore_patterns)} patterns)")
        
        self.normal_mode_errors = []
        self.normal_mode_stats = {
            'files': 0,
            'errors': 0,
            'lines': 0,
            'foreign': 0,
            'english': 0,
            'numbers': 0
        }
        self.normal_mode_settings = {
            'check_foreign_languages': check_foreign_languages,
            'check_english': check_english,
            'check_numbers': check_numbers
        }
        
        if not input_directory:
            st.error("❌ กรุณาเลือกโฟลเดอร์ต้นทางสำหรับโหมดทั่วไป")
            return
        
        if not input_directory.exists():
            st.error(f"❌ ไม่พบโฟลเดอร์ `{input_directory}`")
            return
        
        txt_files = list(input_directory.glob("*.txt"))
        if not txt_files:
            st.warning(f"⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ `{input_directory}`")
            st.info("💡 กรุณาตรวจสอบว่าโฟลเดอร์มีไฟล์ .txt พร้อมตรวจสอบ")
            return
        
        # Limit files for performance
        if len(txt_files) > app_config.max_files_per_batch:
            st.warning(f"⚠️ พบไฟล์ {len(txt_files)} ไฟล์ จำกัดการประมวลผลที่ {app_config.max_files_per_batch} ไฟล์ (เพื่อประสิทธิภาพ)")
            st.info(f"💡 กำลังประมวลผล {app_config.max_files_per_batch} ไฟล์แรก หากต้องการประมวลผลทั้งหมด สามารถแบ่งไฟล์ออกเป็นหลาย batch ได้")
            txt_files = txt_files[:app_config.max_files_per_batch]
        else:
            st.success(f"✅ พบไฟล์ทั้งหมด {len(txt_files)} ไฟล์ กำลังประมวลผลทั้งหมด...")
        
        self.normal_mode_source = input_directory
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(txt_files)
        processed_files = 0
        total_lines_scanned = 0
        total_foreign = 0
        total_english = 0
        total_numbers = 0
        
        logger.info(f"Starting normal mode analysis of {total_files} files")

        # ⚡ ประมวลผลขนานเหมือน AB mode
        from concurrent.futures import ThreadPoolExecutor

        def _scan(file_path: Path):
            return self.file_analyzer.analyze_file_content(
                file_path, check_foreign_languages, check_english, check_numbers, skip_ab_markers=False
            )

        max_workers = min(16, max(4, total_files))
        update_every = max(1, total_files // 50)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for file_errors in pool.map(_scan, txt_files):
                processed_files += 1
                total_lines_scanned += len(file_errors)

                for error in file_errors:
                    flags = error.get('flags', {})
                    total_foreign += int(flags.get('foreign', False) and check_foreign_languages)
                    total_english += int(flags.get('english', False) and check_english)
                    total_numbers += int(flags.get('numbers', False) and check_numbers)
                    # เตรียม slot สำหรับ correction — ถูกเติมตอน import_normal_mode_corrections()
                    error.setdefault('corrected_content', error.get('line_content', ''))

                self.normal_mode_errors.extend(file_errors)

                if processed_files == total_files or processed_files % update_every == 0:
                    progress_bar.progress(processed_files / total_files)
                    status_text.text(f"กำลังวิเคราะห์ไฟล์ ({processed_files}/{total_files})")

                if processed_files % app_config.progress_update_interval == 0:
                    logger.info(f"Processed {processed_files}/{total_files} files")
        
        # Update statistics
        self.normal_mode_stats = {
            'files': total_files,
            'errors': len(self.normal_mode_errors),
            'lines': total_lines_scanned,
            'foreign': total_foreign,
            'english': total_english,
            'numbers': total_numbers
        }
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("🎉 กระบวนการวิเคราะห์โหมดทั่วไปเสร็จสิ้น!")
        
        logger.info(f"Normal mode analysis completed. Found {len(self.normal_mode_errors)} errors")
        
        # Show results
        if self.normal_mode_errors:
            st.success(f"""
            🔍 **โหมดทั่วไป: การวิเคราะห์เสร็จสิ้น!**
            
            📊 **ผลลัพธ์:**
            - จำนวนไฟล์ที่วิเคราะห์: **{total_files}** ไฟล์
            - จำนวนบรรทัดที่สแกน: **{total_lines_scanned}** บรรทัด
            - จำนวนบรรทัดที่ต้องตรวจสอบ: **{len(self.normal_mode_errors)}** รายการ
            
            💡 **เคล็ดลับ:** ตรวจสอบบรรทัดที่พบเพื่อแก้ไขภาษาต่างประเทศหรือตัวเลขที่ไม่ต้องการ
            """)
        else:
            st.success(f"""
            ✅ **โหมดทั่วไป: ไม่พบภาษาต่างประเทศตามเงื่อนไขที่เลือก!**
            
            📊 **ผลลัพธ์:**
            - จำนวนไฟล์ที่วิเคราะห์: **{total_files}** ไฟล์
            - จำนวนบรรทัดที่สแกน: **{total_lines_scanned}** บรรทัด
            - จำนวนบรรทัดที่ต้องตรวจสอบ: **0** รายการ
            
            🎉 เยี่ยมมาก! เนื้อหาปลอดจากภาษาต่างประเทศและตัวเลขตามที่กำหนด
            """)

    def _render_normal_mode_blocks(self) -> List[str]:
        """Render normal_mode_errors เป็น list ของบรรทัด (string) พร้อมเขียนลงไฟล์.

        รูปแบบที่ออก:
            ## filename.txt
            123|
            [เดิม] ข้อความเดิม
            [แก้] ข้อความเดิม (ถ้ายังไม่ได้แก้) หรือข้อความใหม่ (ถ้าแก้แล้ว)
            <blank>

        ผู้ใช้แก้ที่บรรทัด `[แก้]` เท่านั้น แล้วเอามา import กลับ.
        """
        out: List[str] = []
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for error in self.normal_mode_errors:
            grouped.setdefault(error['file_path'], []).append(error)

        for file_path_str, errors in grouped.items():
            file_name = Path(file_path_str).name
            out.append(f"## {file_name}")
            for error in errors:
                original = error.get('line_content', '').rstrip('\n')
                corrected = error.get('corrected_content', original).rstrip('\n')
                categories = ', '.join(error.get('categories', []))
                if categories:
                    out.append(f"# พบ: {categories}")
                out.append(f"{error['line_number']}|")
                out.append(f"[เดิม] {original}")
                out.append(f"[แก้] {corrected}")
                out.append("")
        return out

    def export_normal_mode_errors(self, chunk_lines: int = 0):
        """ส่งออกข้อผิดพลาดจากโหมดทั่วไป — รูปแบบ editable พร้อม import กลับได้.

        เขียน 2 ระดับเสมอ:
          1. Output/normal_mode_errors.txt (master) — ทุก entry รวมกัน
          2. Import/normal_mode_import.txt (สำเนา) — ให้ user แก้ในที่ได้

        ถ้า `chunk_lines > 0` และเนื้อหายาวเกิน → split เป็น
        normal_mode_errors_001.txt, _002.txt, ... โดยห้ามตัดกลาง entry
        (entry = 4 บรรทัด: line_number|, [เดิม], [แก้], blank).

        Args:
            chunk_lines: เป้าหมายจำนวนบรรทัดต่อ chunk (0 = ไม่ split, มีแต่ master)
        """
        if not self.normal_mode_errors:
            st.warning("⚠️ ไม่มีข้อมูลโหมดทั่วไปให้ส่งออก")
            return

        # ใช้ paths.OUTPUT_DIR แบบ dynamic — กันเคสที่ singleton snapshot ค่าผิด
        # (เช่นตอนสลับ project แล้ว self.output_dir ค้าง workspace เดิม)
        output_dir = paths.OUTPUT_DIR
        try:
            with st.spinner("กำลังสร้างไฟล์ normal_mode_errors.txt..."):
                output_dir.mkdir(parents=True, exist_ok=True)

                # ลบ part files เก่าก่อน (กัน mix old+new)
                for old in output_dir.glob("normal_mode_errors_*.txt"):
                    try:
                        old.unlink()
                    except Exception:
                        pass

                body_lines = self._render_normal_mode_blocks()

                # Header อธิบายวิธีทำงานครั้งเดียว — ผู้ใช้ / AI อ่านแล้วเข้าใจทันที
                def _build_header(part_label: str = "") -> List[str]:
                    return [
                        f"# โหมดทั่วไป — รายการบรรทัดที่ต้องแก้{part_label}",
                        "#",
                        "# วิธีแก้:",
                        "#   1. ดูบรรทัด [เดิม] ของแต่ละ entry — บรรทัดที่ระบบจับได้ว่ามีปัญหา",
                        "#   2. เขียนผลที่แก้แล้วลงในบรรทัด [แก้] (แทนที่ข้อความเดิมทั้งบรรทัด)",
                        "#   3. แปลคำต่างประเทศ/อักษรจีนเป็นภาษาไทยให้เหมาะกับบริบท",
                        "#   4. คงไว้ตามเดิมได้: ชื่อคน · ชื่อสถานที่ · คำเฉพาะ · ตัวเลขจริง",
                        "#",
                        "# ห้ามแก้: บรรทัด `## filename` และบรรทัด `123|`",
                        "#         ระบบใช้สองอย่างนี้จับคู่ตอน import กลับ — ถ้าผิด entry นั้นจะถูกข้าม",
                        "#",
                        "",
                    ]

                master_header = _build_header()
                master_path = output_dir / "normal_mode_errors.txt"
                with open(master_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(master_header))
                    f.write("\n".join(body_lines))
                    f.write("\n")

                # สำเนาไว้ใน Import/ ให้ user แก้ในที่
                import_fix_dir = paths.IMPORT_FIX_DIR
                import_fix_dir.mkdir(parents=True, exist_ok=True)
                import_copy = import_fix_dir / "normal_mode_import.txt"
                with open(import_copy, 'w', encoding='utf-8') as f:
                    f.write("\n".join(_build_header(" (สำเนาแก้ในที่)")))
                    f.write("\n".join(body_lines))
                    f.write("\n")

                # Chunk split (optional)
                total_parts = 1
                if chunk_lines > 0:
                    chunks = self._split_normal_mode_blocks(body_lines, chunk_lines)
                    total_parts = len(chunks)
                    if total_parts > 1:
                        for idx, chunk in enumerate(chunks):
                            part_name = f"normal_mode_errors_{idx + 1:03d}.txt"
                            part_path = output_dir / part_name
                            part_label = f" — ส่วนที่ {idx + 1}/{total_parts}"
                            with open(part_path, 'w', encoding='utf-8') as f:
                                f.write("\n".join(_build_header(part_label)))
                                f.write("\n".join(chunk))
                                f.write("\n")

            if total_parts > 1:
                st.success(
                    f"Export สำเร็จ — ส่งออก {len(self.normal_mode_errors)} รายการ · "
                    f"master + {total_parts} chunks (~{chunk_lines} บรรทัด/chunk)"
                )
                st.toast(f"Export master + {total_parts} chunks สำเร็จ", icon="📤")
            else:
                st.success(
                    f"Export สำเร็จ — ส่งออก {len(self.normal_mode_errors)} รายการ "
                    f"(master เดียว) · สำเนาอยู่ที่ Import/normal_mode_import.txt"
                )
                st.toast(f"Export สำเร็จ — {len(self.normal_mode_errors)} รายการ", icon="📤")

        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการส่งออก: {str(e)}")
            st.exception(e)

    @staticmethod
    def _split_normal_mode_blocks(body_lines: List[str], chunk_lines: int) -> List[List[str]]:
        """แบ่ง body_lines เป็น chunks โดยห้ามตัดกลาง entry.

        Entry = ## file header หรือ 4 บรรทัด (line_num|, [เดิม], [แก้], blank).
        วิธีง่ายๆ: แบ่งระหว่าง entry boundaries — boundary = บรรทัดว่าง
        หรือบรรทัดที่ขึ้นต้นด้วย "## ".

        Args:
            body_lines: list ของบรรทัด (ไม่รวม header)
            chunk_lines: เป้าหมายจำนวนบรรทัดต่อ chunk

        Returns:
            list ของ chunks — แต่ละ chunk = list ของบรรทัด
        """
        if chunk_lines <= 0 or not body_lines:
            return [body_lines]

        # แบ่ง body เป็น "blocks" ก่อน (1 block = 1 entry หรือ 1 file header)
        blocks: List[List[str]] = []
        current: List[str] = []
        for line in body_lines:
            current.append(line)
            # boundary = บรรทัดว่าง → จบ entry block
            if line == "":
                blocks.append(current)
                current = []
            elif line.startswith("## ") and len(current) > 1:
                # file header กลาง stream → flush previous
                blocks.append(current[:-1])
                current = [line]
        if current:
            blocks.append(current)

        # รวม blocks → chunks ทีละ chunk_lines บรรทัด
        chunks: List[List[str]] = []
        current_chunk: List[str] = []
        current_count = 0
        # เก็บ "header context" ของไฟล์ปัจจุบัน เพื่อ repeat ในทุก chunk
        current_file_header: Optional[str] = None
        for block in blocks:
            # ถ้า block นี้คือ file header — อัพเดต context
            for ln in block:
                if ln.startswith("## "):
                    current_file_header = ln
                    break

            if current_count + len(block) > chunk_lines and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_count = 0
                # Repeat file header ใน chunk ใหม่ ถ้า block ปัจจุบันไม่ใช่ header เอง
                if current_file_header and not any(ln.startswith("## ") for ln in block):
                    current_chunk.append(current_file_header)
                    current_chunk.append("")
                    current_count += 2
            current_chunk.extend(block)
            current_count += len(block)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [body_lines]

    def import_normal_mode_corrections(self) -> int:
        """อ่านไฟล์ที่ user แก้กลับ → เติม corrected_content ลง normal_mode_errors.

        Search priority:
          1. Import/normal_mode_*.txt (user-supplied)
          2. Output/normal_mode_*.txt (fallback)

        **Match strategy: EXACT เท่านั้น** ด้วย (normalized filename, line_number).
        โหมดนี้ไม่มี [A] เป็น anchor verify เหมือน AB mode → fuzzy ไม่ปลอดภัย
        ต้อง match ตรงเป๊ะด้วยหมายเลขบรรทัด.

        ถ้า [เดิม] ใน import file ไม่ตรงกับ line_content ใน memory → warn แต่ยังแทนที่
        (เพราะ user ตั้งใจให้แก้ที่บรรทัดนั้น). ถ้าจับคู่ไม่ได้ → ข้ามและรายงาน.

        Returns:
            จำนวน entries ที่ถูก update ด้วย corrected_content
        """
        if not self.normal_mode_errors:
            st.error(
                "ไม่พบข้อมูลการวิเคราะห์ในหน่วยความจำ — "
                "กด **วิเคราะห์โหมดทั่วไป** ก่อน 1 ครั้งให้ระบบรู้จัก target"
            )
            return 0

        # หา part files
        def _collect_from(directory: Path) -> List[Path]:
            if not directory.exists():
                return []
            found = sorted(directory.glob("normal_mode_errors_*.txt"))
            for fname in ("normal_mode_import.txt", "normal_mode_errors.txt"):
                extra = directory / fname
                if extra.exists() and extra not in found:
                    found.append(extra)
            return found

        part_files: List[Path] = _collect_from(paths.IMPORT_FIX_DIR)
        source_dir: Optional[Path] = paths.IMPORT_FIX_DIR if part_files else None
        if not part_files:
            part_files = _collect_from(paths.OUTPUT_DIR)
            if part_files:
                source_dir = paths.OUTPUT_DIR

        if not part_files:
            st.error(
                "ไม่พบไฟล์ normal_mode_*.txt — ลองทั้ง `Import/` และ `Output/` แล้ว\n"
                "วิธีแก้: กด **ส่งออกแก้กลับได้** ก่อน 1 ครั้ง "
                "(จะสร้าง `Import/normal_mode_import.txt`) แล้วลองอีกครั้ง"
            )
            return 0

        st.caption(
            f"📂 อ่าน import จาก: `{source_dir.name if source_dir else '?'}/` "
            f"({len(part_files)} ไฟล์ · match ด้วยหมายเลขบรรทัดแม่นๆ)"
        )

        # Build exact-match index: (norm_filename, line_number) → error
        index: Dict[Tuple[str, int], Dict[str, Any]] = {}
        for error in self.normal_mode_errors:
            fname_norm = self._normalize_import_filename(Path(error['file_path']).name)
            key = (fname_norm, int(error['line_number']))
            index[key] = error

        # Parse content
        content_parts: List[str] = []
        for pf in part_files:
            try:
                content_parts.append(pf.read_text('utf-8'))
            except Exception as e:
                st.warning(f"⚠ อ่าน {pf.name} ไม่ได้: {e}")
        content = "\n".join(content_parts)
        lines = content.split('\n')

        updated = 0
        verify_mismatched = 0  # [เดิม] ไม่ตรงกับ line_content (ยังแทนที่อยู่ — แค่เตือน)
        not_matched = 0
        mismatch_samples: List[str] = []
        notfound_samples: List[str] = []
        current_file = ""
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            file_header = self._parse_import_file_header(stripped)
            if file_header:
                current_file = self._normalize_import_filename(file_header)
                i += 1
                continue
            if not stripped or stripped.startswith('#'):
                i += 1
                continue

            line_number = self._parse_import_line_number(stripped)
            if line_number is None or not current_file:
                i += 1
                continue

            # หา [เดิม] / [แก้] ใน 1-6 บรรทัดถัดไป
            orig_line: Optional[str] = None
            fixed_line: Optional[str] = None
            j = i + 1
            while j < len(lines) and (j - i) <= 6:
                t = lines[j].strip()
                if self._parse_import_file_header(t) or self._parse_import_line_number(t) is not None:
                    break
                if orig_line is None and t.startswith('[เดิม]'):
                    orig_line = t[len('[เดิม]'):].lstrip()
                elif fixed_line is None and t.startswith('[แก้]'):
                    fixed_line = t[len('[แก้]'):].lstrip()
                j += 1

            if fixed_line is None:
                i = j
                continue

            # EXACT match เท่านั้น
            target = index.get((current_file, line_number))
            if target is not None:
                # Verify [เดิม] ตรงกับ line_content (sanity check)
                if orig_line is not None:
                    expected = self._normalize_import_text(target.get('line_content', ''))
                    actual = self._normalize_import_text(orig_line)
                    if expected and actual and expected != actual:
                        verify_mismatched += 1
                        if len(mismatch_samples) < 3:
                            mismatch_samples.append(
                                f"`{current_file}` บรรทัด {line_number}"
                            )
                target['corrected_content'] = fixed_line
                updated += 1
            else:
                not_matched += 1
                if len(notfound_samples) < 3:
                    notfound_samples.append(f"`{current_file}` บรรทัด {line_number}")

            i = j

        # สรุปผล
        if updated > 0:
            msg = f"นำเข้าการแก้ไขสำเร็จ — อัพเดต {updated} รายการ"
            if not_matched:
                msg += f" · จับคู่ไม่ได้: {not_matched}"
            st.success(msg)
            st.toast(f"Import สำเร็จ {updated} รายการ", icon="📥")
            if verify_mismatched:
                st.warning(
                    f"พบ {verify_mismatched} รายการที่ [เดิม] ไม่ตรงกับเนื้อหาในหน่วยความจำ "
                    f"(แทนที่ตามหมายเลขบรรทัดอยู่ แต่อาจมาจากการแก้ผิดบรรทัด): "
                    + ", ".join(mismatch_samples)
                    + ("..." if verify_mismatched > len(mismatch_samples) else "")
                )
            if not_matched:
                st.warning(
                    f"จับคู่ไม่ได้ {not_matched} รายการ: "
                    + ", ".join(notfound_samples)
                    + ("..." if not_matched > len(notfound_samples) else "")
                    + " — ตรวจชื่อไฟล์/หมายเลขบรรทัดให้ตรงกับตอนวิเคราะห์"
                )
        else:
            st.warning(
                f"ไม่มี entry ที่อัพเดตได้ (จับคู่ไม่ได้: {not_matched}) — "
                "ตรวจชื่อไฟล์/หมายเลขบรรทัด หรือเช็คว่าบรรทัด [แก้] ไม่ถูกลบ"
            )

        return updated

    def fix_normal_mode_files(
        self,
        destination_dir: Optional[Path] = None,
        in_place: bool = False,
    ) -> Dict[str, int]:
        """เขียนไฟล์ที่แก้แล้ว — แทนที่บรรทัดที่มี corrected_content ในไฟล์ต้นทาง.

        Args:
            destination_dir: โฟลเดอร์ปลายทาง (ละเว้นถ้า in_place=True)
            in_place: ถ้า True เขียนทับไฟล์ต้นทาง (ระวัง: destructive)

        Returns:
            dict สรุปจำนวน: {'files': N, 'lines_replaced': M, 'errors': E}
        """
        if not self.normal_mode_errors:
            st.warning("ไม่มีข้อมูลให้แก้ — กดวิเคราะห์โหมดทั่วไป + นำเข้าการแก้ไข ก่อน")
            return {'files': 0, 'lines_replaced': 0, 'errors': 0}

        # Group by source file
        errors_by_file: Dict[str, List[Dict[str, Any]]] = {}
        for error in self.normal_mode_errors:
            errors_by_file.setdefault(error['file_path'], []).append(error)

        # Setup destination
        if not in_place:
            if destination_dir is None:
                destination_dir = paths.FINISH_DIR
            destination_dir = Path(destination_dir).expanduser()
            destination_dir.mkdir(parents=True, exist_ok=True)

        progress_bar = st.progress(0)
        status_text = st.empty()

        total_files = len(errors_by_file)
        files_done = 0
        lines_replaced_total = 0
        files_with_changes = 0

        for source_path_str, errors in errors_by_file.items():
            files_done += 1
            source_path = Path(source_path_str)
            file_name = source_path.name

            progress_bar.progress(files_done / total_files)
            status_text.text(f"กำลังเขียน: {file_name} ({files_done}/{total_files})")

            if not source_path.exists():
                st.warning(f"⚠ ไฟล์ต้นทางหาย: `{source_path}` — ข้าม")
                continue

            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                st.error(f"❌ อ่าน {file_name} ไม่ได้: {e}")
                continue

            replaced_in_file = 0
            for error in errors:
                line_idx = int(error['line_number']) - 1
                if line_idx < 0 or line_idx >= len(lines):
                    continue
                original = error.get('line_content', '').rstrip('\n')
                corrected = error.get('corrected_content', original)
                if corrected == original:
                    continue  # ยังไม่ได้แก้
                # คง newline เดิม (อาจเป็น \n หรือ \r\n)
                orig_raw = lines[line_idx]
                newline = '\r\n' if orig_raw.endswith('\r\n') else '\n'
                lines[line_idx] = corrected.rstrip('\r\n') + newline
                replaced_in_file += 1

            if replaced_in_file == 0:
                continue  # ไม่มีการเปลี่ยน → ข้ามไฟล์นี้ ไม่เขียนทับ

            # Write
            if in_place:
                dest_path = source_path
            else:
                dest_path = destination_dir / file_name
            try:
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            except Exception as e:
                st.error(f"❌ เขียน {dest_path} ไม่ได้: {e}")
                continue

            lines_replaced_total += replaced_in_file
            files_with_changes += 1

        progress_bar.progress(1.0)
        status_text.text("เขียนไฟล์ที่แก้แล้วเสร็จสิ้น")

        summary = {
            'files': files_with_changes,
            'lines_replaced': lines_replaced_total,
            'errors': len(self.normal_mode_errors),
        }

        if files_with_changes > 0:
            dest_label = "ไฟล์ต้นทาง (in-place)" if in_place else f"`{destination_dir}`"
            st.success(
                f"แก้ไขสำเร็จ — {files_with_changes} ไฟล์ · {lines_replaced_total} บรรทัด → {dest_label}"
            )
            st.toast(f"Fix สำเร็จ {files_with_changes} ไฟล์", icon="🛠️")
        else:
            st.info("ไม่มีบรรทัดที่ถูกแก้ (corrected_content ยังเท่ากับ line_content) — กดนำเข้าการแก้ไขก่อน")

        return summary

    def build_fix_markdown(self, error_content: str) -> str:
        error_body = error_content.rstrip()
        return f"""**1. บทบาทและภารกิจหลัก**

1.1. **บทบาท:** เจ้าได้รับการแต่งตั้งให้เป็น **ปรมาจารย์ AI ผู้ตรวจทานและเกลาสำนวน (Master AI Proofreader & Refiner)** ภารกิจของเจ้าไม่ใช่การแปลใหม่ทั้งหมด แต่คือการ **ตรวจสอบ, แก้ไข, และยกระดับ** คำแปลที่มีอยู่แล้วในบรรทัด `[B]` ให้สมบูรณ์แบบ โดยใช้ข้อความต้นฉบับในบรรทัด `[A]` เป็นแหล่งอ้างอิงความหมายที่ถูกต้องที่สุด

1.2. **ภารกิจหลัก:** ประมวลผลข้อความที่ได้รับซึ่งอยู่ในรูปแบบเฉพาะ (`line_number|[A]...[B]...`) และดำเนินการดังนี้:
    *   วิเคราะห์ข้อความต้นฉบับใน `[A]` เพื่อทำความเข้าใจความหมายและเจตนาที่แท้จริง 100%
    *   ตรวจสอบคำแปลใน `[B]` เพื่อหาข้อผิดพลาด ซึ่งรวมถึง:
        *   อักขระภาษาต้นทาง (เช่น จีน) ที่ยังแปลไม่หมด
        *   สำนวนที่แปลตรงตัวเกินไปจนฟังดูไม่เป็นธรรมชาติ ("ภาษาแปล")
        *   การตีความหมายผิดพลาด
        *   กรณีที่บรรทัดขึ้นต้นด้วย `# แปลไม่ครบ ต้องแก้เป็นคำ => ...` ให้ถือว่าเป็น **คำศัพท์บังคับ** ที่ต้องสะท้อนอยู่ใน `[B]` หลังการแก้ไข
    *   สร้างเนื้อหาสำหรับ `[B]` ขึ้นมาใหม่ให้สมบูรณ์แบบ โดยยึดตามหลักการในข้อถัดไป
    *   **ส่งคืนผลลัพธ์ทั้งหมดในโครงสร้างและรูปแบบดั้งเดิมทุกประการ** ห้ามเปลี่ยนแปลงลำดับ, `line_number|`, หรือโครงสร้าง `[A]`, `[B]` โดยเด็ดขาด

**2. หลักการสำคัญในการตรวจแก้ (กฎเหล็กสูงสุด)**

2.1. **ยึด [A] เป็นแหล่งความจริงสูงสุด (Source of Truth):** ความหมายของ `[B]` ที่แก้ไขแล้ว จะต้องถูกต้องและสอดคล้องกับความหมายของ `[A]` อย่างสมบูรณ์แบบ หากคำแปลเดิมใน `[B]` สื่อความหมายผิดเพี้ยนไปจาก `[A]` จะต้องแก้ไขให้ถูกต้องทันที

2.2. **ความสมบูรณ์ 100% ของภาษาไทย (Thai Language Completeness):**
    *   **[กฎเหล็กเด็ดขาด]** `[B]` ที่ผ่านการแก้ไขแล้ว **ห้ามมีอักขระภาษาต้นทาง (เช่น จีน, อังกฤษ ฯลฯ) หลงเหลืออยู่แม้แต่ตัวเดียว**
    *   ผลลัพธ์ใน `[B]` ต้องเป็นภาษาไทยที่สะอาดหมดจด

2.3. **การปรับสำนวนตามบริบท (Contextual Adaptation - กฎความเป็นกลาง):**
    *   เจ้าต้องวิเคราะห์น้ำเสียงและลีลาจากทั้ง `[A]` และ `[B]` เดิม เพื่อกำหนดสไตล์การแปลที่เหมาะสม
    *   **หากบริบทเป็นแนวโบราณ/กำลังภายใน** ให้เกลาสำนวนใน `[B]` ให้คงไว้ซึ่งความคลาสสิก สละสลวย และเหมาะสมกับยุคนั้น
    *   **หากบริบทเป็นแนวปัจจุบัน/ทั่วไป** ให้เกลาสำนวนใน `[B]` ให้เป็นภาษาไทยร่วมสมัยที่เข้าใจง่ายและเป็นธรรมชาติ
    *   **เป้าหมายคือความสอดคล้อง:** `[B]` ที่แก้ไขแล้วต้องมีน้ำเสียงและลีลาที่กลมกลืนไปกับเนื้อหาส่วนอื่นๆ ของเรื่อง

2.4. **ความเป็นธรรมชาติและลื่นไหล (Natural Flow Enhancement):** นอกจากการแก้ไขข้อผิดพลาดแล้ว เจ้ามีหน้าที่เกลาประโยคใน `[B]` ที่ฟังดูแข็งทื่อหรือแปลก ให้กลายเป็นภาษาไทยที่อ่านง่ายและลื่นไหล เหมือนถูกเขียนขึ้นโดยคนไทยตั้งแต่แรก โดยยังคงความหมายจาก `[A]` ไว้อย่างครบถ้วน

**3. กฎการดำเนินการและรูปแบบผลลัพธ์ (ปฏิบัติตามอย่างเคร่งครัด)**

3.1. **รักษาโครงสร้างไฟล์ต้นฉบับอย่างสมบูรณ์:**
    *   บรรทัดที่เป็นความคิดเห็น (ขึ้นต้นด้วย `#`) ต้องคงอยู่ตามเดิม
    *   บรรทัดที่เป็นชื่อไฟล์ (ขึ้นต้นด้วย `##`) ต้องคงอยู่ตามเดิม
    *   คำนำหน้าบรรทัด `line_number|` ต้องคงอยู่ตามเดิม ห้ามแก้ไขหรือลบออก
    *   แท็ก `[A]` และ `[B]` ต้องคงอยู่ตามเดิม

3.2. **แก้ไขเฉพาะเนื้อหาภายใน [B] เท่านั้น:**
    *   ห้ามแก้ไขข้อความภายใน `[A]` โดยเด็ดขาด
    *   หน้าที่ของเจ้าจำกัดอยู่แค่การสร้างข้อความภาษาไทยที่สมบูรณ์แบบเพื่อนำไปแทนที่ข้อความเดิมที่อยู่ใน `[B]` เท่านั้น

3.3. **ห้ามเพิ่มหรือลบองค์ประกอบ:** ห้ามเพิ่มบรรทัดว่าง, ความคิดเห็น, หรือลบบรรทัดใดๆ ที่มีอยู่ในข้อมูลนำเข้า ผลลัพธ์ต้องมีจำนวนบรรทัดและโครงสร้างเหมือนต้นฉบับทุกประการ

---

**คำสั่ง:**
จงทำหน้าที่เป็น **ปรมาจารย์ AI ผู้ตรวจทานและเกลาสำนวน** ประมวลผลข้อความต่อไปนี้ตามกฎทั้งหมดที่ระบุไว้ข้างต้น วิเคราะห์แต่ละคู่ `[A]` และ `[B]` อย่างละเอียด จากนั้นแก้ไขเนื้อหาภายใน `[B]` ให้เป็นภาษาไทยที่สมบูรณ์แบบ 100% ถูกต้องตามความหมาย และสอดคล้องกับบริบทของเรื่องราว ก่อนจะส่งคืนผลลัพธ์ทั้งหมดในรูปแบบดั้งเดิมทุกประการ

```text
{error_body}
```
"""
    
    def _render_error_blocks(self) -> List[Any]:
        """Render self.found_errors → list ของ Block สำหรับ chunker.

        Block flow:
          SECTION → FILE → (VOCAB_HINT) → ENTRY → ENTRY → ... → FILE → ...
        """
        from modules.error_chunker import (
            Block, BLOCK_SECTION, BLOCK_FILE, BLOCK_VOCAB_HINT, BLOCK_ENTRY,
        )

        bucket_titles = {
            'foreign_and_vocab': 'ภาษาต่างประเทศ,อังกฤษ, เลข + ศัพท์ไม่ตรง วิเคราะห์เพิ่ม',
            'foreign_only': 'ภาษาต่างประเทศ,อังกฤษ, เลข',
            'vocab_only': 'ศัพท์ไม่ตรง วิเคราะห์เพิ่ม',
            'missing_translation': 'บรรทัดที่ AI ข้ามแปล (กรอก [B] ให้ครบ)',
        }

        blocks: List[Any] = []

        for bucket_key in ['foreign_and_vocab', 'foreign_only', 'vocab_only', 'missing_translation']:
            bucket_errors = [e for e in self.found_errors if e.get('error_bucket') == bucket_key]
            if not bucket_errors:
                continue

            blocks.append(Block(
                kind=BLOCK_SECTION,
                lines=[f"# ===== {bucket_titles[bucket_key]} ({len(bucket_errors)} รายการ) ====="],
            ))

            files_dict: Dict[str, List[Dict[str, Any]]] = {}
            for error in bucket_errors:
                file_name = Path(error['file_path']).name
                files_dict.setdefault(file_name, []).append(error)

            for file_name, errors in files_dict.items():
                blocks.append(Block(kind=BLOCK_FILE, lines=[f"## {file_name}"]))

                unique_missing_pairs = []
                seen_missing_pairs = set()
                for error in errors:
                    for item in error.get('missing_vocab_pairs', []):
                        pair_key = (item['cn'], item['th'])
                        if pair_key not in seen_missing_pairs:
                            seen_missing_pairs.add(pair_key)
                            unique_missing_pairs.append(pair_key)

                if unique_missing_pairs:
                    missing_text = ', '.join(
                        [f"{cn} => {th}" for cn, th in unique_missing_pairs]
                    )
                    blocks.append(Block(
                        kind=BLOCK_VOCAB_HINT,
                        lines=[f"# แปลไม่ตรง วิเคราะห์ว่าควรแก้เป็น => {missing_text} หรือไม่"],
                    ))

                for error in errors:
                    entry_lines: List[str] = []
                    if error.get('error_bucket') == 'missing_translation':
                        entry_lines.append(
                            f"# [กรณี B] แปลไม่ครบ — กรอก [B] ให้ครบ "
                            f"(chapter={error.get('missing_chapter', '?')} "
                            f"raw_line={error.get('missing_raw_line', '?')} "
                            f"ratio={error.get('missing_best_ratio', 0):.2f})"
                        )
                    entry_lines.append(f"{error['line_number_B']}|")
                    original_a = self._strip_ab_prefix(error['original_A'], 'A')
                    entry_lines.append(f"[A] {original_a}")
                    original_b = self._strip_ab_prefix(error['original_B'], 'B')
                    entry_lines.append(f"[B] {original_b}")
                    entry_lines.append('')  # blank separator
                    blocks.append(Block(kind=BLOCK_ENTRY, lines=entry_lines))

        return blocks

    def export_errors(self, chunk_lines: int = 0):
        """ส่งออกข้อผิดพลาดเป็นไฟล์ error_trans.txt + chunks (ถ้ากำหนด).

        เขียน 2 ระดับเสมอ:
          1. error_trans.txt (master) — ข้อมูลเต็มทุก error เก็บไว้เป็น single source of truth
          2. error_trans_001.txt, _002.txt, ... (chunks) — ถ้า chunk_lines > 0 และจำนวนบรรทัด
             ทั้งหมดเกิน chunk_lines → split โดยห้ามตัดกลาง entry

        Args:
            chunk_lines: เป้าหมายจำนวนบรรทัดต่อ chunk (0 = ไม่ split, มีแต่ master)
        """
        if not self.found_errors:
            st.warning("⚠️ ไม่มีข้อผิดพลาดให้ส่งออก")
            return

        # ใช้ paths.* dynamic — กันเคสที่ snapshot ค่าผิดตอนสลับ project
        output_dir = paths.OUTPUT_DIR
        input_dir = paths.INPUT_DIR
        try:
            from modules.error_chunker import (
                split_blocks_by_line_count, build_part_filename,
            )

            with st.spinner("กำลังสร้างไฟล์ error_trans.txt..."):
                output_dir.mkdir(parents=True, exist_ok=True)

                # ลบ part files เก่าก่อน (กัน mix old+new)
                for old in output_dir.glob("error_trans_*.txt"):
                    try:
                        old.unlink()
                    except Exception:
                        pass

                # 1. Render เป็น blocks
                blocks = self._render_error_blocks()

                # 2. เขียน master (ทุก block flat — มาตรฐาน) เสมอ
                master_header = (
                    "# แก้ไขเฉพาะบรรทัด [B] เท่านั้น (ไฟล์ master รวมทุกรายการ)\n"
                    "# รูปแบบ: line_number| แล้วตามด้วย [A] และ [B]\n\n"
                )
                master_path = output_dir / "error_trans.txt"
                with open(master_path, 'w', encoding='utf-8') as f:
                    f.write(master_header)
                    for block in blocks:
                        f.write(block.render())

                # 2b. เขียน 5-import/import_errors.txt — สำเนาไว้ให้ user แก้ในที่
                # (กัน user หลงลบ chunks หรือเริ่มจากของในนี้แทน 0)
                import_fix_dir = paths.IMPORT_FIX_DIR
                import_fix_dir.mkdir(parents=True, exist_ok=True)
                import_errors_path = import_fix_dir / "import_errors.txt"
                with open(import_errors_path, 'w', encoding='utf-8') as f:
                    f.write(
                        "# import_errors.txt — แก้ในไฟล์นี้แล้วกด Import กลับได้เลย\n"
                        "# (สำเนาของ output/error_trans.txt — โปรแกรมเขียนทับทุกครั้งที่ Export)\n"
                        "# แก้ไขเฉพาะบรรทัด [B] เท่านั้น\n\n"
                    )
                    for block in blocks:
                        f.write(block.render())

                # 3. ถ้าตั้ง chunk_lines → split + เขียน chunks
                total_parts = 1
                if chunk_lines > 0:
                    chunks = split_blocks_by_line_count(blocks, chunk_lines)
                    total_parts = len(chunks)
                    if total_parts > 1:
                        for part_index, chunk_blocks in enumerate(chunks):
                            part_filename = build_part_filename("error_trans.txt", part_index, total_parts)
                            part_path = output_dir / part_filename
                            with open(part_path, 'w', encoding='utf-8') as f:
                                f.write(
                                    f"# แก้ไขเฉพาะบรรทัด [B] เท่านั้น "
                                    f"(ส่วนที่ {part_index + 1}/{total_parts})\n"
                                )
                                f.write("# รูปแบบ: line_number| แล้วตามด้วย [A] และ [B]\n")
                                f.write(
                                    f"# ⚠️ part กำกับ: ส่วนที่ {part_index + 1} จาก {total_parts} "
                                    f"— ต้องแก้ครบทุก part ก่อน import กลับ\n\n"
                                )
                                for block in chunk_blocks:
                                    f.write(block.render())

                # หลังจากส่งออก error_trans แล้ว ทำการ export คำศัพท์จากไฟล์ input
                all_vocab = []
                txt_files = list(input_dir.glob("*.txt"))
                for file_path in txt_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        collect_vocab_section = False
                        for raw_line in lines:
                            line = raw_line.strip()
                            if not line:
                                continue
                            # เริ่มส่วนคำศัพท์
                            if line == "ศัพท์ใหม่ภาษาจีน | คำแปลภาษาไทย":
                                collect_vocab_section = True
                                continue
                            # ข้ามบรรทัดปิดท้าย
                            if line == "[จบแล้ว]":
                                continue
                            # เก็บคำศัพท์เฉพาะเมื่ออยู่ในส่วนคำศัพท์ และเป็นรูปแบบ จีน | ไทย และมีอักขระจีน
                            if collect_vocab_section and " | " in line and re.search(VOCAB_PATTERN, line):
                                all_vocab.append(line)
                    except Exception:
                        # ข้ามไฟล์ที่อ่านไม่ได้
                        continue

                if all_vocab:
                    vocab_file = output_dir / "vocab.txt"
                    with open(vocab_file, 'w', encoding='utf-8') as vf:
                        for vocab in all_vocab:
                            vf.write(vocab + "\n")
            
            # แสดงผลลัพธ์การ export
            if total_parts > 1:
                st.success(
                    f"Export สำเร็จ — ส่งออก {len(self.found_errors)} รายการ · "
                    f"master + {total_parts} chunks (~{chunk_lines} บรรทัด/chunk)"
                )
                st.toast(f"Export master + {total_parts} chunks สำเร็จ", icon="📤")
            else:
                st.success(f"Export สำเร็จ — ส่งออก {len(self.found_errors)} รายการ (master เดียว)")
                st.toast(f"Export สำเร็จ — {len(self.found_errors)} รายการ", icon="📤")
        
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการส่งออกไฟล์: {str(e)}")
            st.exception(e)
    
    def grab_and_import_file(self, fuzzy_min_ratio: float = 0.95):
        """Grab ไฟล์ error_trans*.txt (และ chunked parts) จาก 5-import/ → fallback output/.

        Search priority:
          1. workspace/5-import/error_trans*.txt — ที่ user paste ไฟล์ที่แก้แล้วมาวาง
          2. workspace/output/error_trans*.txt   — backward compat (export ปกติ)

        Args:
            fuzzy_min_ratio: threshold สำหรับ fuzzy fallback ใน _fuzzy_find_import_target
                (0.95 default = แม่นๆ, ลด false match)
        """
        from modules.error_chunker import find_import_parts

        # เก็บ threshold ไว้ให้ _fuzzy_find_import_target ใช้
        self._import_fuzzy_min_ratio = float(fuzzy_min_ratio)

        def _collect_from(directory: Path) -> List[Path]:
            """หาไฟล์ import ทั้ง error_trans*.txt และ import_errors.txt ในโฟลเดอร์นี้"""
            if not directory.exists():
                return []
            found = list(find_import_parts(directory, "error_trans.txt"))
            extra = directory / "import_errors.txt"
            if extra.exists() and extra not in found:
                found.append(extra)
            return found

        # 1. ลอง 5-import/ ก่อน (user-supplied corrections)
        part_files: List[Path] = _collect_from(paths.IMPORT_FIX_DIR)
        source_dir: Optional[Path] = paths.IMPORT_FIX_DIR if part_files else None

        # 2. Fallback: output/
        if not part_files:
            part_files = _collect_from(paths.OUTPUT_DIR)
            if part_files:
                source_dir = paths.OUTPUT_DIR

        if not part_files:
            st.error(
                "ไม่พบไฟล์ import — ลองทั้ง `Import/` และ `Output/` แล้ว\n"
                "วิธีแก้: กด Export ก่อน 1 ครั้ง (จะสร้าง `Import/import_errors.txt`)\n"
                "หรือวาง chunks ที่แก้แล้วใน `Import/` แล้วลองอีกครั้ง"
            )
            return

        # แสดงว่ามาจากไหน
        st.caption(f"📂 อ่าน import จาก: `{source_dir.name if source_dir else '?'}/` "
                   f"({len(part_files)} ไฟล์ · fuzzy threshold ≥ {fuzzy_min_ratio:.2f})")

        try:
            with st.spinner(f"กำลัง Import {len(part_files)} ไฟล์..."):
                if not self.found_errors:
                    st.info("ℹ️ ไม่พบข้อมูลข้อผิดพลาดในหน่วยความจำ จะกู้รายการจากไฟล์ใน 0-input ระหว่างการ import ให้อัตโนมัติ")

                # รวม content จากทุก part file
                content_parts = []
                for pf in part_files:
                    try:
                        content_parts.append(pf.read_text('utf-8'))
                    except Exception as e:
                        st.warning(f"⚠ อ่าน {pf.name} ไม่ได้: {e}")
                content = "\n".join(content_parts)
                lines = content.split('\n')

                if len(part_files) > 1:
                    st.caption(f"📥 รวม {len(part_files)} ไฟล์ part เข้าด้วยกันแล้ว")
                
                updated_targets = set()
                fallback_targets = set()
                bootstrapped_targets = set()
                current_file = ""
                i = 0
                
                while i < len(lines):
                    line = lines[i].strip()
                    file_header = self._parse_import_file_header(line)
                    
                    # ข้าม comment lines และ empty lines (แต่ไม่ skip ##)
                    if (line.startswith('#') and not file_header) or not line:
                        i += 1
                        continue
                    
                    # หาชื่อไฟล์ (## filename)
                    if file_header:
                        current_file = file_header
                        i += 1
                        continue
                    
                    # หา pattern: line_number|
                    line_number = self._parse_import_line_number(line)
                    if line_number is not None and current_file:
                        a_line = ""
                        b_line = None
                        j = i + 1

                        while j < len(lines):
                            temp_line = lines[j].strip()
                            if self._parse_import_file_header(temp_line) or self._parse_import_line_number(temp_line) is not None:
                                break

                            if not a_line and temp_line.startswith('[A]'):
                                a_line = temp_line[3:].lstrip()
                            elif b_line is None and temp_line.startswith('[B]'):
                                b_line = temp_line[3:].lstrip()

                            j += 1

                        if b_line is not None:
                            corrected_b = '[B] ' + b_line
                            matched_error, match_mode = self._find_import_target(current_file, line_number, a_line)

                            if matched_error is not None:
                                matched_error['corrected_B'] = corrected_b

                                target_key = (
                                    self._normalize_import_filename(Path(matched_error['file_path']).name),
                                    matched_error['line_number_B']
                                )
                                updated_targets.add(target_key)
                                if match_mode != 'exact':
                                    fallback_targets.add(target_key)
                                if match_mode.startswith('bootstrapped'):
                                    bootstrapped_targets.add(target_key)
                            else:
                                st.write(f"🔍 **Debug Import:** ไม่พบ match สำหรับ {current_file} บรรทัด {line_number}")
                                if a_line:
                                    st.write(f"   A: `{a_line[:50]}...`")
                                st.write(f"   B: `{b_line[:50]}...`")

                            i = j
                            continue
                    
                    i += 1
            
            # แสดงผลลัพธ์การ import
            updated_count = len(updated_targets)
            if updated_count > 0:
                st.success(f"✅ Import สำเร็จ! อัปเดต {updated_count} รายการ")
                st.toast(f"✅ Import สำเร็จ! อัปเดต {updated_count} รายการ", icon="📥")
                if fallback_targets:
                    st.info(
                        f"ℹ️ จับคู่แบบยืดหยุ่น {len(fallback_targets)} รายการ โดยอ้างอิงจากชื่อไฟล์และบรรทัด แม้ข้อความ [A] จะไม่ตรงเป๊ะ"
                    )
                if bootstrapped_targets:
                    st.info(
                        f"ℹ️ กู้รายการจากไฟล์ต้นฉบับใน 0-input {len(bootstrapped_targets)} รายการ เพื่อให้ import ทำงานได้แม้ session เดิมจะหายไป"
                    )
            else:
                st.warning("⚠️ ไม่พบการเปลี่ยนแปลงในไฟล์ error_trans.txt")
                st.toast("⚠️ ไม่พบการเปลี่ยนแปลง", icon="⚠️")
            
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดในการ Import ไฟล์: {str(e)}")
            st.exception(e)
    
    def check_remaining_errors(self, check_foreign_languages: bool, check_numbers: bool):
        """ตรวจสอบข้อผิดพลาดที่เหลืออยู่"""
        remaining_errors = 0
        
        for error in self.found_errors:
            text = error.get('corrected_B', '')
            source_text = self._strip_ab_prefix(error.get('original_A', ''), 'A')
            if isinstance(text, str) and text.startswith('[B]'):
                text_to_check = text[3:].lstrip()
            else:
                text_to_check = text

            detection = self.detect_characters(
                text_to_check,
                check_foreign_languages,
                check_numbers,
                skip_ab_markers=False,
                check_english=self.ab_settings.get('check_english', False)
            )
            vocab_matches = self._find_missing_translation_vocab(source_text, text_to_check)
            if detection['should_flag'] or vocab_matches.get('missing'):
                remaining_errors += 1
        
        return remaining_errors
    
    def analyze_multiple_folders_mode(self, check_foreign_languages: bool, check_numbers: bool, check_english: bool):
        """วิเคราะห์หลาย subfolders ใน 0-input พร้อมกัน (รองรับ nested folders)"""
        import streamlit as st
        
        # 🔄 Auto-reload exclude patterns
        if regex_patterns.check_and_reload():
            st.info(f"🔄 ตรวจพบการเปลี่ยนแปลง exclude.txt โหลด patterns ใหม่แล้ว ({len(regex_patterns.ignore_patterns)} patterns)")
        
        self.multi_folder_results = {}
        self.multi_folder_settings = {
            'check_foreign_languages': check_foreign_languages,
            'check_english': check_english,
            'check_numbers': check_numbers
        }
        
        if not self.input_dir.exists():
            st.error("❌ ไม่พบโฟลเดอร์ 0-input")
            st.info("💡 กรุณาสร้างโฟลเดอร์ 0-input และวาง subfolders ที่ต้องการตรวจสอบ")
            return
        
        # หา level 1 folders (นักแปล)
        level1_folders = [f for f in self.input_dir.iterdir() if f.is_dir()]
        
        if not level1_folders:
            st.warning("⚠️ ไม่พบ subfolder ใน 0-input")
            st.info("💡 กรุณาสร้าง subfolders ที่มีไฟล์ .txt ภายใน 0-input")
            return
        
        # รวบรวม target folders ที่จะตรวจ (รองรับทั้ง flat และ nested)
        target_folders = []
        for level1 in level1_folders:
            # ตรวจสอบว่ามี level 2 folders หรือไม่
            level2_folders = [f for f in level1.iterdir() if f.is_dir()]
            
            if level2_folders:
                # มี nested folders (นักแปล/ชื่อเรื่อง)
                for level2 in level2_folders:
                    display_name = f"{level1.name}/{level2.name}"
                    target_folders.append((display_name, level2, level1.name))
            else:
                # ไม่มี nested, มีไฟล์ .txt โดยตรง
                txt_files = list(level1.glob("*.txt"))
                if txt_files:
                    target_folders.append((level1.name, level1, None))
        
        if not target_folders:
            st.warning("⚠️ ไม่พบไฟล์ .txt ในโฟลเดอร์ใดๆ")
            st.info("💡 กรุณาตรวจสอบว่ามีไฟล์ .txt ในโฟลเดอร์")
            return
        
        st.success(f"✅ พบ {len(target_folders)} โฟลเดอร์ที่มีไฟล์ กำลังประมวลผล...")
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_folders = len(target_folders)
        processed_folders = 0
        
        logger.info(f"Starting multi-folder mode analysis of {total_folders} folders")
        
        for display_name, folder_path, parent_name in target_folders:
            processed_folders += 1
            
            # Update progress
            progress = processed_folders / total_folders
            progress_bar.progress(progress)
            status_text.text(f"กำลังวิเคราะห์: {display_name} ({processed_folders}/{total_folders})")
            
            # หา .txt files ใน folder (recursive ใน subfolder เดียวกัน)
            txt_files = list(folder_path.glob("**/*.txt"))
            
            if not txt_files:
                # บันทึกว่าไม่มีไฟล์
                self.multi_folder_results[display_name] = {
                    'path': folder_path,
                    'parent': parent_name,
                    'files': 0,
                    'errors': [],
                    'total_errors': 0,
                    'stats': {
                        'foreign': 0,
                        'english': 0,
                        'numbers': 0
                    }
                }
                continue
            
            # ⚡ วิเคราะห์ไฟล์แบบขนาน
            folder_errors = []
            total_foreign = 0
            total_english = 0
            total_numbers = 0

            from concurrent.futures import ThreadPoolExecutor as _Pool
            with _Pool(max_workers=min(16, max(4, len(txt_files)))) as pool:
                for file_errors in pool.map(
                    lambda fp: self.file_analyzer.analyze_file_content(
                        fp, check_foreign_languages, check_english, check_numbers, skip_ab_markers=False
                    ),
                    txt_files,
                ):
                    for error in file_errors:
                        flags = error.get('flags', {})
                        total_foreign += int(flags.get('foreign', False) and check_foreign_languages)
                        total_english += int(flags.get('english', False) and check_english)
                        total_numbers += int(flags.get('numbers', False) and check_numbers)
                    folder_errors.extend(file_errors)
            
            # บันทึกผลลัพธ์
            self.multi_folder_results[display_name] = {
                'path': folder_path,
                'parent': parent_name,
                'files': len(txt_files),
                'errors': folder_errors,
                'total_errors': len(folder_errors),
                'stats': {
                    'foreign': total_foreign,
                    'english': total_english,
                    'numbers': total_numbers
                }
            }
            
            logger.info(f"Folder {display_name}: {len(txt_files)} files, {len(folder_errors)} errors")
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("🎉 กระบวนการวิเคราะห์เสร็จสิ้น!")
        
        # Calculate totals
        total_files = sum(r['files'] for r in self.multi_folder_results.values())
        total_errors = sum(r['total_errors'] for r in self.multi_folder_results.values())
        
        logger.info(f"Multi-folder analysis completed. {total_folders} folders, {total_files} files, {total_errors} errors")
        
        # Show summary
        st.success(f"""
        🔍 **การวิเคราะห์หลายโฟลเดอร์เสร็จสิ้น!**
        
        📊 **ผลลัพธ์:**
        - จำนวนโฟลเดอร์ที่วิเคราะห์: **{total_folders}** โฟลเดอร์
        - จำนวนไฟล์ทั้งหมด: **{total_files}** ไฟล์
        - จำนวน errors ทั้งหมด: **{total_errors}** รายการ
        
        💡 **ขั้นตอนต่อไป:** ตรวจสอบผลลัพธ์และกด "บันทึกผลและเปลี่ยนชื่อโฟลเดอร์"
        """)
    
    def export_multiple_folders_errors(self):
        """ส่งออก errors แต่ละโฟลเดอร์และเปลี่ยนชื่อโฟลเดอร์ (รองรับ nested folders)"""
        import streamlit as st
        import os
        
        if not self.multi_folder_results:
            st.warning("⚠️ ไม่มีข้อมูลหลายโฟลเดอร์ให้ส่งออก")
            return
        
        try:
            with st.spinner("กำลังบันทึกผลและเปลี่ยนชื่อโฟลเดอร์..."):
                renamed_count = 0
                saved_count = 0
                skipped_count = 0
                
                for display_name, result in self.multi_folder_results.items():
                    folder_path = result['path']
                    errors = result['errors']
                    error_count = result['total_errors']
                    parent_name = result.get('parent', None)
                    
                    # ตรวจสอบว่าโฟลเดอร์ยังมีอยู่หรือไม่
                    if not folder_path.exists():
                        skipped_count += 1
                        continue
                    
                    # กำหนด prefix ตามจำนวน errors
                    if error_count > 0:
                        prefix = "w "
                    else:
                        prefix = "c "
                    
                    # ตรวจสอบว่าชื่อโฟลเดอร์มี prefix อยู่แล้วหรือไม่
                    current_name = folder_path.name
                    if current_name.startswith("w ") or current_name.startswith("c "):
                        # ลบ prefix เก่าออกก่อน
                        current_name = current_name[2:]
                    
                    new_name = prefix + current_name
                    new_path = folder_path.parent / new_name
                    
                    # เปลี่ยนชื่อโฟลเดอร์
                    if folder_path != new_path:
                        try:
                            os.rename(folder_path, new_path)
                            renamed_count += 1
                            logger.info(f"Renamed: {folder_path} -> {new_path}")
                        except Exception as e:
                            st.warning(f"⚠️ ไม่สามารถเปลี่ยนชื่อโฟลเดอร์ {display_name}: {str(e)}")
                            new_path = folder_path  # ใช้ path เดิมถ้าเปลี่ยนชื่อไม่ได้
                            skipped_count += 1
                    
                    # บันทึกไฟล์ errors-[จำนวน].txt ถ้ามี errors
                    if error_count > 0:
                        error_file_path = new_path / f"errors-{error_count}.txt"
                        
                        try:
                            with open(error_file_path, 'w', encoding='utf-8') as f:
                                f.write(f"# รายการบรรทัดที่ต้องตรวจสอบในโฟลเดอร์: {display_name}\n")
                                f.write(f"# จำนวน errors: {error_count}\n")
                                if parent_name:
                                    f.write(f"# โฟลเดอร์หลัก: {parent_name}\n")
                                f.write("# รูปแบบ: ไฟล์ :: line_number| ข้อความ [ประเภท]\n\n")
                                
                                # จัดกลุ่ม errors ตามไฟล์
                                grouped_errors: Dict[str, List[Dict[str, Any]]] = {}
                                for error in errors:
                                    file_name = error['file_name']
                                    grouped_errors.setdefault(file_name, []).append(error)
                                
                                # เขียน errors แยกตามไฟล์
                                for file_name, file_errors in grouped_errors.items():
                                    f.write(f"## {file_name}\n")
                                    for error in file_errors:
                                        content = error['line_content'].strip()
                                        categories = ', '.join(error.get('categories', []))
                                        category_text = f" [{categories}]" if categories else ""
                                        f.write(f"{error['line_number']}| {content}{category_text}\n")
                                    f.write("\n")
                            
                            saved_count += 1
                            logger.info(f"Saved errors file: {error_file_path}")
                        except Exception as e:
                            st.warning(f"⚠️ ไม่สามารถบันทึกไฟล์ errors ในโฟลเดอร์ {display_name}: {str(e)}")
                            skipped_count += 1
                
                # แสดงผลลัพธ์
                success_msg = f"""
                ✅ **บันทึกและเปลี่ยนชื่อเสร็จสิ้น!**
                
                📊 **สรุป:**
                - โฟลเดอร์ที่เปลี่ยนชื่อ: **{renamed_count}** โฟลเดอร์
                - ไฟล์ errors ที่บันทึก: **{saved_count}** ไฟล์
                """
                
                if skipped_count > 0:
                    success_msg += f"\n- ข้าม/ข้อผิดพลาด: **{skipped_count}** รายการ"
                
                success_msg += """
                
                💡 **คำอธิบาย:**
                - โฟลเดอร์ที่ขึ้นต้นด้วย **w** = พบ errors (warning)
                - โฟลเดอร์ที่ขึ้นต้นด้วย **c** = ไม่พบ errors (clean)
                - รองรับ nested folders (นักแปล/ชื่อเรื่อง/ตอน)
                """
                
                st.success(success_msg)
                st.toast("✅ บันทึกและเปลี่ยนชื่อเสร็จสิ้น!", icon="📁")
                
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
            st.exception(e)
