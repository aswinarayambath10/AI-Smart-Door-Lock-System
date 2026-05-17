"""
Setup Script — Smart Door Lock System
Creates folder structure and sample access log entries
Run: python setup_dataset.py
"""

import os
import json
from datetime import datetime, timedelta


def create_dataset_structure():
    dirs = ["data/known_faces", "data/logs"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✅ Created: {d}")

    registry_path = "data/known_faces/registry.json"
    if not os.path.exists(registry_path):
        with open(registry_path, "w") as f:
            json.dump([], f)
        print(f"✅ Created: {registry_path}")

    log_path = "data/logs/detections.csv"
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("timestamp,name,status,confidence\n")
            samples = [
                ("2025-01-15 09:00:00", "John Doe",      "GRANTED", "0.92"),
                ("2025-01-15 09:15:00", "Unknown Person", "DENIED",  "N/A"),
                ("2025-01-15 10:00:00", "Jane Smith",    "GRANTED", "0.89"),
                ("2025-01-15 11:30:00", "Unknown Person", "DENIED",  "N/A"),
                ("2025-01-15 13:00:00", "John Doe",      "GRANTED", "0.94"),
            ]
            for s in samples:
                f.write(",".join(s) + "\n")
        print(f"✅ Created sample access log: {log_path}")

    print("\n📁 Smart Door Lock System — ready!")
    print("\nNext steps:")
    print("  1. Run: streamlit run app.py")
    print("  2. Go to 👤 Face Registration — register the people who can access the door")
    print("  3. Go to 🚪 Door Lock Control — start the face scanner")
    print("  4. Registered faces → 🔓 DOOR OPENS | Unknown faces → 🔒 ACCESS DENIED")


if __name__ == "__main__":
    create_dataset_structure()
