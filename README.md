# Ask AI 🤖✨

A premium, local LLM companion for Ubuntu/GNOME. **Ask AI** integrates directly with your system shell and tray bar, bringing the power of local inference to a floating HUD window and command line utility.

It consists of two unified interfaces:
1. 📟 **A CLI Utility (`ask`)** to query models directly or update settings from your terminal.
2. 🎛️ **A System Tray Service** that reveals a borderless, translucent, GNOME-styled overlay window with a single input.

---

## ✨ Features

- **Translucent HUD Overlay**: A floating borderless window styled with a modern dark zinc container, rounded corners, and a subtle border highlight.
- **Micro-interactions**:
  - *Click & Drag*: Drag the overlay window by holding left click anywhere on its background.
  - *Auto-shrink*: The window automatically sizes its height to fit the content, shrinking down to the input field on reset and expanding to show answers.
  - *Auto-hide*: Tap `Escape` or click anywhere outside the window to immediately hide it.
- **GNOME Tray Integration**: Integrates directly with the GNOME status tray (beside the wireless icon) using native `AppIndicator` libraries.
- **Single-Instance IPC Control**: Attempting to launch the GUI again (or clicking the launcher icon in the GNOME app grid) signals the existing background process to pop the window up, preventing multiple instances.
- **Asynchronous Execution**: Model inference runs in a background worker thread, ensuring the GUI remains fluid and displays a spinner while the LLM is "thinking".

---

## 🛠️ Prerequisites

This tool is designed to work with a local installation of **llama.cpp** and `.gguf` format models.

### System Dependencies
To enable the top bar tray icon in GNOME, install the system's AppIndicator repository:
```bash
sudo apt install gir1.2-ayatanaappindicator3-0.1
```

### Models & LLM Engine
1. **llama.cpp**: Needs to be compiled with the `llama-completion` binary.
2. **Model Files**: GGUF model files placed in your local directory (default models are Qwen 2.5 1.5B and Llama 3.2 3B).

*Note: You can inspect and update paths to `llama.cpp` and model files directly inside [ask.py](ask.py).*

---

## 🚀 Installation & Setup

1. **Deploy executable & shortcuts**:
   Run the installer script:
   ```bash
   ./install.sh
   ```
   This script will:
   - Copy the utility to `~/.local/bin/ask` (making it globally accessible in your terminal).
   - Create a desktop entry at `~/.local/share/applications/ask-ai.desktop` so you can search for "Ask AI" in your GNOME applications grid.
   - Register the autostart launcher at `~/.config/autostart/ask-ai.desktop` to boot the tray daemon on login.

2. **Start the GUI Service**:
   Start the background daemon manually:
   ```bash
   ask --gui &
   ```

---

## 📖 Usage

### Command Line Interface

```bash
# Query the default model (Llama 3.2 3B)
ask "What is the distance between the Earth and the Moon?"

# Override and use a different model for a specific query
ask --model qwen "Explain dark matter in one sentence."

# Change the default model saved in your config (~/.config/ask_ai/config.json)
ask --set-default-model llama-xs

# Launch the system tray GUI service
ask --gui
```

### Graphical Interface

- **Open overlay**: Click the question mark icon `?` in your top status bar, launch "Ask AI" from your applications launcher, or type `ask --gui`.
- **Submit Question**: Write your query in the input bar and press `Enter`. The input will slide away and show a thinking indicator until the answer appears.
- **Reposition Window**: Click and drag any empty space of the translucent background.
- **Reset / Start Over**: Click the circular refresh button `↻` at the bottom of the answer scroll view to return to the input screen.
- **Hide Window**: Click outside the HUD window or press `Escape`.

---

## 📂 Project Structure

- `ask.py` - Core logic containing model routing, config readers, CLI, and the PyGObject GUI loop.
- `install.sh` - Installs the desktop configurations and system binaries.
- `run_llm.sh` - Simple terminal-only bash script wrapper.
- `.gitignore` - Excludes model binaries, cmake environments, and configuration states from tracking.
