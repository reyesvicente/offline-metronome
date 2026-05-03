#!/usr/bin/env bash
set -e

# Get absolute path to the project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/env"

echo "--- ChronicBeat Installation ---"

# 1. Ensure Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it first."
    exit 1
fi

# 2. Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR" || {
        echo "Error: Failed to create virtual environment."
        echo "You might need to install python3-venv (e.g., sudo apt install python3-venv)"
        exit 1
    }
fi

# 3. Define paths to venv binaries
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# 4. Install/Update dependencies
echo "→ Updating dependencies..."
"$PIP" install --upgrade pip -q
"$PIP" install -r "$SCRIPT_DIR/requirements.txt" -q

# 5. Determine Icon
ICON="multimedia-volume-control" # Default system icon
if [ -f "$SCRIPT_DIR/metronome.png" ]; then
    ICON="$SCRIPT_DIR/metronome.png"
fi

# 6. Create Desktop launcher
echo "→ Creating desktop entry..."
DESKTOP_PATH="$HOME/.local/share/applications/chronicbeat.desktop"
mkdir -p "$(dirname "$DESKTOP_PATH")"

cat > "$DESKTOP_PATH" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ChronicBeat
GenericName=Metronome
Comment=High-precision professional metronome
Exec=$PYTHON $SCRIPT_DIR/metronome.py
Icon=$ICON
Terminal=false
Categories=AudioVideo;Music;Utility;
Keywords=metronome;bpm;tempo;beat;music;
StartupNotify=true
EOF

# Refresh desktop database
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "✓ Successfully installed!"
echo "-----------------------"
echo "You can now launch 'ChronicBeat' from your application menu."
echo "Or run manually: $PYTHON $SCRIPT_DIR/metronome.py"
