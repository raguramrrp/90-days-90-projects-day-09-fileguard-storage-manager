# FileGuard — User Guide

Welcome to the comprehensive user manual for **FileGuard — Intelligent Duplicate File Detection & Storage Manager**.

---

## 1. Overview Dashboard
Upon launch, the Overview screen provides real, database-backed storage metrics:
- **Indexed Files:** Total file count and storage space registered in the latest scan.
- **Duplicate Groups:** Distinct groups of verified exact duplicates and total redundant copies.
- **Recoverable Space:** Potential savings if only one copy is retained per group: `(N - 1) * S`.
- **Reclaimed Space:** Total storage currently isolated in quarantine.
- **Recent Scans Table:** Quick history of past operations with timestamps and scopes.
- **Safety & Audit Trail:** Real-time log of security, scan, quarantine, and restoration events.

---

## 2. Scanning Files
1. Navigate to **📁 Scan Files**.
2. Click **➕ Add Folder...** to select one or more directories to inspect. (Or click **📁 Add Sample Data Folder** to test the bundled demo environment).
3. **Removing Folders from the Scan Scope:**
   - To remove a single folder from the scope list: Click the folder in the listbox and click **➖ Remove Selected**.
   - To clear all folders from the scope list: Click **✕ Clear All Folders**.
4. Click **🚀 Start Full Deduplication Scan**.
5. The live progress bar will show current stage (Discovery ➔ Quick Hash ➔ SHA-256 Hashing ➔ Finalizing).
6. You can cancel at any time using **⏹ Cancel Scan**; incomplete scans are safely recorded and do not pollute duplicate records.

---

## 2.1 Removing Completed Scans & Resetting Data
After you have finished reviewing duplicates and completing quarantine operations, you can easily remove the scanned data from FileGuard:
- **Remove a Specific Scanned Folder Record:**
  Navigate to **⏱️ Scan History**, select the completed scan in the table, and click **🗑️ Remove Scan Record**. This automatically purges that folder's indexed files, duplicate groups, and metrics from FileGuard's database (your actual physical files on disk remain completely untouched).
- **Purge All Past Scan History:**
  Navigate to **⚙️ Settings** ➔ Under *Developer & Demo Tools*, click **🗑️ Purge Scan History & Reset Index**. This resets the Overview and Duplicate Review tabs to a clean state.
- **Handling Quarantined Files:**
  If you quarantined redundant copies and now wish to clear them, navigate to **🛡️ Quarantine & Recovery** where you can either restore them or click **⚠️ Permanently Delete File**.

---

## 3. Duplicate Review & Selection Advisor
Once scanning completes, FileGuard automatically navigates to **📑 Duplicate Review**:
- **Group Hierarchy:** Groups are sorted by potential recoverable space descending.
- **Selection Advisor Suggestions:**
  - FileGuard analyzes directory depth, preferred folders, and filename naming patterns.
  - Copies in `Documents` are given high retention priority.
  - Redundant copies in `Downloads`, `Temp`, or containing duplicate indicators like `(1)` or `copy` are flagged as **Candidate for cleanup** with a clear explanation.
- **Bulk Selection Buttons:**
  - *Select Suggested Copies:* Automatically checks recommended candidates while protecting canonical copies.
  - *Select All (Retain 1):* Selects all redundant copies in every group while preserving the primary file.
  - *Clear Selection:* Unchecks all items.
- **Retained-Copy Protection:** If you accidentally check all copies in a group, FileGuard blocks cleanup during safety validation.

---

## 4. Reversible Quarantine Cleanup
1. In Duplicate Review, click **🛡️ Move Selected to Quarantine...**.
2. The **Safety Cleanup Preview** modal appears showing every file, its size, full path, and the verified retained copy that will stay on disk.
3. Click **Confirm & Move to Quarantine**.
4. The files are copied to isolated quarantine storage with UUID prefixes, their cryptographic hashes are verified on disk, and the original files are removed only after verified copy.

---

## 5. Quarantine Recovery & Undo
1. Navigate to **🛡️ Quarantine & Recovery**.
2. **Restore to Original Location:** Select an item and click *Restore to Original Location*. FileGuard copies the file back and verifies its hash. If a new file has since been created at that path, FileGuard prevents accidental overwriting by naming the restored file `_restored`.
3. **Restore to Alternate Folder:** Choose any custom destination folder.
4. **1-Click Undo (`Ctrl+Z`):** Click *Undo Last Quarantine* or press `Ctrl+Z` from anywhere in the app to immediately restore all items from the most recent cleanup operation.
5. **Permanent Deletion:** Exposed only as an advanced manual action inside the Quarantine tab with an irreversible-action confirmation prompt.

---

## 6. Large Files Finder
1. Navigate to **📦 Large Files**.
2. Filter files by threshold: `1 MB`, `5 MB`, `10 MB`, `25 MB`, `50 MB`, `100 MB`, `500 MB`.
3. Filter by category (Video, Archives, Documents, Images, etc.) or search by name.
4. Double-click or click **Reveal in Explorer** in the right preview pane to reveal the file highlighted in Windows File Explorer.

---

## 7. Storage Intelligence & Analysis
1. Navigate to **📈 Storage Analysis**.
2. View total indexed size versus real drive free space.
3. Review storage distribution across categories (Documents, Images, Video, Audio, Code).
4. Inspect the largest direct folders without nested double counting.

---

## 8. Empty Folders & Temporary Files
1. Navigate to **🧹 Empty & Temp Files**.
2. **Empty Folders Tab:** Identifies folders with zero files and zero subdirectories, while distinguishing genuinely empty directories from folders blocked by Windows permissions.
3. **Temporary Files Tab:** Analyzes `.tmp`, `.bak`, `.log`, and `~*` files with rule descriptions and age in days. Allows safe preview and quarantine.

---

## 9. File Cryptographic Integrity Checks
1. Navigate to **🔒 Integrity Checks**.
2. Click **Run Full Integrity Verification**.
3. FileGuard recalculates SHA-256 digests for all indexed files and compares against the database baseline.
4. Flags files as `Unchanged`, `Modified` (potential bit rot or edits), `Missing`, or `Inaccessible`.
5. Export results to CSV for compliance records.

---

## 10. Visual Similar Photos (dHash)
1. Navigate to **🖼️ Similar Photos**.
2. Select desired similarity threshold (75% to 95%).
3. Click **Analyze Images for Visual Similarity**.
4. FileGuard calculates 64-bit difference hashes and computes Hamming distances between photos.
5. Select a pair to view side-by-side thumbnail previews, resolutions, and similarity scores.

---

## 11. Reports & Compliance Export
1. Navigate to **📄 Reports & Export**.
2. Choose from:
   - *Duplicate Files HTML Audit Report* (standalone responsive HTML dashboard).
   - *Duplicate Groups CSV Dataset*.
   - *Large Files Inventory CSV*.
   - *Quarantine & Disaster Recovery Audit CSV*.
3. Click *Open Reports Folder* to view generated files in Windows File Explorer.
