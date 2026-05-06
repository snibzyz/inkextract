import csv
import streamlit as st
from pathlib import Path
from typing import List, Dict, Tuple, Iterable, Optional
from collections import Counter, defaultdict
import pandas as pd
import re
import os
import io

from modules import paths

# 🔑 รองรับทุก separator ในไฟล์เดียวกัน:
#   CN\tTH        → split ที่ TAB
#   CN | TH       → split ที่ ` | ` (มี/ไม่มี whitespace)
#   CN|TH         → split ที่ `|`
#   CN|TH|NOTE    → split ทุก `|` ได้พร้อมกัน
# regex ครอบทั้งหมดในครั้งเดียว → ไม่ต้องเดา delimiter ต่อไฟล์อีก
_VOCAB_DELIM_RE = re.compile(r'\t|\s*\|\s*')
_HEADER_VALUES = {'cn', 'chinese', '中文', 'th', 'thai', 'ไทย'}


def _split_vocab_line(line: str) -> List[str]:
    """แยก line เป็นคอลัมน์ — รองรับ TAB, |, ` | ` ผสมกันในไฟล์เดียวก็ได้"""
    if not line:
        return []
    parts = [p.strip() for p in _VOCAB_DELIM_RE.split(line)]
    # ตัด trailing empty คอลัมน์ออก แต่เก็บ empty คอลัมน์กลางไว้ (กัน schema เพี้ยน)
    while parts and parts[-1] == '':
        parts.pop()
    return parts


def parse_vocab_text(content: str, source_file: str = '') -> List[Dict]:
    """parse ข้อความ vocab รวมทุก format → list ของ dict
    แต่ละ dict มี keys: cn, th, columns (list[str]), source_file
    `columns` เก็บคอลัมน์ทั้งหมดตามต้นฉบับ — ทำให้ NOTE/extra columns ไม่หายเวลา export
    """
    if not content:
        return []

    # ลองตัดสินใจว่าบรรทัดแรกเป็น header หรือไม่ จากค่าคอลัมน์ที่ 1
    lines = content.splitlines()
    if not lines:
        return []

    records: List[Dict] = []
    first = True
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        cols = _split_vocab_line(line)
        if len(cols) < 2:
            continue

        cn, th = cols[0], cols[1]

        # ข้าม header (ตรวจครั้งเดียวที่บรรทัดแรกที่มีข้อมูล)
        if first:
            first = False
            if cn.lower() in _HEADER_VALUES:
                continue

        if not cn or not th:
            continue

        records.append({
            'cn': cn,
            'th': th,
            'columns': cols,
            'source_file': source_file,
        })

    return records


class VocabProcessor:
    def __init__(self):
        self.base_dir = paths.ROOT
        self.output_dir = paths.OUTPUT_DIR
        paths.ensure_dirs()

    # ===== Unified entry point =====
    def parse_uploaded_files(self, uploaded_files) -> List[Dict]:
        """อ่านทุกไฟล์ที่ผู้ใช้อัปโหลด — รองรับทุก format ในชุดเดียว

        Excel (.xlsx) อ่านด้วย pandas (รักษา header detection เดิม)
        ไฟล์ข้อความ (.txt/.tsv/.csv) parse ด้วย parse_vocab_text เพื่อให้
        delimiter ผสมกันได้
        """
        all_records: List[Dict] = []
        total_files = len(uploaded_files)

        if total_files > 1:
            progress_bar = st.progress(0)
            status_text = st.empty()

        for idx, uploaded_file in enumerate(uploaded_files):
            try:
                if total_files > 1:
                    progress_bar.progress((idx + 1) / total_files)
                    status_text.text(f"กำลังอ่านไฟล์ {idx + 1}/{total_files}: {uploaded_file.name}")

                ext = uploaded_file.name.lower().rsplit('.', 1)[-1]
                if ext == 'xlsx':
                    all_records.extend(self._parse_xlsx(uploaded_file))
                else:
                    uploaded_file.seek(0)
                    content = uploaded_file.read().decode('utf-8', errors='replace')
                    all_records.extend(parse_vocab_text(content, uploaded_file.name))
            except Exception as e:
                st.error(f"ไม่สามารถอ่านไฟล์ {uploaded_file.name}: {e}")

        if total_files > 1:
            progress_bar.empty()
            status_text.empty()

        return all_records

    @staticmethod
    def _parse_xlsx(uploaded_file) -> List[Dict]:
        """อ่าน Excel — เก็บทุกคอลัมน์ ไม่ตัดเหลือแค่ A,B"""
        uploaded_file.seek(0)
        df = pd.read_excel(
            uploaded_file,
            engine='openpyxl',
            header=None,
            dtype=str,
            na_filter=False,
        )
        if df.empty:
            return []

        # ตัด header ออกถ้าเซลล์แรกตรงกับ header values
        first_val = str(df.iat[0, 0]).strip().lower() if len(df) > 0 else ''
        if first_val in _HEADER_VALUES:
            df = df.iloc[1:]

        records: List[Dict] = []
        # vectorized: เปลี่ยนเป็น list-of-list ทีเดียว
        rows = df.astype(str).values.tolist()
        name = uploaded_file.name
        for row in rows:
            cols = [c.strip() for c in row if c.strip() and c.strip().lower() != 'nan']
            if len(cols) < 2:
                continue
            records.append({
                'cn': cols[0],
                'th': cols[1],
                'columns': cols,
                'source_file': name,
            })
        return records

    # ===== Backward-compat wrappers =====
    def read_csv_files(self, uploaded_files) -> List[Dict]:
        """wrapper สำหรับโค้ดเก่า — เรียก unified parser"""
        return self.parse_uploaded_files(uploaded_files)

    def read_txt_files(self, uploaded_files) -> List[str]:
        """wrapper เก่า: คืน list ของบรรทัด format `中文 | Thai | Description`"""
        records = self.parse_uploaded_files(uploaded_files)
        return [' | '.join(r['columns']) for r in records]

    @staticmethod
    def _row_columns(item: Dict) -> List[str]:
        """ดึง full row (ทุกคอลัมน์) ออกมา — รับมาจาก columns ถ้ามี ไม่งั้นใช้ cn,th"""
        cols = item.get('columns')
        if cols:
            return list(cols)
        return [item.get('cn', ''), item.get('th', '')]

    def _write_tsv(self, output_file: Path, rows: List[List[str]], header: bool = False) -> None:
        """เขียน TSV — รักษา N คอลัมน์ตามต้นฉบับ (CN/TH/NOTE/...)"""
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            if header:
                writer.writerow(['CN', 'TH'])
            writer.writerows(rows)

    def sort_vocab_by_length(self, vocab_list: List[Dict[str, str]], group_duplicates: bool = True) -> List[Dict[str, str]]:
        """เรียงคำศัพท์จากยาว→สั้น (vectorized ด้วย pandas)"""
        if not vocab_list:
            return []

        if not group_duplicates:
            return sorted(vocab_list, key=lambda x: len(x.get('cn', '')), reverse=True)

        # ⚡ Vectorized: ใช้ pandas สำหรับงาน group + sort ก้อนใหญ่
        df = pd.DataFrame({
            'idx': range(len(vocab_list)),
            'cn': [it.get('cn', '') for it in vocab_list],
            'th': [it.get('th', '') for it in vocab_list],
        })
        df['cn_len'] = df['cn'].str.len()
        # เรียงกลุ่ม (cn,th) ตามความยาว cn จากมาก→น้อย แล้วในกลุ่มเรียงตาม idx เดิม
        df = df.sort_values(['cn_len', 'cn', 'th', 'idx'], ascending=[False, True, True, True])
        order = df['idx'].tolist()
        return [vocab_list[i] for i in order]

    def create_sort_vocab_output(self, vocab_list: List[Dict[str, str]], group_duplicates: bool = True) -> str:
        """สร้าง sort_vocab.tsv — เก็บคอลัมน์ครบ (CN/TH/NOTE)"""
        output_file = self.output_dir / "sort_vocab.txt"
        sorted_vocab = self.sort_vocab_by_length(vocab_list, group_duplicates)
        self._write_tsv(output_file, [self._row_columns(it) for it in sorted_vocab], header=False)
        return str(output_file)

    # ===== คำซ้ำเป๊ะ vs คำขัดแย้ง — เพิ่มเข้ามาใน redesign 2026-05-06 =====

    def dedupe_by_pair(self, vocab_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """ตัดคำซ้ำเป๊ะ (CN+TH ตรงกัน) — เก็บอันแรกของคู่ละ 1 บรรทัด"""
        seen = set()
        out: List[Dict[str, str]] = []
        for it in vocab_list:
            key = (it.get('cn', ''), it.get('th', ''))
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    def create_unique_sorted_output(self, vocab_list: List[Dict[str, str]]) -> str:
        """ตัดซ้ำ (CN+TH) + เรียงยาว→สั้น → sorted_unique.tsv"""
        output_file = self.output_dir / "sorted_unique.txt"
        unique = self.dedupe_by_pair(vocab_list)
        sorted_vocab = sorted(unique, key=lambda x: len(x.get('cn', '')), reverse=True)
        self._write_tsv(output_file, [self._row_columns(it) for it in sorted_vocab], header=False)
        return str(output_file)

    def find_exact_duplicates(self, vocab_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """คืน entries ที่ (CN,TH) ซ้ำตั้งแต่ 2 ครั้งขึ้นไป — รวมทุก instance"""
        freq = Counter((it.get('cn', ''), it.get('th', '')) for it in vocab_list)
        dup_keys = {k for k, c in freq.items() if c > 1}
        return [it for it in vocab_list if (it.get('cn', ''), it.get('th', '')) in dup_keys]

    def create_exact_duplicates_output(self, vocab_list: List[Dict[str, str]]) -> str:
        """รายการคำซ้ำเป๊ะทั้งหมด → exact_duplicates.tsv (กลุ่ม CN+TH ติดกัน)"""
        output_file = self.output_dir / "exact_duplicates.txt"
        dups = self.find_exact_duplicates(vocab_list)
        # group แบบ CN+TH ติดกัน เรียงกลุ่มที่ซ้ำเยอะอยู่ก่อน
        groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        for it in dups:
            groups[(it['cn'], it['th'])].append(it)
        ordered = sorted(groups.values(), key=lambda g: len(g), reverse=True)
        rows = [self._row_columns(it) for grp in ordered for it in grp]
        self._write_tsv(output_file, rows, header=False)
        return str(output_file)

    def find_conflicting_translations(self, vocab_list: List[Dict[str, str]]) -> Dict[str, List[Dict]]:
        """หา CN ที่มีคำแปล TH หลายแบบ → {cn: [entries...]} (เฉพาะกลุ่มที่ TH > 1 แบบ)"""
        cn_groups: Dict[str, List[Dict]] = defaultdict(list)
        for it in vocab_list:
            cn_groups[it.get('cn', '')].append(it)
        return {
            cn: items for cn, items in cn_groups.items()
            if len({it.get('th', '') for it in items}) > 1
        }

    def create_conflicts_output(self, vocab_list: List[Dict[str, str]]) -> str:
        """รายการคำที่ CN ตรง แต่ TH ต่าง → conflicts.tsv (กลุ่ม CN ติดกัน)"""
        output_file = self.output_dir / "conflicts.txt"
        conflicts = self.find_conflicting_translations(vocab_list)
        # เรียงกลุ่มที่มีคำแปลต่างกันมากสุดอยู่ก่อน
        ordered = sorted(
            conflicts.items(),
            key=lambda kv: len({it['th'] for it in kv[1]}),
            reverse=True,
        )
        rows: List[List[str]] = []
        for cn, items in ordered:
            for it in sorted(items, key=lambda x: x.get('th', '')):
                rows.append(self._row_columns(it))
        self._write_tsv(output_file, rows, header=False)
        return str(output_file)

    # ===== Pipeline composer (filter → sort → output) =====

    def apply_pipeline(
        self,
        vocab_list: List[Dict[str, str]],
        *,
        # === content filters ===
        dedupe_pairs: bool = False,
        only_conflicts: bool = False,
        only_exact_duplicates: bool = False,
        # === range filters ===
        min_frequency: int = 1,
        max_frequency: Optional[int] = None,
        min_cn_length: int = 1,
        max_cn_length: Optional[int] = None,
        # === text/source filters ===
        search_text: str = "",
        source_files: Optional[Iterable[str]] = None,
        # === post-sort limit ===
        limit: int = 0,
        # === sort ===
        sort_by: str = "length_desc",
    ) -> List[Dict[str, str]]:
        """ประกอบ pipeline แบบยืดหยุ่น — ทุก filter ทำงานต่อเนื่อง (AND)

        ลำดับการทำงาน:
            1. กรองตาม source_files (ถ้ามีหลายไฟล์)
            2. กรองตาม CN length (min/max)
            3. กรองตาม search_text (substring ใน cn หรือ th)
            4. กรองคำขัดแย้ง / คำซ้ำเป๊ะ (เลือกได้)
            5. กรองความถี่ (min/max)
            6. ตัดคำซ้ำ (CN+TH)
            7. เรียง (sort_by)
            8. ตัดให้เหลือ limit บรรทัดแรก
        """
        if not vocab_list:
            return []

        # snapshot ความถี่จากข้อมูลต้นฉบับ — ใช้สำหรับ frequency sort
        original_freq = self.get_vocab_frequency(vocab_list)
        result = list(vocab_list)

        # ===== FILTERS =====
        if source_files:
            allowed = set(source_files)
            result = [it for it in result if it.get('source_file', '') in allowed]

        if min_cn_length > 1:
            result = [it for it in result if len(it.get('cn', '')) >= min_cn_length]
        if max_cn_length is not None and max_cn_length > 0:
            result = [it for it in result if len(it.get('cn', '')) <= max_cn_length]

        if search_text:
            s = search_text.lower().strip()
            if s:
                result = [
                    it for it in result
                    if s in it.get('cn', '').lower() or s in it.get('th', '').lower()
                ]

        if only_conflicts:
            conflict_cns = set(self.find_conflicting_translations(result).keys())
            result = [it for it in result if it.get('cn', '') in conflict_cns]

        if only_exact_duplicates:
            result = self.find_exact_duplicates(result)

        if min_frequency > 1 or (max_frequency is not None and max_frequency > 0):
            freq = self.get_vocab_frequency(result)
            lo = max(1, min_frequency)
            hi = max_frequency if (max_frequency is not None and max_frequency > 0) else float('inf')
            valid = {k for k, c in freq.items() if lo <= c <= hi}
            result = [it for it in result if (it.get('cn', ''), it.get('th', '')) in valid]

        if dedupe_pairs:
            result = self.dedupe_by_pair(result)

        # ===== SORT =====
        if sort_by == "length_desc":
            result = sorted(result, key=lambda x: len(x.get('cn', '')), reverse=True)
        elif sort_by == "length_asc":
            result = sorted(result, key=lambda x: len(x.get('cn', '')))
        elif sort_by == "prefix":
            result = self.sort_by_prefix_or_suffix(result, "prefix")
        elif sort_by == "suffix":
            result = self.sort_by_prefix_or_suffix(result, "suffix")
        elif sort_by == "frequency_desc":
            result = sorted(
                result,
                key=lambda x: original_freq.get((x.get('cn', ''), x.get('th', '')), 0),
                reverse=True,
            )
        elif sort_by == "frequency_asc":
            result = sorted(
                result,
                key=lambda x: original_freq.get((x.get('cn', ''), x.get('th', '')), 0),
            )
        elif sort_by == "group_by_cn":
            # จัดกลุ่ม CN ซ้ำให้ติดกัน — กลุ่มที่มีคนเยอะอยู่ก่อน
            cn_groups: Dict[str, List[Dict]] = defaultdict(list)
            for it in result:
                cn_groups[it.get('cn', '')].append(it)
            ordered = sorted(cn_groups.values(), key=lambda g: len(g), reverse=True)
            result = [it for g in ordered for it in g]
        elif sort_by == "alpha_cn":
            result = sorted(result, key=lambda x: x.get('cn', ''))
        elif sort_by == "alpha_th":
            result = sorted(result, key=lambda x: x.get('th', ''))
        # else "none": ไม่เรียง

        # ===== LIMIT (post-sort) =====
        if limit and limit > 0:
            result = result[:limit]

        return result

    def create_pipeline_output(
        self,
        vocab_list: List[Dict[str, str]],
        filename: str = "vocab_pipeline.txt",
        **opts,
    ) -> str:
        """รัน pipeline + เขียนไฟล์"""
        output = self.output_dir / filename
        result = self.apply_pipeline(vocab_list, **opts)
        self._write_tsv(output, [self._row_columns(it) for it in result], header=False)
        return str(output)

    def get_enhanced_statistics(self, vocab_list: List[Dict[str, str]]) -> Dict:
        """สถิติครอบคลุม — แยกชัด: คู่ซ้ำเป๊ะ vs CN ขัดแย้ง"""
        total = len(vocab_list)
        if total == 0:
            return {
                'total': 0, 'unique_pairs': 0, 'duplicate_entries': 0,
                'unique_cn': 0, 'conflict_cn_count': 0, 'conflict_entries': 0,
                'most_common_pair': None, 'frequency_distribution': {}, 'frequency_map': {},
            }

        pair_freq = Counter((it.get('cn', ''), it.get('th', '')) for it in vocab_list)
        unique_pairs = len(pair_freq)
        duplicate_entries = total - unique_pairs

        cn_to_ths: Dict[str, set] = defaultdict(set)
        for it in vocab_list:
            cn_to_ths[it.get('cn', '')].add(it.get('th', ''))
        unique_cn = len(cn_to_ths)
        conflict_cns = [cn for cn, ths in cn_to_ths.items() if len(ths) > 1]
        conflict_cn_count = len(conflict_cns)
        conflict_set = set(conflict_cns)
        conflict_entries = sum(1 for it in vocab_list if it.get('cn', '') in conflict_set)

        most_common_pair = max(pair_freq.items(), key=lambda x: x[1])

        return {
            'total': total,
            'unique_pairs': unique_pairs,
            'duplicate_entries': duplicate_entries,
            'unique_cn': unique_cn,
            'conflict_cn_count': conflict_cn_count,
            'conflict_entries': conflict_entries,
            'most_common_pair': most_common_pair,
            'frequency_distribution': dict(Counter(pair_freq.values())),
            'frequency_map': dict(pair_freq),
        }

    def get_vocab_frequency(self, vocab_list: List[Dict[str, str]]) -> Dict[Tuple[str, str], int]:
        """นับความถี่ — Counter หนึ่งเดียว, O(n)"""
        if not vocab_list:
            return {}
        return dict(Counter((it['cn'], it['th']) for it in vocab_list))

    def filter_vocab_by_frequency(self, vocab_list: List[Dict[str, str]],
                                 min_frequency: int = 2,
                                 include_duplicates: bool = True,
                                 vocab_freq: Dict[Tuple[str, str], int] = None) -> List[Dict[str, str]]:
        """กรองตามความถี่ — vectorized"""
        if vocab_freq is None:
            vocab_freq = self.get_vocab_frequency(vocab_list)

        # หา keys ที่ผ่านเกณฑ์
        valid_keys = {k for k, freq in vocab_freq.items() if freq >= min_frequency}
        if not valid_keys:
            return []

        if include_duplicates:
            # คงทุก instance เดิม (รวม columns/extra) — แค่กรอง
            filtered = [it for it in vocab_list if (it['cn'], it['th']) in valid_keys]
        else:
            # เก็บ instance แรกของแต่ละคู่ (รักษา columns ของไฟล์ต้นฉบับ)
            seen = set()
            filtered = []
            for it in vocab_list:
                key = (it['cn'], it['th'])
                if key in valid_keys and key not in seen:
                    seen.add(key)
                    filtered.append(it)

        return self.sort_vocab_by_length(filtered)

    def create_filter_vocab_output(self, vocab_list: List[Dict[str, str]],
                                  min_frequency: int = 2,
                                  include_duplicates: bool = True,
                                  vocab_freq: Dict[Tuple[str, str], int] = None) -> str:
        output_file = self.output_dir / "filter_vocab.txt"
        filtered_vocab = self.filter_vocab_by_frequency(vocab_list, min_frequency, include_duplicates, vocab_freq)
        self._write_tsv(output_file, [self._row_columns(it) for it in filtered_vocab], header=False)
        return str(output_file)
    
    def get_vocab_statistics(self, vocab_list: List[Dict[str, str]]) -> Dict:
        """ดูสถิติคำศัพท์ - ส่งคืน full frequency map ด้วย"""
        vocab_freq = self.get_vocab_frequency(vocab_list)
        
        total_entries = len(vocab_list)
        unique_entries = len(vocab_freq)
        duplicates = total_entries - unique_entries
        
        # หาคำที่ซ้ำมากที่สุด
        most_common = max(vocab_freq.items(), key=lambda x: x[1]) if vocab_freq else None
        
        # แจกแจงตามความถี่
        freq_distribution = Counter(vocab_freq.values())
        
        return {
            'total_entries': total_entries,
            'unique_entries': unique_entries,
            'duplicates': duplicates,
            'most_common': most_common,
            'frequency_distribution': dict(freq_distribution),
            'frequency_map': vocab_freq  # เพิ่ม field นี้เพื่อ cache ไว้ใช้ต่อ
        }
    
    def preview_vocab(self, vocab_list: List[Dict[str, str]], limit: int = 10) -> pd.DataFrame:
        """แสดงตัวอย่างคำศัพท์"""
        preview_data = vocab_list[:limit]
        df = pd.DataFrame(preview_data)
        return df
    
    # ===== TXT Mode Functions =====
    
    def count_chinese_characters(self, text: str) -> int:
        """นับจำนวนตัวอักษรจีนในข้อความ"""
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        return len(chinese_pattern.findall(text))
    
    def extract_chinese_part(self, line: str) -> str:
        """แยกส่วนภาษาจีนออกจากบรรทัด"""
        # รูปแบบ: 中文 | Thai | Description
        parts = line.split(' | ', 2)
        if len(parts) >= 1:
            return parts[0].strip()
        return ""
    
    def is_chinese_line(self, line: str) -> bool:
        """ตรวจสอบว่าบรรทัดนี้มีข้อมูลภาษาจีนหรือไม่"""
        line = line.strip()
        return line and '|' in line and not line.startswith('#')
    
    def remove_txt_duplicates(self, data: List[str]) -> List[str]:
        """ลบคำที่ซ้ำกันออก เหลือแค่คำเดียว"""
        seen_chinese = set()
        unique_lines = []
        
        for line in data:
            chinese_part = self.extract_chinese_part(line)
            if chinese_part and chinese_part not in seen_chinese:
                seen_chinese.add(chinese_part)
                unique_lines.append(line)
        
        return unique_lines
    
    def sort_txt_by_chinese_length(self, data: List[str]) -> List[str]:
        """จัดเรียงข้อมูลตามความยาวของตัวอักษรจีน (ยาวไปสั้น)"""
        def get_chinese_length(line):
            chinese_part = self.extract_chinese_part(line)
            return self.count_chinese_characters(chinese_part)
        
        return sorted(data, key=get_chinese_length, reverse=True)
    
    def create_txt_sorted_output(self, txt_lines: List[str]) -> str:
        """สร้างไฟล์ sorted_chinese.txt"""
        output_file = self.output_dir / "sorted_chinese.txt"
        
        # ลบคำที่ซ้ำกันออก
        unique_lines = self.remove_txt_duplicates(txt_lines)
        
        # จัดเรียงตามความยาวของข้อความภาษาจีน
        final_sorted = self.sort_txt_by_chinese_length(unique_lines)
        
        # เขียนไฟล์
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in final_sorted:
                f.write(line + "\n")
        
        return str(output_file)
    
    def get_txt_statistics(self, txt_lines: List[str]) -> Dict:
        """ดูสถิติข้อมูล TXT"""
        unique_lines = self.remove_txt_duplicates(txt_lines)
        
        # หาคำที่ยาวที่สุด
        longest_lines = sorted(unique_lines, 
                             key=lambda x: self.count_chinese_characters(self.extract_chinese_part(x)), 
                             reverse=True)[:5]
        
        longest_words = []
        for line in longest_lines:
            chinese_part = self.extract_chinese_part(line)
            char_count = self.count_chinese_characters(chinese_part)
            longest_words.append({'chinese': chinese_part, 'length': char_count, 'full_line': line})
        
        return {
            'total_lines': len(txt_lines),
            'unique_lines': len(unique_lines),
            'duplicates': len(txt_lines) - len(unique_lines),
            'longest_words': longest_words
        }
    
    def preview_txt_data(self, txt_lines: List[str], limit: int = 10) -> pd.DataFrame:
        """แสดงตัวอย่างข้อมูล TXT"""
        preview_data = []
        for line in txt_lines[:limit]:
            chinese_part = self.extract_chinese_part(line)
            char_count = self.count_chinese_characters(chinese_part)
            preview_data.append({
                'Chinese': chinese_part,
                'Length': char_count,
                'Full Line': line
            })
        
        return pd.DataFrame(preview_data)
    
    # ===== Prefix/Suffix Sorting Functions (เรียงตามอักษรหน้า/ท้าย) =====
    
    def sort_by_prefix_or_suffix(self, vocab_list: List[Dict[str, str]],
                                 sort_by: str = "suffix") -> List[Dict[str, str]]:
        """เรียงตามอักษรหน้า/ท้าย — O(n log n) แทนที่จะ O(n²)

        วิธีคิด: หลังจาก sort lex แล้ว คำที่มี common prefix/suffix อยู่ติดกัน
        แค่ scan ผ่านครั้งเดียว สะสมเป็นกลุ่มเมื่อ startswith กับ anchor (คำที่สั้นที่สุดในกลุ่ม)
        """
        if not vocab_list:
            return []

        # เตรียม key สำหรับ sort
        if sort_by == "prefix":
            keyed = [(it['cn'], it) for it in vocab_list]
        else:
            keyed = [(it['cn'][::-1], it) for it in vocab_list]

        # sort lex — O(n log n)
        keyed.sort(key=lambda x: x[0])

        # group ตาม common prefix (anchor = ตัวที่สั้นสุดในกลุ่ม)
        groups: List[List[Tuple[str, Dict]]] = []
        if keyed:
            current = [keyed[0]]
            anchor = keyed[0][0]
            for k, it in keyed[1:]:
                if k.startswith(anchor) or anchor.startswith(k):
                    current.append((k, it))
                    if len(k) < len(anchor):
                        anchor = k
                else:
                    groups.append(current)
                    current = [(k, it)]
                    anchor = k
            groups.append(current)

        # เรียงในกลุ่มตามความยาว CN (ยาว→สั้น), เรียงระหว่างกลุ่มตามจำนวน (มาก→น้อย)
        for g in groups:
            g.sort(key=lambda kv: len(kv[1].get('cn', '')), reverse=True)
        groups.sort(key=lambda g: len(g), reverse=True)

        return [kv[1] for g in groups for kv in g]

    def create_prefix_suffix_sorted_output(self, vocab_list: List[Dict[str, str]],
                                          sort_by: str = "suffix") -> str:
        """สร้างไฟล์ prefix/suffix sorted — เก็บคอลัมน์ครบ"""
        output_file = self.output_dir / (
            "prefix_sorted_vocab.txt" if sort_by == "prefix" else "suffix_sorted_vocab.txt"
        )
        sorted_vocab = self.sort_by_prefix_or_suffix(vocab_list, sort_by)
        self._write_tsv(output_file, [self._row_columns(it) for it in sorted_vocab], header=False)
        return str(output_file)
    
    def get_prefix_suffix_statistics(self, vocab_list: List[Dict[str, str]], 
                                    sort_by: str = "suffix",
                                    min_length: int = 2) -> Dict:
        """ดูสถิติการจัดกลุ่มตาม prefix หรือ suffix"""
        sorted_vocab = self.sort_by_prefix_or_suffix(vocab_list, sort_by)
        
        # นับกลุ่ม
        groups = {}
        for item in sorted_vocab:
            cn = item['cn']
            if sort_by == "prefix":
                # หาคำที่ขึ้นต้นเหมือนกัน
                if len(cn) >= min_length:
                    key = cn[:min_length]  # เอาอักษรหน้า
                else:
                    key = cn
            else:
                # หาคำที่ลงท้ายเหมือนกัน
                if len(cn) >= min_length:
                    key = cn[-min_length:]  # เอาอักษรท้าย
                else:
                    key = cn
            
            if key not in groups:
                groups[key] = []
            groups[key].append(cn)
        
        # หากลุ่มที่มีคำมากกว่า 1 คำ
        filtered_groups = {k: v for k, v in groups.items() if len(v) > 1}
        
        # หากลุ่มที่ใหญ่ที่สุด
        top_groups = sorted(filtered_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        
        return {
            'total_groups': len(filtered_groups),
            'top_groups': top_groups,
            'total_grouped_words': sum(len(words) for words in filtered_groups.values())
        }
    
    # ===== Duplicate Check Mode Functions (โหมดตรวจคำซ้ำ) =====
    
    def create_duplicate_check_output(self, vocab_list: List[Dict[str, str]]) -> str:
        """
        สร้างไฟล์สำหรับโหมดตรวจคำซ้ำ
        จัดเรียงคำที่มี CN ซ้ำกันให้อยู่ติดกัน โดยไม่เว้นบรรทัด
        
        เช่น:
        圣者	ปราชญ์
        圣者	ปราชญ์
        圣者	นักบุญ
        破军	ก
        破军	ข
        者	เจ๋อ
        圣	ศักดิ์สิทธิ์
        
        Returns:
            str: path ของไฟล์ที่สร้าง
        """
        output_file = self.output_dir / "duplicate_check.txt"
        
        # ใช้ defaultdict เพื่อความเร็ว
        cn_frequency = defaultdict(list)
        for item in vocab_list:
            cn_frequency[item['cn']].append(item)
        
        # แยกคำที่ซ้ำและไม่ซ้ำ - ใช้ list comprehension
        duplicate_groups = [
            sorted(items, key=lambda x: x['th'])
            for items in cn_frequency.values()
            if len(items) > 1
        ]
        
        unique_words = [
            items[0]
            for items in cn_frequency.values()
            if len(items) == 1
        ]
        
        # เรียงกลุ่มคำซ้ำตามจำนวนคำ (กลุ่มที่มีคำเยอะอยู่ก่อน)
        duplicate_groups.sort(key=lambda group: len(group), reverse=True)
        
        # เรียงคำที่ไม่ซ้ำตาม CN
        unique_words.sort(key=lambda x: x['cn'])
        
        rows: List[List[str]] = []
        for group in duplicate_groups:
            rows.extend(self._row_columns(it) for it in group)
        if unique_words:
            rows.extend(self._row_columns(it) for it in unique_words)
        self._write_tsv(output_file, rows, header=False)

        return str(output_file)
    
    def get_duplicate_check_statistics(self, vocab_list: List[Dict[str, str]]) -> Dict:
        """ดูสถิติสำหรับโหมดตรวจคำซ้ำ"""
        # นับความถี่ของคำ CN
        cn_frequency = {}
        for item in vocab_list:
            cn = item['cn']
            if cn not in cn_frequency:
                cn_frequency[cn] = []
            cn_frequency[cn].append(item)
        
        # แยกคำที่ซ้ำและไม่ซ้ำ
        duplicate_words = []
        unique_words = []
        
        for cn, items in cn_frequency.items():
            if len(items) > 1:
                duplicate_words.extend(items)
            else:
                unique_words.extend(items)
        
        # หาคำที่ซ้ำมากที่สุด
        max_duplicates = 0
        most_duplicated_cn = ""
        for cn, items in cn_frequency.items():
            if len(items) > max_duplicates:
                max_duplicates = len(items)
                most_duplicated_cn = cn
        
        # แจกแจงจำนวนคำในแต่ละกลุ่มซ้ำ
        duplicate_groups_count = {}
        for cn, items in cn_frequency.items():
            if len(items) > 1:
                group_size = len(items)
                if group_size not in duplicate_groups_count:
                    duplicate_groups_count[group_size] = 0
                duplicate_groups_count[group_size] += 1
        
        return {
            'total_entries': len(vocab_list),
            'unique_cn_words': len(cn_frequency),
            'duplicate_entries': len(duplicate_words),
            'unique_entries': len(unique_words),
            'duplicate_groups': len([cn for cn, items in cn_frequency.items() if len(items) > 1]),
            'most_duplicated': {
                'cn': most_duplicated_cn,
                'count': max_duplicates,
                'translations': [item['th'] for item in cn_frequency.get(most_duplicated_cn, [])]
            },
            'duplicate_groups_distribution': duplicate_groups_count
        }