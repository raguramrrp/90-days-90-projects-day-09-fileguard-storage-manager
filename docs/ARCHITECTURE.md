# FileGuard — Architecture & System Design

FileGuard is built on a clean layered desktop architecture separating core filesystem operations, cryptographic engines, and persistence layers from the Tkinter/ttk user interface.

---

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    UI["Desktop UI Layer (Tkinter & ttk)\nTheme Engine | Paned Explorer | Navigation | Previews"]
    
    subgraph CoreEngine ["Core Engine & Business Logic"]
        Scanner["Filesystem Scanner\nos.walk & Reparse Safeguards"]
        HashEngine["Hash Engine\nChunked SHA-256 (64 KB)"]
        DupDetector["Duplicate Detector\nSize -> Quick Hash -> SHA-256"]
        Advisor["Selection Advisor\nRule-based Copy Recommendation"]
        StorageAnalyzer["Storage Analyzer\nNon-Double Counting Folder Tree"]
        PerceptualEngine["Perceptual Hash Engine\nImage dHash & Hamming Distance"]
    end

    subgraph SafetyLayer ["Disaster Recovery & Safety Layer"]
        CleanupMgr["Cleanup Manager\nRetained-Copy & Protection Checks"]
        QuarantineMgr["Quarantine Manager\nCollision-Safe Storage & Verification"]
        RestoreMgr["Restore Manager\nConflict Resolution & 1-Click Undo"]
        ExclusionMgr["Exclusion Manager\nSystem Paths, Patterns, Size Rules"]
    end

    subgraph Persistence ["Persistence & Audit (SQLite WAL)"]
        DB[("SQLite Database (fileguard.db)\nFiles | Duplicates | Quarantine | Scans | Audits")]
    end

    UI --> Scanner
    UI --> DupDetector
    UI --> CleanupMgr
    UI --> QuarantineMgr
    UI --> RestoreMgr
    UI --> StorageAnalyzer
    UI --> PerceptualEngine
    
    Scanner --> ExclusionMgr
    Scanner --> HashEngine
    Scanner --> DB
    
    DupDetector --> HashEngine
    DupDetector --> Advisor
    DupDetector --> DB
    
    CleanupMgr --> ExclusionMgr
    CleanupMgr --> QuarantineMgr
    
    QuarantineMgr --> DB
    RestoreMgr --> DB
```

---

## 2. Multi-Stage Exact Duplicate Detection Algorithm

Calculating full SHA-256 fingerprints on every file in a 100 GB drive would bottleneck disk I/O. FileGuard employs a 4-stage deterministic funnel:

```text
[All Discovered Files]
       │
       ▼ (Stage 1: Size Clustering)
Group files by exact size in bytes.
Discard all size buckets with count < 2 (unique sizes cannot be duplicates).
       │
       ▼ (Stage 2: Partial Quick Hash for files >= 32 KB)
Read only first 4 KB chunk and compute partial SHA-256.
Group by (size, partial_hash). Discard buckets with count < 2.
       │
       ▼ (Stage 3: Full Chunked SHA-256 Hashing)
For candidate collisions, read entire file in 64 KB memory-safe chunks.
Compute standard 256-bit cryptographic digest. Re-verify st_size and st_mtime.
       │
       ▼ (Stage 4: Verification & Savings Calculation)
Group by (size, sha256). Form DuplicateGroups where file_count >= 2.
Theoretical Recoverable Space = (N - 1) * S
Pass group to SelectionAdvisor to suggest canonical retained copy.
```

---

## 3. Database Entity-Relationship Schema

FileGuard utilizes SQLite in WAL (Write-Ahead Logging) mode with foreign keys enabled:

```mermaid
erDiagram
    SCANS ||--o{ FILES : contains
    SCANS ||--o{ DUPLICATE_GROUPS : generates
    DUPLICATE_GROUPS ||--o{ DUPLICATE_GROUP_MEMBERS : associates
    FILES ||--o{ DUPLICATE_GROUP_MEMBERS : references
    CLEANUP_OPERATIONS ||--o{ QUARANTINE_ITEMS : tracks
    SCANS ||--o{ SCAN_ERRORS : logs
    
    SCANS {
        int id PK
        string scan_name
        text root_paths
        string started_at
        string completed_at
        string status
        int files_processed
        int duplicate_groups_count
        int potential_recoverable_bytes
    }
    
    FILES {
        int id PK
        int scan_id FK
        string path
        string filename
        int size_bytes
        string category
        string sha256_hash
        string hash_status
    }
    
    DUPLICATE_GROUPS {
        int id PK
        int scan_id FK
        string sha256_hash
        int size_bytes
        int file_count
        int max_recoverable_bytes
    }
    
    QUARANTINE_ITEMS {
        int id PK
        int operation_id FK
        string original_path
        string quarantine_path
        string filename
        int size_bytes
        string sha256_hash
        string status
        string quarantined_at
        string restored_at
    }
```
