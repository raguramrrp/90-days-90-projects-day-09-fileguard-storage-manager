"""
Similar Photos Page for FileGuard (Priority 3 Advanced Capability).
Identifies visually similar / near-duplicate photos using difference hashing (dHash),
Hamming distance calculations, and side-by-side comparison without mixing into exact SHA-256 groups.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from fileguard.models import FileRecord, format_bytes
from fileguard.database import Database
from fileguard.perceptual_hash import (
    is_pillow_available, compute_dhash, calculate_hamming_distance,
    calculate_similarity_percent, get_image_dimensions
)
from fileguard.workers import run_in_background


class SimilarPhotosPage(tk.Frame):
    def __init__(self, parent, db: Database, palette: Dict[str, str], **kwargs):
        super().__init__(parent, bg=palette.get("bg", "#0f172a"), padx=20, pady=16, **kwargs)
        self.db = db
        self.palette = palette

        self.similar_pairs: List[Dict[str, Any]] = []
        self._photo_ref_a = None
        self._photo_ref_b = None

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
        header.pack(fill="x", pady=(0, 10))

        tk.Label(header, text="Visual Similar-Photo Discovery (Perceptual dHash)", font=("Segoe UI", 16, "bold"), fg=text_pri, bg=bg).pack(anchor="w")
        tk.Label(
            header,
            text="Detects visually similar photos across different dimensions or compressions. Kept strictly distinct from exact SHA-256 duplicates.",
            font=("Segoe UI", 9),
            fg=text_sec,
            bg=bg
        ).pack(anchor="w", pady=(2, 0))

        # Toolstrip Controls
        toolstrip = tk.Frame(self, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=8)
        toolstrip.pack(fill="x", pady=(0, 10))

        self.btn_scan_similar = ttk.Button(toolstrip, text="🔍 Analyze Images for Visual Similarity", style="Accent.TButton", command=self._start_analysis)
        self.btn_scan_similar.pack(side="left", padx=(0, 12))

        tk.Label(toolstrip, text="Similarity Threshold:", font=("Segoe UI", 9), fg=text_sec, bg=surface).pack(side="left", padx=(0, 4))
        self.threshold_var = tk.StringVar(value="85%")
        self.cb_thresh = ttk.Combobox(toolstrip, textvariable=self.threshold_var, values=["75%", "80%", "85%", "90%", "95%"], state="readonly", width=6)
        self.cb_thresh.pack(side="left", padx=(0, 15))

        self.status_lbl = tk.Label(toolstrip, text="", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface)
        self.status_lbl.pack(side="right")

        # Paned Window (Left: Pairs Table, Right: Side-by-side thumbnails)
        self.paned = ttk.Panedwindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        # Left Table Frame
        table_frame = tk.Frame(self.paned, bg=bg)
        self.paned.add(table_frame, weight=3)

        cols = ("similarity", "distance", "photo_a", "photo_b")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("similarity", text="Similarity")
        self.tree.heading("distance", text="Hamming Dist")
        self.tree.heading("photo_a", text="Image A")
        self.tree.heading("photo_b", text="Image B")

        self.tree.column("similarity", width=90, anchor="center")
        self.tree.column("distance", width=100, anchor="center")
        self.tree.column("photo_a", width=240)
        self.tree.column("photo_b", width=240)

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_pair)

        # Right Side-by-Side Comparison Frame
        cmp_frame = tk.Frame(self.paned, bg=surface, highlightbackground=p.get("border", "#334155"), highlightthickness=1, padx=12, pady=12)
        self.paned.add(cmp_frame, weight=2)

        tk.Label(cmp_frame, text="SIDE-BY-SIDE VISUAL COMPARISON", font=("Segoe UI", 9, "bold"), fg=accent, bg=surface).pack(anchor="w", pady=(0, 10))

        # Two thumbnail slots
        thumbs_box = tk.Frame(cmp_frame, bg=surface)
        thumbs_box.pack(fill="both", expand=True)
        thumbs_box.columnconfigure((0, 1), weight=1)

        # Slot A
        self.frame_a = tk.Frame(thumbs_box, bg=bg, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        self.frame_a.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.lbl_img_a = tk.Label(self.frame_a, bg=bg, fg=text_sec, text="Select a pair to compare", font=("Segoe UI", 8))
        self.lbl_img_a.pack(fill="both", expand=True)
        self.lbl_meta_a = tk.Label(self.frame_a, bg=bg, fg=text_pri, font=("Segoe UI", 8), text="")
        self.lbl_meta_a.pack(fill="x", pady=2)

        # Slot B
        self.frame_b = tk.Frame(thumbs_box, bg=bg, highlightbackground=p.get("border", "#334155"), highlightthickness=1)
        self.frame_b.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.lbl_img_b = tk.Label(self.frame_b, bg=bg, fg=text_sec, text="Select a pair to compare", font=("Segoe UI", 8))
        self.lbl_img_b.pack(fill="both", expand=True)
        self.lbl_meta_b = tk.Label(self.frame_b, bg=bg, fg=text_pri, font=("Segoe UI", 8), text="")
        self.lbl_meta_b.pack(fill="x", pady=2)

    def _start_analysis(self):
        if not is_pillow_available():
            messagebox.showwarning("Pillow Not Installed", "Pillow is required for perceptual image hashing.", parent=self)
            return

        latest = self.db.get_latest_scan()
        if not latest:
            messagebox.showinfo("No Scans", "Please run a file scan first.", parent=self)
            return

        files = self.db.get_files_by_scan(latest.id)
        image_files = [f for f in files if f.category == "Images" and os.path.exists(f.path)]

        if len(image_files) < 2:
            messagebox.showinfo("Insufficient Images", "Found fewer than 2 indexed images in the latest scan scope.", parent=self)
            return

        thresh_val = int(self.threshold_var.get().replace("%", ""))

        self.btn_scan_similar.config(state="disabled")
        self.status_lbl.config(text=f"Computing perceptual hashes for {len(image_files)} images...")

        def run_proc():
            # 1. Compute dHash for all images
            hashes: Dict[int, str] = {}
            for img_f in image_files:
                h = compute_dhash(img_f.path)
                if h:
                    hashes[img_f.id] = h

            # 2. Pairwise comparison
            pairs = []
            img_list = [f for f in image_files if f.id in hashes]
            n = len(img_list)

            for i in range(n):
                for j in range(i + 1, n):
                    f_a = img_list[i]
                    f_b = img_list[j]

                    # Skip exact identical files (they are exact duplicates, not approximate!)
                    if f_a.sha256_hash and f_b.sha256_hash and f_a.sha256_hash == f_b.sha256_hash:
                        continue

                    h_a = hashes[f_a.id]
                    h_b = hashes[f_b.id]
                    dist = calculate_hamming_distance(h_a, h_b)
                    sim = calculate_similarity_percent(dist)

                    if sim >= thresh_val:
                        pairs.append({
                            "similarity": sim,
                            "distance": dist,
                            "file_a": f_a,
                            "file_b": f_b
                        })

            pairs.sort(key=lambda x: x["similarity"], reverse=True)
            self.after(50, lambda: self._on_analysis_done(pairs))

        run_in_background(run_proc)

    def _on_analysis_done(self, pairs: List[Dict[str, Any]]):
        self.btn_scan_similar.config(state="normal")
        self.similar_pairs = pairs

        for it in self.tree.get_children():
            self.tree.delete(it)

        for idx, p in enumerate(self.similar_pairs):
            self.tree.insert("", "end", iid=str(idx), values=(
                f"{p['similarity']}%",
                f"{p['distance']} bits",
                p["file_a"].filename,
                p["file_b"].filename
            ))

        self.status_lbl.config(text=f"Found {len(pairs)} visually similar image pairs.")
        if not pairs:
            messagebox.showinfo("No Similar Images", "No images exceeded the visual similarity threshold.", parent=self)

    def _on_select_pair(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        pair = self.similar_pairs[idx]
        fa = pair["file_a"]
        fb = pair["file_b"]

        self._load_thumbnail(fa.path, self.lbl_img_a, self.lbl_meta_a, is_a=True)
        self._load_thumbnail(fb.path, self.lbl_img_b, self.lbl_meta_b, is_a=False)

    def _load_thumbnail(self, path_str: str, img_lbl: tk.Label, meta_lbl: tk.Label, is_a: bool):
        if not HAS_PIL or not os.path.exists(path_str):
            img_lbl.config(text="Image unavailable", image="")
            meta_lbl.config(text="")
            return

        try:
            with Image.open(path_str) as img:
                w, h = img.size
                img.thumbnail((220, 180))
                p_img = ImageTk.PhotoImage(img)
                if is_a:
                    self._photo_ref_a = p_img
                else:
                    self._photo_ref_b = p_img
                img_lbl.config(image=p_img, text="")
                meta_lbl.config(text=f"{Path(path_str).name}\n{w}x{h} px  •  {format_bytes(os.path.getsize(path_str))}")
        except Exception:
            img_lbl.config(text="Decode error", image="")
            meta_lbl.config(text="")
