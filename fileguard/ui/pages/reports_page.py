"""
Reports & Audit Export Page for FileGuard.
Generates standalone HTML and CSV reports for duplicates, storage, large files,
and quarantine audit trails.
"""
import os
import subprocess
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.config import REPORTS_DIR
from fileguard.database import Database
from fileguard.report_generator import ReportGenerator


class ReportsPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.generator = ReportGenerator(self.db)

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
        header.pack(fill="x", pady=(0, 20))

        tk.Label(header, text="Reports & Compliance Audit Export", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="Generate polished standalone HTML and CSV reports. All reports are self-contained and formatted for auditing, archiving, or sharing.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Action Cards for each report type
        cards_grid = tk.Frame(self, bg=bg)
        cards_grid.pack(fill="x", pady=(0, 20))
        cards_grid.columnconfigure((0, 1), weight=1)

        # Card 1: Duplicate Groups HTML
        self._build_report_card(
            cards_grid,
            title="DUPLICATE FILES HTML AUDIT REPORT",
            desc="Visual standalone HTML dashboard with KPI summary, duplicate groups hierarchy, verified hashes, and recommendation reasoning.",
            btn_text="📄 Generate HTML Report",
            command=self._generate_duplicates_html,
            row=0, col=0
        )

        # Card 2: Duplicate Groups CSV
        self._build_report_card(
            cards_grid,
            title="DUPLICATE GROUPS CSV DATASET",
            desc="Raw structured spreadsheet format containing all duplicate groups, member file paths, sizes, and suggestion explanations.",
            btn_text="📊 Export Duplicates CSV",
            command=self._export_duplicates_csv,
            row=0, col=1
        )

        # Card 3: Large Files CSV
        self._build_report_card(
            cards_grid,
            title="LARGE FILES INVENTORY CSV",
            desc="Complete table of all files exceeding threshold, categorized with size rankings and last modified timestamps.",
            btn_text="📦 Export Large Files CSV",
            command=self._export_large_files_csv,
            row=1, col=0
        )

        # Card 4: Quarantine Audit CSV
        self._build_report_card(
            cards_grid,
            title="QUARANTINE & DISASTER RECOVERY AUDIT CSV",
            desc="Full historical log of all quarantined items, original paths, collision-safe destinations, hashes, and restoration outcomes.",
            btn_text="🛡️ Export Quarantine Audit CSV",
            command=self._export_quarantine_csv,
            row=1, col=1
        )

        # Generated Reports Directory View
        dir_panel = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        dir_panel.pack(fill="both", expand=True)

        dir_head = tk.Frame(dir_panel, bg=surface)
        dir_head.pack(fill="x", pady=(0, 8))

        tk.Label(dir_head, text="GENERATED LOCAL REPORTS", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(side="left")
        ttk.Button(dir_head, text="📁 Open Reports Folder", style="Secondary.TButton", command=self._open_reports_dir).pack(side="right")
        ttk.Button(dir_head, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="right", padx=(0, 8))

        self.reports_listbox = tk.Listbox(
            dir_panel,
            bg=p.get("bg", "#0f172a"),
            fg=text_pri,
            selectbackground=p.get("accent_bg", "#134e4a"),
            selectforeground=text_pri,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9)
        )
        self.reports_listbox.pack(fill="both", expand=True)
        self.reports_listbox.bind("<Double-1>", self._on_double_click_report)

    def _build_report_card(self, parent: tk.Frame, title: str, desc: str, btn_text: str, command: Callable, row: int, col: int):
        p = self.palette
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        card = tk.Frame(parent, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg=accent, bg=surface).pack(anchor="w")
        tk.Label(card, text=desc, font=("Segoe UI", 8), fg=text_sec, bg=surface, wraplength=340, justify="left").pack(anchor="w", pady=(4, 10))
        ttk.Button(card, text=btn_text, style="Accent.TButton", command=command).pack(anchor="w")

    def refresh(self):
        self.reports_listbox.delete(0, tk.END)
        reports = list(REPORTS_DIR.glob("*.*"))
        reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        if not reports:
            self.reports_listbox.insert(tk.END, " No generated reports yet. Click one of the buttons above to export.")
        else:
            for r in reports:
                self.reports_listbox.insert(tk.END, f" {r.name}")

    def _generate_duplicates_html(self):
        groups = self.db.get_duplicate_groups()
        latest = self.db.get_latest_scan()
        if not groups:
            messagebox.showinfo("No Duplicates", "No duplicate groups found to export. Please run a scan first.", parent=self)
            return

        fp = self.generator.generate_duplicates_html(groups, scan=latest)
        self.refresh()
        ask = messagebox.askyesno("Report Generated", f"Successfully generated HTML report:\n{Path(fp).name}\n\nOpen now in default web browser?", parent=self)
        if ask:
            webbrowser.open(f"file://{os.path.abspath(fp)}")

    def _export_duplicates_csv(self):
        groups = self.db.get_duplicate_groups()
        if not groups:
            messagebox.showinfo("No Duplicates", "No duplicate groups to export.", parent=self)
            return
        fp = self.generator.export_duplicates_csv(groups)
        self.refresh()
        messagebox.showinfo("Export Complete", f"Duplicates CSV exported to:\n{fp}", parent=self)

    def _export_large_files_csv(self):
        files = self.db.get_large_files(min_size_bytes=10 * 1024 * 1024)
        if not files:
            messagebox.showinfo("No Files", "No large files found above threshold.", parent=self)
            return
        fp = self.generator.export_large_files_csv(files)
        self.refresh()
        messagebox.showinfo("Export Complete", f"Large files CSV exported to:\n{fp}", parent=self)

    def _export_quarantine_csv(self):
        items = self.db.get_all_quarantine_items()
        fp = self.generator.export_quarantine_audit_csv(items)
        self.refresh()
        messagebox.showinfo("Export Complete", f"Quarantine audit trail CSV exported to:\n{fp}", parent=self)

    def _open_reports_dir(self):
        d = str(REPORTS_DIR)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer.exe", d])
        else:
            subprocess.Popen(["xdg-open", d])

    def _on_double_click_report(self, event):
        sel = self.reports_listbox.curselection()
        if not sel:
            return
        fname = self.reports_listbox.get(sel[0]).strip()
        fp = REPORTS_DIR / fname
        if fp.exists():
            if fp.suffix.lower() == ".html":
                webbrowser.open(f"file://{fp.resolve()}")
            else:
                if sys.platform.startswith("win"):
                    os.startfile(str(fp))
                else:
                    subprocess.Popen(["xdg-open", str(fp)])
