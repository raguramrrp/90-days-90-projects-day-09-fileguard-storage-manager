"""
Custom Premium Theme System for FileGuard.
Teal-accented color schemes supporting runtime switching between Light and Dark modes.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

PALETTES = {
    "dark": {
        "bg": "#0f172a",             # Main window background
        "surface": "#1e293b",        # Panels, cards, tables
        "surface_hover": "#334155",  # Hover states
        "surface_active": "#243248",
        "border": "#334155",         # Dividers and borders
        "border_light": "#475569",
        "text_primary": "#f8fafc",   # Crisp readable white
        "text_secondary": "#94a3b8", # Muted labels
        "text_muted": "#64748b",
        "accent": "#14b8a6",         # Primary Teal accent
        "accent_hover": "#0d9488",   # Darker teal for click/hover
        "accent_bg": "#134e4a",      # Low-opacity teal backdrop
        "accent_text": "#ffffff",
        "success": "#34d399",        # Soft green
        "warning": "#fbbf24",        # Amber
        "danger": "#f87171",         # Muted coral/red
        "danger_hover": "#ef4444",
        "tree_select_bg": "#0f766e", # Deep teal selection
        "tree_select_fg": "#ffffff",
        "input_bg": "#0f172a",
        "input_fg": "#f8fafc"
    },
    "light": {
        "bg": "#f8fafc",             # Clean neutral slate-50
        "surface": "#ffffff",        # White cards and panels
        "surface_hover": "#f1f5f9",  # Subtle hover
        "surface_active": "#e2e8f0",
        "border": "#e2e8f0",         # Subtle grey borders
        "border_light": "#cbd5e1",
        "text_primary": "#0f172a",   # Deep charcoal primary
        "text_secondary": "#64748b", # Muted secondary
        "text_muted": "#94a3b8",
        "accent": "#0d9488",         # Rich teal
        "accent_hover": "#0f766e",
        "accent_bg": "#ccfbf1",
        "accent_text": "#ffffff",
        "success": "#10b981",
        "warning": "#d97706",
        "danger": "#ef4444",
        "danger_hover": "#dc2626",
        "tree_select_bg": "#ccfbf1",
        "tree_select_fg": "#0f766e",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a"
    }
}


def apply_theme(root: tk.Tk, theme_name: str = "dark") -> Dict[str, str]:
    """Configure ttk Styles and Tkinter root options for the specified theme."""
    palette = PALETTES.get(theme_name, PALETTES["dark"])
    style = ttk.Style()
    style.theme_use("clam")

    # General configuration
    root.configure(bg=palette["bg"])

    # Configure TFrame
    style.configure("TFrame", background=palette["bg"])
    style.configure("Surface.TFrame", background=palette["surface"])
    style.configure("Card.TFrame", background=palette["surface"], relief="flat")

    # Configure TLabel
    style.configure(
        "TLabel",
        background=palette["bg"],
        foreground=palette["text_primary"],
        font=("Segoe UI", 9)
    )
    style.configure(
        "Surface.TLabel",
        background=palette["surface"],
        foreground=palette["text_primary"],
        font=("Segoe UI", 9)
    )
    style.configure(
        "Secondary.TLabel",
        background=palette["bg"],
        foreground=palette["text_secondary"],
        font=("Segoe UI", 8)
    )
    style.configure(
        "SurfaceSecondary.TLabel",
        background=palette["surface"],
        foreground=palette["text_secondary"],
        font=("Segoe UI", 8)
    )
    style.configure(
        "Header.TLabel",
        background=palette["bg"],
        foreground=palette["text_primary"],
        font=("Segoe UI", 16, "bold")
    )
    style.configure(
        "Subheader.TLabel",
        background=palette["bg"],
        foreground=palette["text_secondary"],
        font=("Segoe UI", 10)
    )

    # Configure TButton (Primary, Secondary, Destructive)
    style.configure(
        "Accent.TButton",
        background=palette["accent"],
        foreground=palette["accent_text"],
        font=("Segoe UI", 9, "bold"),
        padding=(12, 6),
        borderwidth=0
    )
    style.map(
        "Accent.TButton",
        background=[("active", palette["accent_hover"]), ("disabled", palette["border"])],
        foreground=[("disabled", palette["text_muted"])]
    )

    style.configure(
        "Secondary.TButton",
        background=palette["surface_hover"],
        foreground=palette["text_primary"],
        font=("Segoe UI", 9),
        padding=(10, 5),
        borderwidth=1,
        relief="flat"
    )
    style.map(
        "Secondary.TButton",
        background=[("active", palette["border"]), ("disabled", palette["bg"])],
        foreground=[("disabled", palette["text_muted"])]
    )

    style.configure(
        "Danger.TButton",
        background=palette["danger"],
        foreground="#ffffff",
        font=("Segoe UI", 9, "bold"),
        padding=(10, 5),
        borderwidth=0
    )
    style.map(
        "Danger.TButton",
        background=[("active", palette["danger_hover"]), ("disabled", palette["border"])],
        foreground=[("disabled", palette["text_muted"])]
    )

    # Configure Treeview (Explorer style table)
    style.configure(
        "Treeview",
        background=palette["surface"],
        foreground=palette["text_primary"],
        fieldbackground=palette["surface"],
        borderwidth=0,
        rowheight=26,
        font=("Segoe UI", 9)
    )
    style.map(
        "Treeview",
        background=[("selected", palette["tree_select_bg"])],
        foreground=[("selected", palette["tree_select_fg"])]
    )

    style.configure(
        "Treeview.Heading",
        background=palette["surface_hover"],
        foreground=palette["text_secondary"],
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padding=(6, 6)
    )
    style.map(
        "Treeview.Heading",
        background=[("active", palette["border"])]
    )

    # Scrollbars
    style.configure(
        "TScrollbar",
        background=palette["surface"],
        troughcolor=palette["bg"],
        borderwidth=0,
        arrowsize=12
    )

    # Entry & Combobox
    style.configure(
        "TEntry",
        fieldbackground=palette["input_bg"],
        foreground=palette["input_fg"],
        insertcolor=palette["text_primary"],
        padding=4
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette["input_bg"],
        background=palette["surface_hover"],
        foreground=palette["text_primary"],
        padding=4
    )

    # Progressbar
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=palette["surface_hover"],
        background=palette["accent"],
        borderwidth=0
    )

    # Separator
    style.configure(
        "TSeparator",
        background=palette["border"]
    )

    # PanedWindow
    style.configure(
        "TPanedwindow",
        background=palette["bg"]
    )

    return palette
