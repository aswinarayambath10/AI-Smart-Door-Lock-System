"""
Access Logger — Door Lock Edition
Logs GRANTED / DENIED access events to CSV
"""

import os
import csv
import pandas as pd
from datetime import datetime


LOG_FILE = "data/logs/detections.csv"
LOG_FIELDS = ["timestamp", "name", "status", "confidence"]


def _ensure_log():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=LOG_FIELDS).writeheader()


def log_detection(name: str, status: str, confidence: str, timestamp: str = None):
    """Log a door access event. Status should be GRANTED or DENIED."""
    _ensure_log()
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=LOG_FIELDS).writerow({
            "timestamp": timestamp,
            "name": name,
            "status": status,
            "confidence": confidence,
        })


def get_logs_df() -> pd.DataFrame:
    _ensure_log()
    try:
        return pd.read_csv(LOG_FILE)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=LOG_FIELDS)


def clear_logs():
    _ensure_log()
    with open(LOG_FILE, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=LOG_FIELDS).writeheader()
