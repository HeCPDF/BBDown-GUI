import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from tkinterdnd2 import TkinterDnD, DND_FILES
import re
import json

TIPS_TEXT = """自制GUI, 不喜勿喷
Based on:
(used binaries) BBDown, ffmpeg, aria2c
(from Python) tkinter, tkinterdnd2

Usage:
- 输入视频链接, 选择模式, 点击“Process”
- 将.m4a文件拖拽到下方区域
  使其转换为mp3并删除原文件
"""


# ============================================================
# Helpers
# ============================================================

def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ============================================================
# Main GUI Class
# ============================================================

class BBDownGUI:

    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("BBDown GUI")

        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config.json"
        )

        self._hide_console()
        self._init_paths()
        self._build_ui()

        self.load_config()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def open_priority_editor(self, title, variable: tk.StringVar, candidates: list[str]):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        frame = tk.Frame(win, padx=10, pady=10)
        frame.pack()

        tk.Label(frame, text=title).pack(anchor="w")

        listbox = tk.Listbox(frame, width=30, height=8, selectmode=tk.SINGLE)
        listbox.pack(side=tk.LEFT, pady=6)

        # scrollbar
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        # content initialization
        current = [x.strip() for x in variable.get().split(",") if x.strip()]
        items = []

        for x in current:
            if x in candidates:
                items.append(x)

        for x in candidates:
            if x not in items:
                items.append(x)

        for item in items:
            listbox.insert(tk.END, item)

        # buttons
        btn_frame = tk.Frame(frame)
        btn_frame.pack(side=tk.LEFT, padx=8)

        def move_up():
            i = listbox.curselection()
            if not i or i[0] == 0:
                return
            idx = i[0]
            text = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx - 1, text)
            listbox.select_set(idx - 1)

        def move_down():
            i = listbox.curselection()
            if not i or i[0] == listbox.size() - 1:
                return
            idx = i[0]
            text = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx + 1, text)
            listbox.select_set(idx + 1)

        tk.Button(btn_frame, text="↑ Up", width=6, command=move_up).pack(pady=2)
        tk.Button(btn_frame, text="↓ Down", width=6, command=move_down).pack(pady=2)

        # bottom buttons
        bottom = tk.Frame(win, pady=6)
        bottom.pack()

        def confirm():
            result = ",".join(listbox.get(0, tk.END))
            variable.set(result)
            win.destroy()

        tk.Button(bottom, text="OK", width=8, command=confirm).pack(side=tk.LEFT, padx=6)
        tk.Button(bottom, text="Cancel", width=8, command=win.destroy).pack(side=tk.LEFT)

    def save_config(self):
        data = {
            "download_mode": self.download_mode.get(),
            "page_type": self.choosed_page_type.get(),
            "page_value": self.page_input_mode_2.get(),
            "delay_enabled": self.delay_enabled.get(),
            "delay_seconds": self.delay_seconds.get(),
            "force_http": self.force_http.get(),
            "download_danmaku": self.download_danmaku.get(),
            "video_ascending": self.video_ascending.get(),
            "audio_ascending": self.audio_ascending.get(),
            "allow_pcdn": self.allow_pcdn.get(),
            "encoding_priority": self.encoding_priority.get(),
            "dfn_priority": self.dfn_priority.get(),
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Failed to save config:", e)

    def load_config(self):
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.download_mode.set(data.get("download_mode", "video"))

        self.choosed_page_type.set(data.get("page_type", 0))
        self.page_input_mode_2.delete(0, tk.END)
        self.page_input_mode_2.insert(0, data.get("page_value", ""))

        self.delay_enabled.set(data.get("delay_enabled", False))
        self.delay_seconds.set(data.get("delay_seconds", "2"))
        self._on_delay_toggle()

        self.force_http.set(data.get("force_http", True))
        self.download_danmaku.set(data.get("download_danmaku", False))
        self.video_ascending.set(data.get("video_ascending", False))
        self.audio_ascending.set(data.get("audio_ascending", False))
        self.allow_pcdn.set(data.get("allow_pcdn", False))

        self.encoding_priority.set(data.get("encoding_priority", ""))
        self.dfn_priority.set(data.get("dfn_priority", ""))

        self._on_page_type_changed()

    def _on_close(self):
        self.save_config()
        self.root.destroy()

    # --------------------------------------------------------
    # Context Menu
    # --------------------------------------------------------
    def make_text_context_menu(self, widget: tk.Widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Control-Button-1>", show_menu)

    # --------------------------------------------------------
    # Init helpers
    # --------------------------------------------------------

    def _hide_console(self):
        if getattr(sys, "frozen", False) and sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0
                )
            except Exception:
                pass

    def _init_paths(self):
        self.bbdown_path = resource_path("utils/BBDown/BBDown.exe")
        self.ffmpeg_path = resource_path("utils/ffmpeg/bin/ffmpeg.exe")
        self.aria2c_path = resource_path("utils/aria2/aria2c.exe")

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="x", padx=10, pady=8)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill="both", expand=True)

        self._build_top(left_frame)
        self._build_actions(left_frame)
        self._build_log(left_frame)
        self._build_drag_area()

        self._build_tips(main_frame)

    def _build_top(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=8)

        tk.Label(frame, text="Bilibili URL:").pack(anchor="w")

        self.url_entry = tk.Entry(frame)
        self.url_entry.pack(fill="x", pady=4)
        self.make_text_context_menu(self.url_entry)

        self._build_controls(frame)

    def _build_controls(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=4)
        self._build_download_mode(frame)
        self._build_page_chooser(frame)
        self._build_advanced_settings(frame)

    def _build_download_mode(self, parent):
        mode_frame = tk.LabelFrame(parent, text="Download Mode")
        mode_frame.pack(anchor="w", pady=4)

        self.download_mode = tk.StringVar(value="video")

        tk.Radiobutton(mode_frame, text="Video", variable=self.download_mode, value="video").pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Audio", variable=self.download_mode, value="audio").pack(side=tk.LEFT)

    # ---------------- PAGE CHOOSER ----------------

    def _on_page_type_changed(self):
        enable = self.choosed_page_type.get() == 2
        self.page_input_mode_2.configure(state=tk.NORMAL if enable else tk.DISABLED)
        if enable:
            self.page_input_mode_2.focus_set()

    def _build_page_chooser(self, parent):
        page_frame = tk.LabelFrame(parent, text="Page Chooser")
        page_frame.pack(fill="x", pady=6)

        self.choosed_page_type = tk.IntVar(value=0)

        tk.Radiobutton(page_frame, text="P1", variable=self.choosed_page_type, value=0, command=self._on_page_type_changed).pack(anchor="w")
        tk.Radiobutton(page_frame, text="ALL", variable=self.choosed_page_type, value=1, command=self._on_page_type_changed).pack(anchor="w")
        tk.Radiobutton(page_frame, text="Advanced", variable=self.choosed_page_type, value=2, command=self._on_page_type_changed).pack(anchor="w")

        adv_frame = tk.Frame(page_frame)
        adv_frame.pack(anchor="w", padx=24, pady=2)

        tk.Label(adv_frame, text="page:").pack(side=tk.LEFT)

        self.page_input_mode_2 = tk.Entry(adv_frame, width=24)
        self.page_input_mode_2.pack(side=tk.LEFT, padx=6)
        self.make_text_context_menu(self.page_input_mode_2)

        tk.Label(adv_frame, text="e.g. 8 | 1-2 | 3-5 | ALL | LAST | LATEST", fg="gray").pack(side=tk.LEFT)

        self.page_input_mode_2.configure(state=tk.DISABLED)

    # ---------------- ADVANCED SETTINGS ----------------

    def _on_delay_toggle(self):
        self.delay_entry.configure(state=tk.NORMAL if self.delay_enabled.get() else tk.DISABLED)

    def _build_advanced_settings(self, parent):
        adv_frame = tk.LabelFrame(parent, text="Advanced Settings")
        adv_frame.pack(fill="x", pady=6)

        # flags
        self.force_http = tk.BooleanVar(value=True)
        self.download_danmaku = tk.BooleanVar(value=False)
        self.video_ascending = tk.BooleanVar(value=False)
        self.audio_ascending = tk.BooleanVar(value=False)
        self.allow_pcdn = tk.BooleanVar(value=False)

        tk.Checkbutton(adv_frame, text="Force HTTP (disable HTTPS)", variable=self.force_http).grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Checkbutton(adv_frame, text="Download Danmaku", variable=self.download_danmaku).grid(row=1, column=0, columnspan=3, sticky="w")
        tk.Checkbutton(adv_frame, text="Video Ascending (smaller size first)", variable=self.video_ascending).grid(row=2, column=0, columnspan=3, sticky="w")
        tk.Checkbutton(adv_frame, text="Audio Ascending (smaller size first)", variable=self.audio_ascending).grid(row=3, column=0, columnspan=3, sticky="w")
        tk.Checkbutton(adv_frame, text="Allow PCDN (fallback only)", variable=self.allow_pcdn).grid(row=4, column=0, columnspan=3, sticky="w")

        # delay
        self.delay_enabled = tk.BooleanVar(value=False)
        self.delay_seconds = tk.StringVar(value="2")

        tk.Checkbutton(adv_frame, text="Delay between parts (seconds)", variable=self.delay_enabled, command=self._on_delay_toggle).grid(row=5, column=0, sticky="w")

        self.delay_entry = tk.Entry(adv_frame, width=6, textvariable=self.delay_seconds)
        self.delay_entry.grid(row=5, column=1, padx=6)
        self.make_text_context_menu(self.delay_entry)
        tk.Label(adv_frame, text="sec", fg="gray").grid(row=5, column=2, sticky="w")

        self.delay_entry.configure(state=tk.DISABLED)

        # encoding priority (DEFAULT EMPTY)
        tk.Label(adv_frame, text="Encoding Priority:").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.encoding_priority = tk.StringVar(value="")
        self.encoding_entry = tk.Entry(adv_frame, textvariable=self.encoding_priority, width=32)
        self.encoding_entry.grid(row=7, column=0, columnspan=2, sticky="w", padx=6)

        tk.Button(
            adv_frame,
            text="Edit",
            width=6,
            command=lambda: self.open_priority_editor(
                title="Encoding Priority",
                variable=self.encoding_priority,
                candidates=["hevc", "av1", "avc"]
            )
        ).grid(row=7, column=2, sticky="w")
        self.make_text_context_menu(self.encoding_entry)
        tk.Label(adv_frame, text="e.g. hevc,av1,avc", fg="gray").grid(row=8, column=0, columnspan=3, sticky="w", padx=6)

        

        # quality priority (DEFAULT EMPTY)
        tk.Label(adv_frame, text="Quality Priority:").grid(row=9, column=0, sticky="w", pady=(8, 0))
        self.dfn_priority = tk.StringVar(value="")
        self.dfn_entry = tk.Entry(adv_frame, textvariable=self.dfn_priority, width=32)
        self.dfn_entry.grid(row=10, column=0, columnspan=2, sticky="w", padx=6)

        tk.Button(
            adv_frame,
            text="Edit",
            width=6,
            command=lambda: self.open_priority_editor(
                title="Quality Priority",
                variable=self.dfn_priority,
                candidates=[
                    "8K 超高清",
                    "4K 超清",
                    "1080P 高码率",
                    "1080P 60帧",
                    "1080P 高清",
                    "720P 高清",
                    "480P 清晰",
                    "360P 流畅",
                ]
            )
        ).grid(row=10, column=2, sticky="w")
        self.make_text_context_menu(self.dfn_entry)
        tk.Label(adv_frame, text="e.g. 8K 超高清,1080P 高码率,HDR 真彩", fg="gray").grid(row=11, column=0, columnspan=3, sticky="w", padx=6)

    # ---------------- ACTIONS ----------------

    def _build_actions(self, parent):
        frame = tk.Frame(parent)
        frame.pack(pady=6)

        tk.Button(frame, text="Process", font=("Segoe UI", 10, "bold"), command=self.process_url).pack()

    def _build_log(self, parent):
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.log_text = ScrolledText(frame, height=12)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.bind("<Key>", lambda e: "break")

    # ---------------- DND ----------------

    def _build_drag_area(self):
        label = tk.Label(self.root, text="Drag and drop an .m4a file here", bg="#eaeaea", relief="groove", height=4)
        label.pack(fill="x", padx=10, pady=(0, 10))
        label.drop_target_register(DND_FILES) # type: ignore[attr-defined]
        label.dnd_bind("<<Drop>>", self.on_file_drop) # type: ignore[attr-defined]

    def _build_tips(self, parent):
        frame = tk.LabelFrame(parent, text="Tips", padx=8, pady=6)
        frame.pack(side=tk.RIGHT, fill="y", padx=(10, 0))

        tk.Label(frame, text=TIPS_TEXT, justify=tk.LEFT, anchor="nw", wraplength=240).pack(fill="both", expand=True)

    # --------------------------------------------------------
    # Logic
    # --------------------------------------------------------

    def log(self, text: str):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def _process_make_cmd(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL.")
            return None

        url = url.split("?")[0]
        self.log(f"Processing URL: {url}\n")

        cmd = [self.bbdown_path]

        if self.download_mode.get() == "audio":
            cmd.append("--audio-only")

        cmd += ["--use-aria2c", "--ffmpeg-path", self.ffmpeg_path, "--aria2c-path", self.aria2c_path]

        # page chooser
        page_type = self.choosed_page_type.get()
        if page_type == 1:
            cmd += ["-p", "ALL"]
        elif page_type == 2:
            page = self.page_input_mode_2.get().strip()
            if not page:
                messagebox.showerror("Error", "Please enter the page(s).")
                return None
            cmd += ["--select-page", page]

        # delay
        if self.delay_enabled.get():
            delay = self.delay_seconds.get().strip()
            if not delay:
                messagebox.showerror("Error", "Please enter delay seconds.")
                return None
            cmd += ["--delay-per-page", delay]

        # flags
        if self.force_http.get(): cmd.append("--force-http")
        if self.download_danmaku.get(): cmd.append("--download-danmaku")
        if self.video_ascending.get(): cmd.append("--video-ascending")
        if self.audio_ascending.get(): cmd.append("--audio-ascending")
        if self.allow_pcdn.get(): cmd.append("--allow-pcdn")

        # encoding priority
        encoding = self.encoding_priority.get().strip()
        if encoding:
            if not re.fullmatch(r"[a-zA-Z0-9,]+", encoding):
                messagebox.showerror("Error", "Encoding format invalid. Example: hevc,av1,avc")
                return None
            cmd += ["--encoding-priority", encoding]

        # quality priority
        dfn = self.dfn_priority.get().strip()
        if dfn:
            cmd += ["--dfn-priority", dfn]

        cmd.append(url)
        return cmd

    def process_url(self):
        self.save_config()
        cmd = self._process_make_cmd()
        if not cmd:
            return

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self.log(line)

        process.wait()
        self.log("Download complete.\n")

    # --------- M4A CONVERT ---------

    def process_file(self, file_path):
        if not file_path.lower().endswith(".m4a"):
            self.log("Only .m4a files are supported.\n")
            return

        output = file_path[:-4] + ".mp3"
        self.log(f"Converting:\n{file_path}\n→ {output}\n")

        process = subprocess.Popen(
            [self.ffmpeg_path, "-i", file_path, "-q:a", "0", "-map", "a", output],
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0,
        )

        assert process.stderr is not None

        for line in process.stderr:
            self.log(line)

        process.wait()
        if process.returncode == 0:
            os.remove(file_path)
            self.log("Conversion done & source deleted.\n")

    def on_file_drop(self, event):
        path = event.data.strip("{}")
        self.process_file(path)

    # --------------------------------------------------------
    # Run
    # --------------------------------------------------------

    def run(self):
        self.root.mainloop()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    BBDownGUI().run()
