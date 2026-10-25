"""
Settings & Exclusion Configuration Page for FileGuard.
Manages application themes, exclusion rules, custom parameters, and test data generation.
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from fileguard.models import ExclusionRule
from fileguard.database import Database
from fileguard.exclusion_manager import ExclusionManager
from fileguard.ui.dialogs import AddExclusionDialog


class SettingsPage(tk.Frame):
    def __init__(
        self,
        parent,
        db: Database,
        palette: Dict[str, str],
        on_theme_changed: Callable[[str], None],
        **kwargs
    ):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=24, pady=20, **kwargs)
        self.db = db
        self.palette = palette
        self.on_theme_changed = on_theme_changed
        self.exclusion_mgr = ExclusionManager(self.db)

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

        tk.Label(header, text="Application Preferences & Exclusion Rules", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(header, text="Configure visual themes, custom exclusion filters, performance thresholds, and retention policies.", font=("Segoe UI", 9), fg=text_sec, bg=bg).pack(anchor="w", pady=(2, 0))

        # Main Settings Container (2-Column Grid)
        content_box = tk.Frame(self, bg=bg)
        content_box.pack(fill="both", expand=True)
        content_box.columnconfigure(0, weight=1)
        content_box.columnconfigure(1, weight=1)

        # Left Column: General Preferences
        left_box = tk.Frame(content_box, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=16)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(left_box, text="GENERAL PREFERENCES", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 12))

        # 1. Theme Selector
        tk.Label(left_box, text="Color Theme:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.theme_var = tk.StringVar(value=self.db.get_setting("theme", "dark"))
        theme_cb = ttk.Combobox(left_box, textvariable=self.theme_var, values=["dark", "light"], state="readonly", width=15)
        theme_cb.pack(anchor="w", pady=(2, 12))
        theme_cb.bind("<<ComboboxSelected>>", self._on_theme_select)

        # 2. Large File Threshold
        tk.Label(left_box, text="Large File Threshold (MB):", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.large_entry = ttk.Entry(left_box, width=15)
        self.large_entry.insert(0, self.db.get_setting("large_file_threshold_mb", "10"))
        self.large_entry.pack(anchor="w", pady=(2, 12))

        # 3. Hashing Chunk Size
        tk.Label(left_box, text="Hashing Chunk Read Size (KB):", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(anchor="w")
        self.chunk_entry = ttk.Entry(left_box, width=15)
        self.chunk_entry.insert(0, self.db.get_setting("chunk_size_kb", "64"))
        self.chunk_entry.pack(anchor="w", pady=(2, 15))

        ttk.Button(left_box, text="💾 Save Preferences", style="Accent.TButton", command=self._save_preferences).pack(anchor="w", pady=(0, 15))

        # Test Data Generator Action
        sep = tk.Frame(left_box, bg=p.get("border", "#334155"), height=1)
        sep.pack(fill="x", pady=10)

        tk.Label(left_box, text="DEVELOPER & DEMO TOOLS", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 6))
        tk.Label(left_box, text="Generate safe test files with duplicates, large files, empty folders, and temp items.", font=("Segoe UI", 8), fg=text_sec, bg=surface).pack(anchor="w", pady=(0, 8))
        ttk.Button(left_box, text="⚡ Generate Sample Test Environment", style="Secondary.TButton", command=self._generate_sample_data).pack(anchor="w", pady=(0, 8))
        ttk.Button(left_box, text="🗑️ Purge Scan History & Reset Index", style="Danger.TButton", command=self._purge_all_scans).pack(anchor="w")

        # Right Column: Exclusion Rules Manager
        right_box = tk.Frame(content_box, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=16, pady=16)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(right_box, text="EXCLUSION RULES (SKIPPED FILES)", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 8))

        rule_btns = tk.Frame(right_box, bg=surface)
        rule_btns.pack(fill="x", pady=(0, 8))

        ttk.Button(rule_btns, text="➕ Add Rule...", style="Accent.TButton", command=self._open_add_rule).pack(side="left", padx=(0, 6))
        ttk.Button(rule_btns, text="Toggle", style="Secondary.TButton", command=self._toggle_rule).pack(side="left", padx=(0, 6))
        ttk.Button(rule_btns, text="Delete", style="Danger.TButton", command=self._delete_rule).pack(side="left")

        # Exclusions table
        cols = ("id", "type", "value", "status")
        self.excl_tree = ttk.Treeview(right_box, columns=cols, show="headings", height=10)
        self.excl_tree.heading("id", text="ID")
        self.excl_tree.heading("type", text="Type")
        self.excl_tree.heading("value", text="Rule Value")
        self.excl_tree.heading("status", text="Enabled")

        self.excl_tree.column("id", width=35, anchor="center")
        self.excl_tree.column("type", width=90)
        self.excl_tree.column("value", width=180)
        self.excl_tree.column("status", width=70, anchor="center")

        self.excl_tree.pack(fill="both", expand=True)

    def refresh(self):
        for it in self.excl_tree.get_children():
            self.excl_tree.delete(it)

        rules = self.db.get_exclusions()
        for r in rules:
            self.excl_tree.insert("", "end", iid=str(r.id), values=(
                r.id,
                r.rule_type,
                r.rule_value,
                "YES" if r.is_enabled else "NO"
            ))

    def _on_theme_select(self, event):
        new_theme = self.theme_var.get()
        self.db.set_setting("theme", new_theme)
        if self.on_theme_changed:
            self.on_theme_changed(new_theme)

    def _save_preferences(self):
        self.db.set_setting("large_file_threshold_mb", self.large_entry.get().strip() or "10")
        self.db.set_setting("chunk_size_kb", self.chunk_entry.get().strip() or "64")
        messagebox.showinfo("Settings Saved", "Preferences persisted to SQLite configuration database.", parent=self)

    def _open_add_rule(self):
        def save_rule_cb(rtype: str, rval: str):
            self.db.add_exclusion(rtype, rval, is_enabled=True)
            self.refresh()

        AddExclusionDialog(self, self.palette, save_rule_cb)

    def _toggle_rule(self):
        sel = self.excl_tree.selection()
        if not sel:
            return
        rid = int(sel[0])
        rules = self.db.get_exclusions()
        target = next((r for r in rules if r.id == rid), None)
        if target:
            self.db.update_exclusion(rid, not target.is_enabled)
            self.refresh()

    def _delete_rule(self):
        sel = self.excl_tree.selection()
        if not sel:
            return
        rid = int(sel[0])
        self.db.delete_exclusion(rid)
        self.refresh()

    def _generate_sample_data(self):
        from scripts.create_sample_data import create_sample_environment
        try:
            path = create_sample_environment()
            messagebox.showinfo(
                "Sample Environment Created",
                f"Generated realistic sample test files in:\n\n{path}\n\nGo to 'Scan Files' and scan this folder to test deduplication, large files, and similar photos.",
                parent=self
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not create sample files: {e}", parent=self)

    def _purge_all_scans(self):
        confirm = messagebox.askyesno(
            "Purge Scan Records",
            "Are you sure you want to purge all scan records and indexed duplicates from FileGuard's database?\n\n"
            "• This clears FileGuard's cached index and resets the Overview & Duplicate Review.\n"
            "• Files on your disk and files in quarantine will NOT be affected.\n\n"
            "Proceed?",
            parent=self
        )
        if confirm:
            self.db.clear_all_scans()
            messagebox.showinfo("Database Reset", "All scan records and indexed duplicate groups have been cleared from FileGuard.", parent=self)
