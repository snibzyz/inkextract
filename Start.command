#!/usr/bin/env bash
# Universal launcher for INKEXTRACT.
#
# Same file ships in:
#   * end-user release bundle  -> uses bundled python/ folder
#   * source repo (developers) -> uses .venv/ folder (or system Python as last resort)
#
# Detection order: bundled python/  >  local .venv/  >  system PATH

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Strip macOS quarantine attribute so Gatekeeper doesn't block our bundled
# Python on first launch (no-op if already cleared, no-op outside macOS).
if command -v xattr >/dev/null 2>&1; then
    xattr -cr . 2>/dev/null || true
fi

export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

# ============================================================
# Apply pending update FIRST, with native rsync.
#
# Why not Python here? On Windows we'd hit a python.exe self-lock; on
# macOS python3 can technically replace itself, but doing the apply in
# shell before any Python runs keeps both platforms on the same
# predictable path.
# ============================================================
if [ -f ".update_pending/READY" ]; then
    echo "Applying staged update..."

    KIND="source"
    if [ -f ".update_pending/staged/.update_kind" ]; then
        KIND=$(tr -d '[:space:]' < .update_pending/staged/.update_kind)
    fi

    # Start.bat/.command are excluded: bash on macOS is more permissive
    # than cmd.exe but still safer to require manual re-download for
    # launcher changes (matches the Windows behavior).
    EXCLUDES=(
        --exclude=".git"
        --exclude=".venv"
        --exclude="workspace"
        --exclude=".config"
        --exclude="__pycache__"
        --exclude=".update_pending"
        --exclude=".update_kind"
        --exclude="Start.bat"
        --exclude="Start.command"
    )
    if [ "$KIND" != "bundle" ]; then
        EXCLUDES+=(--exclude="python")
    fi

    if command -v rsync >/dev/null 2>&1; then
        rsync -a "${EXCLUDES[@]}" .update_pending/staged/ ./ \
            || echo "[WARN] rsync had issues - continuing anyway."
    else
        # Extreme fallback: tar pipe, exclusions baked in.
        echo "[WARN] rsync not available, using tar fallback."
        ( cd .update_pending/staged \
            && tar cf - --exclude=".update_kind" . ) | tar xf - -C ./ \
            || echo "[WARN] tar copy had issues."
    fi

    NEW_TAG=$(tr -d '[:space:]' < .update_pending/READY)
    NEW_TAG="${NEW_TAG#v}"
    if [ -n "$NEW_TAG" ]; then
        echo "$NEW_TAG" > .app/VERSION
    fi

    rm -rf .update_pending
    echo "Update applied: $NEW_TAG"
    echo
fi

PY=""
if [ -x "python/bin/python3" ]; then
    PY="python/bin/python3"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
    echo "[WARN] Using system Python (no python/ bundle, no .venv detected)."
    echo "       For dev, run once:"
    echo "           python3 -m venv .venv && .venv/bin/pip install -r .app/requirements.txt"
    echo
fi

if [ -z "$PY" ]; then
    echo
    echo "[X] No Python interpreter found."
    echo
    echo "If you downloaded a release bundle, the python/ folder should be"
    echo "next to this file. Re-download from:"
    echo "    https://github.com/snibzyz/inkextract/releases/latest"
    echo
    echo "If you cloned the source, install Python first then run:"
    echo "    python3 -m venv .venv"
    echo "    .venv/bin/pip install -r .app/requirements.txt"
    echo
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

echo
echo "============================================================"
echo "        INKEXTRACT - Translation Toolkit"
echo "============================================================"
echo "Starting app... your browser will open shortly."
echo "To quit: close this Terminal window or press Ctrl+C."
echo "============================================================"
echo

"$PY" -m streamlit run ".app/app.py"

ec=$?
if [ $ec -ne 0 ]; then
    echo
    echo "App exited with an error (code $ec)."
    read -n 1 -s -r -p "Press any key to close..."
fi
