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

# Detect Python EARLY so we can call updater before apply
PY=""
if [ -x "python/bin/python3" ]; then
    PY="python/bin/python3"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
fi

# ============================================================
# Loop body — re-enters from bottom if Streamlit triggers a restart
# (sets .restart_pending flag before exiting)
# ============================================================
while true; do

# ============================================================
# Step 0: Poll GitHub for new release + download silently
# (Skipped if no Python or no internet — graceful)
# ============================================================
if [ -n "$PY" ]; then
    echo "Checking for updates..."
    "$PY" ".app/updater.py" --check-and-download --timeout 4 || true
    echo
fi

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

    # If we're a source-installed user (.venv mode) AND the update was
    # source-only, refresh deps in case requirements.txt changed.
    if [ "$KIND" = "source" ] && [ -x ".venv/bin/python" ]; then
        echo "Refreshing dependencies..."
        .venv/bin/python -m pip install -r .app/requirements.txt --quiet --disable-pip-version-check \
            || echo "[WARN] Dependency refresh failed. If the app crashes, run Install.command again."
    fi
    echo
fi

# Python detection already done at top — just verify it's still set
if [ -z "$PY" ]; then
    echo
    echo "[X] Not set up yet."
    echo
    echo "Neither the bundled python/ folder nor a local .venv/ was found."
    echo "This usually means you downloaded the 'Source code (zip)' from GitHub"
    echo "instead of a release bundle."
    echo
    echo "Easiest fix - one of:"
    echo
    echo "  A) Run Install.command once (needs Python on your machine):"
    echo "       Right-click Install.command -> Open  (first time only)"
    echo "       Wait 1-3 min for it to finish"
    echo "       Then double-click Start.command again"
    echo
    echo "  B) Download the pre-built bundle (no Python install needed):"
    echo "       https://github.com/snibzyz/inkextract/releases/latest"
    echo "       File: INKEXTRACT-macos-arm64.zip  (Apple Silicon)"
    echo "         or: INKEXTRACT-macos-x64.zip    (Intel)"
    echo
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

# ============================================================
# Kill any existing Streamlit process bound to port 8501 to prevent
# double-launches across multiple INKEXTRACT installs on the same machine
# ============================================================
STREAMLIT_PORT=8501
if command -v lsof >/dev/null 2>&1; then
    for pid in $(lsof -ti tcp:$STREAMLIT_PORT 2>/dev/null); do
        echo "Found existing process on port $STREAMLIT_PORT (PID $pid) - killing..."
        kill -9 "$pid" 2>/dev/null || true
    done
fi

echo
echo "============================================================"
echo "        INKEXTRACT - Translation Toolkit"
echo "============================================================"
echo "Starting app... your browser will open shortly."
echo "To quit: close this Terminal window or press Ctrl+C."
echo "Install root: $SCRIPT_DIR"
echo "============================================================"
echo

set +e
"$PY" -m streamlit run ".app/app.py" --server.port "$STREAMLIT_PORT"
ec=$?
set -e

# ============================================================
# Auto-restart support: if Streamlit's update banner triggered
# a restart (writes .restart_pending flag before os._exit), loop
# back to apply the staged update and relaunch.
# ============================================================
if [ -f ".restart_pending" ]; then
    echo
    echo "=== Restart requested by update — applying and relaunching ==="
    rm -f ".restart_pending"
    sleep 2
    continue
fi
break

done

if [ "${ec:-0}" -ne 0 ]; then
    echo
    echo "App exited with an error (code ${ec})."
    read -n 1 -s -r -p "Press any key to close..."
fi
