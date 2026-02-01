import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from tkinterdnd2 import TkinterDnD, DND_FILES

TIPS_TEXT = """自制GUI, 不喜勿喷
Based on:
(used binaries) BBDown, ffmpeg, aria2c
(from Python) tkinter, tkinterdnd2

Usage:
- 输入视频链接, 选择模式, 点击“Process”
- 将.m4a文件拖拽到下方区域
  使其转换为mp3并删除原文件

Known Issues:
1. 若目录下存在同一标题的视频, 
   即使选择“Audio Only”模式, 
   再下载同一视频仍会跳过

To Do:
1. 想办法确定生成的文件名称
   以实现m4a自动转mp3
"""

# ============================================================
# Runtime / PyInstaller helpers
# ============================================================


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource (works for dev & PyInstaller)."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# Hide console window when packaged with PyInstaller (Windows only)
if getattr(sys, "frozen", False) and sys.platform.startswith("win"):
    try:
        import ctypes

        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

# ============================================================
# External tools paths
# ============================================================

BBDOWN_PATH = resource_path(
    os.path.join(
        "utils",
        "BBDown",
        "BBDown.exe",
    )
)

FFMPEG_PATH = resource_path(
    os.path.join(
        "utils",
        "ffmpeg-7.1-essentials_build",
        "bin",
        "ffmpeg.exe",
    )
)

ARIA2C_PATH = resource_path(
    os.path.join(
        "utils",
        "aria2-1.37.0-win-64bit-build1",
        "aria2c.exe",
    )
)


# ============================================================
# Context menus & readonly helpers
# ============================================================


def make_text_context_menu(widget: tk.Widget) -> None:
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(
        label="Select All", command=lambda: widget.event_generate("<<SelectAll>>")
    )

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
    widget.bind("<Control-Button-1>", show_menu)  # macOS


def make_readonly_context_menu(widget: tk.Widget) -> None:
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(
        label="Select All", command=lambda: widget.event_generate("<<SelectAll>>")
    )

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
    widget.bind("<Control-Button-1>", show_menu)  # macOS


def readonly_text_key_handler(event):
    """Allow navigation & copy shortcuts, block modifications."""
    # Ctrl+C / Ctrl+A
    if (event.state & 0x4) and event.keysym.lower() in ("c", "a"):
        return

    # Navigation keys
    if event.keysym in (
        "Left",
        "Right",
        "Up",
        "Down",
        "Home",
        "End",
        "Prior",
        "Next",
        "Escape",
    ):
        return

    return "break"


# ============================================================
# Business logic
# ============================================================


def process_url():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a URL.")
        return

    url = url.split("?")[0]
    log_text.insert(tk.END, f"Processing URL: {url}\n")

    try:
        cmd = [BBDOWN_PATH]

        if download_mode.get() == "audio":
            cmd.append("--audio-only")
        # --use-aria2c
        cmd.append("--use-aria2c")
        # --ffmpeg-path ".\utils\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe"
        cmd.append("--ffmpeg-path")
        cmd.append(FFMPEG_PATH)
        # --aria2c-path ".\utils\aria2-1.37.0-win-64bit-build1\aria2c.exe"
        cmd.append("--aria2c-path")
        cmd.append(ARIA2C_PATH)
        cmd.append(url)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
        )

        assert process.stdout is not None
        assert process.stderr is not None

        for line in process.stdout:
            log_text.insert(tk.END, line)
            log_text.see(tk.END)
            log_text.update_idletasks()

        process.wait()
        log_text.insert(tk.END, f"Download complete for URL: {url}\n")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


def process_file(file_path: str):
    if not file_path.lower().endswith(".m4a"):
        log_text.insert(tk.END, "Error: Only .m4a files are supported.\n")
        log_text.see(tk.END)
        return

    output_file = file_path[:-4] + ".mp3"
    log_text.insert(
        tk.END, f"Starting ffmpeg conversion:\n{file_path} -> {output_file}\n"
    )
    log_text.see(tk.END)

    try:
        process = subprocess.Popen(
            [
                FFMPEG_PATH,
                "-i",
                file_path,
                "-q:a",
                "0",
                "-map",
                "a",
                output_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",  # It's strange that ffmpeg uses UTF-8 but BBDown uses system encoding
            text=True,
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
        )

        assert process.stdout is not None
        assert process.stderr is not None

        # ffmpeg writes progress mostly to stderr
        for line in process.stderr:
            log_text.insert(tk.END, line)
            log_text.see(tk.END)
            log_text.update_idletasks()

        process.wait()

        if process.returncode == 0:
            log_text.insert(tk.END, f"Conversion successful: {output_file}\n")
            os.remove(file_path)
            log_text.insert(tk.END, f"Deleted original file: {file_path}\n")
        else:
            log_text.insert(tk.END, f"ffmpeg exited with code {process.returncode}\n")

        log_text.see(tk.END)

    except FileNotFoundError:
        log_text.insert(tk.END, f"Error: ffmpeg not found at path:\n{FFMPEG_PATH}\n")
        log_text.see(tk.END)

    except Exception as e:
        log_text.insert(tk.END, f"An unexpected error occurred: {e}\n")
        log_text.see(tk.END)


def on_file_drop(event):
    file_path = event.data.strip()
    if file_path.startswith("{") and file_path.endswith("}"):
        file_path = file_path[1:-1]
    process_file(file_path)


# ============================================================
# UI setup
# ============================================================

root = TkinterDnD.Tk()
root.title("BBDown GUI")

# =========================
# Top control frame
# =========================

main_frame = tk.Frame(root)
main_frame.pack(fill="x", padx=10, pady=8)

left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill="x", expand=True)

top_frame = tk.Frame(left_frame)
top_frame.pack(fill="x", padx=10, pady=8)

url_label = tk.Label(top_frame, text="Bilibili URL:")
url_label.pack(anchor="w")

url_entry = tk.Entry(top_frame)
url_entry.pack(fill="x", pady=4)
make_text_context_menu(url_entry)

mode_frame = tk.LabelFrame(top_frame, text="Download Mode")
mode_frame.pack(anchor="w", pady=4)

download_mode = tk.StringVar(value="video")

tk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT, padx=(0, 8))

tk.Radiobutton(
    mode_frame,
    text="Video",
    variable=download_mode,
    value="video",
).pack(side=tk.LEFT)

tk.Radiobutton(
    mode_frame,
    text="Audio",
    variable=download_mode,
    value="audio",
).pack(side=tk.LEFT)

# =========================
# Action frame
# =========================
action_frame = tk.Frame(left_frame)
action_frame.pack(pady=6)

process_button = tk.Button(
    action_frame,
    text="Process",
    font=("Segoe UI", 10, "bold"),
    command=process_url,
)
process_button.pack()

# =========================
# Log frame
# =========================
log_frame = tk.Frame(left_frame)
log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

log_text = ScrolledText(log_frame, height=12)
log_text.pack(fill="both", expand=True)
make_readonly_context_menu(log_text)
log_text.bind("<Key>", readonly_text_key_handler)

# =========================
# Drag & drop frame
# =========================
drag_label = tk.Label(
    root,
    text="Drag and drop an .m4a file here",
    bg="#eaeaea",
    relief="groove",
    height=4,
)
drag_label.pack(fill="x", padx=10, pady=(0, 10))

drag_label.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
drag_label.dnd_bind("<<Drop>>", on_file_drop)  # type: ignore[attr-defined]

right_frame = tk.LabelFrame(main_frame, text="Tips", padx=8, pady=6)
right_frame.pack(side=tk.RIGHT, fill="y", padx=(10, 0))

tips_label = tk.Label(
    right_frame,
    text=TIPS_TEXT,
    justify=tk.LEFT,
    anchor="nw",
    wraplength=240,
)
tips_label.pack(fill="both", expand=True)


# ============================================================
# Main loop
# ============================================================
# messagebox.showinfo("欢迎", STARTUP_MESSAGE)
root.mainloop()
