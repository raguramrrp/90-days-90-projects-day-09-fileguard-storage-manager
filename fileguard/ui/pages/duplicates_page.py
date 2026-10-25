"""
Duplicate Review Page for FileGuard.
Explorer-style duplicate review table with group hierarchy, theoretical vs selected savings,
selection advisors, safety preview, and resizable preview pane.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from fileguard.models import DuplicateGroup, FileRecord, format_bytes
from fileguard.database import Database
from fileguard.cleanup_manager import CleanupManager
from fileguard.quarantine_manager import QuarantineManager
from fileguard.ui.components import SearchBar, PreviewPane
from fileguard.ui.dialogs import CleanupPreviewDialog


class DuplicatesPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette

        self.cleanup_mgr = CleanupManager(self.db)
        self.quarantine_mgr = QuarantineManager(self.db)

        self.all_groups: List[DuplicateGroup] = []
        self.filtered_groups: List[DuplicateGroup] = []
        self.selected_file_ids: Set[int] = set()
        self.file_map: Dict[int, FileRecord] = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        p = self.palette
        bg = p.get("bg", "#0f172a")
        surface = p.get("surface", "#1e293b")
        text_pri = p.get("text_primary", "#f8fafc")
        text_sec = p.get("text_secondary", "#94a3b8")
        accent = p.get("accent", "#14b8a6")

        # Top Control & Filter Bar
        top_bar = tk.Frame(self, bg=bg)
        top_bar.pack(fill="x", pady=(0, 10))

        # Search box
        self.search_bar = SearchBar(top_bar, placeholder="Filter by filename, folder, or extension...", on_search=self._on_search_changed, palette=p)
        self.search_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Category filter
        self.cat_var = tk.StringVar(value="All Categories")
        self.cat_cb = ttk.Combobox(
            top_bar,
            textvariable=self.cat_var,
            values=["All Categories", "Documents", "Images", "Code", "Audio", "Video", "Archives", "Other"],
            state="readonly",
            width=15
        )
        self.cat_cb.pack(side="left", padx=(0, 10))
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Refresh
        ttk.Button(top_bar, text="🔄 Refresh", style="Secondary.TButton", command=self.refresh).pack(side="left")

        # Selection & Action Toolstrip
        toolstrip = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        toolstrip.pack(fill="x", pady=(0, 10))

        ttk.Button(toolstrip, text="✨ Select Suggested Copies", style="Secondary.TButton", command=self._select_suggested).pack(side="left", padx=(0, 6))
        ttk.Button(toolstrip, text="Select All (Retain 1)", style="Secondary.TButton", command=self._select_all_safe).pack(side="left", padx=(0, 6))
        ttk.Button(toolstrip, text="Clear Selection", style="Secondary.TButton", command=self._clear_selection).pack(side="left", padx=(0, 15))

        self.selection_summary_lbl = tk.Label(
            toolstrip,
            text="Selected: 0 files (0 B) | Theoretical Savings: 0 B",
            font=("Segoe UI", 9, "bold"),
            fg=accent,
            bg=surface
        )
        self.selection_summary_lbl.pack(side="left")

        self.btn_clean = ttk.Button(toolstrip, text="🛡️ Move Selected to Quarantine...", style="Accent.TButton", command=self._open_cleanup_modal)
        self.btn_clean.pack(side="right")

        # Resizable Paned Window (Left: Table, Right: Preview Pane)
        self.paned = ttk.Panedwindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        # Left Table Frame
        table_frame = tk.Frame(self.paned, bg=bg)
        self.paned.add(table_frame, weight=3)

        cols = ("check", "role", "name", "size", "reason", "path")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Duplicate Group / Hash")
        self.tree.heading("check", text="Sel")
        self.tree.heading("role", text="Role")
        self.tree.heading("name", text="File Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("reason", text="Recommendation Reason")
        self.tree.heading("path", text="Path")

        self.tree.column("#0", width=180)
        self.tree.column("check", width=40, anchor="center")
        self.tree.column("role", width=80, anchor="center")
        self.tree.column("name", width=180)
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("reason", width=220)
        self.tree.column("path", width=260)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Right Preview Frame
        self.preview_pane = PreviewPane(self.paned, palette=p)
        self.paned.add(self.preview_pane, weight=1)

    def refresh(self):
        """Fetch latest duplicate groups from DB."""
        self.all_groups = self.db.get_duplicate_groups()
        self.file_map = {}
        for g in self.all_groups:
            for m in g.members:
                self.file_map[m.id] = m

        self._apply_filters()

    def _apply_filters(self):
        query = self.search_bar.search_var.get().strip().lower()
        cat = self.cat_var.get()

        self.filtered_groups = []
        for g in self.all_groups:
            matched_members = []
            for m in g.members:
                if cat != "All Categories" and m.category != cat:
                    continue
                if query and (query not in m.filename.lower() and query not in m.path.lower()):
                    continue
                matched_members.append(m)

            if len(matched_members) >= 2 or (query and len(matched_members) >= 1):
                # Include group if criteria match
                self.filtered_groups.append(g)

        self._populate_tree()
        self._update_selection_summary()

    def _populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for g in self.filtered_groups:
            group_label = f"Group #{g.id} ({g.file_count} copies, max save {g.formatted_max_recoverable})"
            group_node = self.tree.insert("", "end", text=group_label, open=True)

            for m in g.members:
                is_selected = m.id in self.selected_file_ids
                check_icon = "☑" if is_selected else "☐"
                is_retained = (g.suggested_retained_file_id == m.id)
                role = "RETAIN" if is_retained else "Candidate"
                reason = g.suggestion_reasons.get(m.id, "")

                self.tree.insert(
                    group_node,
                    "end",
                    iid=f"file_{m.id}",
                    values=(check_icon, role, m.filename, m.formatted_size, reason, m.path)
                )

    def _on_tree_click(self, event):
        """Handle clicks on the checkbox column to toggle selection."""
        region = self.tree.identify_region(event.x, event.y)
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)

        if not item or not item.startswith("file_"):
            return

        file_id = int(item.replace("file_", ""))

        if column == "#1":  # 'check' column
            if file_id in self.selected_file_ids:
                self.selected_file_ids.remove(file_id)
            else:
                self.selected_file_ids.add(file_id)
            self._update_item_checkbox(item, file_id)
            self._update_selection_summary()

    def _update_item_checkbox(self, item_iid: str, file_id: int):
        cur_vals = list(self.tree.item(item_iid, "values"))
        cur_vals[0] = "☑" if file_id in self.selected_file_ids else "☐"
        self.tree.item(item_iid, values=cur_vals)

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = sel[0]
        if item_id.startswith("file_"):
            fid = int(item_id.replace("file_", ""))
            f = self.file_map.get(fid)
            if f:
                self.preview_pane.show_file(
                    f.path,
                    size_bytes=f.size_bytes,
                    sha256_hash=f.sha256_hash,
                    modified_time=f.formatted_modified
                )

    def _on_search_changed(self, text: str):
        self._apply_filters()

    def _select_suggested(self):
        """Select all recommended cleanup candidates while leaving suggested retained copies unchecked."""
        self.selected_file_ids.clear()
        for g in self.all_groups:
            retained_id = g.suggested_retained_file_id
            for m in g.members:
                if m.id != retained_id:
                    self.selected_file_ids.add(m.id)
        self._populate_tree()
        self._update_selection_summary()

    def _select_all_safe(self):
        """Select all duplicates except the first copy in each group."""
        self.selected_file_ids.clear()
        for g in self.all_groups:
            if g.members:
                # Keep first member, select rest
                for m in g.members[1:]:
                    self.selected_file_ids.add(m.id)
        self._populate_tree()
        self._update_selection_summary()

    def _clear_selection(self):
        self.selected_file_ids.clear()
        self._populate_tree()
        self._update_selection_summary()

    def _update_selection_summary(self):
        sel_count = len(self.selected_file_ids)
        sel_bytes = sum(self.file_map[fid].size_bytes for fid in self.selected_file_ids if fid in self.file_map)
        theo_bytes = sum(g.max_recoverable_bytes for g in self.all_groups)

        self.selection_summary_lbl.config(
            text=f"Selected: {sel_count} files ({format_bytes(sel_bytes)})  |  Max Theoretical Savings: {format_bytes(theo_bytes)}"
        )

    def _open_cleanup_modal(self):
        if not self.selected_file_ids:
            messagebox.showinfo("No Files Selected", "Please select one or more candidate files to quarantine.", parent=self)
            return

        preview = self.cleanup_mgr.prepare_cleanup_preview(list(self.selected_file_ids), self.all_groups)

        if not preview["can_proceed"]:
            # All items were blocked (e.g. all copies selected violation or protected paths)
            reasons = "\n• ".join([f"{it['filename']}: {it['reason']}" for it in preview.get("blocked_items", [])[:5]])
            messagebox.showerror(
                "Cleanup Blocked by Safety Guard",
                f"Selected operations cannot proceed due to safety restrictions:\n\n• {reasons}",
                parent=self
            )
            return

        def do_quarantine():
            op = self.quarantine_mgr.execute_quarantine(preview["items_to_clean"])
            self.selected_file_ids.clear()
            self.refresh()
            messagebox.showinfo(
                "Quarantine Successful",
                f"Successfully moved {op.items_count} duplicate files ({op.formatted_bytes}) to safe quarantine storage.\n"
                f"You can restore or undo anytime in the Quarantine tab.",
                parent=self
            )

        CleanupPreviewDialog(self, preview, self.palette, do_quarantine)
