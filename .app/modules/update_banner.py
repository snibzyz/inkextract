"""Streamlit-side UI for the auto-updater.

Renders a small banner at the top of the app. On click, downloads the new
release in a background thread and updates a progress bar in real time.
The actual file swap happens at next launch via `Start.bat / Start.command`,
so this never touches a file the running Python process is using.
"""

from __future__ import annotations

import threading
from typing import Optional

import streamlit as st

# Import via package path so this works whether streamlit launches us as
# `.app/app.py` or `.app.app` module.
import sys
from pathlib import Path
_HERE = Path(__file__).resolve()
_APP_DIR = _HERE.parent.parent  # .app/
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from updater import check_for_update, download_and_stage, read_version  # noqa: E402


_STATE_KEY = "_update_banner_state"


def _get_state() -> dict:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = {
            "checked": False,        # have we polled GitHub this session?
            "release": None,         # dict from check_for_update or None
            "phase": "idle",         # idle | downloading | done | error
            "progress": 0.0,
            "status": "",
            "thread": None,
            "error": "",
        }
    return st.session_state[_STATE_KEY]


def _start_download(state: dict) -> None:
    """Kick off download in a background thread."""
    release = state["release"]
    if not release:
        return

    # Snapshot we mutate from the worker thread. Streamlit can't call
    # st.* from another thread, so we just write into this dict and
    # the next rerun reads it.
    progress_holder = {"frac": 0.0, "msg": "Starting..."}

    def cb(frac: float, msg: str) -> None:
        progress_holder["frac"] = float(frac)
        progress_holder["msg"] = str(msg)

    def worker():
        result = download_and_stage(release, on_progress=cb)
        progress_holder["result"] = result

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    state["thread"] = t
    state["phase"] = "downloading"
    state["progress_holder"] = progress_holder


def _poll_download(state: dict) -> None:
    """Pull progress out of the worker thread holder."""
    holder = state.get("progress_holder") or {}
    state["progress"] = float(holder.get("frac", state["progress"]))
    state["status"] = str(holder.get("msg", state["status"]))

    result = holder.get("result")
    if result is not None:
        if result.get("ok"):
            state["phase"] = "done"
        else:
            state["phase"] = "error"
            state["error"] = str(result.get("error", "unknown"))


def render() -> None:
    """Call this near the top of app.py (after page_setup, before main content)."""
    state = _get_state()

    # First-time poll (one HTTP request per session)
    if not state["checked"]:
        state["checked"] = True
        try:
            state["release"] = check_for_update(timeout=4.0)
        except Exception:
            state["release"] = None

    release = state["release"]
    if not release and state["phase"] == "idle":
        # nothing to show
        return

    # If we're in a downloading state, refresh progress from worker thread
    if state["phase"] == "downloading":
        _poll_download(state)

    # ---------- render ----------
    with st.container(border=True):
        if state["phase"] == "idle" and release:
            cols = st.columns([0.78, 0.22])
            with cols[0]:
                st.markdown(
                    f"**:material/system_update: มีเวอร์ชันใหม่:** "
                    f"`{read_version()}` → **`{release['latest']}`**"
                )
                with st.expander("รายละเอียดอัปเดต", expanded=False):
                    st.markdown(release.get("body") or "_(ไม่มีรายละเอียด)_")
                    if release.get("html_url"):
                        st.markdown(f"[ดูบน GitHub]({release['html_url']})")
            with cols[1]:
                if st.button("Update now", type="primary", use_container_width=True,
                             key="_update_btn", icon=":material/download:"):
                    _start_download(state)
                    st.rerun()
                if st.button("ภายหลัง", use_container_width=True, key="_update_dismiss"):
                    state["release"] = None
                    st.rerun()

        elif state["phase"] == "downloading":
            st.markdown(f"**:material/cloud_download: กำลังอัปเดต** → `{release['latest']}`")
            st.progress(state["progress"], text=state["status"] or "Working...")
            # Tell Streamlit to rerun every second so the progress bar updates.
            # (We use st.empty + a tiny sleep loop pattern via st_autorefresh
            # if available; otherwise rely on the user's interactions.)
            try:
                from streamlit_autorefresh import st_autorefresh  # type: ignore
                st_autorefresh(interval=750, key="_update_refresh")
            except Exception:
                # graceful fallback - the bar updates on any rerun
                st.caption("(หน้าจะรีเฟรชเองเมื่อมีการโต้ตอบ)")

        elif state["phase"] == "done":
            st.success(
                f":material/check_circle: ดาวน์โหลดเสร็จ — รีสตาร์ทโปรแกรม"
                f" (ปิดหน้าต่างนี้แล้วเปิด **Start** ใหม่) "
                f"เพื่อใช้เวอร์ชัน `{release['latest']}`"
            )

        elif state["phase"] == "error":
            st.error(f":material/error: อัปเดตไม่สำเร็จ — {state['error']}")
            if st.button("ลองอีกครั้ง", key="_update_retry"):
                state["phase"] = "idle"
                state["progress"] = 0.0
                state["error"] = ""
                st.rerun()
