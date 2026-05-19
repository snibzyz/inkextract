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

from updater import check_for_update, download_and_stage, read_version, ROOT_DIR  # noqa: E402


_STATE_KEY = "_update_banner_state"

# Process-level cache สำหรับผลการเช็ค GitHub release
#   เก็บที่ระดับโมดูล ไม่ใช่ st.session_state — เพราะ session ของ Streamlit
#   เริ่มใหม่ทุก refresh ของ browser แต่ Python process เริ่มใหม่เฉพาะ
#   ตอน Start.bat เปิดใหม่ → ตรงกับเงื่อนไข "เช็คครั้งเดียวต่อ launch"
_PROCESS_UPDATE_CACHE: dict = {
    "checked": False,       # background thread ทำงานเสร็จแล้ว
    "started": False,       # ยิง background thread ไปแล้วหรือยัง
    "release": None,        # ผลลัพธ์ของ check_for_update — dict | None
}


def _ensure_bg_check_started() -> None:
    """ยิง background thread ครั้งแรกที่ render() ถูกเรียก — non-blocking.

    หลังจากครั้งแรก ทุก session/rerun แค่อ่านจาก _PROCESS_UPDATE_CACHE
    ไม่บล็อค render. ผลค้างไปจนกว่า Python process จะเริ่มใหม่ (Start.bat รีลอนช์)
    """
    if _PROCESS_UPDATE_CACHE["started"]:
        return
    _PROCESS_UPDATE_CACHE["started"] = True

    def _worker() -> None:
        try:
            result = check_for_update(timeout=4.0)
        except Exception:
            result = None
        _PROCESS_UPDATE_CACHE["release"] = result
        _PROCESS_UPDATE_CACHE["checked"] = True

    threading.Thread(target=_worker, daemon=True, name="inkextract-update-check").start()


def _launcher_has_restart_loop(launcher: Path) -> bool:
    """True if Start.bat/Start.command has the :main_loop label (v1.3.0+).

    Old launchers exit when Streamlit exits — we need to spawn a detached
    relauncher. New launchers loop on .restart_pending flag — we just write
    the flag and exit.
    """
    try:
        content = launcher.read_text(encoding="utf-8", errors="ignore")
        return ":main_loop" in content
    except Exception:
        return False


def _trigger_auto_restart() -> None:
    """Restart the whole app stack so the staged update gets applied.

    Two paths depending on whether the launcher supports the loop pattern:

    **New launcher (v1.3.0+, has :main_loop label):**
      1. Write .restart_pending flag
      2. os._exit(0) — kills Streamlit
      3. Start.bat sees Streamlit returned → detects flag → loops to
         :main_loop → applies staged update → re-runs Streamlit

    **Old launcher (no loop):**
      1. Spawn detached cmd/sh that waits 3 sec then runs Start.bat
      2. os._exit(0) — kills Streamlit
      3. Old cmd window closes (no loop)
      4. Detached process runs Start.bat → applies + launches

    Both paths end with the user on the new version with zero clicks
    after pressing "รีสตาร์ทเลย" in the banner.
    """
    import os
    import platform
    import subprocess

    root = ROOT_DIR
    is_windows = platform.system() == "Windows"
    launcher = root / ("Start.bat" if is_windows else "Start.command")

    flag = root / ".restart_pending"
    try:
        flag.write_text("requested", encoding="utf-8")
    except Exception:
        pass

    # If launcher doesn't loop, spawn detached re-launcher
    use_detached = launcher.exists() and not _launcher_has_restart_loop(launcher)
    if use_detached:
        try:
            if is_windows:
                cmd = f'timeout /t 3 /nobreak >nul & start "" "{launcher}"'
                subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=str(root),
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                                  | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                    close_fds=True,
                )
            else:
                subprocess.Popen(
                    ["bash", "-c", f"sleep 3 && open '{launcher}'"],
                    cwd=str(root),
                    start_new_session=True,
                    close_fds=True,
                )
        except Exception:
            pass  # Best-effort — user may need to relaunch manually

    # Give browser a moment to render the "กำลังรีสตาร์ท..." message before killing
    import threading as _th
    def _delayed_exit():
        import time
        time.sleep(1.0)
        os._exit(0)
    _th.Thread(target=_delayed_exit, daemon=True).start()


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
            "popup_shown": False,    # dialog popped already in this session?
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


def _render_popup(state: dict, release: dict) -> None:
    """Render the update dialog as a modal popup (Streamlit >= 1.32 with st.dialog)."""

    @st.dialog("มีเวอร์ชันใหม่!", width="large")
    def _dialog():
        size_mb = (release.get("size") or 0) / (1024 * 1024)
        size_text = f" · ~{size_mb:.0f} MB" if size_mb > 0.5 else ""
        kind = release.get("kind") or "source"
        kind_label = "อัปเดตเต็ม (รวม Python + libs)" if kind == "bundle" else "อัปเดตโค้ดเท่านั้น"

        st.markdown(
            f"### `{read_version()}` → **`{release['latest']}`**  \n"
            f"_{kind_label}{size_text}_"
        )

        body = release.get("body") or ""
        if body.strip():
            with st.expander("รายละเอียดอัปเดต", expanded=True):
                st.markdown(body)

        if release.get("html_url"):
            st.caption(f"[ดูเต็มบน GitHub]({release['html_url']})")

        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("อัปเดตเลย", type="primary", use_container_width=True,
                         key="_popup_update_btn"):
                _start_download(state)
                st.rerun()
        with c2:
            if st.button("ภายหลัง", use_container_width=True, key="_popup_later_btn"):
                # Don't clear release — keep banner visible at top of page
                st.rerun()

    _dialog()


def render() -> None:
    """Call this near the top of app.py (after page_setup, before main content).

    เช็ค GitHub release ครั้งเดียวต่อ launch (Python process) ผ่าน background thread
    ในเว็บ session/rerun ต่อๆ ไปจะอ่านจาก process cache ทันที — ไม่บล็อค render
    """
    state = _get_state()

    # Kick off background check on the very first render (no-op afterwards)
    _ensure_bg_check_started()

    # ระหว่างที่ background thread ยังเช็ค GitHub อยู่ — auto-refresh สั้น ๆ
    # เพื่อให้ banner โผล่อัตโนมัติทันทีที่เช็คเสร็จ (ไม่ต้อง F5)
    # check_for_update มี timeout 4.0s → poll ทุก 800ms สูงสุด ~7 ครั้ง (~5.6s)
    # พอ cache populated แล้วครั้งถัดไป condition นี้ False → autorefresh ไม่ถูกเรียก หยุดเอง
    if not _PROCESS_UPDATE_CACHE["checked"]:
        try:
            from streamlit_autorefresh import st_autorefresh  # type: ignore
            st_autorefresh(interval=800, limit=7, key="_update_check_poll")
        except Exception:
            pass  # fallback: user still needs F5 if package missing

    # อ่านผลจาก process cache — ถ้ายังเช็คไม่เสร็จ release = None → return ทันที
    # autorefresh ด้านบนจะ rerun ให้เองเมื่อ cache มีค่า
    if not state["checked"] and _PROCESS_UPDATE_CACHE["checked"]:
        state["checked"] = True
        state["release"] = _PROCESS_UPDATE_CACHE["release"]

    release = state["release"]
    if not release and state["phase"] == "idle":
        # nothing to show — either still checking, no update, or offline
        return

    # If we're in a downloading state, refresh progress from worker thread
    if state["phase"] == "downloading":
        _poll_download(state)

    # Show popup ONCE per session when an update is first discovered (idle phase)
    if (release and state["phase"] == "idle"
            and not state["popup_shown"]
            and hasattr(st, "dialog")):
        state["popup_shown"] = True
        try:
            _render_popup(state, release)
        except Exception:
            # Streamlit version doesn't support dialog — fall through to banner only
            pass

    # ---------- render ----------
    with st.container(border=True):
        if state["phase"] == "idle" and release:
            cols = st.columns([0.78, 0.22])
            with cols[0]:
                size_mb = (release.get("size") or 0) / (1024 * 1024)
                size_text = f" · ~{size_mb:.0f} MB" if size_mb > 0.5 else ""
                kind = release.get("kind") or "source"
                kind_label = "อัปเดตเต็ม (รวม Python + libs)" if kind == "bundle" else "อัปเดตโค้ดเท่านั้น"
                st.markdown(
                    f"**:material/system_update: มีเวอร์ชันใหม่:** "
                    f"`{read_version()}` → **`{release['latest']}`**  \n"
                    f":small[{kind_label}{size_text}]"
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
            cols = st.columns([0.78, 0.22])
            with cols[0]:
                st.success(
                    f"ดาวน์โหลดเสร็จ — กดปุ่ม **รีสตาร์ทเลย** "
                    f"เพื่อใช้เวอร์ชัน `{release['latest']}` (ระบบจะปิดและเปิดใหม่ให้อัตโนมัติ)"
                )
            with cols[1]:
                if st.button("รีสตาร์ทเลย", type="primary",
                             use_container_width=True, key="_restart_btn"):
                    _trigger_auto_restart()
                if st.button("ปิดเอง", use_container_width=True,
                             key="_restart_manual"):
                    state["release"] = None
                    state["phase"] = "idle"
                    st.rerun()

        elif state["phase"] == "error":
            st.error(f":material/error: อัปเดตไม่สำเร็จ — {state['error']}")
            if st.button("ลองอีกครั้ง", key="_update_retry"):
                state["phase"] = "idle"
                state["progress"] = 0.0
                state["error"] = ""
                st.rerun()
