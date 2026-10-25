"""
Duplicate Detector for FileGuard.
Implements the multi-stage exact duplicate detection algorithm:
1. Size clustering
2. Partial hash pruning
3. Memory-safe chunked SHA-256 verification
4. Theoretical recoverable space calculation: (N - 1) * S
5. Recommendation integration via SelectionAdvisor
"""
from collections import defaultdict
from typing import List, Dict, Optional, Callable
from pathlib import Path

from fileguard.models import FileRecord, DuplicateGroup
from fileguard.hash_engine import compute_sha256, compute_quick_hash, HashEngineError
from fileguard.selection_advisor import SelectionAdvisor


class DuplicateDetector:
    def __init__(self, advisor: Optional[SelectionAdvisor] = None):
        self.advisor = advisor or SelectionAdvisor()

    def detect_duplicates(
        self,
        files: List[FileRecord],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> List[DuplicateGroup]:
        """
        Group files by exact SHA-256 fingerprint after size and partial hash filtering.
        """
        if cancel_check and cancel_check():
            return []

        # Stage 1: Group by size
        if progress_callback:
            progress_callback("Grouping candidates by file size...", 0, len(files))

        size_groups: Dict[int, List[FileRecord]] = defaultdict(list)
        for f in files:
            # Files of 0 bytes can also be duplicate empty files, but only if count >= 2
            size_groups[f.size_bytes].append(f)

        # Retain only sizes with 2 or more files
        candidate_sizes = {sz: file_list for sz, file_list in size_groups.items() if len(file_list) >= 2}
        total_candidates = sum(len(fl) for fl in candidate_sizes.values())

        if total_candidates == 0:
            return []

        # Stage 2: Quick Hash Pre-filter for files >= 32 KB
        quick_hash_groups: Dict[str, List[FileRecord]] = defaultdict(list)
        processed_candidates = 0

        for sz, file_list in candidate_sizes.items():
            if cancel_check and cancel_check():
                return []

            if sz >= 32768:  # 32 KB
                for f in file_list:
                    if cancel_check and cancel_check():
                        return []
                    qhash = compute_quick_hash(f.path)
                    if qhash:
                        key = f"{sz}_{qhash}"
                        quick_hash_groups[key].append(f)
                    else:
                        f.hash_status = "failed"
            else:
                for f in file_list:
                    key = f"{sz}_small"
                    quick_hash_groups[key].append(f)

            processed_candidates += len(file_list)
            if progress_callback:
                progress_callback("Running quick pre-filter...", processed_candidates, total_candidates)

        # Stage 3: Full SHA-256 calculation for collisions
        hash_candidates = {k: fl for k, fl in quick_hash_groups.items() if len(fl) >= 2}
        total_to_hash = sum(len(fl) for fl in hash_candidates.values())
        hashed_count = 0

        full_hash_groups: Dict[str, List[FileRecord]] = defaultdict(list)

        for key, file_list in hash_candidates.items():
            for f in file_list:
                if cancel_check and cancel_check():
                    return []

                if not f.sha256_hash or f.hash_status != "verified":
                    try:
                        digest, _ = compute_sha256(f.path, cancel_check=cancel_check)
                        f.sha256_hash = digest
                        f.hash_status = "verified"
                    except HashEngineError:
                        f.hash_status = "failed"
                        continue
                    except InterruptedError:
                        return []

                hashed_count += 1
                if progress_callback:
                    progress_callback(f"Computing SHA-256: {f.filename}", hashed_count, total_to_hash)

                if f.sha256_hash:
                    # Final exact collision key: (size, sha256)
                    group_key = f"{f.size_bytes}_{f.sha256_hash}"
                    full_hash_groups[group_key].append(f)

        # Stage 4: Build DuplicateGroup objects
        duplicate_groups: List[DuplicateGroup] = []
        for group_key, members in full_hash_groups.items():
            if len(members) >= 2:
                sample = members[0]
                size_one = sample.size_bytes
                count = len(members)
                total_sz = size_one * count
                max_rec = (count - 1) * size_one  # (N - 1) * S

                group = DuplicateGroup(
                    group_key=group_key,
                    sha256_hash=sample.sha256_hash,
                    size_bytes=size_one,
                    file_count=count,
                    total_size_bytes=total_sz,
                    max_recoverable_bytes=max_rec,
                    members=members
                )

                # Advise retention
                retained_id, reasons = self.advisor.advise_group(group)
                group.suggested_retained_file_id = retained_id
                group.suggestion_reasons = reasons

                duplicate_groups.append(group)

        # Sort groups by recoverable space descending
        duplicate_groups.sort(key=lambda g: g.max_recoverable_bytes, reverse=True)
        return duplicate_groups
