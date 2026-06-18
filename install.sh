#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Target paths
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
APP_DIR="$HOME/.local/share/applications"

# Ensure directories exist
mkdir -p "$BIN_DIR"
mkdir -p "$AUTOSTART_DIR"
mkdir -p "$APP_DIR"

echo "Installing ask executable..."
cp ask.py "$BIN_DIR/ask"
chmod +x "$BIN_DIR/ask"

# Create wrapper for llama-completion if found in the global ~/ai directory
GLOBAL_LLAMA_DIR="$HOME/ai/llama.cpp"
if [ -f "$GLOBAL_LLAMA_DIR/build/bin/llama-completion" ]; then
    echo "Creating wrapper for llama-completion in $BIN_DIR..."
    cat << EOF > "$BIN_DIR/llama-completion"
#!/bin/bash
export LD_LIBRARY_PATH="$GLOBAL_LLAMA_DIR/build/bin:\$LD_LIBRARY_PATH"
exec "$GLOBAL_LLAMA_DIR/build/bin/llama-completion" "\$@"
EOF
    chmod +x "$BIN_DIR/llama-completion"
fi

echo "Creating autostart configuration..."
cat << EOF > "$AUTOSTART_DIR/ask-ai.desktop"
[Desktop Entry]
Type=Application
Exec=$BIN_DIR/ask --gui
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Ask AI Tray Service
Comment=Runs the local LLM system tray service
Icon=dialog-question-symbolic
EOF

echo "Creating GNOME desktop application entry..."
cat << EOF > "$APP_DIR/ask-ai.desktop"
[Desktop Entry]
Type=Application
Name=Ask AI
Comment=Ask questions to your local LLM
Exec=$BIN_DIR/ask --gui
Icon=dialog-question-symbolic
Terminal=false
Categories=Utility;Development;
EOF

echo "Installation complete!"
echo "You can now run 'ask' from the command line, search for 'Ask AI' in your GNOME apps, or launch the GUI tray service with 'ask --gui'."
