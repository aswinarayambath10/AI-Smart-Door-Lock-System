"""
Smart Door Lock Control Page — v3
Features:
  - Face recognition (GRANTED / DENIED)
  - Anti-spoofing (detects photo/screen attacks)
  - OTP/PIN backup access (if face not recognized)
  - Sound alerts (chime / beep)
"""

import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime
from utils.face_db import load_known_encodings, get_registered_faces
from utils.logger import log_detection
from utils.pin_manager import verify_pin, is_pin_enabled
from utils.anti_spoof import analyze_frame, draw_spoof_overlay


# ── Sound alerts 
SOUND_DENIED_HTML = """
<script>
(function() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        function beep(freq, start, duration, vol) {
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'square';
            o.frequency.value = freq;
            g.gain.setValueAtTime(vol, ctx.currentTime + start);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
            o.start(ctx.currentTime + start);
            o.stop(ctx.currentTime + start + duration + 0.05);
        }
        beep(400, 0.00, 0.18, 0.7);
        beep(400, 0.22, 0.18, 0.7);
        beep(400, 0.44, 0.18, 0.7);
    } catch(e) {}
})();
</script>
"""

SOUND_GRANTED_HTML = """
<script>
(function() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        function note(freq, start, duration, vol) {
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine';
            o.frequency.value = freq;
            g.gain.setValueAtTime(vol, ctx.currentTime + start);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
            o.start(ctx.currentTime + start);
            o.stop(ctx.currentTime + start + duration + 0.05);
        }
        note(523, 0.0,  0.25, 0.5);
        note(784, 0.28, 0.45, 0.5);
    } catch(e) {}
})();
</script>
"""

SOUND_SPOOF_HTML = """
<script>
(function() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        function beep(freq, start, duration, vol) {
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sawtooth';
            o.frequency.value = freq;
            g.gain.setValueAtTime(vol, ctx.currentTime + start);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
            o.start(ctx.currentTime + start);
            o.stop(ctx.currentTime + start + duration + 0.05);
        }
        beep(200, 0.00, 0.3, 0.8);
        beep(150, 0.35, 0.3, 0.8);
    } catch(e) {}
})();
</script>
"""

# ── Door state panels 
DOOR_OPEN_HTML = """
<div style="background:rgba(0,255,136,0.08);border:3px solid #00ff88;border-radius:16px;
padding:2.5rem 1rem;text-align:center;font-family:'Share Tech Mono',monospace;
animation:pulse-green 1s ease-in-out infinite alternate;">
    <div style="font-size:5rem;">🔓</div>
    <div style="font-size:2rem;color:#00ff88;font-weight:bold;letter-spacing:4px;">ACCESS GRANTED</div>
    <div style="font-size:1rem;color:#00cc66;margin-top:0.5rem;">DOOR IS OPEN</div>
</div>
<style>@keyframes pulse-green{from{box-shadow:0 0 10px rgba(0,255,136,0.3)}to{box-shadow:0 0 30px rgba(0,255,136,0.7)}}</style>
"""

DOOR_DENIED_HTML = """
<div style="background:rgba(255,60,60,0.08);border:3px solid #ff3c3c;border-radius:16px;
padding:2.5rem 1rem;text-align:center;font-family:'Share Tech Mono',monospace;
animation:pulse-red 0.5s ease-in-out infinite alternate;">
    <div style="font-size:5rem;">🔒</div>
    <div style="font-size:2rem;color:#ff3c3c;font-weight:bold;letter-spacing:4px;">ACCESS DENIED</div>
    <div style="font-size:1rem;color:#cc2222;margin-top:0.5rem;">UNKNOWN PERSON</div>
</div>
<style>@keyframes pulse-red{from{box-shadow:0 0 10px rgba(255,60,60,0.3)}to{box-shadow:0 0 30px rgba(255,60,60,0.7)}}</style>
"""

DOOR_SPOOF_HTML = """
<div style="background:rgba(255,180,0,0.08);border:3px solid #ffb800;border-radius:16px;
padding:2.5rem 1rem;text-align:center;font-family:'Share Tech Mono',monospace;
animation:pulse-warn 0.4s ease-in-out infinite alternate;">
    <div style="font-size:5rem;">⚠️</div>
    <div style="font-size:2rem;color:#ffb800;font-weight:bold;letter-spacing:4px;">SPOOF DETECTED</div>
    <div style="font-size:1rem;color:#cc8800;margin-top:0.5rem;">PHOTO / SCREEN ATTACK</div>
</div>
<style>@keyframes pulse-warn{from{box-shadow:0 0 10px rgba(255,180,0,0.3)}to{box-shadow:0 0 30px rgba(255,180,0,0.8)}}</style>
"""

DOOR_STANDBY_HTML = """
<div style="background:rgba(26,86,160,0.08);border:3px solid #1a56a0;border-radius:16px;
padding:2.5rem 1rem;text-align:center;font-family:'Share Tech Mono',monospace;">
    <div style="font-size:5rem;">🔒</div>
    <div style="font-size:2rem;color:#3a7ad5;font-weight:bold;letter-spacing:4px;">STANDBY</div>
    <div style="font-size:1rem;color:#2a5aaa;margin-top:0.5rem;">WAITING FOR FACE SCAN...</div>
</div>
"""

DOOR_PIN_HTML = """
<div style="background:rgba(160,80,200,0.08);border:3px solid #a050c8;border-radius:16px;
padding:2.5rem 1rem;text-align:center;font-family:'Share Tech Mono',monospace;">
    <div style="font-size:5rem;">🔑</div>
    <div style="font-size:2rem;color:#a050c8;font-weight:bold;letter-spacing:4px;">PIN MODE</div>
    <div style="font-size:1rem;color:#8040a0;margin-top:0.5rem;">ENTER YOUR PIN BELOW</div>
</div>
"""


def show():
    st.markdown("# 🚪 SMART DOOR LOCK CONTROL")
    st.markdown("Face recognition · Anti-spoofing · PIN backup · Sound alerts")
    st.markdown("---")

    registered = get_registered_faces()

    # ── Top metrics ────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Registered Persons", len(registered))
    c2.metric("Door Status", "OPEN" if st.session_state.get("door_open") else "LOCKED")
    c3.metric("Auto-Lock After", "5 sec")
    c4.metric("🛡️ Anti-Spoofing", "ON")
    c5.metric("🔑 PIN Backup", "ON" if is_pin_enabled() else "OFF")

    st.markdown("---")

    # ── Settings expander 
    with st.expander("⚙️ Settings", expanded=False):
        tab_sound, tab_spoof, tab_pin = st.tabs(["🔊 Sound", "🛡️ Anti-Spoofing", "🔑 PIN Setup"])

        with tab_sound:
            sound_denied  = st.checkbox("🔴 Beep on ACCESS DENIED",    value=True)
            sound_granted = st.checkbox("🟢 Chime on ACCESS GRANTED",  value=True)
            sound_spoof   = st.checkbox("⚠️ Alert on SPOOF DETECTED",  value=True)

        with tab_spoof:
            st.markdown("**Anti-spoofing detects photo and screen attacks.**")
            spoof_enabled     = st.checkbox("Enable Anti-Spoofing", value=True)
            texture_threshold = st.slider("Texture Sensitivity",  30.0, 200.0, 80.0, 5.0,
                                          help="Higher = stricter. Raise if real faces flagged as spoof.")
            color_threshold   = st.slider("Color Sensitivity",   100.0, 800.0, 400.0, 50.0)
            st.caption("How it works: Checks texture, edge complexity, color variance, and screen glare.")

        with tab_pin:
            st.markdown("**Set a PIN as backup access when face is not recognized.**")
            pin_info = is_pin_enabled()
            if pin_info:
                st.success("✅ PIN is currently enabled")
            else:
                st.warning("⚠️ No PIN set — PIN backup is inactive")

            new_pin     = st.text_input("Enter New PIN (4–8 digits)", type="password",
                                         placeholder="e.g. 1234")
            confirm_pin = st.text_input("Confirm PIN", type="password")

            col_set, col_dis = st.columns(2)
            with col_set:
                if st.button("💾 Save PIN", use_container_width=True):
                    if new_pin != confirm_pin:
                        st.error("❌ PINs do not match!")
                    else:
                        from utils.pin_manager import set_pin
                        ok, msg = set_pin(new_pin)
                        st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
            with col_dis:
                if st.button("🗑️ Disable PIN", use_container_width=True):
                    from utils.pin_manager import disable_pin
                    disable_pin()
                    st.info("PIN backup disabled.")
    st.markdown("---")

    if not registered:
        st.warning("⚠️ No faces registered! Go to **👤 Face Registration** first.")
        return

    # ── Layout: camera | door status 
    cam_col, status_col = st.columns([3, 2])

    with cam_col:
        st.markdown("### 📷 Face Scanner")
        s1, s2 = st.columns(2)
        with s1:
            start_btn = st.button("▶ START SCANNER", use_container_width=True)
        with s2:
            stop_btn  = st.button("⏹ STOP",          use_container_width=True)

        for key, val in [("door_running", False), ("door_open", False),
                         ("door_person", None),   ("last_sound_state", "standby"),
                         ("pin_mode", False)]:
            if key not in st.session_state:
                st.session_state[key] = val

        if start_btn:
            st.session_state.door_running    = True
            st.session_state.door_open       = False
            st.session_state.pin_mode        = False
            st.session_state.last_sound_state = "standby"
        if stop_btn:
            st.session_state.door_running    = False
            st.session_state.door_open       = False
            st.session_state.pin_mode        = False

        frame_placeholder = st.empty()
        scan_status       = st.empty()
        sound_placeholder = st.empty()

    with status_col:
        st.markdown("### 🔐 Door Status")
        door_display   = st.empty()
        person_display = st.empty()

        # ── PIN entry panel (always visible on right side) 
        st.markdown("---")
        st.markdown("### 🔑 PIN Backup Access")
        if is_pin_enabled():
            pin_input = st.text_input("Enter PIN to unlock door",
                                      type="password",
                                      placeholder="Enter your PIN",
                                      key="pin_input_field")
            if st.button("🔓 UNLOCK WITH PIN", use_container_width=True):
                if verify_pin(pin_input):
                    st.session_state.door_open = True
                    st.success("✅ PIN Correct — ACCESS GRANTED!")
                    log_detection(
                        name="PIN Access",
                        status="GRANTED",
                        confidence="PIN",
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    door_display.markdown(DOOR_OPEN_HTML, unsafe_allow_html=True)
                    sound_placeholder.markdown(SOUND_GRANTED_HTML, unsafe_allow_html=True)
                else:
                    st.error("❌ Wrong PIN — ACCESS DENIED!")
                    log_detection(
                        name="PIN Attempt",
                        status="DENIED",
                        confidence="PIN",
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    sound_placeholder.markdown(SOUND_DENIED_HTML, unsafe_allow_html=True)
        else:
            st.info("Set a PIN in ⚙️ Settings → PIN Setup to enable backup access.")

        st.markdown("---")
        st.markdown("### 👥 Authorised Persons")
        for r in registered:
            st.markdown(
                f"""<div style="background:#0d1b2a;border-left:3px solid #00ff88;
                padding:0.4rem 0.8rem;margin:0.3rem 0;border-radius:2px;
                font-family:'Share Tech Mono',monospace;font-size:0.82rem;color:#c8d8e8;">
                ✅ {r['name']} — <span style="color:#3a7ad5">{r.get('role','N/A')}</span>
                </div>""",
                unsafe_allow_html=True
            )

    # ── Show standby if not running 
    if not st.session_state.door_running:
        door_display.markdown(DOOR_STANDBY_HTML, unsafe_allow_html=True)
        frame_placeholder.markdown("""
        <div style="background:#0d1b2a;border:2px dashed #1a3a5c;border-radius:8px;
        height:320px;display:flex;align-items:center;justify-content:center;
        flex-direction:column;font-family:'Share Tech Mono',monospace;color:#3a6a9c;">
            <div style="font-size:3rem;margin-bottom:1rem;">📷</div>
            <div>SCANNER OFFLINE</div>
            <div style="font-size:0.8rem;margin-top:0.5rem;">Press START SCANNER to begin</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Load face recognition 
    try:
        import face_recognition
    except ImportError:
        st.error("❌ face_recognition not installed.")
        return

    known_encodings, known_names = load_known_encodings()
    if not known_encodings:
        st.error("❌ No face encodings found. Please register faces first.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("❌ Cannot open camera.")
        st.session_state.door_running = False
        return

    door_open_until = 0
    last_log_time   = {}
    face_tolerance  = 0.55

    scan_status.markdown(
        '<div style="color:#3a7ad5;font-family:Share Tech Mono,monospace;font-size:0.85rem;">'
        '● SCANNER ACTIVE — Stand in front of camera</div>',
        unsafe_allow_html=True
    )

    while st.session_state.door_running:
        ret, frame = cap.read()
        if not ret:
            break

        now        = time.time()
        rgb_small  = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.5, fy=0.5), cv2.COLOR_BGR2RGB)
        face_locs  = face_recognition.face_locations(rgb_small)
        face_encs  = face_recognition.face_encodings(rgb_small, face_locs)

        door_state    = "standby"
        detected_name = None
        spoof_info    = None

        for (top, right, bottom, left), enc in zip(face_locs, face_encs):
            top, right, bottom, left = top*2, right*2, bottom*2, left*2
            face_box = (left, top, right, bottom)

            # ── Anti-spoofing check first 
            if spoof_enabled:
                spoof_info = analyze_frame(
                    frame, face_box,
                    texture_thresh=texture_threshold,
                    color_thresh=color_threshold,
                )
                frame = draw_spoof_overlay(frame, face_box, spoof_info)

                if not spoof_info["is_real"]:
                    door_state    = "spoof"
                    detected_name = "SPOOF ATTACK"
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 140, 255), 3)
                    log_detection(
                        name="Spoof Attack",
                        status="DENIED",
                        confidence="SPOOF",
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    continue   # Skip face recognition for spoof faces

            # ── Face recognition 
            name   = "Unknown"
            status = "DENIED"
            color  = (60, 60, 255)

            distances = face_recognition.face_distance(known_encodings, enc)
            best_idx  = int(np.argmin(distances))

            if distances[best_idx] <= face_tolerance:
                name   = known_names[best_idx]
                status = "GRANTED"
                color  = (0, 255, 136)
                door_open_until = now + 5
                door_state      = "open"
                detected_name   = name
            else:
                door_state    = "denied"
                detected_name = "Unknown Person"

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom-32), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, f"{name} — {status}",
                        (left+4, bottom-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

            if name not in last_log_time or (now - last_log_time[name]) > 10:
                log_detection(
                    name=name, status=status,
                    confidence=f"{1 - distances[best_idx]:.2f}",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                last_log_time[name] = now

        if now < door_open_until and door_state not in ("denied", "spoof"):
            door_state = "open"

        # ── Sound on state change 
        prev = st.session_state.last_sound_state
        if door_state != prev:
            if   door_state == "denied"  and sound_denied:
                sound_placeholder.markdown(SOUND_DENIED_HTML,  unsafe_allow_html=True)
            elif door_state == "open"    and sound_granted and prev != "open":
                sound_placeholder.markdown(SOUND_GRANTED_HTML, unsafe_allow_html=True)
            elif door_state == "spoof"   and sound_spoof:
                sound_placeholder.markdown(SOUND_SPOOF_HTML,   unsafe_allow_html=True)
            else:
                sound_placeholder.empty()
            st.session_state.last_sound_state = door_state

        # ── Update door display panel 
        if door_state == "open":
            door_display.markdown(DOOR_OPEN_HTML, unsafe_allow_html=True)
            remaining = max(int(door_open_until - now) + 1, 0)
            person_display.markdown(
                f"""<div style="background:#0d1b2a;border:1px solid #00ff88;border-radius:8px;
                padding:0.8rem;text-align:center;font-family:'Share Tech Mono',monospace;">
                <div style="color:#00ff88;font-size:1.1rem;">👤 {detected_name}</div>
                <div style="color:#666;font-size:0.8rem;margin-top:0.3rem;">
                🔊 Chime played &nbsp;|&nbsp; Auto-locking in {remaining}s</div></div>""",
                unsafe_allow_html=True
            )
        elif door_state == "spoof":
            door_display.markdown(DOOR_SPOOF_HTML, unsafe_allow_html=True)
            reason = spoof_info.get("reason", "") if spoof_info else ""
            person_display.markdown(
                f"""<div style="background:#0d1b2a;border:1px solid #ffb800;border-radius:8px;
                padding:0.8rem;text-align:center;font-family:'Share Tech Mono',monospace;">
                <div style="color:#ffb800;font-size:1rem;">⚠️ Spoof Attack Blocked</div>
                <div style="color:#888;font-size:0.78rem;margin-top:0.3rem;">{reason}</div>
                </div>""",
                unsafe_allow_html=True
            )
        elif door_state == "denied":
            door_display.markdown(DOOR_DENIED_HTML, unsafe_allow_html=True)
            person_display.markdown(
                """<div style="background:#0d1b2a;border:1px solid #ff3c3c;border-radius:8px;
                padding:0.8rem;text-align:center;font-family:'Share Tech Mono',monospace;">
                <div style="color:#ff3c3c;font-size:1.1rem;">⚠️ Unauthorised Person</div>
                <div style="color:#666;font-size:0.8rem;margin-top:0.3rem;">
                🔊 Alert beep played &nbsp;|&nbsp; Use PIN if authorised</div></div>""",
                unsafe_allow_html=True
            )
        else:
            door_display.markdown(DOOR_STANDBY_HTML, unsafe_allow_html=True)
            person_display.markdown(
                """<div style="background:#0d1b2a;border:1px solid #1a3a5c;border-radius:8px;
                padding:0.8rem;text-align:center;font-family:'Share Tech Mono',monospace;">
                <div style="color:#3a7ad5;font-size:1rem;">No face detected</div>
                </div>""",
                unsafe_allow_html=True
            )

        # ── HUD overlay 
        ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 36), (5, 10, 14), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        door_text  = ("DOOR: OPEN"    if door_state == "open"
                      else "SPOOF!"   if door_state == "spoof"
                      else "DENIED"   if door_state == "denied"
                      else "LOCKED")
        hud_color  = ((0,255,136)   if door_state == "open"
                      else (0,140,255)  if door_state == "spoof"
                      else (60,60,255)  if door_state == "denied"
                      else (100,150,255))
        spoof_tag  = "  |  ANTI-SPOOF: ON" if spoof_enabled else ""
        cv2.putText(frame,
                    f"SMART DOOR LOCK  |  {door_text}  |  {ts}{spoof_tag}",
                    (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, hud_color, 1)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)
        time.sleep(0.05)

    cap.release()
    door_display.markdown(DOOR_STANDBY_HTML, unsafe_allow_html=True)
    sound_placeholder.empty()
    scan_status.markdown(
        '<div style="color:#ff3c3c;font-family:Share Tech Mono,monospace;font-size:0.85rem;">'
        '● SCANNER STOPPED</div>',
        unsafe_allow_html=True
    )
