"""
Face Database Utility
Handles registration, storage, and loading of known face encodings
"""

import os
import json
import numpy as np
import face_recognition
from PIL import Image
from datetime import datetime
import io


KNOWN_FACES_DIR = "data/known_faces"
REGISTRY_FILE = "data/known_faces/registry.json"


def _ensure_dirs():
    os.makedirs(KNOWN_FACES_DIR, exist_ok=True)


def _load_registry() -> list:
    if not os.path.exists(REGISTRY_FILE):
        return []
    with open(REGISTRY_FILE, "r") as f:
        return json.load(f)


def _save_registry(registry: list):
    _ensure_dirs()
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def register_face(name: str, role: str, department: str, image: Image.Image):
    """
    Register a new face encoding.
    Returns: (success: bool, message: str)
    """
    _ensure_dirs()
    try:
        # Convert PIL image to numpy array
        img_array = np.array(image.convert("RGB"))

        # Detect face locations
        face_locations = face_recognition.face_locations(img_array)
        if not face_locations:
            return False, "No face detected in the image. Please use a clear, front-facing photo."

        if len(face_locations) > 1:
            return False, f"Multiple faces detected ({len(face_locations)}). Please use a photo with a single person."

        # Get face encoding
        encodings = face_recognition.face_encodings(img_array, face_locations)
        if not encodings:
            return False, "Failed to extract face encoding. Try a higher-resolution photo."

        encoding = encodings[0]

        # Save image
        safe_name = name.replace(" ", "_").lower()
        img_filename = f"{safe_name}_{int(datetime.now().timestamp())}.jpg"
        img_path = os.path.join(KNOWN_FACES_DIR, img_filename)
        image.save(img_path)

        # Save encoding as .npy
        enc_filename = img_filename.replace(".jpg", ".npy")
        enc_path = os.path.join(KNOWN_FACES_DIR, enc_filename)
        np.save(enc_path, encoding)

        # Update registry
        registry = _load_registry()
        # Remove existing entry if same name
        registry = [r for r in registry if r["name"].lower() != name.lower()]
        registry.append({
            "name": name,
            "role": role,
            "department": department,
            "filename": img_filename,
            "encoding_file": enc_filename,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _save_registry(registry)

        return True, f"'{name}' registered successfully!"

    except Exception as e:
        return False, f"Registration failed: {str(e)}"


def load_known_encodings():
    """
    Load all known face encodings and their names.
    Returns: (encodings_list, names_list)
    """
    _ensure_dirs()
    registry = _load_registry()
    encodings = []
    names = []

    for entry in registry:
        enc_path = os.path.join(KNOWN_FACES_DIR, entry["encoding_file"])
        if os.path.exists(enc_path):
            enc = np.load(enc_path)
            encodings.append(enc)
            names.append(entry["name"])

    return encodings, names


def get_registered_faces() -> list:
    """Return list of all registered face records."""
    return _load_registry()


def delete_face(name: str):
    """Delete a registered face by name."""
    registry = _load_registry()
    to_delete = [r for r in registry if r["name"].lower() == name.lower()]
    for entry in to_delete:
        # Remove files
        for key in ["filename", "encoding_file"]:
            path = os.path.join(KNOWN_FACES_DIR, entry.get(key, ""))
            if path and os.path.exists(path):
                os.remove(path)
    registry = [r for r in registry if r["name"].lower() != name.lower()]
    _save_registry(registry)
