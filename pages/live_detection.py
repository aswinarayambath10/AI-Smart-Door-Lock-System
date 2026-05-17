"""
Live Detection Page — Door Lock Edition
Shows YOLO + face recognition + MediaPipe with GRANTED/DENIED overlay
"""

import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import time
from utils.detector import SurveillanceDetector
from utils.logger import log_detection


def show():
    st.markdown("# 📷 LIVE DETECTION")
    st.markdown("Real-time person detection with door access overlay")
    st.markdown("---")

    with st.expander("⚙️ Detection Settings", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            yolo_conf = st.slider("YOLO Confidence", 0.1, 1.0, 0.5, 0.05)
            show_yolo = st.checkbox("Show YOLO Boxes", value=True)
        with col2:
            face_conf = st.slider("Face Tolerance", 0.3, 0.7, 0.55, 0.05,
                                  help="Lower = stricter. Recommended 0.55 for door security.")
            show_face = st.checkbox("Show Face Recognition", value=True)
        with col3:
            show_landmarks = st.checkbox("Show MediaPipe Landmarks", value=True)
            log_enabled = st.checkbox("Enable Logging", value=True)

    st.markdown("---")

    col_start, col_stop = st.columns([1, 1])
    with col_start:
        start_btn = st.button("▶ START DETECTION", use_container_width=True)
    with col_stop:
        stop_btn = st.button("⏹ STOP", use_container_width=True)

    if "running" not in st.session_state:
        st.session_state.running = False
    if start_btn:
        st.session_state.running = True
    if stop_btn:
        st.session_state.running = False

    frame_placeholder = st.empty()
    status_placeholder = st.empty()

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    persons_metric = stat_col1.empty()
    granted_metric = stat_col2.empty()
    denied_metric  = stat_col3.empty()
    fps_metric     = stat_col4.empty()

    if st.session_state.running:
        status_placeholder.markdown(
            '<div style="color:#00ff88;font-family:Share Tech Mono,monospace;">● CAMERA ACTIVE</div>',
            unsafe_allow_html=True
        )
        try:
            detector = SurveillanceDetector(
                yolo_conf=yolo_conf,
                face_tolerance=face_conf,
                show_landmarks=show_landmarks,
                show_face=show_face,
                show_yolo=show_yolo,
            )
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                st.error("❌ Cannot open camera.")
                st.session_state.running = False
                return

            frame_count = 0
            start_time = time.time()
            last_log_time = {}

            while st.session_state.running:
                ret, frame = cap.read()
                if not ret:
                    break

                processed_frame, detections = detector.process_frame(frame)
                rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                frame_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

                if log_enabled and detections:
                    for det in detections:
                        name = det.get("name", "Unknown")
                        now = time.time()
                        if name not in last_log_time or (now - last_log_time[name]) > 30:
                            status = "GRANTED" if det.get("status") == "KNOWN" else "DENIED"
                            log_detection(
                                name=name,
                                status=status,
                                confidence=det.get("confidence", "N/A"),
                                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            last_log_time[name] = now

                frame_count += 1
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0

                granted = sum(1 for d in detections if d.get("status") == "KNOWN")
                denied  = sum(1 for d in detections if d.get("status") == "UNKNOWN")

                persons_metric.metric("Persons Detected", len(detections))
                granted_metric.metric("✅ Access Granted", granted)
                denied_metric.metric("❌ Access Denied", denied)
                fps_metric.metric("FPS", f"{fps:.1f}")

                time.sleep(0.03)

            cap.release()
            status_placeholder.markdown(
                '<div style="color:#ff3c3c;font-family:Share Tech Mono,monospace;">● CAMERA STOPPED</div>',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"❌ Detection error: {e}")
            st.session_state.running = False
    else:
        frame_placeholder.markdown("""
        <div style="background:#0d1b2a;border:2px dashed #1a3a5c;border-radius:8px;
        height:400px;display:flex;align-items:center;justify-content:center;
        flex-direction:column;font-family:'Share Tech Mono',monospace;color:#3a6a9c;">
            <div style="font-size:4rem;margin-bottom:1rem;">📷</div>
            <div style="font-size:1.2rem;">CAMERA OFFLINE</div>
            <div style="font-size:0.8rem;margin-top:0.5rem;">Press START DETECTION to begin</div>
        </div>
        """, unsafe_allow_html=True)
