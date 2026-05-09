"""Auto-Updater for INKEXTRACT.

Two roles:

1. **Library** (called from inside the running Streamlit app)
   - check_for_update()      -> dict | None  (lightweight: just polls GitHub)
   - download_and_stage()    -> dict         (heavy: downloads zip, extracts to .update_pending/staged)
                                              Does NOT touch any in-use files.
   These are the entry points the UI calls. Progress is reported via a
   callback so the UI can render a progress bar.

2. **Apply step** (CLI: `python -m .app.updater --apply-staged`)
   Run by the launcher (Start.bat / Start.command) BEFORE the Streamlit
   process starts. Moves files from .update_pending/staged into place,
   bumps VERSION, deletes the staging folder.

Layout while an update is pending:
    <root>/
        .update_pending/
            <tag>.zip            (downloaded)
            staged/              (extracted, with .git/.venv/workspace stripped)
            READY                (touched once staging is complete)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional

try:
    import requests
    from packaging import version as pkg_version
except ImportError:
    requests = None
    pkg_version = None


# ============================================================
# CONFIG
# ============================================================
REPO_OWNER = "snibzyz"
REPO_NAME = "inkextract"
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT_DIR / ".app" / "VERSION"
PENDING_DIR = ROOT_DIR / ".update_pending"
STAGED_DIR = PENDING_DIR / "staged"
READY_FLAG = PENDING_DIR / "READY"

RELEASES_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

# Folders we never overwrite during update merge
SKIP_DIRS = {".git", ".venv", "workspace", ".config", "__pycache__", ".update_pending", "python"}

ProgressCb = Callable[[float, str], None]  # (fraction 0..1, status text)


# ============================================================
# Version helpers
# ============================================================
def read_version() -> str:
    if VERSION_FILE.exists():
        try:
            return VERSION_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return "0.0.0"


def write_version(v: str) -> None:
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(v.lstrip("v"), encoding="utf-8")


def _is_newer(remote_tag: str, local: str) -> bool:
    if not pkg_version:
        return False
    try:
        return pkg_version.parse(remote_tag) > pkg_version.parse(local)
    except Exception:
        return False


# ============================================================
# 1. Polling: check_for_update
# ============================================================
def check_for_update(timeout: float = 5.0) -> Optional[dict]:
    """Poll GitHub releases. Returns None if up-to-date or offline.

    On update available:
        {
            "current": "1.0.2",
            "latest": "v1.0.3",
            "url": "https://api.github.com/.../zipball/v1.0.3",
            "body": "<release notes markdown>",
            "html_url": "https://github.com/.../releases/tag/v1.0.3",
        }
    """
    if not requests or not pkg_version:
        return None
    try:
        resp = requests.get(RELEASES_API, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    tag = data.get("tag_name") or ""
    current = read_version()
    if not _is_newer(tag, current):
        return None

    return {
        "current": current,
        "latest": tag,
        "url": data.get("zipball_url") or "",
        "body": data.get("body") or "",
        "html_url": data.get("html_url") or "",
    }


# ============================================================
# 2. Download + stage (called from UI in background)
# ============================================================
def download_and_stage(release: dict, on_progress: Optional[ProgressCb] = None) -> dict:
    """Download the release zip and extract it into .update_pending/staged.

    Does NOT overwrite any in-use file - that's done at next launch by
    --apply-staged. So this is safe to call while Streamlit is running.

    Returns:
        {"ok": True, "tag": "<tag>"}
        {"ok": False, "error": "<message>"}
    """
    if not requests:
        return {"ok": False, "error": "requests not installed"}

    cb = on_progress or (lambda f, msg: None)
    url = release.get("url") or ""
    tag = release.get("latest") or "unknown"

    if not url:
        return {"ok": False, "error": "no zipball url"}

    try:
        # Clean any previous pending state
        if PENDING_DIR.exists():
            shutil.rmtree(PENDING_DIR, ignore_errors=True)
        PENDING_DIR.mkdir(parents=True, exist_ok=True)

        zip_path = PENDING_DIR / f"{tag}.zip"

        # ---- download ----
        cb(0.0, "Connecting...")
        with requests.get(url, timeout=30, stream=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length") or 0)
            written = 0
            with zip_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        # downloads occupy 0..0.7 of the progress bar
                        cb(0.70 * (written / total), f"Downloading {tag}...")
                    else:
                        cb(0.35, f"Downloading {tag}...")

        # ---- extract ----
        cb(0.72, "Extracting...")
        extract_root = PENDING_DIR / "_extracted"
        extract_root.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)

        # GitHub zipball wraps everything in <owner>-<repo>-<sha>/
        children = [p for p in extract_root.iterdir() if p.is_dir()]
        if not children:
            return {"ok": False, "error": "zip is empty"}
        src_root = children[0]

        # ---- stage (copy into staged/, skipping volatile dirs) ----
        cb(0.85, "Staging files...")
        if STAGED_DIR.exists():
            shutil.rmtree(STAGED_DIR, ignore_errors=True)
        STAGED_DIR.mkdir(parents=True, exist_ok=True)

        def copy_tree(src: Path, dst: Path) -> None:
            for item in src.iterdir():
                if item.name in SKIP_DIRS:
                    continue
                target = dst / item.name
                if item.is_dir():
                    target.mkdir(exist_ok=True)
                    copy_tree(item, target)
                else:
                    shutil.copy2(item, target)

        copy_tree(src_root, STAGED_DIR)

        # cleanup intermediate
        shutil.rmtree(extract_root, ignore_errors=True)
        try:
            zip_path.unlink()
        except Exception:
            pass

        # mark READY - launcher uses this to decide whether to apply
        READY_FLAG.write_text(tag, encoding="utf-8")

        cb(1.0, f"Ready - restart to apply {tag}")
        return {"ok": True, "tag": tag}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# 3. Apply staged update (CLI, run by launcher BEFORE app starts)
# ============================================================
def apply_staged() -> int:
    """Move files from .update_pending/staged into place. Returns process exit code."""
    if not READY_FLAG.exists() or not STAGED_DIR.exists():
        # nothing to do
        return 0

    tag = ""
    try:
        tag = READY_FLAG.read_text(encoding="utf-8").strip()
    except Exception:
        pass

    print(f"[updater] Applying staged update {tag}...")

    def merge(src: Path, dst: Path) -> None:
        for item in src.iterdir():
            target = dst / item.name
            if item.is_dir():
                target.mkdir(exist_ok=True)
                merge(item, target)
            else:
                # overwrite existing files
                try:
                    if target.exists():
                        target.unlink()
                except Exception:
                    pass
                shutil.copy2(item, target)

    try:
        merge(STAGED_DIR, ROOT_DIR)
        if tag:
            write_version(tag)
        print(f"[updater] Update {tag} applied.")
    except Exception as e:
        print(f"[updater] Apply failed: {e}")
        return 1
    finally:
        # always clean up the pending dir so we don't try again
        shutil.rmtree(PENDING_DIR, ignore_errors=True)

    return 0


# ============================================================
# CLI
# ============================================================
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="updater")
    p.add_argument("--apply-staged", action="store_true",
                   help="Apply a previously-staged update. Used by launchers.")
    p.add_argument("--check", action="store_true",
                   help="Just check for an update and print the result.")
    args = p.parse_args(argv)

    if args.apply_staged:
        return apply_staged()

    if args.check:
        info = check_for_update()
        if info:
            print(f"Update available: {info['current']} -> {info['latest']}")
            return 0
        print("Up to date.")
        return 1

    # default: print short status
    print(f"INKEXTRACT version: {read_version()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
