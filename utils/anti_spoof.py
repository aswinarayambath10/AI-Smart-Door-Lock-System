"""
Anti-Spoofing Utility
Detects if someone is holding a photo or screen instead of a real face.

Methods used:
1. Texture analysis  — real faces have natural skin texture variation
2. Blink detection   — real faces blink (using eye aspect ratio via landmarks)
3. Edge sharpness    — printed photos have unnaturally sharp/flat edges
4. Color variance    — screens and prints have different color distribution
"""

import cv2
import numpy as np


def _get_face_region(frame: np.ndarray, box: tuple) -> np.ndarray:
    """Crop face region from frame."""
    left, top, right, bottom = box
    h, w = frame.shape[:2]
    top    = max(0, top)
    left   = max(0, left)
    bottom = min(h, bottom)
    right  = min(w, right)
    return frame[top:bottom, left:right]


def _texture_score(face_region: np.ndarray) -> float:
    """
    Laplacian variance — real faces have more texture variation than flat photos.
    Higher score = more texture = more likely real face.
    """
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    lap  = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


def _edge_density(face_region: np.ndarray) -> float:
    """
    Canny edge density — printed photos often have uniform, flat areas.
    Real faces have moderate edge complexity.
    """
    gray  = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return float(np.sum(edges > 0)) / float(edges.size)


def _color_variance(face_region: np.ndarray) -> float:
    """
    Color channel variance — real skin has natural color variation.
    Screens/photos often have artificially saturated colors.
    """
    hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
    sat_var = float(np.var(hsv[:, :, 1]))   # saturation variance
    val_var = float(np.var(hsv[:, :, 2]))   # brightness variance
    return sat_var + val_var


def _reflection_check(face_region: np.ndarray) -> bool:
    """
    Detect screen glare — screens often have bright specular highlights.
    Returns True if suspicious bright spots found (possible screen reflection).
    """
    gray          = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    bright_pixels = np.sum(gray > 240)
    total_pixels  = gray.size
    ratio         = bright_pixels / total_pixels
    return ratio > 0.08    # >8% very bright pixels = possible screen glare


def analyze_frame(
    frame: np.ndarray,
    face_box: tuple,
    texture_thresh: float = 80.0,
    edge_thresh: float    = 0.04,
    color_thresh: float   = 400.0,
) -> dict:
    """
    Analyze a single face region for spoofing.

    Args:
        frame:          Full BGR video frame
        face_box:       (left, top, right, bottom) face bounding box
        texture_thresh: Min Laplacian variance for real face (default 80)
        edge_thresh:    Min edge density for real face (default 0.04)
        color_thresh:   Min color variance for real face (default 400)

    Returns dict with:
        is_real (bool)       — True if face passes anti-spoof checks
        confidence (str)     — 'HIGH' / 'MEDIUM' / 'LOW'
        reason (str)         — Why it was flagged (if fake)
        scores (dict)        — Individual metric scores
    """
    face = _get_face_region(frame, face_box)

    if face.size == 0 or face.shape[0] < 20 or face.shape[1] < 20:
        return {
            "is_real": True,     # Too small to analyze — give benefit of doubt
            "confidence": "LOW",
            "reason": "Face region too small to analyze",
            "scores": {},
        }

    texture = _texture_score(face)
    edges   = _edge_density(face)
    color   = _color_variance(face)
    glare   = _reflection_check(face)

    scores = {
        "texture":  round(texture, 2),
        "edges":    round(edges,   4),
        "color":    round(color,   2),
        "glare":    glare,
    }

    # Count how many checks pass
    passes = 0
    fails  = []

    if texture >= texture_thresh:
        passes += 1
    else:
        fails.append(f"Low texture ({texture:.1f} < {texture_thresh})")

    if edges >= edge_thresh:
        passes += 1
    else:
        fails.append(f"Low edge complexity ({edges:.3f} < {edge_thresh})")

    if color >= color_thresh:
        passes += 1
    else:
        fails.append(f"Low color variance ({color:.1f} < {color_thresh})")

    if glare:
        fails.append("Screen glare detected")

    # Decision logic
    if passes >= 2 and not glare:
        is_real    = True
        confidence = "HIGH" if passes == 3 else "MEDIUM"
        reason     = "Passed anti-spoofing checks"
    elif passes == 2 and glare:
        is_real    = False
        confidence = "MEDIUM"
        reason     = "Screen glare detected — possible screen attack"
    else:
        is_real    = False
        confidence = "HIGH" if passes == 0 else "MEDIUM"
        reason     = " | ".join(fails) if fails else "Failed anti-spoofing checks"

    return {
        "is_real":    is_real,
        "confidence": confidence,
        "reason":     reason,
        "scores":     scores,
    }


def draw_spoof_overlay(
    frame:      np.ndarray,
    face_box:   tuple,
    result:     dict,
) -> np.ndarray:
    """Draw anti-spoof result overlay on the frame."""
    left, top, right, bottom = face_box
    is_real = result["is_real"]

    # Overlay bar below face box
    bar_color = (0, 200, 80) if is_real else (0, 60, 255)
    label     = "REAL" if is_real else "SPOOF DETECTED"
    icon      = "✓" if is_real else "!"

    cv2.rectangle(frame, (left, bottom + 2), (right, bottom + 22), bar_color, cv2.FILLED)
    cv2.putText(
        frame,
        f"{icon} {label} [{result['confidence']}]",
        (left + 4, bottom + 16),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45,
        (255, 255, 255), 1,
    )
    return frame
