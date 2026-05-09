import json
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from modules import paths


class PreferencesManager:
    """จัดการ user preferences และบันทึกการตั้งค่าต่างๆ"""

    def __init__(self):
        self.prefs_file = paths.USER_PREFS_FILE
        paths.CONFIG_DIR.mkdir(exist_ok=True)
        self.prefs = self.load_preferences()
    
    def load_preferences(self) -> Dict[str, Any]:
        """โหลด preferences จากไฟล์"""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
                return self.merge_with_defaults(prefs)
            except Exception as e:
                st.error(f"ไม่สามารถโหลดการตั้งค่า: {e}")
                return self.get_default_preferences()
        else:
            return self.get_default_preferences()
    
    def get_default_preferences(self) -> Dict[str, Any]:
        """ค่าเริ่มต้น preferences"""
        return {
            "proofreading_settings": {
                "ab_mode": {
                    "check_foreign_languages": True,
                    "check_numbers": False,
                    "check_english": False,
                    "check_translation_vocab": False,
                    "selected_vocab_file": "",
                    "ignore_patterns": [
                        "【.*?】",
                        "・",
                        "（.*?）",
                        "「.*?」",
                        "『.*?』"
                    ]
                },
                "normal_mode": {
                    "check_foreign_languages": True,
                    "check_numbers": False,
                    "check_english": False,
                    "source_folder": "Clean"
                }
            },
            "file_processing": {
                "merge_settings": {
                    "input_folder_mode": "ใช้โฟลเดอร์แนะนำ",
                    "input_folder_recommended": "Clean (แนะนำ)",
                    "output_folder_mode": "ใช้โฟลเดอร์แนะนำ",
                    "chapters_per_file": 5,
                    "focus_keyword": "###",
                    "title_prefix": "Chapter ",
                    "title_suffix": "",
                    "chapter_padding": 3,
                    "start_number": 1,
                    "end_credit": "จบตอน",
                    "add_chapter_heading": True,
                    "add_filename_separator": False
                },
                "separate_settings": {
                    "focus_keyword": "###",
                    "title_prefix": "Chapter ",
                    "title_suffix": "",
                    "chapter_padding": 3,
                    "start_number": 1,
                    "strip_end_credit": True,
                    "end_credit_text": "จบตอน"
                },
                "generate_settings": {
                    "file_prefix": "Chapter ",
                    "file_suffix": "",
                    "number_padding": 3,
                    "start_number": 1,
                    "batch_size": 10,
                    "add_chapter_title": True,
                    "use_filename_as_title": True,
                    "chapter_title_template": "ระบบเซียนหมื่นพรสวรรค์ ตอนที่ "
                }
            },
            "converter_settings": {
                "source_folder": "Clean (TXT)"
            },
            "clear_settings": {
                "selected_folders": {
                    "Input": True,
                    "Fix": True,
                    "Clean": True,
                    "Merge": False,
                    "Separate": False
                }
            },
            "vocab_settings": {
                "mode": "TXT Mode",
                "tsv_frequency": 2,
                "tsv_include_duplicates": False
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def merge_with_defaults(self, user_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """รวม user preferences กับ default preferences"""
        default_prefs = self.get_default_preferences()
        
        def deep_merge(default: Dict, user: Dict) -> Dict:
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(default_prefs, user_prefs)
    
    def save_preferences(self):
        """บันทึก preferences ลงไฟล์"""
        try:
            self.prefs["last_updated"] = datetime.now().isoformat()
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"ไม่สามารถบันทึกการตั้งค่า: {e}")
    
    def get_setting(self, category: str, key: str, default: Any = None) -> Any:
        """ดึงค่าการตั้งค่าจาก preferences"""
        try:
            category_dict = self.prefs.get(category, {})
            return category_dict.get(key, default)
        except:
            return default
    
    def set_setting(self, category: str, key: str, value: Any):
        """ตั้งค่าการตั้งค่าใน preferences"""
        if category not in self.prefs:
            self.prefs[category] = {}
        self.prefs[category][key] = value
    
    def get_checkbox_setting(self, category: str, key: str, default: bool = False) -> bool:
        """ดึงค่าการตั้งค่า checkbox"""
        return self.get_setting(category, key, default)
    
    def set_checkbox_setting(self, category: str, key: str, value: bool):
        """ตั้งค่าการตั้งค่า checkbox"""
        self.set_setting(category, key, value)
    
    def get_text_setting(self, category: str, key: str, default: str = "") -> str:
        """ดึงค่าการตั้งค่า text"""
        return self.get_setting(category, key, default)
    
    def set_text_setting(self, category: str, key: str, value: str):
        """ตั้งค่าการตั้งค่า text"""
        self.set_setting(category, key, value)
    
    def get_number_setting(self, category: str, key: str, default: int = 0) -> int:
        """ดึงค่าการตั้งค่า number"""
        return self.get_setting(category, key, default)
    
    def set_number_setting(self, category: str, key: str, value: int):
        """ตั้งค่าการตั้งค่า number"""
        self.set_setting(category, key, value)
    
    def get_selectbox_setting(self, category: str, key: str, default: str = "") -> str:
        """ดึงค่าการตั้งค่า selectbox"""
        return self.get_setting(category, key, default)
    
    def set_selectbox_setting(self, category: str, key: str, value: str):
        """ตั้งค่าการตั้งค่า selectbox"""
        self.set_setting(category, key, value)
    
    def reset_to_defaults(self):
        """รีเซ็ตการตั้งค่าเป็นค่าเริ่มต้น"""
        self.prefs = self.get_default_preferences()
        self.save_preferences()
        st.success("✅ รีเซ็ตการตั้งค่าเป็นค่าเริ่มต้นแล้ว!")
        st.rerun()
    
    def export_preferences(self) -> str:
        """ส่งออก preferences เป็น JSON string"""
        try:
            return json.dumps(self.prefs, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"ไม่สามารถส่งออกการตั้งค่า: {e}")
            return ""
    
    def import_preferences(self, json_string: str):
        """นำเข้า preferences จาก JSON string"""
        try:
            imported_prefs = json.loads(json_string)
            self.prefs = self.merge_with_defaults(imported_prefs)
            self.save_preferences()
            st.success("✅ นำเข้าการตั้งค่าสำเร็จ!")
            st.rerun()
        except Exception as e:
            st.error(f"ไม่สามารถนำเข้าการตั้งค่า: {e}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """ดึงการตั้งค่าทั้งหมด"""
        return self.prefs.copy()
    
    def log_usage(self, action: str, details: Dict[str, Any]):
        """บันทึก usage logs"""
        if "usage_logs" not in self.prefs:
            self.prefs["usage_logs"] = []
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        
        self.prefs["usage_logs"].append(log_entry)
        
        # เก็บแค่ 100 entries ล่าสุด
        if len(self.prefs["usage_logs"]) > 100:
            self.prefs["usage_logs"] = self.prefs["usage_logs"][-100:]
        
        self.save_preferences()


# Global instance
preferences_manager = PreferencesManager()
