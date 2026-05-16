"""backend.py — Bridge ระหว่าง Reflex และ business logic ที่อยู่ใน .app/modules/

กลยุทธ์:
1. ใส่ ../.app เข้า sys.path → import modules ได้เหมือนรันใน Streamlit
2. Stub `streamlit` ใน sys.modules ก่อน import — เพราะ proofreader.py และ
   vocab_processor.py มี `import streamlit as st` แม้ไม่ได้เรียก st.xxx
   ใน function path ที่เราใช้ก็จริง แต่ import เองจะ fail ถ้าไม่มี streamlit
3. Export module objects ให้ state.py ใช้
"""
from __future__ import annotations
import sys
import types
from pathlib import Path


# ── 1. เพิ่ม .app เข้า sys.path ──────────────────────────────────────────────
_THIS = Path(__file__).resolve()
_APP_DIR = _THIS.parent.parent.parent / ".app"      # _poc_reflex/.../..  -> .app
if not _APP_DIR.exists():
    raise RuntimeError(f"Cannot find .app directory at {_APP_DIR}")
sys.path.insert(0, str(_APP_DIR))


# ── 2. Stub streamlit before importing modules ──────────────────────────────
if "streamlit" not in sys.modules:
    _stub = types.ModuleType("streamlit")

    class _NoOp:
        """Catch-all stub — return None for anything called on it"""
        def __init__(self, *a, **kw): pass
        def __getattr__(self, name): return _NoOp()
        def __call__(self, *a, **kw): return _NoOp()
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def __iter__(self): return iter([])
        def __bool__(self): return False

    _stub.session_state = {}
    _stub.cache_resource = lambda *a, **kw: (lambda f: f)
    _stub.cache_data = lambda *a, **kw: (lambda f: f)

    # Common st.* fns ที่ proofreader/vocab อาจเรียก
    for fn in ("toast", "error", "warning", "info", "success",
               "write", "markdown", "rerun", "experimental_rerun",
               "stop", "spinner", "container", "empty", "progress",
               "columns", "tabs", "expander", "form", "sidebar"):
        setattr(_stub, fn, _NoOp())

    sys.modules["streamlit"] = _stub


# ── 3. Import + re-export business modules ──────────────────────────────────
from modules import paths            # noqa: E402
from modules import project_manager  # noqa: E402
from modules import manuscript_checker  # noqa: E402

# Lazy imports สำหรับ heavy modules — load เมื่อต้องใช้
def get_proofreader():
    from modules.proofreader import NovelProofreader
    return NovelProofreader()


def get_file_processor():
    from modules.file_processor import FileProcessor
    return FileProcessor()


def get_vocab_processor():
    from modules.vocab_processor import VocabProcessor
    return VocabProcessor()


def get_merge_processor():
    from modules.merge_processor import MergeProcessor
    return MergeProcessor()


def get_separate_processor():
    from modules.separate_processor import SeparateProcessor
    return SeparateProcessor()


__all__ = [
    "paths", "project_manager", "manuscript_checker",
    "get_proofreader", "get_file_processor", "get_vocab_processor",
    "get_merge_processor", "get_separate_processor",
]
