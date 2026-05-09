#!/usr/bin/env bash
# Launcher for the bundled INKEXTRACT distribution on macOS.
# Just runs the bundled Python with the app. No install, no venv, no pip.

set -e

# cd to the directory this script lives in (works whether run from Finder or terminal)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Strip macOS quarantine attribute so Gatekeeper doesn't block our bundled Python.
# (No-op if already cleared. We do this on every launch in case the bundle was
# unzipped without xattr-clear.)
xattr -cr . 2>/dev/null || true

PY="python/bin/python3"

if [ ! -x "$PY" ]; then
    echo
    echo "[X] Bundled Python is missing."
    echo "    Re-download the latest release from:"
    echo "    https://github.com/snibzyz/inkextract/releases/latest"
    echo
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

# Apply staged update (if a previous run downloaded one)
if [ -f ".update_pending/READY" ]; then
    echo "Applying queued update..."
    "$PY" -c "import sys; sys.path.insert(0, '.app'); import updater; sys.exit(updater.apply_staged())" \
        || echo "Update apply failed - continuing with current version."
fi

echo
echo "============================================================"
echo "        INKEXTRACT - Translation Toolkit"
echo "============================================================"
echo "Starting app... your browser will open shortly."
echo "To quit: close this Terminal window or press Ctrl+C."
echo "============================================================"
echo

"$PY" -m streamlit run ".app/app.py" --server.headless=false

# Keep terminal open if streamlit exits with error so user can read it
ec=$?
if [ $ec -ne 0 ]; then
    echo
    echo "App exited with an error (code $ec)."
    read -n 1 -s -r -p "Press any key to close..."
fi
