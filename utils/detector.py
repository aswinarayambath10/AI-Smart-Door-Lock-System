"""
Surveillance Detector
Integrates YOLO, face_recognition, and MediaPipe,opencv,numpy,pandas,rag
"""

import cv2
import numpy as np
import os
import json
import face_recognition
import mediapipe as mp
from ultralytics import YOLO
from utils.face_db import load_known_encodings


KNOWN_FACES_DIR = "data/known_faces"


class SurveillanceDetector:
    """
    Main detection engine combining:
    - YOLOv8 for person detection
    - face_recognition (dlib) for face ID
    - MediaPipe for facial landmark overlay
    """

    def __init__(
        self,
        yolo_conf: float = 0.5,
        face_tolerance: float = 0.6,
        show_landmarks: bool = True,
        show_face: bool = True,
        show_yolo: bool = True,
        yolo_model: str = "yolov8n.pt",
    ):
        self.yolo_conf = yolo_conf
        self.face_tolerance = face_tolerance
        self.show_landmarks = show_landmarks
        self.show_face = show_face
        self.show_yolo = show_yolo

        # Load YOLO model
        self.yolo = YOLO(yolo_model)

        # Load known face encodings
        self.known_encodings, self.known_names = load_known_encodings()

        # MediaPipe face mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def process_frame(self, frame: np.ndarray):
        """
        Process a single video frame.
        Returns: (annotated_frame, list_of_detections)
        """
        detections = []
        h, w = frame.shape[:2]

        # ---- 1. YOLO Person Detection ----
        yolo_results = self.yolo(frame, conf=self.yolo_conf, classes=[0], verbose=False)
        person_boxes = []
        for result in yolo_results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                person_boxes.append((x1, y1, x2, y2, conf))

                if self.show_yolo:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 136), 2)
                    cv2.putText(
                        frame, f"PERSON {conf:.2f}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 136), 1
                    )

        # ---- 2. MediaPipe Facial Landmarks ----
        if self.show_landmarks:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_result = self.face_mesh.process(rgb)
            if mp_result.multi_face_landmarks:
                for face_lms in mp_result.multi_face_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame,
                        face_lms,
                        self.mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style(),
                    )
                    self.mp_drawing.draw_landmarks(
                        frame,
                        face_lms,
                        self.mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style(),
                    )

        # ---- 3. Face Recognition ----
        if self.show_face:
            small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

            for (top, right, bottom, left), enc in zip(face_locations, face_encodings):
                # Scale back up
                top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2

                name = "Unknown"
                status = "UNKNOWN"
                confidence = "N/A"
                color = (60, 60, 255)  # Red for unknown

                if self.known_encodings:
                    distances = face_recognition.face_distance(self.known_encodings, enc)
                    best_idx = np.argmin(distances)
                    if distances[best_idx] <= self.face_tolerance:
                        name = self.known_names[best_idx]
                        status = "KNOWN"
                        confidence = f"{1 - distances[best_idx]:.2f}"
                        color = (136, 255, 0)  # Green for known

                # Draw face box
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, cv2.FILLED)
                cv2.putText(
                    frame, f"{name} [{confidence}]",
                    (left + 4, bottom - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1
                )

                detections.append({
                    "name": name,
                    "status": status,
                    "confidence": confidence,
                    "box": (left, top, right, bottom),
                })

        # ---- Overlay HUD ----
        _draw_hud(frame, len(person_boxes), len(detections))

        return frame, detections


def _draw_hud(frame, persons: int, faces: int):
    """Draw surveillance HUD overlay."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Top bar
    cv2.rectangle(overlay, (0, 0), (w, 36), (5, 10, 14), -1)
    alpha = 0.7
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    cv2.putText(frame, f"LIVE  |  PERSONS: {persons}  |  FACES: {faces}  |  {ts}",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 136), 1)

    # Corner brackets
    bracket_len, thick = 20, 2
    color = (0, 255, 136)
    for (x, y, dx, dy) in [(0, 0, 1, 1), (w - 1, 0, -1, 1), (0, h - 1, 1, -1), (w - 1, h - 1, -1, -1)]:
        cv2.line(frame, (x, y), (x + dx * bracket_len, y), color, thick)
        cv2.line(frame, (x, y), (x, y + dy * bracket_len), color, thick)
