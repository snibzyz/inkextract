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

# Apply staged update (bundle mode)
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

"$PY" -m streamlit run ".app/app.py"

ec=$?
if [ $ec -ne 0 ]; then
    echo
    echo "App exited with an error (code $ec)."
    read -n 1 -s -r -p "Press any key to close..."
fi
