"""ทดสอบ preferences_manager — load/save/get/set"""
import sys
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# patch paths.USER_PREFS_FILE สำหรับการ test
from modules import paths  # noqa: E402

# import ทีหลังเพราะ PreferencesManager() อ่านไฟล์ตอน init
from modules.preferences_manager import PreferencesManager  # noqa: E402


def test_default_preferences_have_expected_keys():
    pm = PreferencesManager()
    defaults = pm.get_default_preferences()
    assert 'proofreading_settings' in defaults
    assert 'file_processing' in defaults
    assert 'vocab_settings' in defaults


def test_get_setting_returns_default_for_missing():
    pm = PreferencesManager()
    val = pm.get_setting('nonexistent_category', 'nonexistent_key', default='fallback')
    assert val == 'fallback'


def test_set_and_get_setting_roundtrip():
    pm = PreferencesManager()
    pm.set_setting('test_category', 'test_key', 'test_value')
    assert pm.get_setting('test_category', 'test_key') == 'test_value'


def test_set_setting_creates_category():
    pm = PreferencesManager()
    pm.set_setting('brand_new_cat_xyz', 'k', 1)
    assert pm.get_setting('brand_new_cat_xyz', 'k') == 1


def test_checkbox_setting_helpers():
    pm = PreferencesManager()
    pm.set_checkbox_setting('test', 'a_flag', True)
    assert pm.get_checkbox_setting('test', 'a_flag') is True
    pm.set_checkbox_setting('test', 'a_flag', False)
    assert pm.get_checkbox_setting('test', 'a_flag') is False


def test_text_setting_helpers():
    pm = PreferencesManager()
    pm.set_text_setting('test', 'a_text', 'hello')
    assert pm.get_text_setting('test', 'a_text') == 'hello'


def test_number_setting_helpers():
    pm = PreferencesManager()
    pm.set_number_setting('test', 'a_num', 42)
    assert pm.get_number_setting('test', 'a_num') == 42


def test_export_preferences_returns_valid_json():
    pm = PreferencesManager()
    out = pm.export_preferences()
    assert out  # non-empty
    parsed = json.loads(out)
    assert isinstance(parsed, dict)
    assert 'proofreading_settings' in parsed


def test_merge_with_defaults_keeps_user_overrides():
    pm = PreferencesManager()
    user = {'vocab_settings': {'mode': 'CUSTOM_MODE'}}
    merged = pm.merge_with_defaults(user)
    assert merged['vocab_settings']['mode'] == 'CUSTOM_MODE'
    # default keys still present
    assert 'proofreading_settings' in merged


def test_merge_with_defaults_keeps_default_keys():
    pm = PreferencesManager()
    merged = pm.merge_with_defaults({})
    assert 'proofreading_settings' in merged
    assert 'file_processing' in merged


def test_get_all_settings_returns_copy():
    pm = PreferencesManager()
    s1 = pm.get_all_settings()
    s1['mutated'] = 'xxx'
    s2 = pm.get_all_settings()
    assert 'mutated' not in s2, "should return a copy"


# ============================================================
if __name__ == '__main__':
    import inspect
    tests = [(n, f) for n, f in inspect.getmembers(sys.modules[__name__])
             if n.startswith('test_') and callable(f)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  ✓ {name}')
            passed += 1
        except AssertionError as e:
            print(f'  ✗ {name}: {e}')
            failed += 1
        except Exception as e:
            print(f'  💥 {name}: {type(e).__name__}: {e}')
            failed += 1
    print(f'\n{passed} passed, {failed} failed')
    sys.exit(1 if failed else 0)
