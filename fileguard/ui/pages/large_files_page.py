"""
Large Files Finder Page for FileGuard.
Identifies storage-heavy files by threshold, supports fast search/sort/filtering,
and safe Explorer revelation with thumbnail preview.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import FileRecord, format_bytes
from fileguard.database import Database
from fileguard.large_file_finder import LargeFileFinder
from fileguard.ui.components import SearchBar, PreviewPane


class LargeFilesPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette
        self.finder = LargeFileFinder(self.db)

        self.current_files: List[FileRecord] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        # Top Control Bar
        top_bar = tk.Frame(self, bg=bg)
        top_bar.pack(fill="x", pady=(0, 10))

        # Search bar
        self.search_bar = SearchBar(top_bar, placeholder="Search large files or directories...", on_search=lambda q: self.refresh(), palette=p)
        self.search_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Size threshold dropdown
        tk.Label(top_bar, text="Min Size:", font=("Segoe UI", 9), fg=text_sec, bg=bg).pack(side="left", padx=(0, 4))
        self.size_var = tk.StringVar(value="10 MB")
        self.size_cb = ttk.Combobox(
            top_bar,
            textvariable=self.size_var,
            values=["1 MB", "5 MB", "10 MB", "25 MB", "50 MB", "100 MB", "500 MB"],
            state="readonly",
            width=8
        )
        self.size_cb.pack(side="left", padx=(0, 10))
        self.size_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Category dropdown
        tk.Label(top_bar, text="Category:", font=("Segoe UI", 9), fg=text_sec, bg=bg).pack(side="left", padx=(0, 4))
        self.cat_var = tk.StringVar(value="All")
        self.cat_cb = ttk.Combobox(
            top_bar,
            textvariable=self.cat_var,
            values=["All", "Documents", "Images", "Video", "Audio", "Archives", "Code", "Other"],
            state="readonly",
            width=12
        )
        self.cat_cb.pack(side="left", padx=(0, 10))
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(top_bar, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="left")

        # Subheader info
        info_bar = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=6)
        info_bar.pack(fill="x", pady=(0, 10))

        self.info_lbl = tk.Label(info_bar, text="Found 0 large files (0 B)", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface)
        self.info_lbl.pack(side="left")

        # Paned Window (Left Table, Right Preview)
        self.paned = ttk.Panedwindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        table_frame = tk.Frame(self.paned, bg=bg)
        self.paned.add(table_frame, weight=3)

        cols = ("name", "size", "cat", "modified", "path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("name", text="File Name", command=lambda: self._sort_column("name"))
        self.tree.heading("size", text="Size", command=lambda: self._sort_column("size"))
        self.tree.heading("cat", text="Category", command=lambda: self._sort_column("cat"))
        self.tree.heading("modified", text="Last Modified", command=lambda: self._sort_column("modified"))
        self.tree.heading("path", text="Directory Path", command=lambda: self._sort_column("path"))

        self.tree.column("name", width=180)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("cat", width=90)
        self.tree.column("modified", width=130)
        self.tree.column("path", width=300)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.preview_pane._reveal_in_explorer())

        # Right Preview Frame
        self.preview_pane = PreviewPane(self.paned, palette=p)
        self.paned.add(self.preview_pane, weight=1)

    def refresh(self):
        # Convert selected threshold string to bytes
        val_str = self.size_var.get().replace(" MB", "")
        try:
            min_mb = int(val_str)
        except ValueError:
            min_mb = 10
        min_bytes = min_mb * 1024 * 1024

        q = self.search_bar.search_var.get().strip()
        cat = self.cat_var.get()

        self.current_files = self.finder.find_large_files(
            min_size_bytes=min_bytes,
            category=cat if cat != "All" else None,
            search_query=q if q else None
        )

        for it in self.tree.get_children():
            self.tree.delete(it)

        total_sz = 0
        for f in self.current_files:
            total_sz += f.size_bytes
            self.tree.insert("", "end", iid=str(f.id), values=(
                f.filename,
                f.formatted_size,
                f.category,
                f.formatted_modified,
                f.path
            ))

        self.info_lbl.config(
            text=f"Found {len(self.current_files)} files exceeding {min_mb} MB  |  Total: {format_bytes(total_sz)}"
        )

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        fid = int(sel[0])
        target = next((f for f in self.current_files if f.id == fid), None)
        if target:
            self.preview_pane.show_file(
                target.path,
                size_bytes=target.size_bytes,
                sha256_hash=target.sha256_hash,
                modified_time=target.formatted_modified
            )

    def _sort_column(self, col: str):
        # Simple column sort
        if col == "size":
            self.current_files.sort(key=lambda x: x.size_bytes, reverse=True)
        elif col == "name":
            self.current_files.sort(key=lambda x: x.filename.lower())
        elif col == "cat":
            self.current_files.sort(key=lambda x: x.category.lower())
        elif col == "modified":
            self.current_files.sort(key=lambda x: x.modified_time or 0, reverse=True)
        elif col == "path":
            self.current_files.sort(key=lambda x: x.path.lower())

        for it in self.tree.get_children():
            self.tree.delete(it)
        for f in self.current_files:
            self.tree.insert("", "end", iid=str(f.id), values=(
                f.filename,
                f.formatted_size,
                f.category,
                f.formatted_modified,
                f.path
            ))
