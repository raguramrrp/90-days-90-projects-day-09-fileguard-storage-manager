# FileGuard — 90-Second Demonstration Script

Follow this structured demonstration script to showcase all essential workflows, safety guarantees, and advanced features during portfolio reviews, hackathons, or recruiter presentations.

---

## 🎬 Demo Overview (60–120 Seconds)

| Time | Step | Screen / Action | Talking Points |
| :--- | :--- | :--- | :--- |
| **00:00–00:15** | **1. Launch & Overview** | Double-click `run.bat` or run `python app.py` | "FileGuard is an intelligent offline Windows storage manager built with Tkinter, SQLite, and chunked SHA-256 hashing. The Overview dashboard displays database-backed metrics, recent scans, and real recoverable space." |
| **00:15–00:30** | **2. Smart Scope & Scan** | Navigate to **📁 Scan Files** ➔ Click *Add Sample Data Folder* ➔ *Start Full Deduplication Scan* | "The scanner runs in a background thread to keep the UI completely responsive. It applies smart exclusions, filters unique file sizes first, and uses chunked memory-safe reads to calculate exact SHA-256 fingerprints." |
| **00:30–00:45** | **3. Duplicate Review & Advisor** | Auto-navigates to **📑 Duplicate Review** | "Exact duplicates are grouped by verified content. Notice the **Selection Advisor**: it recommends retaining copies in organized folders while marking redundant copies in Downloads or Temp as quarantine candidates, with clear human-readable explanations." |
| **00:45–01:05** | **4. Safety Preview & Quarantine** | Click *Select Suggested Copies* ➔ *Move Selected to Quarantine...* | "**Safety Guarantee #1**: FileGuard blocks any operation if all copies in a group are selected. The Cleanup Preview modal verifies file existence and shows the exact retained copy before any disk action. Once confirmed, files are safely isolated in reversible quarantine." |
| **01:05–01:15** | **5. Storage Intelligence & Large Files** | Navigate to **📈 Storage Analysis** & **📦 Large Files** | "Accurate folder-size aggregation calculates true storage without nested double-counting. Large files can be sorted, filtered, and revealed in native Windows File Explorer with one click." |
| **01:15–01:25** | **6. Recovery & Undo** | Navigate to **🛡️ Quarantine & Recovery** ➔ Press `Ctrl+Z` | "**Safety Guarantee #2**: Every quarantine action is 100% reversible. Pressing `Ctrl+Z` or clicking *Undo* restores all files with hash verification and collision safeguards. Permanent deletion is separated and never triggered automatically." |
| **01:25–01:35** | **7. Similar Photos & Reports** | Navigate to **🖼️ Similar Photos** ➔ Click *Analyze Images* ➔ Navigate to **📄 Reports** ➔ *Generate HTML Report* | "Near-duplicate images are identified using perceptual difference hashing (dHash) and Hamming distance, kept strictly separate from exact duplicates. Finally, standalone responsive HTML and CSV reports can be exported for auditing." |

---

## 🛠️ Step-by-Step Execution Checklist

1. **Verify Sample Test Files Exist:**
   ```powershell
   python scripts/create_sample_data.py
   ```
2. **Launch Application:**
   ```powershell
   python app.py
   ```
3. **Run Automated Tests:**
   ```powershell
   .\test.bat
   ```
