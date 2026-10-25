"""
Report Generator for FileGuard.
Generates CSV and standalone responsive HTML reports with safe escaping,
KPI metrics, and complete audit details.
"""
import csv
import html
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fileguard.config import REPORTS_DIR
from fileguard.models import DuplicateGroup, FileRecord, ScanRecord, QuarantineItem, format_bytes
from fileguard.database import Database


class ReportGenerator:
    def __init__(self, db: Optional[Database] = None, output_dir: Optional[Path] = None):
        self.db = db or Database()
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ----------------- CSV EXPORTS -----------------
    def export_duplicates_csv(self, groups: List[DuplicateGroup], filepath: Optional[str] = None) -> str:
        """Export duplicate groups and all members to CSV."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"duplicate_groups_{timestamp}.csv")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Group ID", "SHA-256 Hash", "File Size (Bytes)", "Formatted Size",
                "Total Copies", "Max Recoverable (Bytes)", "Formatted Recoverable",
                "File Path", "File Name", "Extension", "Category", "Role", "Reason"
            ])

            for g in groups:
                for m in g.members:
                    is_retained = (g.suggested_retained_file_id == m.id)
                    role = "Retain" if is_retained else "Candidate"
                    reason = g.suggestion_reasons.get(m.id, "")
                    writer.writerow([
                        g.id, g.sha256_hash, g.size_bytes, g.formatted_copy_size,
                        g.file_count, g.max_recoverable_bytes, g.formatted_max_recoverable,
                        m.path, m.filename, m.extension, m.category, role, reason
                    ])

        return filepath

    def export_large_files_csv(self, files: List[FileRecord], filepath: Optional[str] = None) -> str:
        """Export large files list to CSV."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"large_files_{timestamp}.csv")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "File Name", "Size (Bytes)", "Formatted Size", "Category", "Modified Date", "Full Path"])
            for fl in files:
                writer.writerow([
                    fl.id, fl.filename, fl.size_bytes, fl.formatted_size,
                    fl.category, fl.formatted_modified, fl.path
                ])

        return filepath

    def export_quarantine_audit_csv(self, items: List[QuarantineItem], filepath: Optional[str] = None) -> str:
        """Export quarantine and recovery history to CSV."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"quarantine_audit_{timestamp}.csv")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Operation ID", "File Name", "Size (Bytes)", "Formatted Size",
                "SHA-256 Hash", "Quarantined At", "Status", "Original Path", "Restored Path"
            ])
            for it in items:
                writer.writerow([
                    it.id, it.operation_id, it.filename, it.size_bytes, it.formatted_size,
                    it.sha256_hash, it.quarantined_at, it.status, it.original_path, it.restored_path or ""
                ])

        return filepath

    # ----------------- HTML REPORTS -----------------
    def generate_duplicates_html(self, groups: List[DuplicateGroup], scan: Optional[ScanRecord] = None, filepath: Optional[str] = None) -> str:
        """Generate a complete standalone HTML report for duplicate detection."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"fileguard_duplicate_report_{timestamp}.html")

        total_groups = len(groups)
        total_duplicate_files = sum(g.file_count for g in groups)
        total_max_recoverable = sum(g.max_recoverable_bytes for g in groups)

        scan_info = f"Scan ID: {scan.id} &bull; Scope: {', '.join(scan.root_paths)}" if scan else "All Verified Records"

        rows_html = []
        for g in groups:
            escaped_hash = html.escape(g.sha256_hash[:16]) + "..."
            rows_html.append(f"""
            <tr class="group-header">
                <td colspan="5">
                    <strong>Group #{g.id}</strong> &mdash; Hash: <code>{escaped_hash}</code> |
                    Copies: <strong>{g.file_count}</strong> |
                    Size each: <strong>{g.formatted_copy_size}</strong> |
                    Theoretical Max Savings: <span class="badge-recoverable">{g.formatted_max_recoverable}</span>
                </td>
            </tr>
            """)
            for m in g.members:
                is_retained = (g.suggested_retained_file_id == m.id)
                role_badge = '<span class="badge-retain">Retain</span>' if is_retained else '<span class="badge-candidate">Quarantine Candidate</span>'
                reason = html.escape(g.suggestion_reasons.get(m.id, "Duplicate copy"))
                path_esc = html.escape(m.path)
                fname_esc = html.escape(m.filename)

                rows_html.append(f"""
                <tr class="member-row">
                    <td>{role_badge}</td>
                    <td><strong>{fname_esc}</strong></td>
                    <td><code>{path_esc}</code></td>
                    <td>{m.formatted_size}</td>
                    <td><small>{reason}</small></td>
                </tr>
                """)

        table_body = "\n".join(rows_html)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FileGuard - Duplicate Files Report</title>
    <style>
        :root {{
            --primary: #0f172a;
            --accent: #0d9488;
            --accent-light: #14b8a6;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --muted: #64748b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 30px;
            line-height: 1.5;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 25px;
        }}
        .brand {{
            font-size: 26px;
            font-weight: 800;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .meta {{
            color: var(--muted);
            font-size: 14px;
            margin-top: 5px;
        }}
        .kpi-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .kpi-title {{
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--muted);
            letter-spacing: 0.5px;
        }}
        .kpi-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--primary);
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        th {{
            background: #f1f5f9;
            text-align: left;
            padding: 12px 15px;
            font-size: 13px;
            font-weight: 600;
            color: var(--muted);
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 10px 15px;
            font-size: 14px;
            border-bottom: 1px solid var(--border);
        }}
        tr.group-header {{
            background-color: #f8fafc;
            font-size: 13px;
            border-top: 2px solid #cbd5e1;
        }}
        tr.member-row:hover {{
            background-color: #f8fafc;
        }}
        .badge-retain {{
            background: #dcfce7;
            color: #166534;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-candidate {{
            background: #fef3c7;
            color: #92400e;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-recoverable {{
            background: #ccfbf1;
            color: #0f766e;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
        }}
        code {{
            font-family: Consolas, Monaco, monospace;
            background: #f1f5f9;
            padding: 2px 5px;
            border-radius: 4px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">FileGuard Storage Intelligence</div>
        <div class="meta">Duplicate Detection Audit Report &bull; Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} &bull; {scan_info}</div>
    </div>

    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Duplicate Groups</div>
            <div class="kpi-value">{total_groups}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Duplicate Files</div>
            <div class="kpi-value">{total_duplicate_files}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Max Recoverable Space</div>
            <div class="kpi-value">{format_bytes(total_max_recoverable)}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 130px;">Action Suggestion</th>
                <th style="width: 220px;">File Name</th>
                <th>Full Path</th>
                <th style="width: 100px;">Size</th>
                <th>Reasoning</th>
            </tr>
        </thead>
        <tbody>
            {table_body}
        </tbody>
    </table>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return filepath
