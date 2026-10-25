"""
Scan Page for FileGuard.
Handles multi-folder selection, scope configuration, live progress bars,
cancellation tokens, and background thread execution.
"""
import os
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any, Callable, List, Optional
from pathlib import Path

from fileguard.models import ScanRecord, format_bytes
from fileguard.database import Database
from fileguard.scanner import Scanner
from fileguard.workers import run_in_background


class ScanPage(tk.Frame):
    def __init__(
        self,
        parent,
        db: Database,
        palette: Dict[str, str],
        on_scan_completed: Callable[[int], None],
        **kwargs
    ):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.on_scan_completed = on_scan_completed

        self.scanner = Scanner(self.db)
        self.selected_roots: List[str] = []
        self.is_scanning = False
        self.worker_queue = queue.Queue()

        self._build_ui()

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

        tk.Label(header, text="Scan & Index Files", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="Choose target folders to scan. FileGuard extracts file sizes, verifies chunked SHA-256 fingerprints, and isolates duplicates.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Root Folder Selector Panel
        selector_panel = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=14)
        selector_panel.pack(fill="x", pady=(0, 15))

        tk.Label(selector_panel, text="SCAN SCOPE (FOLDERS TO SCAN)", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 8))

        btn_bar = tk.Frame(selector_panel, bg=surface)
        btn_bar.pack(fill="x", pady=(0, 8))

        ttk.Button(btn_bar, text="➕ Add Folder...", style="Accent.TButton", command=self._add_folder).pack(side="left", padx=(0, 8))
        ttk.Button(btn_bar, text="➖ Remove Selected", style="Secondary.TButton", command=self._remove_selected_folder).pack(side="left", padx=(0, 8))
        ttk.Button(btn_bar, text="✕ Clear All Folders", style="Secondary.TButton", command=self._clear_all_folders).pack(side="left", padx=(0, 8))
        ttk.Button(btn_bar, text="📁 Add Sample Data Folder", style="Secondary.TButton", command=self._add_sample_data).pack(side="left")

        # Folder Listbox
        self.folder_listbox = tk.Listbox(
            selector_panel,
            bg=p.get("bg", "#0f172a"),
            fg=text_pri,
            selectbackground=p.get("accent_bg", "#134e4a"),
            selectforeground=text_pri,
            height=4,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9)
        )
        self.folder_listbox.pack(fill="x", pady=(0, 10))

        # Action bar to Start / Cancel
        action_bar = tk.Frame(selector_panel, bg=surface)
        action_bar.pack(fill="x")

        self.btn_start = ttk.Button(action_bar, text="🚀 Start Full Deduplication Scan", style="Accent.TButton", command=self.start_scan)
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_cancel = ttk.Button(action_bar, text="⏹ Cancel Scan", style="Danger.TButton", command=self.cancel_scan, state="disabled")
        self.btn_cancel.pack(side="left")

        # Live Progress & Metrics Panel
        self.progress_panel = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=16)
        self.progress_panel.pack(fill="both", expand=True)

        tk.Label(self.progress_panel, text="LIVE SCAN PROGRESS", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        self.stage_lbl = tk.Label(self.progress_panel, text="Ready. Add folders and press 'Start Full Deduplication Scan'.", font=("Segoe UI", 9, "bold"), fg=text_pri, bg=surface)
        self.stage_lbl.pack(anchor="w", pady=(0, 6))

        self.progress_bar = ttk.Progressbar(self.progress_panel, orient="horizontal", mode="determinate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 12))

        self.path_lbl = tk.Label(self.progress_panel, text="", font=("Consolas", 8), fg=text_sec, bg=surface, anchor="w")
        self.path_lbl.pack(fill="x", pady=(0, 15))

        # Live Counter Badges
        metrics_box = tk.Frame(self.progress_panel, bg=surface)
        metrics_box.pack(fill="x")

        self.cnt_discovered = self._make_counter(metrics_box, "Files Found", "0", 0)
        self.cnt_processed = self._make_counter(metrics_box, "Indexed", "0", 1)
        self.cnt_hashed = self._make_counter(metrics_box, "Hashed SHA-256", "0", 2)
        self.cnt_skipped = self._make_counter(metrics_box, "Skipped", "0", 3)
        self.cnt_failed = self._make_counter(metrics_box, "Errors", "0", 4)

    def _make_counter(self, parent: tk.Frame, label: str, init_val: str, col: int) -> tk.Label:
        box = tk.Frame(parent, bg=self.palette.get("bg", "#0f172a"), padx=12, pady=8, highlightbackground=self.palette.get("border", "#334155"), highlightthickness=1)
        box.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(box, text=label.upper(), font=("Segoe UI", 7, "bold"), fg=self.palette.get("text_secondary", "#94a3b8"), bg=self.palette.get("bg", "#0f172a")).pack(anchor="w")
        val_lbl = tk.Label(box, text=init_val, font=("Segoe UI", 13, "bold"), fg=self.palette.get("text_primary", "#f8fafc"), bg=self.palette.get("bg", "#0f172a"))
        val_lbl.pack(anchor="w")
        return val_lbl

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder and folder not in self.selected_roots:
            self.selected_roots.append(folder)
            self.folder_listbox.insert(tk.END, folder)

    def _remove_selected_folder(self):
        sel = self.folder_listbox.curselection()
        if sel:
            idx = sel[0]
            val = self.folder_listbox.get(idx)
            self.folder_listbox.delete(idx)
            if val in self.selected_roots:
                self.selected_roots.remove(val)

    def _clear_all_folders(self):
        self.selected_roots.clear()
        self.folder_listbox.delete(0, tk.END)

    def _add_sample_data(self):
        sample_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sample_files"
        sample_str = str(sample_dir)
        if os.path.exists(sample_str) and sample_str not in self.selected_roots:
            self.selected_roots.append(sample_str)
            self.folder_listbox.insert(tk.END, sample_str)

    def start_scan(self):
        if not self.selected_roots:
            messagebox.showwarning("No Folders Selected", "Please add at least one folder to scan.", parent=self)
            return

        self.is_scanning = True
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.progress_bar["value"] = 0

        # Run scanner in background thread
        def run_scan():
            def cb(data: Dict[str, Any]):
                self.worker_queue.put({"type": "progress", "data": data})

            try:
                res = self.scanner.scan(self.selected_roots, progress_callback=cb)
                self.worker_queue.put({"type": "done", "result": res})
            except Exception as e:
                self.worker_queue.put({"type": "error", "error": e})

        run_in_background(run_scan)
        self.after(50, self._poll_queue)

    def cancel_scan(self):
        if self.is_scanning:
            self.scanner.cancel()
            self.stage_lbl.config(text="Cancelling scan safely...")
            self.btn_cancel.config(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                msg = self.worker_queue.get_nowait()
                mtype = msg.get("type")

                if mtype == "progress":
                    data = msg["data"]
                    self.stage_lbl.config(text=data["stage"])
                    self.path_lbl.config(text=data["current_path"][:90] if data["current_path"] else "")
                    self.progress_bar["value"] = data["progress_percent"]
                    self.cnt_discovered.config(text=f"{data['discovered']:,}")
                    self.cnt_processed.config(text=f"{data['processed']:,}")
                    self.cnt_skipped.config(text=f"{data['skipped']:,}")
                    self.cnt_failed.config(text=f"{data['failed']:,}")

                elif mtype == "done":
                    scan_record = msg["result"]
                    self.is_scanning = False
                    self.btn_start.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    self.progress_bar["value"] = 100

                    if scan_record.status == "cancelled":
                        self.stage_lbl.config(text="Scan was cancelled by user.")
                    else:
                        self.stage_lbl.config(
                            text=f"Scan Complete! Found {scan_record.duplicate_groups_count} duplicate groups "
                                 f"({scan_record.formatted_recoverable_size} recoverable)."
                        )
                        if self.on_scan_completed:
                            self.on_scan_completed(scan_record.id)

                    return

                elif mtype == "error":
                    self.is_scanning = False
                    self.btn_start.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    self.stage_lbl.config(text=f"Scan error: {msg['error']}")
                    return

        except queue.Empty:
            pass

        if self.is_scanning:
            self.after(50, self._poll_queue)
