"""
Overview Dashboard Page for FileGuard.
Displays real, database-backed storage metrics, KPI cards, recent scan activity,
and quick action triggers.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, Optional

from fileguard.models import format_bytes
from fileguard.database import Database
from fileguard.ui.components import StatCard


class OverviewPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], on_navigate: Callable[[str], None], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.on_navigate = on_navigate

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        # Top Header Bar
        header = tk.Frame(self, bg=bg)
        header.pack(fill="x", pady=(0, 20))

        title_box = tk.Frame(header, bg=bg)
        title_box.pack(side="left")

        tk.Label(title_box, text="Storage & Duplicate Overview", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        self.scope_lbl = tk.Label(title_box, text="No scan records found.", font=("Segoe UI", 9), fg=text_sec, bg=bg)
        self.scope_lbl.pack(anchor="w", pady=(2, 0))

        btn_box = tk.Frame(header, bg=bg)
        btn_box.pack(side="right")

        ttk.Button(btn_box, text="⚡ Run New Scan", style="Accent.TButton", command=lambda: self.on_navigate("scan")).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Refresh", style="Secondary.TButton", command=self.refresh).pack(side="right")

        # KPI Metrics Cards (4 columns)
        self.kpi_frame = tk.Frame(self, bg=bg)
        self.kpi_frame.pack(fill="x", pady=(0, 20))
        self.kpi_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self.card_files = StatCard(self.kpi_frame, "Indexed Files", "0", "Awaiting scan", palette=p)
        self.card_files.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.card_duplicates = StatCard(self.kpi_frame, "Duplicate Groups", "0", "0 copies found", palette=p)
        self.card_duplicates.grid(row=0, column=1, sticky="nsew", padx=4)

        self.card_recoverable = StatCard(self.kpi_frame, "Recoverable Space", "0 B", "Potential savings (N-1)*S", palette=p, accent_color=p.get("accent", "#14b8a6"))
        self.card_recoverable.grid(row=0, column=2, sticky="nsew", padx=4)

        self.card_reclaimed = StatCard(self.kpi_frame, "Reclaimed Space", "0 B", "Quarantined files", palette=p, accent_color=p.get("success", "#34d399"))
        self.card_reclaimed.grid(row=0, column=3, sticky="nsew", padx=(8, 0))

        # Two-Column Content Area (Recent Scans & Audit Log)
        content_frame = tk.Frame(self, bg=bg)
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)

        # Left Column: Recent Scans Table
        left_panel = tk.Frame(content_frame, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(left_panel, text="RECENT SCAN ACTIVITY", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        cols = ("date", "status", "files", "duplicates", "recoverable")
        self.scan_tree = ttk.Treeview(left_panel, columns=cols, show="headings", height=8)
        self.scan_tree.heading("date", text="Date")
        self.scan_tree.heading("status", text="Status")
        self.scan_tree.heading("files", text="Files")
        self.scan_tree.heading("duplicates", text="Dup Groups")
        self.scan_tree.heading("recoverable", text="Recoverable")

        self.scan_tree.column("date", width=120)
        self.scan_tree.column("status", width=80)
        self.scan_tree.column("files", width=70)
        self.scan_tree.column("duplicates", width=80)
        self.scan_tree.column("recoverable", width=90)

        self.scan_tree.pack(fill="both", expand=True)

        # Right Column: Recent Safety & Audit Events
        right_panel = tk.Frame(content_frame, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(right_panel, text="SAFETY & AUDIT TRAIL", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        self.audit_listbox = tk.Listbox(
            right_panel,
            bg=p.get("bg", "#0f172a"),
            fg=text_pri,
            selectbackground=p.get("accent_bg", "#134e4a"),
            selectforeground=text_pri,
            relief="flat",
            bd=0,
            font=("Segoe UI", 8)
        )
        self.audit_listbox.pack(fill="both", expand=True)

    def refresh(self):
        """Fetch latest database records and update UI."""
        metrics = self.db.get_storage_overview_metrics()

        if metrics["has_scan"]:
            date_str = (metrics["latest_scan_date"] or "")[:19]
            roots_str = ", ".join(metrics["scan_roots"][:2]) if metrics["scan_roots"] else "Directory Scan"
            self.scope_lbl.config(text=f"Last Scan: {date_str}  •  Scope: {roots_str}")

            self.card_files.update_values(
                f"{metrics['total_indexed_files']:,}",
                f"{format_bytes(metrics['total_indexed_bytes'])} indexed"
            )
            self.card_duplicates.update_values(
                str(metrics["duplicate_groups_count"]),
                f"{metrics['duplicate_files_count']} total copies"
            )
            self.card_recoverable.update_values(
                format_bytes(metrics["potential_recoverable_bytes"]),
                "Available to clean"
            )
            self.card_reclaimed.update_values(
                format_bytes(metrics["reclaimed_bytes"]),
                f"{metrics['quarantined_files_count']} files in quarantine"
            )
        else:
            self.scope_lbl.config(text="No scans performed yet. Click 'Run New Scan' to index files.")
            self.card_files.update_values("0", "No data")
            self.card_duplicates.update_values("0", "0 copies")
            self.card_recoverable.update_values("0 B", "Potential savings")
            self.card_reclaimed.update_values(format_bytes(metrics["reclaimed_bytes"]), f"{metrics['quarantined_files_count']} files in quarantine")

        # Refresh Recent Scans Table
        for row in self.scan_tree.get_children():
            self.scan_tree.delete(row)

        scans = self.db.get_all_scans()[:8]
        for s in scans:
            d = (s.completed_at or s.started_at or "")[:16]
            self.scan_tree.insert("", "end", values=(
                d,
                s.status.capitalize(),
                f"{s.files_processed:,}",
                s.duplicate_groups_count,
                s.formatted_recoverable_size
            ))

        # Refresh Audit Trail
        self.audit_listbox.delete(0, tk.END)
        events = self.db.get_recent_audit_events(limit=15)
        if not events:
            self.audit_listbox.insert(tk.END, " No safety events recorded yet.")
        for ev in events:
            ts = ev["timestamp"][11:19]
            etype = ev["event_type"].replace("_", " ").upper()
            self.audit_listbox.insert(tk.END, f" [{ts}] {etype}")
