"""
RAG Query Assistant Page
Natural language question answering over detection logs
"""

import streamlit as st
import pandas as pd
from utils.rag_engine import RAGEngine
from utils.logger import get_logs_df
from datetime import datetime


def show():
    st.markdown("# 🤖 RAG QUERY ASSISTANT")
    st.markdown("Ask natural language questions about surveillance activity")
    st.markdown("---")

    st.info("""
    💬 **Examples of questions you can ask:**
    - "Who was detected today?"
    - "How many unknown persons were detected this week?"
    - "When was person last seen?"
    - "List all unknown detections in the morning"
    - "Which person was detected most frequently?"
    """)

    logs_df = get_logs_df()

    if logs_df.empty:
        st.warning("⚠️ No logs available. Run Live Detection first to populate activity data.")
        return

    # Initialize RAG engine
    if "rag_engine" not in st.session_state:
        with st.spinner("🔧 Initializing RAG engine..."):
            st.session_state.rag_engine = RAGEngine()
            st.session_state.rag_engine.build_index(logs_df)
        st.success("✅ RAG engine ready!")

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div style="background:#0d1b2a;border-left:3px solid #3a6a9c;padding:0.75rem 1rem;
            margin:0.5rem 0;border-radius:4px;font-family:'Rajdhani',sans-serif;">
            <strong style="color:#3a6a9c;">YOU</strong><br>{msg['content']}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#0d1b2a;border-left:3px solid #00ff88;padding:0.75rem 1rem;
            margin:0.5rem 0;border-radius:4px;font-family:'Rajdhani',sans-serif;">
            <strong style="color:#00ff88;">SYSTEM AI</strong><br>{msg['content']}
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Query input
    query = st.text_input(
        "Ask a question about surveillance activity:",
        placeholder="e.g. Who was detected most today?",
        key="rag_query_input"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        submit = st.button("🔍 QUERY", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            st.rerun()

    if submit and query:
        with st.spinner("Searching logs..."):
            answer = st.session_state.rag_engine.query(query, logs_df)

        st.session_state.chat_history.append({"role": "user", "content": query})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    # Rebuild index if new logs added
    st.markdown("---")
    if st.button("🔄 Rebuild Index (refresh with latest logs)"):
        with st.spinner("Rebuilding..."):
            new_logs = get_logs_df()
            st.session_state.rag_engine.build_index(new_logs)
        st.success("✅ Index rebuilt!")
