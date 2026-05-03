#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/env"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

echo "→ Installing Python dependencies into $VENV …"
"$PIP" install --upgrade pip -q
"$PIP" install -r "$SCRIPT_DIR/requirements.txt"

# ── Desktop launcher ──────────────────────────────────────────────────────────
DESKTOP="$HOME/.local/share/applications/metronome.desktop"
mkdir -p "$(dirname "$DESKTOP")"

cat > "$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Metronome
GenericName=Metronome
Comment=BPM Metronome for musicians
Exec=$PYTHON $SCRIPT_DIR/metronome.py
Icon=multimedia-volume-control
Terminal=false
Categories=AudioVideo;Music;Utility;
Keywords=metronome;bpm;tempo;beat;music;
StartupNotify=true
EOF

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "✓ Done!"
echo "  Run directly :  $PYTHON $SCRIPT_DIR/metronome.py"
echo "  Or launch from the application menu: Metronome"
