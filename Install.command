#!/usr/bin/env bash
# First-time install for INKEXTRACT (macOS / Linux).
#
# You only need this if you downloaded "Source code (zip)" from GitHub
# or cloned the repo. The pre-built release bundle
# (INKEXTRACT-macos-arm64.zip / INKEXTRACT-macos-x64.zip) does NOT need
# this - it ships with Python and libs inside, just run Start.command.
#
# What this does:
#   1. Find a system Python 3.x
#   2. Create a local .venv folder
#   3. pip-install everything in .app/requirements.txt
#
# Re-run if you ever delete .venv or want to refresh dependencies.

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

# Strip macOS quarantine attribute on first launch from Finder
if command -v xattr >/dev/null 2>&1; then
    xattr -cr . 2>/dev/null || true
fi

export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

echo
echo "============================================================"
echo "       INKEXTRACT - First-time Install"
echo "============================================================"
echo

# ---- 1. Find system Python ----
SYS_PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        ver=$("$cand" --version 2>&1 || true)
        case "$ver" in
            "Python 3."*)
                SYS_PY="$cand"
                break
                ;;
        esac
    fi
done

if [ -z "$SYS_PY" ]; then
    echo "[X] No Python 3 found on this machine."
    echo
    echo "Easiest fix: download the pre-built bundle which already includes Python:"
    echo "    https://github.com/snibzyz/inkextract/releases/latest"
    echo
    echo "Or install Python from python.org:"
    echo "    https://www.python.org/downloads/macos/"
    echo
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi
echo "[1/3] Found system Python: $SYS_PY ($($SYS_PY --version))"
echo

# ---- 2. Create venv ----
if [ -x ".venv/bin/python" ]; then
    echo "[2/3] .venv already exists - keeping it."
else
    echo "[2/3] Creating .venv ..."
    "$SYS_PY" -m venv .venv
fi
echo

# ---- 3. Install dependencies ----
echo "[3/3] Installing dependencies (may take 1-3 minutes) ..."
.venv/bin/python -m pip install --upgrade pip --quiet --disable-pip-version-check
.venv/bin/python -m pip install -r .app/requirements.txt --disable-pip-version-check

echo
echo "============================================================"
echo "  Install complete!"
echo
echo "  Double-click Start.command to launch the app."
echo "============================================================"
echo
read -n 1 -s -r -p "Press any key to close..."
