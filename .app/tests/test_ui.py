"""ทดสอบ ui module — pure helpers"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules import ui  # noqa: E402


def test_format_bytes_zero():
    assert ui.format_bytes(0) == "0 Bytes"


def test_format_bytes_negative():
    assert ui.format_bytes(-1) == "0 Bytes"


def test_format_bytes_small():
    assert "Bytes" in ui.format_bytes(500)


def test_format_bytes_kb():
    assert "KB" in ui.format_bytes(2048)


def test_format_bytes_mb():
    assert "MB" in ui.format_bytes(2 * 1024 * 1024)


def test_format_bytes_gb():
    assert "GB" in ui.format_bytes(3 * 1024 * 1024 * 1024)


def test_app_constants():
    assert ui.APP_NAME == "INKEXTRACT"
    assert "นิยายแปล" in ui.APP_TAGLINE


def test_orange_palette():
    assert ui.ORANGE_PRIMARY.startswith("#")
    assert ui.ORANGE_DARK.startswith("#")
    assert ui.ORANGE_LIGHT.startswith("#")
    assert len(ui.ORANGE_PRIMARY) == 7  # #RRGGBB


def test_chip_returns_html():
    out = ui.chip("test")
    assert '<span class="ink-chip">' in out
    assert 'test' in out


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
