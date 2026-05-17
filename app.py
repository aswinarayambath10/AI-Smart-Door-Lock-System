"""
Smart AI Surveillance System — Door Lock Edition
Main Entry Point
"""

import streamlit as st

st.set_page_config(
    page_title="Smart Door Lock System",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

    .stApp { background-color: #050a0e; color: #c8d8e8; font-family: 'Rajdhani', sans-serif; }
    .stSidebar { background-color: #0d1b2a !important; border-right: 1px solid #1a3a5c; }
    h1, h2, h3 { font-family: 'Share Tech Mono', monospace; color: #00ff88 !important; }

    .stButton > button {
        background: transparent;
        border: 1px solid #00ff88;
        color: #00ff88;
        font-family: 'Share Tech Mono', monospace;
        letter-spacing: 2px;
        transition: all 0.3s;
    }
    .stButton > button:hover { background: #00ff88; color: #050a0e; }
    .status-online { color: #00ff88; font-family: 'Share Tech Mono', monospace; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🔐 SMART DOOR LOCK")
    st.markdown("---")
    st.markdown("**System Status:** <span class='status-online'>● ONLINE</span>", unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "🚪 Door Lock Control",
            "📷 Live Detection",
            "👤 Face Registration",
            "📋 Access Logs",
            "🤖 RAG Query Assistant",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("**v2.0.0** | Smart Door Lock AI")

if page == "🚪 Door Lock Control":
    from pages import door_lock
    door_lock.show()
elif page == "📷 Live Detection":
    from pages import live_detection
    live_detection.show()
elif page == "👤 Face Registration":
    from pages import face_registration
    face_registration.show()
elif page == "📋 Access Logs":
    from pages import activity_logs
    activity_logs.show()
elif page == "🤖 RAG Query Assistant":
    from pages import rag_assistant
    rag_assistant.show()
