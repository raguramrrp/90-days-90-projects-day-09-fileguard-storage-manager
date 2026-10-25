"""
Scan History & Comparison Page for FileGuard.
Allows users to browse past scan executions, inspect detailed scope metrics,
and diff two completed scans with scope-compatibility safeguards.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import ScanRecord, format_bytes
from fileguard.database import Database
from fileguard.history_manager import HistoryManager


class HistoryPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette
        self.history_mgr = HistoryManager(self.db)

        self.scans: List[ScanRecord] = []
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

        tk.Label(header, text="Historical Scans & Change Tracking", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(header, text="Browse historical scan records and compare changes between two completed inventory snapshots.", font=("Segoe UI", 9), fg=text_sec, bg=bg).pack(anchor="w", pady=(2, 0))

        # Comparison Control Bar
        cmp_bar = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        cmp_bar.pack(fill="x", pady=(0, 10))

        tk.Label(cmp_bar, text="Compare Scans: Baseline Scan:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(side="left", padx=(0, 4))
        self.scan_a_var = tk.StringVar()
        self.cb_scan_a = ttk.Combobox(cmp_bar, textvariable=self.scan_a_var, state="readonly", width=22)
        self.cb_scan_a.pack(side="left", padx=(0, 10))

        tk.Label(cmp_bar, text="Target Scan:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(side="left", padx=(0, 4))
        self.scan_b_var = tk.StringVar()
        self.cb_scan_b = ttk.Combobox(cmp_bar, textvariable=self.scan_b_var, state="readonly", width=22)
        self.cb_scan_b.pack(side="left", padx=(0, 10))

        ttk.Button(cmp_bar, text="📊 Run Scope Comparison", style="Accent.TButton", command=self._run_comparison).pack(side="left", padx=(0, 10))
        ttk.Button(cmp_bar, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="left", padx=(0, 10))
        ttk.Button(cmp_bar, text="🗑️ Remove Scan Record", style="Danger.TButton", command=self._delete_selected_scan).pack(side="right")

        # Two-Column View: Top Scans Table, Bottom Comparison Results
        self.paned = ttk.Panedwindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True)

        # Scans History Table
        table_frame = tk.Frame(self.paned, bg=surface)
        self.paned.add(table_frame, weight=2)

        cols = ("id", "name", "date", "status", "files", "hashed", "groups", "recoverable", "roots")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Scan Name")
        self.tree.heading("date", text="Execution Date")
        self.tree.heading("status", text="Status")
        self.tree.heading("files", text="Files")
        self.tree.heading("hashed", text="Hashed")
        self.tree.heading("groups", text="Duplicates")
        self.tree.heading("recoverable", text="Recoverable")
        self.tree.heading("roots", text="Scan Root Paths")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=140)
        self.tree.column("date", width=130)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("files", width=70, anchor="e")
        self.tree.column("hashed", width=70, anchor="e")
        self.tree.column("groups", width=80, anchor="e")
        self.tree.column("recoverable", width=90, anchor="e")
        self.tree.column("roots", width=280)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Comparison Results Panel
        self.cmp_panel = tk.Frame(self.paned, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=12)
        self.paned.add(self.cmp_panel, weight=1)

        tk.Label(self.cmp_panel, text="SCAN DELTA & CHANGE SUMMARY", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 6))

        self.cmp_text = tk.Label(
            self.cmp_panel,
            text="Select two completed scans above and click 'Run Scope Comparison' to view deltas.",
            font=("Segoe UI", 9),
            fg=text_pri,
            bg=surface,
            justify="left",
            wraplength=850
        )
        self.cmp_text.pack(anchor="w")

    def refresh(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        self.scans = self.history_mgr.get_all_scans()
        scan_options = []

        for s in self.scans:
            roots_str = ", ".join(s.root_paths) if s.root_paths else "No scope"
            d = (s.completed_at or s.started_at or "")[:19]
            self.tree.insert("", "end", iid=str(s.id), values=(
                s.id,
                s.scan_name,
                d,
                s.status.upper(),
                f"{s.files_processed:,}",
                f"{s.files_hashed:,}",
                s.duplicate_groups_count,
                s.formatted_recoverable_size,
                roots_str
            ))
            if s.status == "completed":
                scan_options.append(f"#{s.id} - {s.scan_name} ({d[:10]})")

        self.cb_scan_a["values"] = scan_options
        self.cb_scan_b["values"] = scan_options

        if len(scan_options) >= 2:
            self.cb_scan_a.current(1)
            self.cb_scan_b.current(0)
        elif len(scan_options) == 1:
            self.cb_scan_a.current(0)
            self.cb_scan_b.current(0)

    def _delete_selected_scan(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Scan", "Please select a scan record from the table to remove.", parent=self)
            return

        scan_id = int(sel[0])
        scan = self.db.get_scan(scan_id)
        name = scan.scan_name if scan else f"#{scan_id}"

        confirm = messagebox.askyesno(
            "Remove Scan Record",
            f"Remove scan record '{name}' (ID #{scan_id}) from FileGuard's database?\n\n"
            f"• Its indexed files and duplicate groups will be purged from the app.\n"
            f"• Your actual files on disk will NOT be touched or modified.\n\n"
            f"Proceed with removing this record?",
            parent=self
        )
        if confirm:
            self.db.delete_scan(scan_id)
            self.refresh()
            messagebox.showinfo("Scan Record Removed", f"Scan #{scan_id} and its indexed records were removed from the database.", parent=self)

    def _run_comparison(self):
        val_a = self.scan_a_var.get()
        val_b = self.scan_b_var.get()

        if not val_a or not val_b:
            messagebox.showinfo("Select Scans", "Please select two scans to compare.", parent=self)
            return

        id_a = int(val_a.split(" ")[0].replace("#", ""))
        id_b = int(val_b.split(" ")[0].replace("#", ""))

        if id_a == id_b:
            messagebox.showinfo("Identical Scans", "Please select two distinct scans to evaluate deltas.", parent=self)
            return

        cmp = self.history_mgr.compare_scans(id_a, id_b)

        warning_line = f"\n⚠️ {cmp['scope_warning']}\n" if cmp["scope_warning"] else ""
        sign_files = "+" if cmp["delta_files"] >= 0 else ""
        sign_bytes = "+" if cmp["delta_bytes"] >= 0 else "-"
        sign_groups = "+" if cmp["delta_duplicate_groups"] >= 0 else ""

        delta_summary = (
            f"Comparing Baseline (Scan #{id_a}) ➔ Target (Scan #{id_b}):\n"
            f"{warning_line}"
            f"• Indexed Files: {sign_files}{cmp['delta_files']:,}\n"
            f"• Storage Delta: {sign_bytes}{cmp['formatted_delta_bytes']}\n"
            f"• Duplicate Groups Delta: {sign_groups}{cmp['delta_duplicate_groups']}\n"
            f"• Recoverable Space Delta: {cmp['formatted_delta_recoverable']}\n"
            f"• Newly Emerged Duplicate Groups: {cmp['new_duplicate_groups_count']}\n"
            f"• Resolved Duplicate Groups: {cmp['resolved_duplicate_groups_count']}\n"
            f"• Persisting Duplicate Groups: {cmp['persisting_duplicate_groups_count']}"
        )
        self.cmp_text.config(text=delta_summary)
