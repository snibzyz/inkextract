"""ทดสอบ paths และ config"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.config import app_config, load_exclude_patterns  # noqa: E402


def test_paths_exist():
    assert paths.ROOT.exists()
    assert paths.APP_DIR.exists()
    assert paths.WORKSPACE_DIR.exists()


def test_paths_relative_layout():
    # PascalCase ตาม schema ใหม่ (migrate จาก 0-input/output/vocab แล้ว)
    assert paths.INPUT_DIR == paths.WORKSPACE_DIR / "Input"
    assert paths.OUTPUT_DIR == paths.WORKSPACE_DIR / "Output"
    assert paths.VOCAB_DIR == paths.WORKSPACE_DIR / "Vocab"


def test_app_config_defaults():
    assert app_config.max_file_size > 0
    assert app_config.max_files_per_batch > 0
    assert app_config.max_lines_per_file > 0


def test_load_exclude_patterns_returns_list():
    patterns = load_exclude_patterns()
    assert isinstance(patterns, list)


def test_ensure_dirs_creates_workspace():
    paths.ensure_dirs()
    for d in paths.ALL_DATA_DIRS:
        assert d.exists(), f"missing: {d}"


def test_every_data_dir_has_gitkeep_for_clone_users():
    """กัน regression — ทุก folder ใน default workspace ต้องมี .gitkeep
    (สำหรับ user ที่ clone จาก git) — user-created projects ใน projects/
    ไม่ต้องมี เพราะสร้างโดย user เอง ไม่อยู่ใน repo"""
    # บังคับ active = default workspace ก่อนเช็ค (อาจ active project อื่นจาก state เดิม)
    paths.set_active_project_root(None)
    missing = [d for d in paths.ALL_DATA_DIRS if not (d / ".gitkeep").exists()]
    assert not missing, (
        f"missing .gitkeep in {len(missing)} folder(s): "
        f"{[str(d.relative_to(paths.ROOT)) for d in missing]}"
    )


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
