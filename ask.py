#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import threading
import socket
import shutil
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

# Check for GNOME AppIndicator support
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    HAS_INDICATOR = True
except Exception:
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
        HAS_INDICATOR = True
    except Exception:
        HAS_INDICATOR = False

# Path Configuration
MODELS_DIR = os.path.expanduser("~/.llm-models")

# Search for the compiled binary globally, then fall back to relocated ~/ai/llama.cpp
BINARY = shutil.which("llama-completion")
if not BINARY:
    FALLBACK_BINARY = os.path.expanduser("~/ai/llama.cpp/build/bin/llama-completion")
    if os.path.exists(FALLBACK_BINARY):
        BINARY = FALLBACK_BINARY
    else:
        # Backward compatibility for local project folder checks
        LOCAL_BINARY = os.path.expanduser("~/ai/llm/llama.cpp/build/bin/llama-completion")
        if os.path.exists(LOCAL_BINARY):
            BINARY = LOCAL_BINARY
        else:
            BINARY = "llama-completion"

MODELS = {
    "qwen": os.path.join(MODELS_DIR, "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"),
    "llama": os.path.join(MODELS_DIR, "Llama-3.2-3B-Instruct-Q4_K_M.gguf"),
    "llama-xs": os.path.join(MODELS_DIR, "Llama-3.2-3B-Instruct-Q2_K.gguf"),
}

CONFIG_DIR = os.path.expanduser("~/.config/ask_ai")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
IPC_SOCKET_FILE = os.path.join(CONFIG_DIR, "ask_ai.ipc")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"default_model": "llama"}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"default_model": "llama"}

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        return False

def run_query(prompt, model_choice):
    model_path = MODELS.get(model_choice)
    if not model_path or not os.path.exists(model_path):
        return f"Error: Model file for '{model_choice}' not found at {model_path}."
    if not os.path.exists(BINARY):
        return f"Error: llama-completion binary not found at {BINARY}."

    if model_choice == "qwen":
        formatted_prompt = f"<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    else:
        formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful assistant.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"

    cmd = [
        BINARY,
        "-m", model_path,
        "-ngl", "99",
        "-no-cnv",
        "--no-display-prompt",
        "-p", formatted_prompt
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        )
        output = proc.stdout
        output = output.replace(" [end of text]", "")
        return output.rstrip() + "\n"
    except subprocess.CalledProcessError as e:
        return f"Error running model: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def send_show_ipc():
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(IPC_SOCKET_FILE)
        client.sendall(b"show")
        client.close()
        return True
    except Exception:
        try:
            os.remove(IPC_SOCKET_FILE)
        except Exception:
            pass
        return False

def start_ipc_server(window):
    try:
        os.remove(IPC_SOCKET_FILE)
    except Exception:
        pass
        
    def server_thread():
        try:
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(IPC_SOCKET_FILE)
            server.listen(5)
            while True:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if data == b"show":
                    GLib.idle_add(window.present_and_focus)
                conn.close()
        except Exception:
            pass

    threading.Thread(target=server_thread, daemon=True).start()

class AskAIWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Ask AI")
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Fit height automatically to child widgets
        self.set_default_size(500, -1)
        
        # Ensure GTK draws default background styles (we will override with CSS)
        self.set_app_paintable(False)
        
        # Enable RGBA Visual for Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            self.set_visual(visual)
            
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("key-press-event", self.on_key_press)
        self.connect("button-press-event", self.on_button_press)
        
        # Outer container that supports CSS background rendering
        self.bg_box = Gtk.EventBox()
        self.bg_box.get_style_context().add_class("main-box")
        self.add(self.bg_box)
        
        # Main Layout Box with CSS styling
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(24)
        self.main_box.set_margin_bottom(24)
        self.bg_box.add(self.main_box)
        
        # Title bar (Label)
        self.title_label = Gtk.Label(label="Ask AI")
        self.title_label.set_xalign(0.0)
        self.title_label.get_style_context().add_class("title-label")
        self.main_box.pack_start(self.title_label, False, False, 0)
        
        # Input Entry
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Ask a question...")
        self.entry.get_style_context().add_class("text-entry")
        self.entry.connect("activate", self.on_submit)
        self.main_box.pack_start(self.entry, False, False, 0)
        
        # Loading State
        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.spinner = Gtk.Spinner()
        self.loading_label = Gtk.Label(label="Thinking...")
        self.loading_label.get_style_context().add_class("loading-label")
        self.loading_box.pack_start(self.spinner, False, False, 0)
        self.loading_box.pack_start(self.loading_label, False, False, 0)
        self.main_box.pack_start(self.loading_box, False, False, 0)
        
        # Answer Scroll View
        self.scroll_win = Gtk.ScrolledWindow()
        self.scroll_win.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll_win.set_shadow_type(Gtk.ShadowType.NONE)
        self.scroll_win.set_min_content_height(180)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.get_style_context().add_class("text-view")
        self.scroll_win.add(self.text_view)
        
        self.main_box.pack_start(self.scroll_win, True, True, 0)
        
        # Start Over / Reset Button (icon-based)
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.reset_btn = Gtk.Button()
        self.reset_btn.set_image(icon)
        self.reset_btn.get_style_context().add_class("btn-reset")
        self.reset_btn.connect("clicked", self.on_reset)
        
        # Center the reset button at the bottom
        self.reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.reset_box.set_center_widget(self.reset_btn)
        self.main_box.pack_start(self.reset_box, False, False, 0)
        
        # Apply CSS style sheet
        self.apply_css()
        
        # Initial GUI State
        self.show_input_state()

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: transparent;
                background-image: none;
                box-shadow: none;
            }
            .main-box {
                background-color: rgba(24, 24, 27, 0.94);
                background-image: none;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            .title-label {
                font-family: 'Outfit', 'Inter', sans-serif;
                font-size: 18px;
                font-weight: 800;
                color: #ffffff;
            }
            .text-entry {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                caret-color: #3584e4;
            }
            .text-entry:focus {
                border-color: #3584e4;
            }
            scrolledwindow, textview, textview text {
                background-color: transparent;
                background-image: none;
                color: #f3f4f6;
            }
            .text-view {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                color: #f3f4f6;
            }
            .loading-label {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                color: #a1a1aa;
                font-style: italic;
            }
            button.btn-reset {
                background-color: rgba(255, 255, 255, 0.08);
                background-image: none;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 8px;
                min-width: 36px;
                min-height: 36px;
                box-shadow: none;
            }
            button.btn-reset:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: #3584e4;
            }
            button.btn-reset image {
                color: #ffffff;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_button_press(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def on_focus_out(self, widget, event):
        # Prevent hiding if mouse is clicked/dragged inside window bounds
        x, y = self.get_pointer()
        alloc = self.get_allocation()
        if 0 <= x <= alloc.width and 0 <= y <= alloc.height:
            return False
        self.hide()
        return False

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def present_and_focus(self):
        self.present()
        self.show_input_state()

    def show_input_state(self):
        self.entry.show()
        self.loading_box.hide()
        self.spinner.stop()
        self.scroll_win.hide()
        self.reset_box.hide()
        self.entry.grab_focus()
        self.resize(500, 1) # Auto-shrink window to fit input content

    def show_loading_state(self):
        self.entry.hide()
        self.loading_box.show()
        self.spinner.start()
        self.scroll_win.hide()
        self.reset_box.hide()
        self.resize(500, 1)

    def show_answer_state(self, answer):
        self.entry.hide()
        self.loading_box.hide()
        self.spinner.stop()
        
        buf = self.text_view.get_buffer()
        buf.set_text(answer)
        
        self.scroll_win.show()
        self.reset_box.show()
        self.reset_btn.grab_focus()

    def on_submit(self, entry):
        prompt = entry.get_text().strip()
        if not prompt:
            return
            
        self.show_loading_state()
        
        config = load_config()
        model_choice = config.get("default_model", "llama")
        
        threading.Thread(target=self.bg_query, args=(prompt, model_choice), daemon=True).start()

    def bg_query(self, prompt, model_choice):
        result = run_query(prompt, model_choice)
        GLib.idle_add(self.show_answer_state, result)

    def on_reset(self, btn):
        self.entry.set_text("")
        self.show_input_state()

class AskAITrayApp:
    def __init__(self):
        self.window = AskAIWindow()
        self.menu = self.create_menu()
        
        if HAS_INDICATOR:
            # Native GNOME status notifier item (Tray Icon)
            self.indicator = AppIndicator.Indicator.new(
                "ask-ai-indicator",
                "dialog-question-symbolic",
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.indicator.set_menu(self.menu)
        else:
            # Fallback to old Gtk.StatusIcon
            self.status_icon = Gtk.StatusIcon()
            self.status_icon.set_from_icon_name("dialog-question-symbolic")
            self.status_icon.set_tooltip_text("Ask AI")
            self.status_icon.connect("activate", self.on_activate)
            self.status_icon.connect("popup-menu", self.on_popup_menu)

    def create_menu(self):
        menu = Gtk.Menu()
        
        config = load_config()
        current_model = config.get("default_model", "llama")
        
        model_item = Gtk.MenuItem(label=f"Active Model: {current_model}")
        model_item.set_sensitive(False)
        menu.append(model_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        show_item = Gtk.MenuItem(label="Ask a Question")
        show_item.connect("activate", lambda w: self.window.present_and_focus())
        menu.append(show_item)
        
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda w: Gtk.main_quit())
        menu.append(quit_item)
        
        menu.show_all()
        return menu

    def on_activate(self, icon):
        if self.window.is_visible():
            self.window.hide()
        else:
            self.window.present_and_focus()

    def on_popup_menu(self, icon, button, activate_time):
        self.menu.popup(None, None, None, None, button, activate_time)

def run_gui():
    if send_show_ipc():
        sys.exit(0)
        
    app = AskAITrayApp()
    start_ipc_server(app.window)
    
    app.window.show_all()
    app.window.present_and_focus()
    
    Gtk.main()

def print_usage():
    print("Ask AI - Desktop assistant for local LLMs\n")
    print("Usage:")
    print("  ask [prompt]                        Run prompt on the default model")
    print("  ask --model <model> [prompt]        Run prompt on a specified model")
    print("  ask --set-default-model <model>     Change default model config")
    print("  ask --gui                           Launch tray application service")
    print("\nModels:")
    print("  qwen, llama, llama-xs")
    print("\nExamples:")
    print("  ask \"How does photosynthesis work?\"")
    print("  ask --set-default-model llama-xs")
    print("  ask --gui &")

def main():
    args = sys.argv[1:]
    
    if not args:
        if sys.stdin.isatty():
            config = load_config()
            default_model = config.get("default_model", "llama")
            prompt = input(f"Enter prompt for {default_model}: ").strip()
            if prompt:
                print(run_query(prompt, default_model), end="")
        else:
            prompt = sys.stdin.read().strip()
            if prompt:
                config = load_config()
                default_model = config.get("default_model", "llama")
                print(run_query(prompt, default_model), end="")
        return

    if args[0] in ["-h", "--help"]:
        print_usage()
        return

    if args[0] == "--set-default-model":
        if len(args) < 2:
            print("Error: Missing model name. Choose from: qwen, llama, llama-xs", file=sys.stderr)
            sys.exit(1)
        model_name = args[1]
        if model_name not in MODELS:
            print(f"Error: Invalid model choice '{model_name}'. Choose from: qwen, llama, llama-xs", file=sys.stderr)
            sys.exit(1)
        config = load_config()
        config["default_model"] = model_name
        if save_config(config):
            print(f"Default model successfully set to: {model_name}")
        sys.exit(0)

    if args[0] == "--gui":
        run_gui()
        return

    if args[0] == "--model":
        if len(args) < 2:
            print("Error: Missing model name for --model flag.", file=sys.stderr)
            sys.exit(1)
        model_name = args[1]
        if model_name not in MODELS:
            print(f"Error: Invalid model choice '{model_name}'. Choose from: qwen, llama, llama-xs", file=sys.stderr)
            sys.exit(1)
        prompt_parts = args[2:]
        if not prompt_parts:
            prompt = input(f"Enter prompt for {model_name}: ").strip()
        else:
            prompt = " ".join(prompt_parts)
        
        if prompt:
            print(run_query(prompt, model_name), end="")
        return

    prompt = " ".join(args)
    config = load_config()
    default_model = config.get("default_model", "llama")
    print(run_query(prompt, default_model), end="")

if __name__ == "__main__":
    main()
