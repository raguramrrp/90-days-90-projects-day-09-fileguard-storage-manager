"""
Storage Analysis Page for FileGuard.
Provides storage intelligence: file-type breakdown, largest directories,
accurate non-double-counted nested folder hierarchy, and drive capacity metrics.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import format_bytes
from fileguard.database import Database
from fileguard.storage_analyzer import StorageAnalyzer


class StoragePage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.analyzer = StorageAnalyzer(self.db)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        # Header
        header = tk.Frame(self, bg=bg)
        header.pack(fill="x", pady=(0, 15))

        title_box = tk.Frame(header, bg=bg)
        title_box.pack(side="left")

        tk.Label(title_box, text="Storage Intelligence & Analysis", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        self.meta_lbl = tk.Label(title_box, text="Analyzing latest completed scan scope...", font=("Segoe UI", 9), fg=text_sec, bg=bg)
        self.meta_lbl.pack(anchor="w", pady=(2, 0))

        ttk.Button(header, text="🔄 Refresh Analytics", style="Secondary.TButton", command=self.refresh).pack(side="right")

        # Top Drive Space & Overview Bar
        self.drive_box = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=10)
        self.drive_box.pack(fill="x", pady=(0, 15))

        self.drive_lbl = tk.Label(self.drive_box, text="Drive Space: Calculating...", font=("Segoe UI", 9, "bold"), fg=text_pri, bg=surface)
        self.drive_lbl.pack(anchor="w")

        # Two-Column Layout (Left: File Categories, Right: Largest Folders)
        body = tk.Frame(self, bg=bg)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Left Column: Category Distribution Table & Bars
        left_panel = tk.Frame(body, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(left_panel, text="STORAGE BY FILE CATEGORY", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        cols_cat = ("cat", "size", "count", "pct")
        self.cat_tree = ttk.Treeview(left_panel, columns=cols_cat, show="headings", height=8)
        self.cat_tree.heading("cat", text="Category")
        self.cat_tree.heading("size", text="Total Size")
        self.cat_tree.heading("count", text="File Count")
        self.cat_tree.heading("pct", text="Share")

        self.cat_tree.column("cat", width=120)
        self.cat_tree.column("size", width=90, anchor="e")
        self.cat_tree.column("count", width=80, anchor="e")
        self.cat_tree.column("pct", width=70, anchor="e")

        self.cat_tree.pack(fill="both", expand=True, pady=(0, 10))

        tk.Label(left_panel, text="TOP FILE EXTENSIONS", font=("Segoe UI", 8, "bold"), fg=text_sec, bg=surface).pack(anchor="w", pady=(5, 4))
        self.ext_lbl = tk.Label(left_panel, text="", font=("Segoe UI", 8), fg=text_pri, bg=surface, justify="left")
        self.ext_lbl.pack(anchor="w")

        # Right Column: Largest Folders (without double-counting nested folders)
        right_panel = tk.Frame(body, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(right_panel, text="LARGEST DIRECT DIRECTORIES", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        cols_fold = ("path", "size", "count")
        self.fold_tree = ttk.Treeview(right_panel, columns=cols_fold, show="headings", height=10)
        self.fold_tree.heading("path", text="Directory Path")
        self.fold_tree.heading("size", text="Size")
        self.fold_tree.heading("count", text="Files")

        self.fold_tree.column("path", width=220)
        self.fold_tree.column("size", width=85, anchor="e")
        self.fold_tree.column("count", width=60, anchor="e")

        self.fold_tree.pack(fill="both", expand=True)

    def refresh(self):
        latest = self.db.get_latest_scan()
        if not latest:
            self.meta_lbl.config(text="No completed scans found. Please run a scan first.")
            self.drive_lbl.config(text="Drive Space: Not available until a scan root is selected.")
            return

        self.meta_lbl.config(
            text=f"Scan #{latest.id} ({latest.scan_name})  •  Completed: {(latest.completed_at or '')[:16]}  •  "
                 f"Indexed: {latest.formatted_indexed_size} across {latest.files_processed:,} files"
        )

        analysis = self.analyzer.analyze_scan_storage(latest.id)

        # Drive stats
        d_stats = analysis.get("drive_stats", [])
        if d_stats:
            d_parts = [
                f"{d['drive']} Total: {d['formatted_total']} | Used: {d['formatted_used']} | Free: {d['formatted_free']} ({d['free_percent']}% available)"
                for d in d_stats
            ]
            self.drive_lbl.config(text="  •  ".join(d_parts))
        else:
            self.drive_lbl.config(text=f"Total Indexed File Size: {analysis['formatted_total_bytes']}")

        # Categories
        for it in self.cat_tree.get_children():
            self.cat_tree.delete(it)

        for c in analysis.get("categories", []):
            self.cat_tree.insert("", "end", values=(
                c["category"],
                c["formatted_bytes"],
                f"{c['count']:,}",
                f"{c['percentage']}%"
            ))

        # Top extensions
        top_e = analysis.get("top_extensions", [])[:5]
        e_str = "   ".join([f"{e['extension']}: {e['formatted_bytes']}" for e in top_e])
        self.ext_lbl.config(text=e_str if e_str else "No extension breakdown available")

        # Largest Folders
        for it in self.fold_tree.get_children():
            self.fold_tree.delete(it)

        for f in analysis.get("largest_direct_folders", []):
            self.fold_tree.insert("", "end", values=(
                f["path"],
                f["formatted_bytes"],
                f["file_count"]
            ))
