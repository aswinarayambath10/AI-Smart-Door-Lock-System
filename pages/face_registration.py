"""
Face Registration Page
Register new known faces into the system
"""

import streamlit as st
import cv2
import os
import numpy as np
from PIL import Image
import io
from utils.face_db import register_face, get_registered_faces, delete_face


KNOWN_FACES_DIR = "data/known_faces"


def show():
    st.markdown("# 👤 FACE REGISTRATION")
    st.markdown("Register known individuals into the surveillance database")
    st.markdown("---")

    tab1, tab2 = st.tabs(["➕ Register New Face", "📋 Manage Registered Faces"])

    with tab1:
        st.markdown("### Register a New Person")
        st.info("💡 Upload a clear, front-facing photo. The system will extract the face encoding and store it.")

        col1, col2 = st.columns([1, 1])

        with col1:
            person_name = st.text_input("Person Name", placeholder="e.g. John Doe")
            person_role = st.selectbox("Role / Access Level",
                                       ["Staff", "Student", "Visitor", "Admin", "Security"])
            person_dept = st.text_input("Department / Notes (optional)", placeholder="e.g. Engineering")

        with col2:
            upload_method = st.radio("Image Source", ["Upload Image", "Use Webcam Capture"])

        st.markdown("---")

        image_data = None

        if upload_method == "Upload Image":
            uploaded = st.file_uploader(
                "Upload face image", type=["jpg", "jpeg", "png"],
                help="Clear, front-facing photo works best"
            )
            if uploaded:
                image_data = Image.open(uploaded)
                st.image(image_data, caption="Preview", width=250)

        else:
            captured = st.camera_input("Capture from Webcam")
            if captured:
                image_data = Image.open(captured)
                st.image(image_data, caption="Captured Frame", width=250)

        st.markdown("---")
        if st.button("💾 REGISTER FACE", use_container_width=True, disabled=(not person_name or image_data is None)):
            if person_name and image_data:
                with st.spinner("Processing face encoding..."):
                    success, message = register_face(
                        name=person_name,
                        role=person_role,
                        department=person_dept,
                        image=image_data,
                    )
                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                else:
                    st.error(f"❌ {message}")
            else:
                st.warning("Please provide a name and an image.")

    with tab2:
        st.markdown("### Registered Persons")
        faces = get_registered_faces()

        if not faces:
            st.info("No registered faces yet. Use the Registration tab to add persons.")
            return

        st.markdown(f"**Total registered:** {len(faces)} persons")
        st.markdown("---")

        for face in faces:
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                img_path = os.path.join(KNOWN_FACES_DIR, face["filename"])
                if os.path.exists(img_path):
                    st.image(img_path, width=80)
                else:
                    st.markdown("🧑")
            with col2:
                st.markdown(f"**{face['name']}**")
                st.markdown(f"Role: `{face.get('role', 'N/A')}` | Dept: `{face.get('department', 'N/A')}`")
                st.markdown(f"Registered: `{face.get('registered_at', 'N/A')}`")
            with col3:
                if st.button("🗑️ Delete", key=f"del_{face['name']}"):
                    delete_face(face["name"])
                    st.rerun()
            st.markdown("---")
