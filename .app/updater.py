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
import platform
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

# Folders we never overwrite during update merge.
# Note: 'python' is in this set when applying a SOURCE update (zipball), but
# we deliberately allow it to be replaced when applying a BUNDLE update -
# see apply_staged() which detects the bundle case from a marker file.
SKIP_DIRS_SOURCE = {".git", ".venv", "workspace", ".config", "__pycache__", ".update_pending", "python"}
SKIP_DIRS_BUNDLE = {".git", ".venv", "workspace", ".config", "__pycache__", ".update_pending"}

# Marker file written into staged/ to distinguish bundle vs source updates
_KIND_MARKER = ".update_kind"


def _bundle_asset_name() -> Optional[str]:
    """Pick the right release asset name for this OS+arch.

    Mirrors the artifact names produced by .github/workflows/release.yml.
    Returns None if we can't identify the platform - the caller should fall
    back to the source zipball.
    """
    sys_name = sys.platform
    arch = (platform.machine() or "").lower()

    if sys_name.startswith("win"):
        return "INKEXTRACT-windows-x64.zip"
    if sys_name == "darwin":
        if arch in ("arm64", "aarch64"):
            return "INKEXTRACT-macos-arm64.zip"
        if arch in ("x86_64", "amd64"):
            return "INKEXTRACT-macos-x64.zip"
    return None

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

    On update available, prefers the platform-specific bundle asset
    (INKEXTRACT-<os>-<arch>.zip) which contains everything including the
    bundled Python interpreter and libs - so a release that bumps
    requirements.txt or the Python version still updates cleanly. Falls
    back to the source zipball if no matching asset exists (e.g. running
    on Linux, or against an old release made before bundle artifacts
    existed).
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

    # Are we running from a bundled install (has python/) or a source/dev
    # install (has .venv or neither)? Bundle users should pull the platform
    # bundle so python+libs stay in sync; source users should pull the
    # source zipball so we don't dump a 150MB python/ folder next to their
    # already-working .venv.
    we_are_bundled = (ROOT_DIR / "python").exists()

    asset_url = ""
    asset_size = 0
    if we_are_bundled:
        asset_name = _bundle_asset_name()
        if asset_name:
            for a in data.get("assets") or []:
                if a.get("name") == asset_name:
                    asset_url = a.get("browser_download_url") or ""
                    asset_size = int(a.get("size") or 0)
                    break

    if asset_url:
        kind = "bundle"
        url = asset_url
    else:
        kind = "source"
        url = data.get("zipball_url") or ""

    return {
        "current": current,
        "latest": tag,
        "url": url,
        "kind": kind,
        "size": asset_size,
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
    kind = release.get("kind") or "source"

    if not url:
        return {"ok": False, "error": "no download url"}

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

        # Both source zipball and bundle zip wrap everything in one top-level dir.
        children = [p for p in extract_root.iterdir() if p.is_dir()]
        if not children:
            return {"ok": False, "error": "zip is empty"}
        src_root = children[0]

        # ---- stage: copy everything (apply_staged decides what to skip during merge) ----
        cb(0.85, "Staging files...")
        if STAGED_DIR.exists():
            shutil.rmtree(STAGED_DIR, ignore_errors=True)
        STAGED_DIR.mkdir(parents=True, exist_ok=True)

        def copy_tree(src: Path, dst: Path) -> None:
            for item in src.iterdir():
                target = dst / item.name
                if item.is_dir():
                    target.mkdir(exist_ok=True)
                    copy_tree(item, target)
                else:
                    shutil.copy2(item, target)

        copy_tree(src_root, STAGED_DIR)

        # Drop a marker so apply_staged knows whether to overwrite python/
        (STAGED_DIR / _KIND_MARKER).write_text(kind, encoding="utf-8")

        # cleanup intermediate
        shutil.rmtree(extract_root, ignore_errors=True)
        try:
            zip_path.unlink()
        except Exception:
            pass

        # mark READY - launcher uses this to decide whether to apply
        READY_FLAG.write_text(tag, encoding="utf-8")

        cb(1.0, f"Ready - restart to apply {tag}")
        return {"ok": True, "tag": tag, "kind": kind}

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

    # Decide what to skip based on what was staged: bundle updates (full
    # platform zip) get to overwrite python/ as well, source updates do not.
    kind_file = STAGED_DIR / _KIND_MARKER
    kind = "source"
    try:
        if kind_file.exists():
            kind = kind_file.read_text(encoding="utf-8").strip() or "source"
    except Exception:
        pass

    skip = SKIP_DIRS_BUNDLE if kind == "bundle" else SKIP_DIRS_SOURCE
    print(f"[updater] Applying staged {kind} update {tag}...")

    def merge(src: Path, dst: Path, top: bool = False) -> None:
        for item in src.iterdir():
            # Don't copy our own kind-marker file across into the live tree
            if top and item.name == _KIND_MARKER:
                continue
            # Top-level skip rules protect user data and (for source updates) python/
            if top and item.name in skip:
                continue
            target = dst / item.name
            if item.is_dir():
                target.mkdir(exist_ok=True)
                merge(item, target, top=False)
            else:
                try:
                    if target.exists():
                        target.unlink()
                except Exception:
                    # If we can't delete (e.g. file is locked), shutil.copy2
                    # will raise below and we surface a clear error.
                    pass
                shutil.copy2(item, target)

    try:
        merge(STAGED_DIR, ROOT_DIR, top=True)
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
# CLI helper: check + download + stage (used by Start.bat)
# ============================================================
def cli_check_and_download(timeout: float = 5.0, quiet: bool = False) -> int:
    """Poll GitHub → download newer release → stage for next apply.

    Designed to run from Start.bat BEFORE Streamlit launches. Prints
    progress to stdout so the cmd window shows what's happening. On any
    network failure, returns 0 (silent skip) so the app still launches.

    Returns:
        0 = up to date OR downloaded successfully OR no network (graceful)
        1 = download started but failed mid-way
    """
    if not requests or not pkg_version:
        if not quiet:
            print("[updater] 'requests'/'packaging' not installed — skip update check.")
        return 0

    if not quiet:
        print(f"[updater] Checking for updates (current: {read_version()})...")

    try:
        release = check_for_update(timeout=timeout)
    except Exception as e:
        if not quiet:
            print(f"[updater] Check failed ({e}) — skip.")
        return 0

    if not release:
        if not quiet:
            print("[updater] Already up to date.")
        return 0

    # Already staged from a previous run? Skip re-download.
    if READY_FLAG.exists():
        if not quiet:
            print(f"[updater] Update already staged ({READY_FLAG.read_text(encoding='utf-8').strip()}) — will apply.")
        return 0

    size_mb = (release.get("size") or 0) / 1024 / 1024
    size_label = f" (~{size_mb:.0f} MB)" if size_mb > 0.5 else ""
    if not quiet:
        print(f"[updater] New version available: {release.get('current')} -> {release.get('latest')}{size_label}")
        print(f"[updater] Downloading... (kind={release.get('kind', '?')})")

    last_pct = [-1]

    def cb(frac: float, msg: str) -> None:
        if quiet:
            return
        pct = int(frac * 100)
        if pct != last_pct[0]:
            last_pct[0] = pct
            short_msg = (msg or "")[:50]
            print(f"\r[updater] {pct:3d}%  {short_msg:<50}", end="", flush=True)

    try:
        result = download_and_stage(release, on_progress=cb)
    except Exception as e:
        if not quiet:
            print(f"\n[updater] Download failed: {e}")
        return 1

    if not quiet:
        print()  # newline after progress bar

    if result.get("ok"):
        if not quiet:
            print(f"[updater] Downloaded and staged — will apply now.")
        return 0
    else:
        if not quiet:
            print(f"[updater] Download failed: {result.get('error', 'unknown')}")
        return 1


# ============================================================
# CLI
# ============================================================
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="updater")
    p.add_argument("--apply-staged", action="store_true",
                   help="Apply a previously-staged update. Used by launchers.")
    p.add_argument("--check", action="store_true",
                   help="Just check for an update and print the result.")
    p.add_argument("--check-and-download", action="store_true",
                   help="Poll GitHub + download + stage if new release exists. "
                        "Used by Start.bat before launching Streamlit.")
    p.add_argument("--quiet", action="store_true",
                   help="Suppress non-error output (for --check-and-download).")
    p.add_argument("--timeout", type=float, default=5.0,
                   help="HTTP timeout in seconds (default 5).")
    args = p.parse_args(argv)

    if args.apply_staged:
        return apply_staged()

    if args.check_and_download:
        return cli_check_and_download(timeout=args.timeout, quiet=args.quiet)

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
