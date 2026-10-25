# FileGuard Sample Data

This directory contains synthetic sample files designed to test and demonstrate FileGuard capabilities:

- **Exact Duplicates**: Files with identical content and SHA-256 hashes across different directories and names.
- **Similar Images**: Images with identical visual structure but re-encoded or resized to test perceptual hashing (dHash).
- **Large Files**: Files with varying sizes (1 MB to 15 MB) to test chunked hashing and large-file detection.
- **Temporary Files**: Files with `.tmp`, `.bak`, `.log`, and `~*` extensions to test temporary candidate analysis.
- **Empty Folders**: Empty directory trees to verify empty-folder detection without false positives on inaccessible paths.

## Generating Sample Data
Run the included generator script:
```powershell
python scripts/create_sample_data.py
```
Or use the built-in "Generate Sample Test Files" action inside FileGuard Settings page.
