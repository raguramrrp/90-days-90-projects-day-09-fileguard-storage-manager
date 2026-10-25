"""
Scheduled Scans Page for FileGuard.
Allows users to configure recurring scans, toggle active jobs, inspect next-run timestamps,
and trigger immediate executions with strict safety guarantees.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import ScheduleConfig
from fileguard.database import Database
from fileguard.scheduler import Scheduler
from fileguard.ui.dialogs import AddScheduleDialog


class SchedulePage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.scheduler = Scheduler(self.db)
        self.scheduler.start()

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

        tk.Label(header, text="Automated Maintenance & Scan Schedules", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="Schedule routine background inventory scans while FileGuard is active. "
                 "CRITICAL SAFETY RULE: Scheduled scans NEVER trigger automatic cleanup or delete files.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Toolstrip Action Bar
        toolstrip = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        toolstrip.pack(fill="x", pady=(0, 15))

        ttk.Button(toolstrip, text="➕ New Schedule...", style="Accent.TButton", command=self._open_add_dialog).pack(side="left", padx=(0, 8))
        ttk.Button(toolstrip, text="⚡ Run Selected Now", style="Secondary.TButton", command=self._run_selected_now).pack(side="left", padx=(0, 8))
        ttk.Button(toolstrip, text="Toggle Enable/Disable", style="Secondary.TButton", command=self._toggle_selected).pack(side="left", padx=(0, 8))
        ttk.Button(toolstrip, text="Delete Schedule", style="Danger.TButton", command=self._delete_selected).pack(side="left", padx=(0, 12))
        ttk.Button(toolstrip, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="left")

        # Schedules Table
        table_frame = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        cols = ("id", "name", "freq", "time", "enabled", "last_run", "next_run", "roots")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Schedule Name")
        self.tree.heading("freq", text="Frequency")
        self.tree.heading("time", text="Target Time")
        self.tree.heading("enabled", text="Status")
        self.tree.heading("last_run", text="Last Run")
        self.tree.heading("next_run", text="Next Scheduled Run")
        self.tree.heading("roots", text="Target Folders")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("name", width=180)
        self.tree.column("freq", width=90, anchor="center")
        self.tree.column("time", width=80, anchor="center")
        self.tree.column("enabled", width=90, anchor="center")
        self.tree.column("last_run", width=130)
        self.tree.column("next_run", width=130)
        self.tree.column("roots", width=260)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def refresh(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        schedules = self.db.get_schedules()
        for s in schedules:
            roots_str = ", ".join(s.root_paths)
            self.tree.insert("", "end", iid=str(s.id), values=(
                s.id,
                s.name,
                s.frequency.capitalize(),
                s.target_time,
                "ACTIVE" if s.enabled else "PAUSED",
                (s.last_run or "Never")[:19],
                (s.next_run or "Pending")[:19],
                roots_str
            ))

    def _open_add_dialog(self):
        def save_cb(name: str, roots: List[str], freq: str, target_time: str):
            next_run = self.scheduler.calculate_next_run(freq, target_time)
            cfg = ScheduleConfig(
                name=name,
                root_paths=roots,
                frequency=freq,
                target_time=target_time,
                enabled=True,
                next_run=next_run
            )
            self.db.add_schedule(cfg)
            self.refresh()
            messagebox.showinfo("Schedule Created", f"Scheduled job '{name}' created. Next run scheduled for:\n{next_run[:16]}", parent=self)

        AddScheduleDialog(self, self.palette, save_cb)

    def _run_selected_now(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Schedule", "Please select a schedule to trigger.", parent=self)
            return

        sid = int(sel[0])
        success = self.scheduler.trigger_scheduled_scan_now(sid)
        if success:
            messagebox.showinfo("Run Completed", "Scheduled scan finished successfully.", parent=self)
            self.refresh()
        else:
            messagebox.showerror("Run Failed", "Scan could not be started.", parent=self)

    def _toggle_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        sid = int(sel[0])
        schedules = self.db.get_schedules()
        target = next((s for s in schedules if s.id == sid), None)
        if target:
            self.db.toggle_schedule(sid, not target.enabled)
            self.refresh()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        sid = int(sel[0])
        if messagebox.askyesno("Delete Schedule", "Delete selected schedule?", parent=self):
            self.db.delete_schedule(sid)
            self.refresh()
