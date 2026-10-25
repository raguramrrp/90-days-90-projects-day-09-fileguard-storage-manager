"""
Main Application Window for FileGuard.
Integrates navigation, theme engine, page routing, keyboard shortcuts,
and background execution loops into a coherent desktop application.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional

from fileguard.config import APP_DIR
from fileguard.database import Database
from fileguard.ui.theme import apply_theme, PALETTES
from fileguard.ui.navigation import NavigationSidebar

# Page imports
from fileguard.ui.pages.overview_page import OverviewPage
from fileguard.ui.pages.scan_page import ScanPage
from fileguard.ui.pages.duplicates_page import DuplicatesPage
from fileguard.ui.pages.large_files_page import LargeFilesPage
from fileguard.ui.pages.storage_page import StoragePage
from fileguard.ui.pages.folder_temp_page import FolderTempPage
from fileguard.ui.pages.quarantine_page import QuarantinePage
from fileguard.ui.pages.history_page import HistoryPage
from fileguard.ui.pages.integrity_page import IntegrityPage
from fileguard.ui.pages.reports_page import ReportsPage
from fileguard.ui.pages.schedule_page import SchedulePage
from fileguard.ui.pages.similar_photos_page import SimilarPhotosPage
from fileguard.ui.pages.settings_page import SettingsPage


class MainWindow(tk.Tk):
    def __init__(self, db: Optional[Database] = None):
        super().__init__()
        self.db = db or Database()
        self.current_theme = self.db.get_setting("theme", "dark")

        # Window Configuration
        self.title("FileGuard — Intelligent Duplicate File Detection & Storage Manager")
        self.geometry("1180x760")
        self.minsize(980, 620)

        # Apply Theme
        self.palette = apply_theme(self, self.current_theme)

        # Assemble Interface Layout
        self._build_layout()
        self._bind_shortcuts()

        # Start on Overview page
        self.navigate_to("overview")

    def _build_layout(self):
        # Top-level container
        self.container = tk.Frame(self, bg=self.palette.get("bg", "#0f172a"))
        self.container.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = NavigationSidebar(self.container, on_navigate=self.navigate_to, palette=self.palette)
        self.sidebar.pack(side="left", fill="y")

        # Main Content Workspace
        self.workspace = tk.Frame(self.container, bg=self.palette.get("bg", "#0f172a"))
        self.workspace.pack(side="right", fill="both", expand=True)

        # Initialize all pages inside workspace
        self.pages: Dict[str, tk.Frame] = {}

        self.pages["overview"] = OverviewPage(self.workspace, self.db, self.palette, on_navigate=self.navigate_to)
        self.pages["scan"] = ScanPage(self.workspace, self.db, self.palette, on_scan_completed=self._on_scan_done)
        self.pages["duplicates"] = DuplicatesPage(self.workspace, self.db, self.palette)
        self.pages["large_files"] = LargeFilesPage(self.workspace, self.db, self.palette)
        self.pages["storage"] = StoragePage(self.workspace, self.db, self.palette)
        self.pages["empty_temp"] = FolderTempPage(self.workspace, self.db, self.palette)
        self.pages["quarantine"] = QuarantinePage(self.workspace, self.db, self.palette)
        self.pages["history"] = HistoryPage(self.workspace, self.db, self.palette)
        self.pages["integrity"] = IntegrityPage(self.workspace, self.db, self.palette)
        self.pages["reports"] = ReportsPage(self.workspace, self.db, self.palette)
        self.pages["schedules"] = SchedulePage(self.workspace, self.db, self.palette)
        self.pages["similar_photos"] = SimilarPhotosPage(self.workspace, self.db, self.palette)
        self.pages["settings"] = SettingsPage(self.workspace, self.db, self.palette, on_theme_changed=self.change_theme)

    def navigate_to(self, page_key: str):
        """Switch active workspace view."""
        for key, p in self.pages.items():
            if key == page_key:
                p.pack(fill="both", expand=True)
                if hasattr(p, "refresh"):
                    p.refresh()
            else:
                p.pack_forget()

        self.sidebar.active_key = page_key
        self.sidebar._update_styles()

    def change_theme(self, new_theme: str):
        """Dynamically re-apply theme across application."""
        self.current_theme = new_theme
        self.palette = apply_theme(self, new_theme)
        self.db.set_setting("theme", new_theme)

        # Rebuild layout to propagate color updates
        self.container.destroy()
        self._build_layout()
        self.navigate_to("settings")

    def _on_scan_done(self, scan_id: int):
        """Triggered automatically when a scan finishes."""
        self.navigate_to("duplicates")

    def _bind_shortcuts(self):
        """Configure standard Windows productivity keyboard shortcuts."""
        # Ctrl+O: Choose scan folders
        self.bind("<Control-o>", lambda e: self._shortcut_open_folder())
        self.bind("<Control-O>", lambda e: self._shortcut_open_folder())

        # Ctrl+F: Focus search
        self.bind("<Control-f>", lambda e: self._shortcut_focus_search())
        self.bind("<Control-F>", lambda e: self._shortcut_focus_search())

        # F5: Refresh active page
        self.bind("<F5>", lambda e: self._shortcut_refresh())

        # Esc: Clear search
        self.bind("<Escape>", lambda e: self._shortcut_escape())

        # Ctrl+E: Open export reports
        self.bind("<Control-e>", lambda e: self.navigate_to("reports"))
        self.bind("<Control-E>", lambda e: self.navigate_to("reports"))

        # Ctrl+Z: Undo last quarantine
        self.bind("<Control-z>", lambda e: self._shortcut_undo())
        self.bind("<Control-Z>", lambda e: self._shortcut_undo())

    def _shortcut_open_folder(self):
        self.navigate_to("scan")
        self.pages["scan"]._add_folder()

    def _shortcut_focus_search(self):
        active = self.sidebar.active_key
        if active in ("duplicates", "large_files"):
            page = self.pages[active]
            if hasattr(page, "search_bar"):
                page.search_bar.focus()

    def _shortcut_refresh(self):
        active = self.sidebar.active_key
        page = self.pages.get(active)
        if page and hasattr(page, "refresh"):
            page.refresh()

    def _shortcut_escape(self):
        active = self.sidebar.active_key
        if active in ("duplicates", "large_files"):
            page = self.pages[active]
            if hasattr(page, "search_bar"):
                page.search_bar.clear()

    def _shortcut_undo(self):
        self.navigate_to("quarantine")
        self.pages["quarantine"].undo_last_quarantine()
