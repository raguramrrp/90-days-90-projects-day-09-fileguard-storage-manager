"""
Sample Data Generator for FileGuard.
Creates realistic test folders with exact duplicates, large files, similar images,
empty folders, and temporary files for safe local evaluation.
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_sample_environment(base_dir: Path = None):
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent / "data" / "sample_files"

    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating FileGuard sample files in: {base_dir}")

    # Subfolders
    docs_dir = base_dir / "Documents"
    downloads_dir = base_dir / "Downloads"
    photos_dir = base_dir / "Photos"
    backup_dir = base_dir / "Backup"
    temp_dir = base_dir / "Temp"
    empty_parent = base_dir / "Empty_Directories" / "Nested_Empty"

    for d in [docs_dir, downloads_dir, photos_dir, backup_dir, temp_dir, empty_parent]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Exact Duplicates Group A (Report PDF / text)
    report_content = (
        b"CONFIDENTIAL PROJECT REPORT\n"
        b"Version 1.0 - Quarter 3 Analysis\n"
        b"Summary: System storage efficiency requires deduplication and quarantine safety.\n"
        * 100
    )
    (docs_dir / "Q3_Financial_Report.txt").write_bytes(report_content)
    (downloads_dir / "Q3_Financial_Report (1).txt").write_bytes(report_content)
    (backup_dir / "Q3_Financial_Report_old.txt").write_bytes(report_content)

    # 2. Exact Duplicates Group B (Source code duplicate)
    code_content = (
        b"# Database connector utility\n"
        b"import sqlite3\n"
        b"def get_conn(): return sqlite3.connect(':memory:')\n"
        * 50
    )
    (docs_dir / "db_connector.py").write_bytes(code_content)
    (downloads_dir / "db_connector_copy.py").write_bytes(code_content)

    # 3. Large Files (12 MB and 8 MB dummy data)
    large_file_path = docs_dir / "System_Archive_Dataset.dat"
    if not large_file_path.exists():
        print("Generating 12 MB large test file...")
        chunk = b"LARGE_TEST_STREAM_BLOCK_RECOVERY_" * 1024  # 32 KB chunk
        with open(large_file_path, "wb") as f:
            for _ in range(384):  # 384 * 32 KB = 12 MB
                f.write(chunk)

    # Duplicate of large file in Backup
    backup_large_file = backup_dir / "System_Archive_Dataset_backup.dat"
    if not backup_large_file.exists():
        backup_large_file.write_bytes(large_file_path.read_bytes())

    # 4. Unique File
    (docs_dir / "Unique_Notes.md").write_text(
        "# Independent Project Notes\nThis file is unique and must never be flagged as a duplicate.",
        encoding="utf-8"
    )

    # 5. Temporary Files
    (temp_dir / "build_cache_001.tmp").write_bytes(b"TEMP_CACHE_STREAM_" * 50)
    (temp_dir / "~WRL0002.tmp").write_bytes(b"WORD_RECOVERY_CACHE" * 30)
    (downloads_dir / "installer_setup.bak").write_bytes(b"OLD_BACKUP_INSTALLER" * 40)
    (temp_dir / "application_debug.log").write_bytes(b"[DEBUG] App initialized\n" * 20)

    # 6. Images (Exact duplicates and Near-duplicates)
    if HAS_PIL:
        # Base image
        img1 = Image.new("RGB", (300, 300), color=(13, 148, 136)) # Teal
        d1 = ImageDraw.Draw(img1)
        d1.rectangle([(50, 50), (250, 250)], fill=(20, 184, 166), outline=(255, 255, 255))
        d1.text((70, 140), "FileGuard Logo", fill=(255, 255, 255))

        img1_path = photos_dir / "fileguard_logo.png"
        img1.save(img1_path)

        # Exact duplicate in downloads
        img1_dup = downloads_dir / "fileguard_logo_download.png"
        img1.save(img1_dup)

        # Near-duplicate: slight resize/compression
        img_similar = img1.resize((280, 280)).resize((300, 300))
        img_similar.save(photos_dir / "fileguard_logo_compressed.jpg", quality=85)

        # Different image
        img2 = Image.new("RGB", (300, 300), color=(244, 63, 94)) # Coral
        d2 = ImageDraw.Draw(img2)
        d2.ellipse([(50, 50), (250, 250)], fill=(251, 113, 133))
        img2.save(photos_dir / "different_photo.png")

    print("Sample test environment generated successfully.")
    return base_dir


if __name__ == "__main__":
    create_sample_environment()
