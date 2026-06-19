import json
import os
import random
import time
from datetime import datetime, timedelta

import streamlit as st

PENDING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_patients.json")


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_pending(pending):
    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)


def remove_pending(patient_id):
    pending = load_pending()
    pending = [p for p in pending if p["id"] != patient_id]
    save_pending(pending)

st.set_page_config(
    page_title="ER Queue Management — Demo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
CTAS_COLORS = {1: "#C0392B", 2: "#E67E22", 3: "#D4AC0D", 4: "#27AE60", 5: "#2980B9"}
CTAS_LABELS = {
    1: "CTAS 1 · Resuscitation",
    2: "CTAS 2 · Emergent",
    3: "CTAS 3 · Urgent",
    4: "CTAS 4 · Less Urgent",
    5: "CTAS 5 · Non-Urgent",
}
CTAS_SHORT_LABELS = {1: "Resuscitation", 2: "Emergent", 3: "Urgent", 4: "Less Urgent", 5: "Non-Urgent"}
CTAS_WAIT = {1: 0, 2: 15, 3: 30, 4: 60, 5: 120}  # minutes per CTAS level
ER_NAMES = {"ER1": "Saint John Regional", "ER2": "St. Joseph's"}


# ─────────────────────────────────────────────────────────────
# Core queue logic
# ─────────────────────────────────────────────────────────────
def add_to_queue(name, age, sex, ctas, er, complaint="", arrival_offset_minutes=0, reasons=None):
    st.session_state.counters[er] += 1
    arrival_time = datetime.now() + timedelta(minutes=arrival_offset_minutes)
    st.session_state.queue.append(
        {
            "id": f"{time.time()}-{random.random()}",
            "ticket_num": st.session_state.counters[er],
            "name": name,
            "age": age,
            "sex": sex,
            "ctas": int(ctas),
            "er": er,
            "complaint": complaint,
            "reasons": reasons or [],
            "arrival_time": arrival_time,
        }
    )
    sort_queue()


def sort_queue():
    st.session_state.queue.sort(key=lambda p: (p["ctas"], p["arrival_time"]))


def er_queue(er):
    return [p for p in st.session_state.queue if p["er"] == er]


def calc_wait(patient):
    eq = er_queue(patient["er"])
    idx = next(i for i, p in enumerate(eq) if p["id"] == patient["id"])
    if idx == 0:
        return 0
    return sum(CTAS_WAIT[p["ctas"]] for p in eq[:idx])


def dismiss(patient_id):
    st.session_state.queue = [p for p in st.session_state.queue if p["id"] != patient_id]


def update_ctas(patient_id, new_ctas):
    for p in st.session_state.queue:
        if p["id"] == patient_id:
            p["ctas"] = int(new_ctas)
            break
    sort_queue()


def seed_queue():
    add_to_queue("John Smith", 54, "Male", 2, "ER1", "Chest pain radiating to left arm", -18,
                 reasons=["high-risk symptom pattern", "moderate symptom severity", "assigned to ER1"])
    add_to_queue("Maria Chen", 31, "Female", 3, "ER1", "Severe headache with nausea", -10,
                 reasons=["moderate symptom severity", "recent onset", "assigned to ER1"])
    add_to_queue("Robert Taylor", 67, "Male", 1, "ER2", "Sudden loss of consciousness", -5,
                 reasons=["high-risk symptom pattern", "older adult risk", "assigned to ER2"])
    add_to_queue("Sarah Lee", 22, "Female", 4, "ER2", "Sprained ankle", -2,
                 reasons=["stable presentation", "assigned to ER2"])


# ─────────────────────────────────────────────────────────────
# Session state init
# ─────────────────────────────────────────────────────────────
if "queue" not in st.session_state:
    st.session_state.queue = []
    st.session_state.counters = {"ER1": 0, "ER2": 0}
    seed_queue()

if "add_success" not in st.session_state:
    st.session_state.add_success = ""


# ─────────────────────────────────────────────────────────────
# Styling (shared look with the rest of the pre-triage app)
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root {
      --red: #C0392B;
      --orange: #E67E22;
      --yellow: #D4AC0D;
      --green: #27AE60;
      --blue: #2980B9;
      --bg: #F7F9FC;
      --card: #FFFFFF;
      --text: #1A2332;
      --muted: #6B7A90;
      --border: #DDE3EC;
      --accent: #1A4A7A;
      --radius: 10px;
    }
    html, body, [class*="css"] {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: #000000;
      color-scheme: light;
    }
    .stApp { background: var(--bg); }
    header[data-testid="stHeader"], div[data-testid="stToolbar"] { display: none; }
    .block-container {
      max-width: 980px !important;
      padding-top: 1.5rem;
      padding-bottom: 2.5rem;
    }
    .hero-header {
      background: var(--accent);
      color: white;
      padding: 18px 24px;
      display: flex;
      align-items: center;
      gap: 14px;
      border-radius: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,.18);
      margin-bottom: 18px;
    }
    .hero-title { font-size: 18px; font-weight: 700; line-height: 1.2; margin: 0; }
    .hero-subtitle { font-size: 12px; opacity: .78; margin-top: 2px; }

    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px 16px;
      box-shadow: 0 1px 4px rgba(0,0,0,.05);
      text-align: center;
    }
    .stat-val { font-size: 24px; font-weight: 800; color: var(--accent); }
    .stat-label { font-size: 11px; color: var(--muted); font-weight: 600; margin-top: 2px; text-transform: uppercase; letter-spacing: .05em; }

    .card-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .07em;
      color: var(--muted);
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .er-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 20px;
      color: white;
      background: var(--accent);
      letter-spacing: .04em;
    }
    .queue-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      margin-bottom: 8px;
      border: 1px solid var(--border);
      background: #FAFBFD;
    }
    .ticket-num {
      font-size: 11px;
      font-weight: 800;
      color: var(--muted);
      min-width: 28px;
      text-align: center;
      background: var(--bg);
      border-radius: 4px;
      padding: 2px 4px;
      border: 1px solid var(--border);
    }
    .patient-name { font-size: 14px; font-weight: 700; color: #000; }
    .patient-meta { font-size: 11px; color: var(--muted); margin-top: 1px; }
    .ctas-label {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 20px;
      color: white;
      white-space: nowrap;
      display: inline-block;
    }
    .wait-time { font-size: 11px; font-weight: 700; color: var(--muted); }
    .empty-state { text-align: center; padding: 24px 16px; color: var(--muted); font-size: 13px; }
    .legend { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; }
    .legend-item { font-size: 11px; color: var(--muted); font-weight: 600; display: flex; align-items: center; gap: 5px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

    .ticket-card {
      max-width: 420px;
      margin: 8px auto 0;
      background: var(--card);
      border-radius: 16px;
      border: 2px solid var(--border);
      padding: 30px 28px;
      text-align: center;
      box-shadow: 0 4px 20px rgba(0,0,0,.08);
    }
    .ticket-top { font-size: 12px; font-weight: 700; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 16px; }
    .ticket-number { font-size: 60px; font-weight: 900; color: var(--accent); line-height: 1; }
    .ticket-name { font-size: 18px; font-weight: 700; margin-top: 6px; color: #000; }
    .ticket-er { font-size: 13px; color: var(--muted); margin-top: 4px; }
    .ticket-ctas {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 8px 18px; border-radius: 30px; font-weight: 700; font-size: 15px;
      color: white; margin: 16px auto 0;
    }
    .ticket-divider { border: none; border-top: 2px dashed var(--border); margin: 18px 0; }
    .ticket-info-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .ticket-info-label { font-size: 12px; color: var(--muted); }
    .ticket-info-val { font-size: 13px; font-weight: 700; color: #000; }

    div[data-testid="stForm"] button[kind="primary"],
    div[data-testid="stFormSubmitButton"] button {
      background: var(--accent) !important;
      color: #ffffff !important;
      border: 1px solid var(--accent) !important;
      font-weight: 800 !important;
      border-radius: 10px !important;
      padding: 0.7rem 1rem !important;
      width: 100%;
    }

    .pending-card {
      background: #FFFBF0;
      border: 1px solid #F0C060;
      border-left: 4px solid #E67E22;
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 12px;
    }
    .pending-card .p-name { font-size: 15px; font-weight: 700; color: #000; }
    .pending-card .p-meta { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .pending-card .p-complaint { font-size: 13px; color: #333; margin-top: 6px; font-style: italic; }
    .pending-badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 9px;
      border-radius: 20px;
      color: white;
      margin-left: 8px;
      vertical-align: middle;
    }
    .pending-submitted-at { font-size: 11px; color: var(--muted); margin-top: 4px; }
    .pending-empty { text-align:center; padding:30px 16px; color:var(--muted); font-size:14px; }

    /* Compact action buttons: tick (dismiss), Approve, Reject */
    div[data-testid="stButton"] button {
      padding: 4px 12px !important;
      font-size: 12px !important;
      min-height: 32px !important;
      border-radius: 6px !important;
      font-weight: 700 !important;
    }
    div[data-testid="stButton"] button[title="Mark as seen"] {
      width: 34px !important;
      min-width: 34px !important;
      padding: 4px 0 !important;
    }

    /* Patient-name popover trigger: looks like a name label, not a button */
    div[data-testid="stPopover"] button {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      min-height: unset !important;
      font-size: 14px !important;
      font-weight: 700 !important;
      color: #000 !important;
      text-align: left !important;
    }
    div[data-testid="stPopover"] button:hover {
      color: var(--accent) !important;
      text-decoration: underline !important;
    }

    /* Patient detail pop-up: small, single-color card */
    div[data-testid="stPopoverBody"],
    div[data-testid="stPopoverBody"] * {
      background-color: transparent !important;
      background-image: none !important;
    }
    div[data-testid="stPopoverBody"] {
      background-color: var(--card) !important;
      border: 1px solid var(--border) !important;
      border-radius: 8px !important;
      padding: 10px 12px !important;
      max-width: 220px !important;
      box-shadow: 0 2px 10px rgba(0,0,0,.1) !important;
    }
    div[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] {
      font-size: 12px !important;
      color: var(--text) !important;
    }
    div[data-testid="stPopoverBody"] div[data-testid="stSelectbox"] {
      font-size: 12px !important;
    }
    div[data-testid="stPopoverBody"] div[data-baseweb="select"] > div {
      background-color: #ffffff !important;
      border-color: var(--border) !important;
    }
    div[data-testid="stPopoverBody"] div[data-baseweb="select"] * {
      color: #000000 !important;
    }
    div[data-testid="stPopoverBody"] button {
      background-color: var(--accent) !important;
      color: #ffffff !important;
      border: none !important;
      font-size: 11px !important;
      padding: 3px 10px !important;
      min-height: 26px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-header">
      <div style="font-size:28px">🏥</div>
      <div>
        <div class="hero-title">ER Queue Management</div>
        <div class="hero-subtitle">Saint John ER Pre-Triage System · Staff View · Demo Only</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_pending_count = len(load_pending())
_pending_label = f"⏳ Awaiting Approval ({_pending_count})" if _pending_count else "⏳ Awaiting Approval"

tab_queue, tab_add, tab_ticket, tab_pending = st.tabs(
    ["📋 Queue Board", "➕ Add Patient", "🎫 Patient Ticket", _pending_label]
)


# ─────────────────────────────────────────────────────────────
# Tab: Queue Board
# ─────────────────────────────────────────────────────────────
with tab_queue:
    total = len(st.session_state.queue)
    er1_count = len(er_queue("ER1"))
    er2_count = len(er_queue("ER2"))
    critical = len([p for p in st.session_state.queue if p["ctas"] <= 2])

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in (
            (c1, total, "Total Waiting"),
            (c2, er1_count, "ER1 Patients"),
            (c3, er2_count, "ER2 Patients"),
            (c4, critical, "CTAS 1–2 (Critical)"),
    ):
        with col:
            st.markdown(
                f"""<div class="stat-card"><div class="stat-val">{val}</div>
                <div class="stat-label">{label}</div></div>""",
                unsafe_allow_html=True,
            )

    st.write("")
    col_er1, col_er2 = st.columns(2)

    def render_er_column(col, er):
        with col:
            st.markdown(
                f"""<div class="card-title">{er} Queue
                <span class="er-badge">{ER_NAMES[er]}</span></div>""",
                unsafe_allow_html=True,
            )
            patients = er_queue(er)
            if not patients:
                st.markdown(
                    '<div class="empty-state">🟢<br>No patients in queue</div>',
                    unsafe_allow_html=True,
                )
                return
            for idx, p in enumerate(patients):
                wait = calc_wait(p)
                wait_label = "Now" if wait == 0 else f"~{wait} min"
                color = CTAS_COLORS[p["ctas"]]
                row = st.container()
                with row:
                    a, b, c = st.columns([5, 2, 1])
                    with a:
                        tnum_col, name_col = st.columns([1, 4])
                        with tnum_col:
                            st.markdown(
                                f'<div class="ticket-num" style="margin-top:7px;">#{p["ticket_num"]}</div>',
                                unsafe_allow_html=True,
                            )
                        with name_col:
                            with st.popover(p["name"], use_container_width=True):
                                reasons = p.get("reasons") or []
                                summary_text = (
                                    ", ".join(reasons).capitalize() + "."
                                    if reasons
                                    else "No AI clinical summary available for this patient."
                                )
                                st.markdown(f"**Clinical Summary:** {summary_text}")
                                new_ctas = st.selectbox(
                                    "New CTAS level",
                                    options=[1, 2, 3, 4, 5],
                                    index=p["ctas"] - 1,
                                    format_func=lambda x: f"{x} — {CTAS_SHORT_LABELS[x]}",
                                    key=f"ctas_select_{p['id']}",
                                    label_visibility="collapsed",
                                )
                                if st.button("Update CTAS", key=f"update_ctas_{p['id']}", use_container_width=True):
                                    update_ctas(p["id"], new_ctas)
                                    st.rerun()
                        st.markdown(
                            f"""<div class="patient-meta" style="margin:-4px 0 0 2px;">{p['age']}y · {p['sex']}{' · ' + p['complaint'] if p['complaint'] else ''}</div>""",
                            unsafe_allow_html=True,
                        )
                    with b:
                        st.markdown(
                            f"""<div style="text-align:right;">
                              <span class="ctas-label" style="background:{color}">CTAS {p['ctas']}</span><br>
                              <span class="wait-time">⏱ {wait_label}</span><br>
                              <span style="font-size:10px;color:var(--muted)">Pos. {idx + 1}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                    with c:
                        if st.button("✓", key=f"dismiss_{p['id']}", help="Mark as seen"):
                            dismiss(p["id"])
                            st.rerun()
                st.markdown("<hr style='margin:4px 0;border-color:var(--border);'>", unsafe_allow_html=True)

    render_er_column(col_er1, "ER1")
    render_er_column(col_er2, "ER2")

    st.markdown(
        """
        <div class="legend">
          <span style="font-size:11px;color:var(--muted);font-weight:700;">CTAS:</span>
          <span class="legend-item"><span class="dot" style="background:#C0392B"></span>1 Resuscitation</span>
          <span class="legend-item"><span class="dot" style="background:#E67E22"></span>2 Emergent</span>
          <span class="legend-item"><span class="dot" style="background:#D4AC0D"></span>3 Urgent</span>
          <span class="legend-item"><span class="dot" style="background:#27AE60"></span>4 Less Urgent</span>
          <span class="legend-item"><span class="dot" style="background:#2980B9"></span>5 Non-Urgent</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# Tab: Add Patient
# ─────────────────────────────────────────────────────────────
with tab_add:
    st.markdown('<div class="card-title">Add Patient to Queue</div>', unsafe_allow_html=True)
    with st.form("add_patient_form", clear_on_submit=True):
        name = st.text_input("Patient Name *", placeholder="e.g. Jane Smith")
        col_age, col_sex = st.columns(2)
        with col_age:
            age = st.number_input("Age *", min_value=0, max_value=120, value=None, placeholder="45")
        with col_sex:
            sex = st.selectbox("Sex *", ["Select…", "Male", "Female", "Other"])
        col_ctas, col_er = st.columns(2)
        with col_ctas:
            ctas_choice = st.selectbox(
                "CTAS Level *",
                ["Select…", "1 — Resuscitation", "2 — Emergent", "3 — Urgent", "4 — Less Urgent", "5 — Non-Urgent"],
            )
        with col_er:
            er_choice = st.selectbox("ER Location *", ["Select…", "ER1 — Regional", "ER2 — St. Joseph's"])
        complaint = st.text_input("Chief Complaint (optional)", placeholder="e.g. chest pain, shortness of breath")
        submitted = st.form_submit_button("➕ Add to Queue")

    if submitted:
        if not name.strip():
            st.error("❌ Please enter patient name.")
        elif age is None:
            st.error("❌ Please enter patient age.")
        elif sex == "Select…":
            st.error("❌ Please select sex.")
        elif ctas_choice == "Select…":
            st.error("❌ Please select CTAS level.")
        elif er_choice == "Select…":
            st.error("❌ Please select ER location.")
        else:
            ctas_level = int(ctas_choice.split(" — ")[0])
            er = er_choice.split(" — ")[0]
            add_to_queue(name.strip(), int(age), sex, ctas_level, er, complaint.strip())
            st.session_state.add_success = (
                f"✅ {name.strip()} added to {er} queue — Ticket #{st.session_state.counters[er]}"
            )
            st.rerun()

    if st.session_state.add_success:
        st.success(st.session_state.add_success)
        st.session_state.add_success = ""


# ─────────────────────────────────────────────────────────────
# Tab: Patient Ticket
# ─────────────────────────────────────────────────────────────
with tab_ticket:
    st.markdown('<div class="card-title">Look Up Patient Ticket</div>', unsafe_allow_html=True)

    if not st.session_state.queue:
        st.info("No patients currently in queue.")
    else:
        options = {"— Choose a patient —": None}
        for p in st.session_state.queue:
            options[f"#{p['ticket_num']} {p['name']} ({p['er']} · CTAS {p['ctas']})"] = p["id"]

        selected_label = st.selectbox("Select Patient", list(options.keys()))
        selected_id = options[selected_label]

        if selected_id:
            p = next(q for q in st.session_state.queue if q["id"] == selected_id)
            eq = er_queue(p["er"])
            pos = next(i for i, q in enumerate(eq) if q["id"] == p["id"]) + 1
            wait = calc_wait(p)
            wait_label = "You are next!" if wait == 0 else f"~{wait} minutes"
            color = CTAS_COLORS[p["ctas"]]
            arrival_str = p["arrival_time"].strftime("%I:%M %p").lstrip("0")
            er_full = "ER1 — Saint John Regional" if p["er"] == "ER1" else "ER2 — St. Joseph's Hospital"
            wait_color = "#27AE60" if wait == 0 else color

            st.markdown(
                f"""
                <div class="ticket-card">
                  <div class="ticket-top">🏥 Saint John ER Pre-Triage · Your Ticket</div>
                  <div class="ticket-number">#{p['ticket_num']}</div>
                  <div class="ticket-name">{p['name']}</div>
                  <div class="ticket-er">{er_full}</div>
                  <div class="ticket-ctas" style="background:{color}">{CTAS_LABELS[p['ctas']]}</div>
                  <hr class="ticket-divider">
                  <div class="ticket-info-row">
                    <span class="ticket-info-label">Queue Position</span>
                    <span class="ticket-info-val">{pos} of {len(eq)}</span>
                  </div>
                  <div class="ticket-info-row">
                    <span class="ticket-info-label">Estimated Wait</span>
                    <span class="ticket-info-val" style="color:{wait_color}">{wait_label}</span>
                  </div>
                  <div class="ticket-info-row">
                    <span class="ticket-info-label">Check-in Time</span>
                    <span class="ticket-info-val">{arrival_str}</span>
                  </div>
                  <div class="ticket-info-row">
                    <span class="ticket-info-label">Age / Sex</span>
                    <span class="ticket-info-val">{p['age']} y/o · {p['sex']}</span>
                  </div>
                  <hr class="ticket-divider">
                  <div style="font-size:11px;color:var(--muted);line-height:1.6;">
                    Please remain in the waiting area. Your position updates automatically as patients are seen.
                    Wait time is estimated based on Canadian CTAS target response times.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────
# Tab: Awaiting Approval
# ─────────────────────────────────────────────────────────────
@st.fragment(run_every="5s")
def render_pending_tab():
    st.markdown('<div class="card-title">Patient Form Submissions — Awaiting Staff Approval</div>', unsafe_allow_html=True)

    pending = load_pending()

    if not pending:
        st.markdown(
            '<div class="pending-empty">✅<br><strong>No pending submissions</strong><br>'
            'New patient self-check-ins will appear here for review.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<p style='font-size:13px;color:var(--muted);margin-bottom:16px;'>"
            f"{len(pending)} submission{'s' if len(pending) != 1 else ''} waiting for approval.</p>",
            unsafe_allow_html=True,
        )

        for p in pending:
            color = CTAS_COLORS[p["ctas"]]
            try:
                submitted_dt = datetime.fromisoformat(p["submitted_at"])
                time_ago = int((datetime.now() - submitted_dt).total_seconds() / 60)
                time_str = f"{time_ago}m ago" if time_ago < 60 else f"{time_ago // 60}h {time_ago % 60}m ago"
            except Exception:
                time_str = "just now"

            name_col, badge_col = st.columns([2, 5])
            with name_col:
                with st.popover(p["name"], use_container_width=True):
                    st.markdown(f"**{p['name']}** · {p['age']} y/o · {p['sex']}")
                    st.markdown(f"**Chief complaint:** {p['complaint'] or '—'}")
                    if p.get("history"):
                        st.markdown(f"**Medical history:** {p['history']}")
                    if p.get("reasons"):
                        st.markdown(f"**AI triage notes:** {', '.join(p['reasons']).capitalize()}")
                    st.markdown(f"**CTAS:** {p['ctas']} · {p['ctas_label']}")
                    st.markdown(f"**ER:** {p['er']} · **Est. wait:** {p['wait_minutes']} min")
            with badge_col:
                st.markdown(
                    f"""<div style="padding-top:9px;">
                      <span class="pending-badge" style="background:{color}">CTAS {p['ctas']} · {p['ctas_label']}</span>
                      <span class="pending-badge" style="background:var(--accent)">{p['er']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""<div class="pending-card" style="margin-top:-8px;">
                  <div class="p-meta">{p['age']} y/o · {p['sex']}</div>
                  <div class="p-complaint">"{p['complaint']}"</div>
                  <div class="pending-submitted-at">⏱ Submitted {time_str} · Est. wait {p['wait_minutes']} min</div>
                </div>""",
                unsafe_allow_html=True,
            )

            col_approve, col_reject, _ = st.columns([1, 1, 3])
            with col_approve:
                if st.button("✅ Approve", key=f"approve_{p['id']}"):
                    add_to_queue(
                        p["name"], p["age"], p["sex"],
                        p["ctas"], p["er"], p["complaint"],
                        reasons=p.get("reasons"),
                    )
                    remove_pending(p["id"])
                    st.session_state.add_success = (
                        f"✅ {p['name']} approved and added to {p['er']} queue — Ticket #{st.session_state.counters[p['er']]}"
                    )
                    st.rerun()
            with col_reject:
                if st.button("❌ Reject", key=f"reject_{p['id']}"):
                    remove_pending(p["id"])
                    st.rerun()

            st.markdown("<hr style='margin:4px 0 12px;border-color:var(--border);'>", unsafe_allow_html=True)


with tab_pending:
    render_pending_tab()

    if st.session_state.add_success:
        st.success(st.session_state.add_success)
        st.session_state.add_success = ""