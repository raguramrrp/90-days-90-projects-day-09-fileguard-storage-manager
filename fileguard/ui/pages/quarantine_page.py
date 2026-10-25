"""
Quarantine & Recovery Page for FileGuard.
Handles file recovery, undo of quarantine operations, destination collision handling,
and separate permanently delete capabilities with explicit warning.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, List, Optional
from pathlib import Path

from fileguard.models import QuarantineItem, format_bytes
from fileguard.database import Database
from fileguard.quarantine_manager import QuarantineManager
from fileguard.restore_manager import RestoreManager


class QuarantinePage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette

        self.quarantine_mgr = QuarantineManager(self.db)
        self.restore_mgr = RestoreManager(self.db)

        self.items: List[QuarantineItem] = []
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

        tk.Label(header, text="Quarantine & Disaster Recovery", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="All cleaned files are safely isolated in reversible quarantine storage. Restore copies to their original paths or alternate folders.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Toolstrip Action Bar
        toolstrip = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        toolstrip.pack(fill="x", pady=(0, 10))

        ttk.Button(toolstrip, text="↩️ Restore to Original Location", style="Accent.TButton", command=self._restore_selected_original).pack(side="left", padx=(0, 6))
        ttk.Button(toolstrip, text="📁 Restore to Alternate Folder...", style="Secondary.TButton", command=self._restore_selected_alternate).pack(side="left", padx=(0, 15))
        ttk.Button(toolstrip, text="⏪ Undo Last Quarantine (Ctrl+Z)", style="Secondary.TButton", command=self.undo_last_quarantine).pack(side="left", padx=(0, 15))
        ttk.Button(toolstrip, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="left")

        # Permanent Delete button (Danger style, pushed right)
        ttk.Button(toolstrip, text="⚠️ Permanently Delete File", style="Danger.TButton", command=self._permanent_delete_selected).pack(side="right")

        # Quarantined Items Table
        table_frame = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        cols = ("id", "name", "size", "date", "status", "orig_path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="File Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("date", text="Quarantined At")
        self.tree.heading("status", text="Status")
        self.tree.heading("orig_path", text="Original Path")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("name", width=180)
        self.tree.column("size", width=85, anchor="e")
        self.tree.column("date", width=130)
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("orig_path", width=380)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def refresh(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        self.items = self.db.get_all_quarantine_items()
        for item in self.items:
            self.tree.insert("", "end", iid=str(item.id), values=(
                item.id,
                item.filename,
                item.formatted_size,
                (item.quarantined_at or "")[:19],
                item.status.upper(),
                item.original_path
            ))

    def _get_selected_item(self) -> Optional[QuarantineItem]:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Item", "Please select an item from the quarantine table.", parent=self)
            return None
        item_id = int(sel[0])
        return next((i for i in self.items if i.id == item_id), None)

    def _restore_selected_original(self):
        item = self._get_selected_item()
        if not item:
            return

        success, path, err = self.restore_mgr.restore_item(item.id)
        if success:
            messagebox.showinfo("Restored", f"File restored successfully to:\n\n{path}", parent=self)
            self.refresh()
        else:
            messagebox.showerror("Restore Failed", f"Could not restore file:\n\n{err}", parent=self)

    def _restore_selected_alternate(self):
        item = self._get_selected_item()
        if not item:
            return

        folder = filedialog.askdirectory(title="Choose Alternate Folder for Restoration")
        if not folder:
            return

        success, path, err = self.restore_mgr.restore_item(item.id, target_directory=folder)
        if success:
            messagebox.showinfo("Restored", f"File restored successfully to alternate location:\n\n{path}", parent=self)
            self.refresh()
        else:
            messagebox.showerror("Restore Failed", f"Could not restore file:\n\n{err}", parent=self)

    def undo_last_quarantine(self):
        success, count, errors = self.restore_mgr.undo_last_quarantine()
        if success:
            messagebox.showinfo(
                "Undo Successful",
                f"Successfully restored {count} quarantined files from the last cleanup operation.",
                parent=self
            )
            self.refresh()
        else:
            msg = "; ".join(errors) if errors else "No eligible quarantine operation found to undo."
            messagebox.showwarning("Undo Operation", msg, parent=self)

    def _permanent_delete_selected(self):
        item = self._get_selected_item()
        if not item:
            return

        confirm = messagebox.askyesno(
            "IRREVERSIBLE ACTION — Permanent Deletion",
            f"WARNING: You are about to permanently delete this file from quarantine storage:\n\n"
            f"File: {item.filename}\n"
            f"Size: {item.formatted_size}\n\n"
            f"This cannot be undone. Are you absolutely certain?",
            icon="warning",
            parent=self
        )
        if confirm:
            success, err = self.quarantine_mgr.permanently_delete_quarantined_item(item.id)
            if success:
                messagebox.showinfo("Deleted", "File permanently erased from quarantine storage.", parent=self)
                self.refresh()
            else:
                messagebox.showerror("Deletion Error", err or "Failed to delete file.", parent=self)
