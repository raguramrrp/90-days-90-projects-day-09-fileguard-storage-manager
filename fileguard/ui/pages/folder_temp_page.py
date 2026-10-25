"""
Empty Folders and Temporary Files Analysis Page for FileGuard.
Provides dual-inspection capabilities:
1. Genuinely empty directory discovery with inaccessible/protected discrimination.
2. Rule-based temporary file candidate identification with reason explanations.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import format_bytes
from fileguard.database import Database
from fileguard.folder_analyzer import FolderAnalyzer
from fileguard.temporary_file_analyzer import TemporaryFileAnalyzer
from fileguard.quarantine_manager import QuarantineManager
from fileguard.cleanup_manager import CleanupManager
from fileguard.ui.dialogs import CleanupPreviewDialog


class FolderTempPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette

        self.folder_analyzer = FolderAnalyzer(self.db)
        self.temp_analyzer = TemporaryFileAnalyzer(self.db)
        self.quarantine_mgr = QuarantineManager(self.db)

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
        header.pack(fill="x", pady=(0, 10))

        tk.Label(header, text="Empty Folders & Temporary Files Analysis", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(header, text="Inspect clean-up candidates without automatic deletion. All removals require explicit confirmation.", font=("Segoe UI", 9), fg=text_sec, bg=bg).pack(anchor="w", pady=(2, 0))

        # Notebook tabs for Empty Folders vs Temp Files
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, pady=(10, 0))

        # Tab 1: Empty Folders
        self.tab_empty = tk.Frame(self.notebook, bg=bg, padx=12, pady=12)
        self.notebook.add(self.tab_empty, text="📁 Empty Folders Analysis")
        self._build_empty_tab()

        # Tab 2: Temporary Files
        self.tab_temp = tk.Frame(self.notebook, bg=bg, padx=12, pady=12)
        self.notebook.add(self.tab_temp, text="🧹 Temporary File Candidates")
        self._build_temp_tab()

    def _build_empty_tab(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        accent = p.get("accent", "#14b8a6")

        top_f = tk.Frame(self.tab_empty, bg=bg)
        top_f.pack(fill="x", pady=(0, 10))

        ttk.Button(top_f, text="🔍 Analyze Scan Roots for Empty Folders", style="Accent.TButton", command=self._analyze_empty_folders).pack(side="left", padx=(0, 10))
        ttk.Button(top_f, text="Delete Selected Empty Folder", style="Danger.TButton", command=self._delete_selected_empty_folder).pack(side="left")

        self.empty_status_lbl = tk.Label(top_f, text="", font=("Segoe UI", 9), fg=accent, bg=bg)
        self.empty_status_lbl.pack(side="right")

        table_frame = tk.Frame(self.tab_empty, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "status", "reason", "path")
        self.empty_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.empty_tree.heading("name", text="Folder Name")
        self.empty_tree.heading("status", text="Classification")
        self.empty_tree.heading("reason", text="Audit Reason")
        self.empty_tree.heading("path", text="Directory Path")

        self.empty_tree.column("name", width=180)
        self.empty_tree.column("status", width=120)
        self.empty_tree.column("reason", width=220)
        self.empty_tree.column("path", width=380)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.empty_tree.yview)
        self.empty_tree.configure(yscrollcommand=sb.set)
        self.empty_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_temp_tab(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        accent = p.get("accent", "#14b8a6")

        top_f = tk.Frame(self.tab_temp, bg=bg)
        top_f.pack(fill="x", pady=(0, 10))

        ttk.Button(top_f, text="🔍 Find Temporary File Candidates", style="Accent.TButton", command=self._analyze_temp_files).pack(side="left", padx=(0, 10))
        ttk.Button(top_f, text="Move Selected to Quarantine", style="Secondary.TButton", command=self._quarantine_selected_temp_file).pack(side="left")

        self.temp_status_lbl = tk.Label(top_f, text="", font=("Segoe UI", 9), fg=accent, bg=bg)
        self.temp_status_lbl.pack(side="right")

        table_frame = tk.Frame(self.tab_temp, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "size", "age", "rules", "path")
        self.temp_tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.temp_tree.heading("name", text="File Name")
        self.temp_tree.heading("size", text="Size")
        self.temp_tree.heading("age", text="Age (Days)")
        self.temp_tree.heading("rules", text="Matched Criteria")
        self.temp_tree.heading("path", text="Full Path")

        self.temp_tree.column("name", width=180)
        self.temp_tree.column("size", width=80, anchor="e")
        self.temp_tree.column("age", width=70, anchor="e")
        self.temp_tree.column("rules", width=200)
        self.temp_tree.column("path", width=350)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.temp_tree.yview)
        self.temp_tree.configure(yscrollcommand=sb.set)
        self.temp_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def refresh(self):
        self._analyze_empty_folders()
        self._analyze_temp_files()

    def _analyze_empty_folders(self):
        latest = self.db.get_latest_scan()
        if not latest or not latest.root_paths:
            self.empty_status_lbl.config(text="No scan roots found.")
            return

        for it in self.empty_tree.get_children():
            self.empty_tree.delete(it)

        results = self.folder_analyzer.find_empty_folders(latest.root_paths)
        for r in results:
            self.empty_tree.insert("", "end", values=(
                r["folder_name"],
                r["status"],
                r["reason"],
                r["path"]
            ))

        self.empty_status_lbl.config(text=f"Found {len(results)} candidate empty folders.")

    def _delete_selected_empty_folder(self):
        sel = self.empty_tree.selection()
        if not sel:
            messagebox.showinfo("Select Folder", "Please select an empty folder to delete.", parent=self)
            return

        item = self.empty_tree.item(sel[0])
        folder_path = item["values"][3]
        status = item["values"][1]

        if "Protected" in status or "Inaccessible" in status:
            messagebox.showerror("Safety Restriction", "Protected or inaccessible folders cannot be deleted.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Empty Directory Removal",
            f"Are you sure you want to remove the empty directory:\n\n{folder_path}\n\nThis directory must have 0 files and 0 subdirectories.",
            parent=self
        )
        if confirm:
            if self.folder_analyzer.safely_remove_empty_folder(folder_path):
                self.empty_tree.delete(sel[0])
                messagebox.showinfo("Folder Removed", "Successfully removed empty folder.", parent=self)
            else:
                messagebox.showerror("Failed", "Folder could not be removed (it may contain locked files).", parent=self)

    def _analyze_temp_files(self):
        for it in self.temp_tree.get_children():
            self.temp_tree.delete(it)

        candidates = self.temp_analyzer.find_temporary_candidates()
        self.temp_candidates_map = {}

        for c in candidates:
            iid = str(c["file_id"])
            self.temp_candidates_map[iid] = c
            self.temp_tree.insert("", "end", iid=iid, values=(
                c["filename"],
                c["formatted_size"],
                c["age_days"],
                c["rules"],
                c["path"]
            ))

        self.temp_status_lbl.config(text=f"Found {len(candidates)} potential temporary files.")

    def _quarantine_selected_temp_file(self):
        sel = self.temp_tree.selection()
        if not sel:
            messagebox.showinfo("Select File", "Please select a temporary file to quarantine.", parent=self)
            return

        item_data = self.temp_candidates_map.get(sel[0])
        if not item_data:
            return

        if item_data["is_protected"]:
            messagebox.showerror("Protected File", f"File is in a protected system directory:\n{item_data['protection_warning']}", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Temporary File Quarantine",
            f"Move temporary candidate to quarantine?\n\nFile: {item_data['filename']}\nPath: {item_data['path']}\n\nYou can restore it anytime.",
            parent=self
        )
        if confirm:
            op = self.quarantine_mgr.execute_quarantine([{
                "path": item_data["path"],
                "filename": item_data["filename"],
                "size_bytes": item_data["size_bytes"],
                "sha256_hash": None
            }])
            self.temp_tree.delete(sel[0])
            messagebox.showinfo("Quarantined", f"File moved to quarantine successfully (Operation #{op.id}).", parent=self)
