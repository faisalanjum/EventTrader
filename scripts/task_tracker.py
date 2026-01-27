#!/usr/bin/env python3
"""
Task Tracker - Persistent task state across sessions

Usage:
    from scripts.task_tracker import TaskTracker

    tracker = TaskTracker()

    # Check status
    status = tracker.get_status("AAPL", "Q1-2024", "0000320193-24-000001")

    # Update status
    tracker.update_status("AAPL", "Q1-2024", "0000320193-24-000001", "prediction", "completed")

    # Get all pending for a ticker
    pending = tracker.get_pending("AAPL")
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Default tracker file location
DEFAULT_TRACKER_PATH = Path(__file__).parent.parent / "earnings-analysis" / "task-tracker.csv"

TASK_COLUMNS = ["news_impact", "guidance", "prediction", "attribution"]
ALL_COLUMNS = ["ticker", "quarter", "accession"] + TASK_COLUMNS + ["last_updated"]


class TaskTracker:
    def __init__(self, tracker_path: Optional[Path] = None):
        self.tracker_path = tracker_path or DEFAULT_TRACKER_PATH
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create tracker file with headers if it doesn't exist"""
        if not self.tracker_path.exists():
            self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(ALL_COLUMNS)

    def _read_all(self) -> List[Dict]:
        """Read all rows from tracker"""
        rows = []
        with open(self.tracker_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def _write_all(self, rows: List[Dict]):
        """Write all rows to tracker"""
        with open(self.tracker_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def get_status(self, ticker: str, quarter: str, accession: str) -> Optional[Dict]:
        """Get status for a specific ticker/quarter/accession"""
        rows = self._read_all()
        for row in rows:
            if row["ticker"] == ticker and row["quarter"] == quarter and row["accession"] == accession:
                return row
        return None

    def get_or_create(self, ticker: str, quarter: str, accession: str) -> Dict:
        """Get existing row or create new one with pending status"""
        existing = self.get_status(ticker, quarter, accession)
        if existing:
            return existing

        # Create new row
        new_row = {
            "ticker": ticker,
            "quarter": quarter,
            "accession": accession,
            "news_impact": "pending",
            "guidance": "pending",
            "prediction": "pending",
            "attribution": "pending",
            "last_updated": datetime.now().isoformat()
        }

        rows = self._read_all()
        rows.append(new_row)
        self._write_all(rows)

        return new_row

    def update_status(self, ticker: str, quarter: str, accession: str,
                      task_name: str, status: str) -> bool:
        """
        Update status for a specific task

        Args:
            ticker: Company ticker (e.g., "AAPL")
            quarter: Quarter identifier (e.g., "Q1-2024")
            accession: SEC accession number
            task_name: One of: news_impact, guidance, prediction, attribution
            status: One of: pending, in_progress, completed

        Returns:
            True if updated, False if row not found
        """
        if task_name not in TASK_COLUMNS:
            raise ValueError(f"Invalid task_name: {task_name}. Must be one of {TASK_COLUMNS}")

        rows = self._read_all()
        updated = False

        for row in rows:
            if row["ticker"] == ticker and row["quarter"] == quarter and row["accession"] == accession:
                row[task_name] = status
                row["last_updated"] = datetime.now().isoformat()
                updated = True
                break

        if updated:
            self._write_all(rows)

        return updated

    def get_pending_tasks(self, ticker: str, quarter: str, accession: str) -> List[str]:
        """Get list of pending task names for a specific row"""
        status = self.get_status(ticker, quarter, accession)
        if not status:
            return TASK_COLUMNS.copy()  # All pending if row doesn't exist

        pending = []
        for task in TASK_COLUMNS:
            if status.get(task) != "completed":
                pending.append(task)
        return pending

    def get_all_pending(self, ticker: Optional[str] = None) -> List[Dict]:
        """Get all rows with at least one pending task"""
        rows = self._read_all()
        pending_rows = []

        for row in rows:
            if ticker and row["ticker"] != ticker:
                continue

            has_pending = any(row.get(task) != "completed" for task in TASK_COLUMNS)
            if has_pending:
                pending_rows.append(row)

        return pending_rows

    def is_complete(self, ticker: str, quarter: str, accession: str) -> bool:
        """Check if all tasks are completed for a row"""
        status = self.get_status(ticker, quarter, accession)
        if not status:
            return False

        return all(status.get(task) == "completed" for task in TASK_COLUMNS)

    def get_next_task(self, ticker: str, quarter: str, accession: str) -> Optional[str]:
        """
        Get next task to execute based on dependencies.

        Dependencies:
        - news_impact: no deps
        - guidance: no deps
        - prediction: requires news_impact AND guidance
        - attribution: requires prediction
        """
        status = self.get_or_create(ticker, quarter, accession)

        # Check news_impact
        if status["news_impact"] != "completed":
            return "news_impact"

        # Check guidance
        if status["guidance"] != "completed":
            return "guidance"

        # Check prediction (requires news_impact and guidance)
        if status["prediction"] != "completed":
            if status["news_impact"] == "completed" and status["guidance"] == "completed":
                return "prediction"
            return None  # Blocked

        # Check attribution (requires prediction)
        if status["attribution"] != "completed":
            if status["prediction"] == "completed":
                return "attribution"
            return None  # Blocked

        return None  # All complete

    def get_parallel_tasks(self, ticker: str, quarter: str, accession: str) -> List[str]:
        """
        Get tasks that can run in parallel (no blockers).

        Returns list of task names that are pending and unblocked.
        """
        status = self.get_or_create(ticker, quarter, accession)
        parallel = []

        # Wave 1: news_impact and guidance (no deps)
        if status["news_impact"] != "completed":
            parallel.append("news_impact")
        if status["guidance"] != "completed":
            parallel.append("guidance")

        # If Wave 1 has pending tasks, return those
        if parallel:
            return parallel

        # Wave 2: prediction (requires Wave 1)
        if status["prediction"] != "completed":
            return ["prediction"]

        # Wave 3: attribution (requires Wave 2)
        if status["attribution"] != "completed":
            return ["attribution"]

        return []  # All complete


def print_status(tracker_path: Optional[str] = None):
    """Print current tracker status"""
    tracker = TaskTracker(Path(tracker_path) if tracker_path else None)
    rows = tracker._read_all()

    if not rows:
        print("No tasks tracked yet.")
        return

    print(f"\n{'='*80}")
    print("Task Tracker Status")
    print(f"{'='*80}")

    for row in rows:
        ticker = row["ticker"]
        quarter = row["quarter"]
        accession = row["accession"]

        print(f"\n{ticker} {quarter} ({accession}):")
        for task in TASK_COLUMNS:
            status = row.get(task, "pending")
            icon = "✅" if status == "completed" else ("🔄" if status == "in_progress" else "⏳")
            print(f"  {icon} {task}: {status}")
        print(f"  Last updated: {row.get('last_updated', 'N/A')}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print_status(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print("Usage:")
        print("  python task_tracker.py status [tracker_path]")
        print("")
        print("Or import and use programmatically:")
        print("  from scripts.task_tracker import TaskTracker")
        print("  tracker = TaskTracker()")
        print("  tracker.get_or_create('AAPL', 'Q1-2024', '0000320193-24-000001')")
