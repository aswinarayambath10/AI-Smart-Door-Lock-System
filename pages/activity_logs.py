"""
Access Logs Page — Door Lock Edition
Shows GRANTED / DENIED access history
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import get_logs_df, clear_logs
import io


def show():
    st.markdown("# 📋 ACCESS LOGS")
    st.markdown("Complete door access history — who was granted or denied entry")
    st.markdown("---")

    logs_df = get_logs_df()

    if logs_df.empty:
        st.info("📭 No access logs yet. Use the Door Lock Control or Live Detection to generate logs.")
        return

    # ── Summary metrics 
    total     = len(logs_df)
    granted   = len(logs_df[logs_df["status"] == "GRANTED"])
    denied    = len(logs_df[logs_df["status"] == "DENIED"])
    today_str = datetime.now().strftime("%Y-%m-%d")
    today     = len(logs_df[logs_df["timestamp"].str.startswith(today_str)])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Access Attempts", total)
    col2.metric("✅ Access Granted", granted)
    col3.metric("❌ Access Denied", denied)
    col4.metric("Today's Attempts", today)

    st.markdown("---")

    # ── Filters 
    st.markdown("### 🔍 Filters")
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        status_filter = st.multiselect(
            "Access Status", ["GRANTED", "DENIED"],
            default=["GRANTED", "DENIED"]
        )
    with fcol2:
        names = ["All"] + sorted(logs_df["name"].unique().tolist())
        name_filter = st.selectbox("Person", names)
    with fcol3:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().date() - timedelta(days=7), datetime.now().date())
        )

    # Apply filters
    filtered = logs_df.copy()
    filtered["datetime"] = pd.to_datetime(filtered["timestamp"])

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if name_filter != "All":
        filtered = filtered[filtered["name"] == name_filter]
    if len(date_range) == 2:
        filtered = filtered[
            (filtered["datetime"].dt.date >= date_range[0]) &
            (filtered["datetime"].dt.date <= date_range[1])
        ]

    filtered = filtered.sort_values("datetime", ascending=False).drop(columns=["datetime"])

    st.markdown(f"**Showing {len(filtered)} of {len(logs_df)} records**")
    st.markdown("---")

    # ── Color coded table
    def highlight_status(val):
        if val == "GRANTED":
            return "background-color: rgba(0,255,136,0.1); color: #00cc66"
        elif val == "DENIED":
            return "background-color: rgba(255,60,60,0.1); color: #ff3c3c"
        return ""

    styled = filtered.style.applymap(highlight_status, subset=["status"])
    st.dataframe(styled, use_container_width=True, height=420)

    # ── Recent access events (visual)
    st.markdown("---")
    st.markdown("### 🕐 Recent Access Events")
    recent = filtered.head(8)
    for _, row in recent.iterrows():
        is_granted = row["status"] == "GRANTED"
        color  = "#00ff88" if is_granted else "#ff3c3c"
        icon   = "✅" if is_granted else "❌"
        label  = "GRANTED" if is_granted else "DENIED"
        st.markdown(
            f"""<div style="background:#0d1b2a;border-left:4px solid {color};
            padding:0.5rem 1rem;margin:0.3rem 0;border-radius:2px;
            font-family:'Share Tech Mono',monospace;font-size:0.85rem;">
            {icon} [{row['timestamp']}] &nbsp;
            <strong style="color:{color}">{label}</strong> &nbsp;|&nbsp;
            {row['name']} &nbsp;|&nbsp; Confidence: {row.get('confidence','N/A')}
            </div>""",
            unsafe_allow_html=True
        )

    # ── Export & Clear 
    st.markdown("---")
    exp_col, clr_col = st.columns([3, 1])

    with exp_col:
        csv_buffer = io.StringIO()
        filtered.to_csv(csv_buffer, index=False)
        st.download_button(
            "⬇️ Export Access Log CSV",
            data=csv_buffer.getvalue(),
            file_name=f"access_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    with clr_col:
        if st.button("🗑️ Clear All Logs"):
            clear_logs()
            st.rerun()
