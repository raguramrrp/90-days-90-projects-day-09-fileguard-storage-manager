"""
Reusable Custom UI Components for FileGuard.
Provides Stat Cards, Search Bars, Table Panes, File Preview with Image Thumbnails,
and Explorer Actions.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Callable, Dict, Any
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from fileguard.models import FileRecord, format_bytes
from fileguard.config import categorize_file


class StatCard(tk.Frame):
    """Clean KPI Metric Card with subtle border and clear typography."""
    def __init__(
        self,
        parent,
        title: str,
        value: str,
        subtitle: str = "",
        palette: Dict[str, str] = None,
        accent_color: Optional[str] = None,
        **kwargs
    ):
        p = palette or {}
        bg = p.get("surface", "#1e293b")
        border = p.get("border", "#334155")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = accent_color or p.get("accent", "#14b8a6")

        super().__init__(parent, bg=bg, highlightbackground=border, highlightthickness=1, padx=16, pady=12, **kwargs)

        self.title_lbl = tk.Label(self, text=title.upper(), font=("Segoe UI", 8, "bold"), fg=text_sec, bg=bg, anchor="w")
        self.title_lbl.pack(fill="x")

        self.val_lbl = tk.Label(self, text=value, font=("Segoe UI", 18, "bold"), fg=accent, bg=bg, anchor="w")
        self.val_lbl.pack(fill="x", pady=(4, 2))

        if subtitle:
            self.sub_lbl = tk.Label(self, text=subtitle, font=("Segoe UI", 8), fg=text_sec, bg=bg, anchor="w")
            self.sub_lbl.pack(fill="x")
        else:
            self.sub_lbl = None

    def update_values(self, value: str, subtitle: Optional[str] = None):
        self.val_lbl.config(text=value)
        if subtitle and self.sub_lbl:
            self.sub_lbl.config(text=subtitle)


class SearchBar(tk.Frame):
    """Filter and Search bar component with callback on entry change."""
    def __init__(self, parent, placeholder: str = "Search files or paths (Ctrl+F)...", on_search: Optional[Callable[[str], None]] = None, palette: Dict[str, str] = None, **kwargs):
        p = palette or {}
        bg = p.get("surface", "#1e293b")
        fg = p.get("text_primary", "#f8fafc")
        border = p.get("border", "#334155")

        super().__init__(parent, bg=bg, highlightbackground=border, highlightthickness=1, padx=8, pady=4, **kwargs)
        self.on_search = on_search

        self.icon_lbl = tk.Label(self, text="🔍", font=("Segoe UI", 9), fg=p.get("text_secondary", "#94a3b8"), bg=bg)
        self.icon_lbl.pack(side="left", padx=(0, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_change)

        self.entry = tk.Entry(
            self,
            textvariable=self.search_var,
            font=("Segoe UI", 9),
            bg=p.get("input_bg", "#0f172a"),
            fg=fg,
            insertbackground=fg,
            relief="flat",
            bd=0
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=4)

        self.clear_btn = tk.Button(
            self,
            text="✕",
            font=("Segoe UI", 8),
            bg=bg,
            fg=p.get("text_secondary", "#94a3b8"),
            activebackground=bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.clear
        )
        self.clear_btn.pack(side="right")

    def _on_change(self, *args):
        if self.on_search:
            self.on_search(self.search_var.get().strip())

    def clear(self):
        self.search_var.set("")
        self.entry.focus_set()

    def focus(self):
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)


class PreviewPane(tk.Frame):
    """File details and safe thumbnail/text preview pane."""
    def __init__(self, parent, palette: Dict[str, str] = None, **kwargs):
        p = palette or {}
        self.palette = p
        bg = p.get("surface", "#1e293b")
        border = p.get("border", "#334155")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")

        super().__init__(parent, bg=bg, highlightbackground=border, highlightthickness=1, padx=12, pady=12, **kwargs)

        self.current_file_path: Optional[str] = None
        self._photo_ref = None  # Prevent GC of PhotoImage

        # Title
        title_lbl = tk.Label(self, text="FILE DETAILS & PREVIEW", font=("Segoe UI", 9, "bold"), fg=p.get("accent", "#14b8a6"), bg=bg, anchor="w")
        title_lbl.pack(fill="x", pady=(0, 10))

        # Preview Container (Thumbnail or Info)
        self.preview_frame = tk.Frame(self, bg=p.get("bg", "#0f172a"), height=160, highlightbackground=border, highlightthickness=1)
        self.preview_frame.pack(fill="x", pady=(0, 10))
        self.preview_frame.pack_propagate(False)

        self.thumbnail_label = tk.Label(self.preview_frame, bg=p.get("bg", "#0f172a"), fg=text_sec, text="Select a file to inspect", font=("Segoe UI", 8))
        self.thumbnail_label.pack(expand=True, fill="both")

        # Text snippet scrolled view (hidden by default)
        self.text_preview = scrolledtext.ScrolledText(
            self.preview_frame,
            wrap="word",
            font=("Consolas", 8),
            bg=p.get("bg", "#0f172a"),
            fg=text_pri,
            insertbackground=text_pri,
            bd=0
        )

        # Metadata fields
        self.meta_frame = tk.Frame(self, bg=bg)
        self.meta_frame.pack(fill="both", expand=True)

        self.lbl_name = self._make_meta_row("Name:", "-")
        self.lbl_size = self._make_meta_row("Size:", "-")
        self.lbl_cat = self._make_meta_row("Category:", "-")
        self.lbl_modified = self._make_meta_row("Modified:", "-")
        self.lbl_hash = self._make_meta_row("SHA-256:", "-")
        self.lbl_path = self._make_meta_row("Path:", "-")

        # Action Buttons
        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill="x", pady=(10, 0))

        self.btn_reveal = ttk.Button(
            btn_frame,
            text="Reveal in Explorer",
            style="Secondary.TButton",
            command=self._reveal_in_explorer
        )
        self.btn_reveal.pack(fill="x", pady=2)

    def _make_meta_row(self, label: str, default_val: str) -> tk.Label:
        row = tk.Frame(self.meta_frame, bg=self.palette.get("surface", "#1e293b"))
        row.pack(fill="x", pady=2)
        lbl = tk.Label(row, text=label, font=("Segoe UI", 8, "bold"), fg=self.palette.get("text_secondary", "#94a3b8"), bg=self.palette.get("surface", "#1e293b"), width=10, anchor="w")
        lbl.pack(side="left")
        val = tk.Label(row, text=default_val, font=("Segoe UI", 8), fg=self.palette.get("text_primary", "#f8fafc"), bg=self.palette.get("surface", "#1e293b"), anchor="w", wraplength=220, justify="left")
        val.pack(side="left", fill="x", expand=True)
        return val

    def show_file(self, file_path: str, size_bytes: Optional[int] = None, sha256_hash: Optional[str] = None, modified_time: Optional[str] = None):
        """Update pane with details and thumbnail/text snippet of file."""
        self.current_file_path = file_path
        abs_path = os.path.abspath(file_path)

        if not os.path.exists(abs_path):
            self.thumbnail_label.config(text="File does not exist on disk", image="")
            self.lbl_name.config(text=Path(abs_path).name)
            self.lbl_size.config(text=format_bytes(size_bytes or 0))
            self.lbl_path.config(text=abs_path)
            return

        p = Path(abs_path)
        ext = p.suffix.lower()
        cat = categorize_file(ext)
        st = os.stat(abs_path)

        self.lbl_name.config(text=p.name)
        self.lbl_size.config(text=format_bytes(size_bytes or st.st_size))
        self.lbl_cat.config(text=cat)
        self.lbl_modified.config(text=modified_time or str(st.st_mtime)[:19])
        self.lbl_hash.config(text=f"{sha256_hash[:16]}..." if sha256_hash else "Unverified")
        self.lbl_path.config(text=abs_path)

        # Thumbnail or Text Preview
        if cat == "Images" and HAS_PIL:
            self.text_preview.pack_forget()
            self.thumbnail_label.pack(expand=True, fill="both")
            try:
                with Image.open(abs_path) as img:
                    img.thumbnail((200, 150))
                    self._photo_ref = ImageTk.PhotoImage(img)
                    self.thumbnail_label.config(image=self._photo_ref, text="")
            except Exception:
                self.thumbnail_label.config(text="Cannot decode image preview", image="")
        elif cat in ("Documents", "Code") and ext in (".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".xml", ".sql"):
            self.thumbnail_label.pack_forget()
            self.text_preview.pack(expand=True, fill="both")
            self.text_preview.config(state="normal")
            self.text_preview.delete("1.0", tk.END)
            try:
                # Read up to 10 KB safely
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(10240)
                    self.text_preview.insert(tk.END, content)
            except Exception as e:
                self.text_preview.insert(tk.END, f"Preview unavailable: {e}")
            self.text_preview.config(state="disabled")
        else:
            self.text_preview.pack_forget()
            self.thumbnail_label.pack(expand=True, fill="both")
            self.thumbnail_label.config(
                image="",
                text=f"{cat} file\n({ext or 'no extension'})\n\nClick 'Reveal in Explorer' to open."
            )

    def _reveal_in_explorer(self):
        if not self.current_file_path:
            return
        abs_path = os.path.abspath(self.current_file_path)
        if not os.path.exists(abs_path):
            return
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer.exe", f"/select,{abs_path}"])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(abs_path)])
