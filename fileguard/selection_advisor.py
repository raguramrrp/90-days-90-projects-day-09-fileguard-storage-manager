"""
Selection Advisor for FileGuard.
Provides transparent, deterministic recommendations on which duplicate copy to retain
and which copies to flag as candidate cleanup items, complete with human-readable reasoning.
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from fileguard.config import is_path_protected
from fileguard.models import FileRecord, DuplicateGroup
from fileguard.database import Database


class SelectionAdvisor:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self._load_preferred_folders()

    def _load_preferred_folders(self):
        raw = self.db.get_setting("preferred_keep_folders", "[]")
        try:
            self.preferred_folders = [p.lower() for p in json.loads(raw)]
        except Exception:
            self.preferred_folders = []

    def advise_group(self, group: DuplicateGroup) -> Tuple[Optional[int], Dict[int, str]]:
        """
        Evaluate all members of a duplicate group and recommend one copy to RETAIN.
        Returns:
            (suggested_retained_file_id, {file_id: explanation_reason})
        """
        if not group.members:
            return None, {}

        if len(group.members) == 1:
            m = group.members[0]
            return m.id, {m.id: "Single remaining copy; must be retained."}

        # Score each candidate copy. Higher score = higher priority to RETAIN.
        scores: Dict[int, float] = {}
        reasons: Dict[int, List[str]] = {}

        for member in group.members:
            score = 100.0
            member_reasons = []
            norm_path = os.path.abspath(member.path).lower()
            norm_parts = [p.lower() for p in Path(norm_path).parts]
            filename = member.filename.lower()

            # Rule 1: Protected System / Application location (+500 points)
            if is_path_protected(member.path):
                score += 500.0
                member_reasons.append("Inside protected system directory (high retain priority)")

            # Rule 2: User Preferred Keep Folders (+200 points)
            for pref in self.preferred_folders:
                if pref and (norm_path.startswith(pref) or pref in norm_path):
                    score += 200.0
                    member_reasons.append(f"Located in user-preferred folder: '{pref}'")
                    break

            # Rule 3: Avoid keeping copies in Downloads, Temp, Recycle, or Cache (-50 points)
            if any(folder in norm_parts for folder in ["downloads", "temp", "tmp", "caches", "cache", "recycle"]):
                score -= 50.0
                member_reasons.append("Located in temporary or downloads location")

            # Rule 4: Penalty for duplicate naming patterns like " (1)", " - Copy", "copy of" (-30 points)
            if re.search(r"(\s*[\(\[]\d+[\)\]]|\s*-\s*copy|\s*_copy|\bcopy\b)", filename):
                score -= 30.0
                member_reasons.append("Filename contains duplicate pattern (e.g. 'copy', '(1)')")

            # Rule 5: Shorter directory depth is usually cleaner and more primary (+10 points for cleaner path)
            depth = len(Path(norm_path).parts)
            score += max(0, 20 - depth)

            # Rule 6: Timestamps as subtle tie-breaker (prefer older creation date if original)
            if member.created_time:
                # Slight preference to original creation
                score += (1.0 / (member.created_time / 1000000000.0)) * 0.01

            scores[member.id] = score
            reasons[member.id] = member_reasons

        # Pick member with highest retain score
        sorted_members = sorted(group.members, key=lambda m: scores[m.id], reverse=True)
        retained = sorted_members[0]

        final_explanations: Dict[int, str] = {}
        for member in group.members:
            if member.id == retained.id:
                details = "; ".join(reasons[member.id]) if reasons[member.id] else "Primary structured path"
                final_explanations[member.id] = f"Recommended to RETAIN ({details})"
            else:
                details = "; ".join(reasons[member.id]) if reasons[member.id] else "Redundant duplicate copy"
                final_explanations[member.id] = f"Candidate for cleanup ({details})"

        return retained.id, final_explanations
