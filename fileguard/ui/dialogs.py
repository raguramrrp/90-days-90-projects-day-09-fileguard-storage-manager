"""
Dialogs and Modals for FileGuard.
Provides Cleanup Confirmation Preview, Destination Conflict Handling,
and Exclusion/Schedule creation dialogs.
"""
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, Any, List, Optional, Callable


class CleanupPreviewDialog(tk.Toplevel):
    """
    Mandatory safety preview before cleanup.
    Presents items to quarantine, retained copies, blocked items, and requires explicit confirmation.
    """
    def __init__(self, parent, preview_data: Dict[str, Any], palette: Dict[str, str], on_confirm: Callable[[], None]):
        super().__init__(parent)
        self.preview_data = preview_data
        self.palette = palette
        self.on_confirm = on_confirm
        self.confirmed = False

        self.title("Confirm Quarantine Cleanup — FileGuard")
        self.geometry("820x540")
        self.minsize(700, 400)
        self.configure(bg=palette.get("bg", "#0f172a"))
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        # Header
        header = tk.Frame(self, bg=surface, padx=20, pady=15, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        header.pack(fill="x")

        title = tk.Label(header, text="SAFETY CLEANUP PREVIEW", font=("Segoe UI", 12, "bold"), fg=accent, bg=surface)
        title.pack(anchor="w")

        desc = tk.Label(
            header,
            text=f"Selected {self.preview_data['total_items_count']} files ({self.preview_data['formatted_total_bytes']}) across "
                 f"{self.preview_data['groups_affected_count']} duplicate groups for reversible quarantine.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=surface
        )
        desc.pack(anchor="w", pady=(2, 0))

        # Main Table of Items to Quarantine
        table_frame = tk.Frame(self, bg=bg, padx=20, pady=10)
        table_frame.pack(fill="both", expand=True)

        cols = ("name", "size", "retained", "path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)
        self.tree.heading("name", text="Candidate for Quarantine")
        self.tree.heading("size", text="Size")
        self.tree.heading("retained", text="Verified Retained Copy")
        self.tree.heading("path", text="Full Path")

        self.tree.column("name", width=180)
        self.tree.column("size", width=90)
        self.tree.column("retained", width=220)
        self.tree.column("path", width=280)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for item in self.preview_data.get("items_to_clean", []):
            self.tree.insert("", "end", values=(
                item["filename"],
                item["formatted_size"],
                item.get("retained_copy", "Protected Copy"),
                item["path"]
            ))

        # Blocked items warning section (if any)
        blocked = self.preview_data.get("blocked_items", [])
        if blocked:
            warn_frame = tk.Frame(self, bg=p.get("danger", "#f87171"), padx=15, pady=8)
            warn_frame.pack(fill="x", padx=20, pady=(0, 10))
            warn_lbl = tk.Label(
                warn_frame,
                text=f"⚠️ {len(blocked)} items BLOCKED by safety rules (Protected system locations or all copies selected). They will not be touched.",
                font=("Segoe UI", 9, "bold"),
                fg="#ffffff",
                bg=p.get("danger", "#f87171")
            )
            warn_lbl.pack(anchor="w")

        # Bottom Action Bar
        btn_bar = tk.Frame(self, bg=surface, padx=20, pady=12, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        btn_bar.pack(fill="x", side="bottom")

        cancel_btn = ttk.Button(btn_bar, text="Cancel (Keep Files)", style="Secondary.TButton", command=self.destroy)
        cancel_btn.pack(side="right", padx=(10, 0))

        confirm_btn = ttk.Button(btn_bar, text="Confirm & Move to Quarantine", style="Accent.TButton", command=self._on_action_confirm)
        confirm_btn.pack(side="right")

    def _on_action_confirm(self):
        self.confirmed = True
        self.destroy()
        if self.on_confirm:
            self.on_confirm()


class AddExclusionDialog(tk.Toplevel):
    """Modal to add directory, extension, pattern, or size exclusion rule."""
    def __init__(self, parent, palette: Dict[str, str], on_save: Callable[[str, str], None]):
        super().__init__(parent)
        self.palette = palette
        self.on_save = on_save

        self.title("Add Exclusion Rule — FileGuard")
        self.geometry("450x260")
        self.resizable(False, False)
        self.configure(bg=palette.get("surface", "#1e293b"))
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        p = self.palette
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")

        f = tk.Frame(self, bg=surface, padx=20, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Add New Exclusion Rule", font=("Segoe UI", 11, "bold"), fg=p.get("accent", "#14b8a6"), bg=surface).pack(anchor="w", pady=(0, 15))

        tk.Label(f, text="Rule Type:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.type_var = tk.StringVar(value="directory")
        type_cb = ttk.Combobox(f, textvariable=self.type_var, values=["directory", "extension", "pattern", "min_size", "max_size"], state="readonly")
        type_cb.pack(fill="x", pady=(2, 10))

        tk.Label(f, text="Rule Value / Pattern:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.val_entry = ttk.Entry(f)
        self.val_entry.pack(fill="x", pady=(2, 15))
        self.val_entry.focus_set()

        btn_box = tk.Frame(f, bg=surface)
        btn_box.pack(fill="x", pady=(5, 0))

        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Add Rule", style="Accent.TButton", command=self._save).pack(side="right")

    def _save(self):
        val = self.val_entry.get().strip()
        if val:
            self.on_save(self.type_var.get(), val)
            self.destroy()


class AddScheduleDialog(tk.Toplevel):
    """Modal to configure a new scheduled scan."""
    def __init__(self, parent, palette: Dict[str, str], on_save: Callable[[str, List[str], str, str], None]):
        super().__init__(parent)
        self.palette = palette
        self.on_save = on_save
        self.selected_paths = []

        self.title("Configure Scheduled Scan — FileGuard")
        self.geometry("500x340")
        self.minsize(450, 300)
        self.configure(bg=palette.get("surface", "#1e293b"))
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        p = self.palette
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")

        f = tk.Frame(self, bg=surface, padx=20, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Schedule Configuration", font=("Segoe UI", 11, "bold"), fg=p.get("accent", "#14b8a6"), bg=surface).pack(anchor="w", pady=(0, 10))

        tk.Label(f, text="Job Name:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.name_entry = ttk.Entry(f)
        self.name_entry.insert(0, "Weekly Documents Maintenance")
        self.name_entry.pack(fill="x", pady=(2, 8))

        # Frequency & Time
        freq_frame = tk.Frame(f, bg=surface)
        freq_frame.pack(fill="x", pady=(0, 8))

        f_left = tk.Frame(freq_frame, bg=surface)
        f_left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Label(f_left, text="Frequency:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.freq_var = tk.StringVar(value="weekly")
        ttk.Combobox(f_left, textvariable=self.freq_var, values=["daily", "weekly", "monthly"], state="readonly").pack(fill="x", pady=2)

        f_right = tk.Frame(freq_frame, bg=surface)
        f_right.pack(side="right", fill="x", expand=True, padx=(5, 0))
        tk.Label(f_right, text="Target Time (HH:MM):", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.time_entry = ttk.Entry(f_right)
        self.time_entry.insert(0, "09:00")
        self.time_entry.pack(fill="x", pady=2)

        # Folders
        tk.Label(f, text="Target Folder Scope:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        folder_frame = tk.Frame(f, bg=surface)
        folder_frame.pack(fill="x", pady=(2, 15))

        self.path_lbl = tk.Label(folder_frame, text="No folder selected", font=("Segoe UI", 8), fg=text_pri, bg=p.get("bg", "#0f172a"), padx=8, pady=4, anchor="w")
        self.path_lbl.pack(side="left", fill="x", expand=True)

        browse_btn = ttk.Button(folder_frame, text="Browse...", style="Secondary.TButton", command=self._browse_folder)
        browse_btn.pack(side="right", padx=(5, 0))

        # Safety note
        note = tk.Label(
            f,
            text="Safety Guarantee: Scheduled scans only discover and report duplicates. They NEVER automatically clean or delete files.",
            font=("Segoe UI", 8),
            fg=p.get("success", "#34d399"),
            bg=surface,
            wraplength=440,
            justify="left"
        )
        note.pack(fill="x", pady=(0, 10))

        btn_box = tk.Frame(f, bg=surface)
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Save Schedule", style="Accent.TButton", command=self._save).pack(side="right")

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder for Scheduled Scan")
        if folder:
            self.selected_paths = [folder]
            self.path_lbl.config(text=folder)

    def _save(self):
        name = self.name_entry.get().strip() or "Scheduled Scan"
        freq = self.freq_var.get()
        t = self.time_entry.get().strip() or "09:00"
        if not self.selected_paths:
            return
        self.on_save(name, self.selected_paths, freq, t)
        self.destroy()
