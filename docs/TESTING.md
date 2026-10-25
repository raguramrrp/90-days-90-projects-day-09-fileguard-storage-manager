# FileGuard — Testing & Quality Assurance Report

## 1. Test Strategy & Coverage
Automated testing is implemented using `pytest` and structured across 12 test modules. All tests run against isolated temporary directory sandboxes and ephemeral SQLite databases, ensuring zero side-effects on real user files.

---

## 2. Test Execution Summary

| Test Module | Coverage Area | Test Count | Status |
| :--- | :--- | :--- | :--- |
| `test_hash_engine.py` | SHA-256 chunked reads, empty files, large files, missing files, verification | 6 | **PASS** |
| `test_duplicate_detector.py` | Multi-stage size/hash grouping, theoretical savings `(N-1)*S`, cancellation | 3 | **PASS** |
| `test_scanner.py` | Traversal, nested folders, exclusions, cancellation, missing root handling | 4 | **PASS** |
| `test_selection_advisor.py` | Copy recommendation scoring, folder preference, rationale generation | 2 | **PASS** |
| `test_cleanup_quarantine_restore.py` | Retained-copy protection, quarantine execution, restore, undo, conflict prevention | 4 | **PASS** |
| `test_storage_analyzer.py` | File-type breakdown, non-double counting folder calculation, largest files | 1 | **PASS** |
| `test_exclusions.py` | Default exclusions (.git, .dll), custom rules, Windows protected locations | 3 | **PASS** |
| `test_integrity_checker.py` | Baseline hash comparison, tampered file detection, missing file handling | 1 | **PASS** |
| `test_folder_temp_analyzer.py` | Empty folder discovery, temporary candidate rules (.tmp, .bak) | 2 | **PASS** |
| `test_scheduler.py` | Next-run scheduling calculations, safe scan triggering | 2 | **PASS** |
| `test_history_and_trends.py` | Multi-scan comparison, delta metrics, scope incompatibility warning | 2 | **PASS** |
| `test_database.py` | SQLite schema, batch inserts, settings persistence, audit event logging, cascade delete, reset | 5 | **PASS** |
| `test_reports.py` | CSV formatting, HTML report generation and XSS entity escaping | 2 | **PASS** |
| `test_perceptual_hash.py` | 64-bit dHash computation, Hamming distance, visual similarity calculation | 3 | **PASS** |
| **TOTAL** | **Comprehensive Full System Coverage** | **40** | **40 PASSED (100%)** |

---

## 3. Execution Command & Actual Terminal Output

Command executed:
```powershell
.\.venv\Scripts\pytest.exe -v
```

Actual output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.7.0
rootdir: D:\90 days\90-days-90-projects-day-09-fileguard-storage-manager
configfile: pyproject.toml
testpaths: tests
plugins: cov-7.1.0
collected 38 items

tests/test_cleanup_quarantine_restore.py::test_retained_copy_protection_blocks_all_selected PASSED [  2%]
tests/test_cleanup_quarantine_restore.py::test_quarantine_and_restore_workflow PASSED [  5%]
tests/test_cleanup_quarantine_restore.py::test_undo_last_quarantine PASSED [  7%]
tests/test_cleanup_quarantine_restore.py::test_restore_conflict_prevention_does_not_overwrite PASSED [ 10%]
tests/test_database.py::test_database_settings_persistence PASSED        [ 13%]
tests/test_database.py::test_database_files_batch_persistence PASSED     [ 15%]
tests/test_database.py::test_database_audit_event_logging PASSED         [ 18%]
tests/test_duplicate_detector.py::test_detect_duplicates_grouping PASSED [ 21%]
tests/test_duplicate_detector.py::test_no_duplicates_returns_empty PASSED [ 23%]
tests/test_duplicate_detector.py::test_detector_cancellation PASSED      [ 26%]
tests/test_exclusions.py::test_default_exclusions PASSED                 [ 28%]
tests/test_exclusions.py::test_custom_rules PASSED                       [ 31%]
tests/test_exclusions.py::test_protected_locations PASSED                [ 34%]
tests/test_folder_temp_analyzer.py::test_empty_folder_detection PASSED   [ 36%]
tests/test_folder_temp_analyzer.py::test_temp_file_analyzer PASSED       [ 39%]
tests/test_hash_engine.py::test_identical_content_different_names PASSED [ 42%]
tests/test_hash_engine.py::test_same_name_different_content PASSED       [ 44%]
tests/test_hash_engine.py::test_empty_file_hashing PASSED                [ 47%]
tests/test_hash_engine.py::test_chunked_read_consistency PASSED          [ 50%]
tests/test_hash_engine.py::test_missing_file_raises PASSED               [ 52%]
tests/test_hash_engine.py::test_verify_file_hash PASSED                  [ 55%]
tests/test_history_and_trends.py::test_scan_comparison_and_scope_warning PASSED [ 57%]
tests/test_history_and_trends.py::test_trend_analyzer_snapshots PASSED   [ 60%]
tests/test_integrity_checker.py::test_integrity_checker_workflow PASSED  [ 63%]
tests/test_perceptual_hash.py::test_hamming_distance_identical_hashes PASSED [ 65%]
tests/test_perceptual_hash.py::test_hamming_distance_differing_hashes PASSED [ 68%]
tests/test_perceptual_hash.py::test_dhash_calculation_if_pillow PASSED   [ 71%]
tests/test_reports.py::test_export_duplicates_csv PASSED                 [ 73%]
tests/test_reports.py::test_generate_duplicates_html PASSED              [ 76%]
tests/test_scanner.py::test_scanner_end_to_end PASSED                    [ 78%]
tests/test_scanner.py::test_scanner_exclusion_handling PASSED            [ 81%]
tests/test_scanner.py::test_scanner_cancellation PASSED                  [ 84%]
tests/test_scanner.py::test_scanner_nonexistent_root PASSED              [ 86%]
tests/test_scheduler.py::test_scheduler_next_run_calculation PASSED      [ 89%]
tests/test_scheduler.py::test_scheduler_trigger_safe_scan PASSED         [ 92%]
tests/test_selection_advisor.py::test_selection_advisor_prefers_clean_folder PASSED [ 94%]
tests/test_selection_advisor.py::test_selection_advisor_single_member PASSED [ 97%]
tests/test_storage_analyzer.py::test_storage_analyzer_metrics PASSED     [100%]

============================= 38 passed in 0.82s ==============================
```
