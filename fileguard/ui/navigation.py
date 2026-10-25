"""
Sidebar Navigation Component for FileGuard.
Provides a clean, productivity-focused sidebar with active state indicators and hover feedback.
"""
import tkinter as tk
from typing import Callable, Dict, List, Optional


class NavigationSidebar(tk.Frame):
    def __init__(
        self,
        parent,
        on_navigate: Callable[[str], None],
        palette: Dict[str, str] = None,
        **kwargs
    ):
        p = palette or {}
        self.palette = p
        bg = p.get("surface", "#1e293b")
        border = p.get("border", "#334155")
        self.on_navigate = on_navigate

        super().__init__(parent, bg=bg, width=220, highlightbackground=border, highlightthickness=1, **kwargs)
        self.pack_propagate(False)

        # Brand / Logo Header
        brand_frame = tk.Frame(self, bg=bg, padx=16, pady=18)
        brand_frame.pack(fill="x")

        brand_title = tk.Label(
            brand_frame,
            text="FILEGUARD",
            font=("Segoe UI", 13, "bold"),
            fg=p.get("accent", "#14b8a6"),
            bg=bg,
            anchor="w"
        )
        brand_title.pack(fill="x")

        brand_sub = tk.Label(
            brand_frame,
            text="Storage Intelligence v1.0",
            font=("Segoe UI", 8),
            fg=p.get("text_secondary", "#94a3b8"),
            bg=bg,
            anchor="w"
        )
        brand_sub.pack(fill="x")

        # Divider
        divider = tk.Frame(self, bg=border, height=1)
        divider.pack(fill="x", padx=12, pady=(0, 10))

        # Nav Items definitions
        self.nav_items = [
            ("overview", "📊  Overview"),
            ("scan", "📁  Scan Files"),
            ("duplicates", "📑  Duplicate Review"),
            ("large_files", "📦  Large Files"),
            ("storage", "📈  Storage Analysis"),
            ("empty_temp", "🧹  Empty & Temp Files"),
            ("quarantine", "🛡️  Quarantine & Recovery"),
            ("history", "⏱️  Scan History"),
            ("integrity", "🔒  Integrity Checks"),
            ("reports", "📄  Reports & Export"),
            ("schedules", "⏰  Scheduled Scans"),
            ("similar_photos", "🖼️  Similar Photos"),
            ("settings", "⚙️  Settings")
        ]

        self.btn_map: Dict[str, tk.Label] = {}
        self.active_key = "overview"

        # Container for scrollable or stacked nav buttons
        self.nav_container = tk.Frame(self, bg=bg)
        self.nav_container.pack(fill="both", expand=True, padx=8)

        for key, label in self.nav_items:
            item_lbl = tk.Label(
                self.nav_container,
                text=label,
                font=("Segoe UI", 9),
                fg=p.get("text_secondary", "#94a3b8"),
                bg=bg,
                anchor="w",
                padx=12,
                pady=7,
                cursor="hand2"
            )
            item_lbl.pack(fill="x", pady=1)

            # Bind events
            item_lbl.bind("<Button-1>", lambda e, k=key: self.select_item(k))
            item_lbl.bind("<Enter>", lambda e, lbl=item_lbl, k=key: self._on_hover(lbl, k))
            item_lbl.bind("<Leave>", lambda e, lbl=item_lbl, k=key: self._on_leave(lbl, k))

            self.btn_map[key] = item_lbl

        self._update_styles()

    def select_item(self, key: str):
        self.active_key = key
        self._update_styles()
        if self.on_navigate:
            self.on_navigate(key)

    def _update_styles(self):
        p = self.palette
        bg = p.get("surface", "#1e293b")
        active_bg = p.get("accent_bg", "#134e4a")
        active_fg = p.get("accent", "#14b8a6")
        normal_fg = p.get("text_secondary", "#94a3b8")

        for key, lbl in self.btn_map.items():
            if key == self.active_key:
                lbl.config(bg=active_bg, fg=active_fg, font=("Segoe UI", 9, "bold"))
            else:
                lbl.config(bg=bg, fg=normal_fg, font=("Segoe UI", 9))

    def _on_hover(self, lbl: tk.Label, key: str):
        if key != self.active_key:
            lbl.config(bg=self.palette.get("surface_hover", "#334155"), fg=self.palette.get("text_primary", "#f8fafc"))

    def _on_leave(self, lbl: tk.Label, key: str):
        if key != self.active_key:
            lbl.config(bg=self.palette.get("surface", "#1e293b"), fg=self.palette.get("text_secondary", "#94a3b8"))
