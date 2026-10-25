"""
File Integrity Verification Page for FileGuard.
Recalculates cryptographic SHA-256 fingerprints of indexed files to detect
silent bit rot, modifications, missing files, or permission regressions.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import IntegrityResult, FileRecord
from fileguard.database import Database
from fileguard.integrity_checker import IntegrityChecker
from fileguard.workers import run_in_background


class IntegrityPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette
        self.checker = IntegrityChecker(self.db)

        self.results: List[IntegrityResult] = []
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

        tk.Label(header, text="File Cryptographic Integrity Verification", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="Recalculate SHA-256 fingerprints to verify files match their stored baseline hashes. Detects modification, corruption, and missing items.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Action Toolstrip
        toolstrip = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        toolstrip.pack(fill="x", pady=(0, 10))

        self.btn_run = ttk.Button(toolstrip, text="🔒 Run Full Integrity Verification", style="Accent.TButton", command=self._start_integrity_check)
        self.btn_run.pack(side="left", padx=(0, 10))

        ttk.Button(toolstrip, text="Export Results CSV...", style="Secondary.TButton", command=self._export_csv).pack(side="left", padx=(0, 10))
        ttk.Button(toolstrip, text="🔄 Refresh Log", style="Secondary.TButton", command=self.refresh).pack(side="left")

        self.status_lbl = tk.Label(toolstrip, text="", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface)
        self.status_lbl.pack(side="right")

        # Results Table
        table_frame = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        cols = ("file", "status", "baseline_hash", "observed_hash", "verified_at", "path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("file", text="File Name")
        self.tree.heading("status", text="Integrity Status")
        self.tree.heading("baseline_hash", text="Baseline Hash (DB)")
        self.tree.heading("observed_hash", text="Observed Hash (Disk)")
        self.tree.heading("verified_at", text="Verification Date")
        self.tree.heading("path", text="Path")

        self.tree.column("file", width=160)
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("baseline_hash", width=160)
        self.tree.column("observed_hash", width=160)
        self.tree.column("verified_at", width=130)
        self.tree.column("path", width=300)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def refresh(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        self.results = self.db.get_integrity_checks(limit=150)
        for r in self.results:
            fname = Path(r.file_path).name
            status_text = r.status.upper()
            self.tree.insert("", "end", values=(
                fname,
                status_text,
                (r.reference_hash[:16] + "...") if r.reference_hash else "None",
                (r.observed_hash[:16] + "...") if r.observed_hash else "None",
                (r.verified_at or "")[:19],
                r.file_path
            ))

        if self.results:
            self.status_lbl.config(text=f"Loaded {len(self.results)} verification records.")

    def _start_integrity_check(self):
        latest = self.db.get_latest_scan()
        if not latest:
            messagebox.showinfo("No Scans", "Please run a file scan first before verifying integrity.", parent=self)
            return

        files = self.db.get_files_by_scan(latest.id)
        if not files:
            messagebox.showinfo("No Files", "No indexed files found in the latest scan.", parent=self)
            return

        self.btn_run.config(state="disabled")
        self.status_lbl.config(text=f"Verifying {len(files)} files in background...")

        def run_check():
            res = self.checker.check_files(files)
            self.after(50, lambda: self._on_check_completed(res))

        run_in_background(run_check)

    def _on_check_completed(self, results: List[IntegrityResult]):
        self.btn_run.config(state="normal")
        unchanged = sum(1 for r in results if r.status == "unchanged")
        modified = sum(1 for r in results if r.status == "modified")
        missing = sum(1 for r in results if r.status == "missing")

        self.status_lbl.config(
            text=f"Complete: {unchanged} Unchanged | {modified} Modified | {missing} Missing"
        )
        self.refresh()
        messagebox.showinfo(
            "Integrity Check Complete",
            f"Integrity check finished for {len(results)} files:\n\n"
            f"• Unchanged (Verified): {unchanged}\n"
            f"• Modified / Hash Mismatch: {modified}\n"
            f"• Missing from Disk: {missing}",
            parent=self
        )

    def _export_csv(self):
        if not self.results:
            messagebox.showinfo("No Data", "No integrity check results to export.", parent=self)
            return

        fp = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="fileguard_integrity_report.csv"
        )
        if not fp:
            return

        import csv
        with open(fp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["File Name", "Status", "Reference Hash", "Observed Hash", "Verified Date", "File Path"])
            for r in self.results:
                w.writerow([
                    Path(r.file_path).name,
                    r.status,
                    r.reference_hash,
                    r.observed_hash or "",
                    r.verified_at,
                    r.file_path
                ])
        messagebox.showinfo("Export Successful", f"Saved integrity report to:\n{fp}", parent=self)
