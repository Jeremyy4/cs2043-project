import re

import streamlit as st


st.set_page_config(
    page_title="Saint John ER Pre-Triage",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def assess_triage(age, pain, fever, symptom_text, duration_hours, history, er_location):
    score = 5
    reasons = []
    symptom_text = symptom_text.lower()
    history = history.lower()

    if any(term in symptom_text for term in ("chest pain", "shortness of breath", "trouble breathing", "stroke", "unconscious")):
        score = min(score, 2)
        reasons.append("high-risk symptom pattern")
    if any(term in symptom_text for term in ("severe", "bleeding", "trauma", "broken", "fracture")):
        score = min(score, 2)
        reasons.append("acute injury or bleeding concern")
    if fever >= 39 or pain >= 8:
        score = min(score, 3)
        reasons.append("high symptom severity")
    elif fever >= 38 or pain >= 6:
        score = min(score, 4)
        reasons.append("moderate symptom severity")
    if age >= 75 and score > 3:
        score = 3
        reasons.append("older adult risk")
    if "diabetes" in history or "heart" in history or "asthma" in history:
        score = min(score, 4)
        reasons.append("relevant medical history")
    if duration_hours <= 2 and score > 2:
        score = 3
        reasons.append("recent onset")

    if er_location == "ER1":
        reasons.append("assigned to ER1")
    else:
        reasons.append("assigned to ER2")

    label = {
        1: "Resuscitation",
        2: "Emergent",
        3: "Urgent",
        4: "Less Urgent",
        5: "Non-Urgent",
    }[score]

    if not reasons:
        reasons = ["stable presentation"]

    return score, label, reasons


def estimate_wait_time(priority, people_ahead):
    base_by_priority = {1: 10, 2: 20, 3: 35, 4: 55, 5: 75}
    return base_by_priority[priority] + people_ahead * 12


def parse_duration_hours(duration_text):
    text = duration_text.lower().strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|h)\b", text)
    if match:
        return max(0.0, float(match.group(1)))
    if "day" in text:
        return 24.0
    if "minute" in text or "min" in text:
        return 1.0
    return 6.0


def field_label(text):
    st.markdown(
        f"<div class='field-label' style='color:#000000 !important;font-size:13px;font-weight:600;margin:0 0 6px;display:block;'>{text}</div>",
        unsafe_allow_html=True,
    )


def reset_patient():
    st.session_state["submitted_result"] = None
    st.session_state["submitted_name"] = ""
    st.session_state["submitted_age"] = 30
    st.session_state["submitted_gender"] = ""
    st.session_state["submitted_pain"] = 5
    st.session_state["submitted_symptom"] = ""
    st.session_state["submitted_duration"] = ""
    st.session_state["submitted_history"] = ""
    st.session_state["submitted_er"] = "ER1"
    st.session_state["submitted_queue"] = 6


if "submitted_result" not in st.session_state:
    reset_patient()


st.markdown(
    """
    <style>
    :root {
      --red: #C0392B;
      --red-dark: #8B1E1E;
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
    .stApp {
      background: var(--bg);
    }
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
      display: none;
    }
    .block-container {
      max-width: 560px !important;
      padding-top: 2rem;
      padding-bottom: 2.5rem;
    }
    .hero-header {
      background: var(--accent);
      color: white;
      padding: 20px 24px 16px;
      display: flex;
      align-items: center;
      gap: 14px;
      border-radius: 0 0 14px 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,.18);
      margin-bottom: 18px;
    }
    .cross {
      width: 38px;
      height: 38px;
      background: white;
      border-radius: 6px;
      display: grid;
      place-items: center;
      flex-shrink: 0;
      font-size: 22px;
    }
    .hero-title {
      font-size: 18px;
      font-weight: 700;
      line-height: 1.2;
      margin: 0;
    }
    .hero-subtitle {
      font-size: 12px;
      opacity: .78;
      margin-top: 2px;
    }
    .browser-banner {
      background: #FFF8E1;
      border-bottom: 2px solid #FFD54F;
      padding: 12px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin: 0 0 18px;
      border-radius: 10px;
      color: #000000;
    }
    .browser-banner code {
      background: #fff;
      border: 1px solid #FFD54F;
      border-radius: 6px;
      padding: 2px 6px;
      color: #000000;
    }
    .browser-banner strong,
    .browser-banner span {
      color: #000000;
    }
    .card {
      background: var(--card);
      border-radius: var(--radius);
      border: 1px solid var(--border);
      padding: 24px 20px;
      margin-bottom: 16px;
      box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    .card-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
      margin-bottom: 18px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }
    .legend {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 6px;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: var(--muted);
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .ctas-badge {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      border-radius: 8px;
      padding: 10px 18px;
      font-weight: 700;
      font-size: 22px;
      margin-bottom: 16px;
      color: white;
    }
    .ctas-badge small {
      font-size: 13px;
      font-weight: 600;
      display: block;
      opacity: .9;
    }
    .result-section { margin-top: 16px; }
    .result-section h4 {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .result-section p {
      font-size: 14px;
      line-height: 1.6;
      color: #000000;
    }
    .result-section p,
    .result-section strong,
    .result-section em,
    .result-section span {
      color: #000000 !important;
    }
    .red-flags {
      list-style: none;
      padding-left: 0;
    }
    .red-flags li {
      font-size: 14px;
      padding: 6px 10px;
      background: #FFF5F5;
      border-left: 3px solid var(--red-dark);
      color: var(--red-dark);
      border-radius: 0 6px 6px 0;
      margin-bottom: 6px;
    }
    .red-flags li::before {
      content: "🚩 ";
      color: var(--red-dark);
    }
    .helper-text {
      color: var(--muted);
      font-size: 0.92rem;
    }
    .field-label {
      color: #000000 !important;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
      display: block;
    }
    .stTextInput label,
    .stNumberInput label,
    .stSelectbox label,
    .stTextArea label,
    .stRadio label,
    .stSlider label {
      color: #000000 !important;
      opacity: 1 !important;
    }
    div[data-testid="stForm"] label,
    div[data-testid="stForm"] p,
    div[data-testid="stForm"] span {
      color: #000000 !important;
      opacity: 1 !important;
    }
    div[data-baseweb="input"] input,
    div[data-baseweb="select"] > div,
    textarea,
    input {
      background: #ffffff !important;
      color: #000000 !important;
      -webkit-text-fill-color: #000000 !important;
    }
    div[data-baseweb="input"] input::placeholder,
    textarea::placeholder {
      color: #666666 !important;
      opacity: 1;
    }
    div[data-baseweb="select"] * {
      color: #000000 !important;
    }
    div[data-baseweb="radio"] label,
    div[data-baseweb="radio"] span {
      color: #000000 !important;
      opacity: 1 !important;
      font-weight: 600;
    }
    div[data-baseweb="radio"] *,
    div[data-baseweb="slider"] * {
      color: #000000 !important;
    }
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stForm"] button[kind="formSubmit"],
    div[data-testid="stForm"] button[type="submit"] {
      background: var(--red) !important;
      color: #ffffff !important;
      -webkit-text-fill-color: #ffffff !important;
      border: 1px solid var(--red) !important;
      font-weight: 800 !important;
      border-radius: 10px !important;
      padding: 0.9rem 1rem !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stForm"] button[kind="formSubmit"]:hover,
    div[data-testid="stForm"] button[type="submit"]:hover {
      background: #A93226 !important;
      color: #ffffff !important;
      -webkit-text-fill-color: #ffffff !important;
      border: 1px solid #A93226 !important;
    }
    div[data-testid="stFormSubmitButton"] button *,
    div[data-testid="stForm"] button[kind="formSubmit"] *,
    div[data-testid="stForm"] button[type="submit"] * {
      color: #ffffff !important;
      -webkit-text-fill-color: #ffffff !important;
    }
    div[data-testid="stFormSubmitButton"] button p,
    div[data-testid="stFormSubmitButton"] button span,
    div[data-testid="stFormSubmitButton"] button div,
    div[data-testid="stFormSubmitButton"] button svg {
      color: #ffffff !important;
      fill: #ffffff !important;
      -webkit-text-fill-color: #ffffff !important;
    }
    div[data-testid="stForm"] button[kind="secondary"] {
      border-radius: 10px !important;
      border: 2px solid var(--accent) !important;
      color: var(--accent) !important;
      background: transparent !important;
      font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-header">
      <div class="cross">🏥</div>
      <div>
        <div class="hero-title">Saint John ER Pre-Triage</div>
        <div class="hero-subtitle">AI-assisted CTAS assessment · For demonstration only</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container():
    st.markdown(
        """
        <div class="browser-banner">
          <strong>Browser note:</strong>
          <span>This Streamlit app opens in your web browser, so the intake form and results feel like a normal browser app instead of a server dashboard.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card" style="padding:14px 20px;">
          <div style="font-size:12px;font-weight:700;color:var(--muted);margin-bottom:8px;">CTAS PRIORITY SCALE</div>
          <div class="legend">
            <div class="legend-item"><div class="dot" style="background:#C0392B"></div> 1 · Resuscitation</div>
            <div class="legend-item"><div class="dot" style="background:#E67E22"></div> 2 · Emergent</div>
            <div class="legend-item"><div class="dot" style="background:#D4AC0D"></div> 3 · Urgent</div>
            <div class="legend-item"><div class="dot" style="background:#27AE60"></div> 4 · Less Urgent</div>
            <div class="legend-item"><div class="dot" style="background:#2980B9"></div> 5 · Non-Urgent</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state["submitted_result"] is None:
        with st.form("patient_form"):
            st.markdown('<div class="card-title">Patient Information</div>', unsafe_allow_html=True)
            field_label("Full Name")
            name = st.text_input("Full Name", placeholder="e.g. Jane Smith", label_visibility="collapsed")

            col_age, col_gender = st.columns(2)
            with col_age:
                field_label("Age")
                age = st.number_input("Age", min_value=0, max_value=120, value=30, label_visibility="collapsed")
            with col_gender:
                field_label("Gender")
                gender = st.selectbox("Gender", ["Select…", "Male", "Female", "Other"], label_visibility="collapsed")

            field_label("Pain Level")
            pain = st.slider("Pain Level", 1, 10, 5, label_visibility="collapsed")

            st.markdown('<div class="card-title" style="margin-top:20px;">Symptoms</div>', unsafe_allow_html=True)
            field_label("Chief Complaint")
            symptom = st.text_area(
                "Chief Complaint",
                placeholder="Describe the main symptom or reason for visit…",
                label_visibility="collapsed",
            )
            field_label("Duration")
            duration = st.text_input(
                "Duration",
                placeholder="e.g. 2 hours, since yesterday morning",
                label_visibility="collapsed",
            )
            field_label("Medical History")
            history = st.text_area(
                "Medical History",
                placeholder="e.g. hypertension, diabetes, allergies…",
                height=70,
                label_visibility="collapsed",
            )

            st.markdown('<div class="card-title" style="margin-top:20px;">Visit Details</div>', unsafe_allow_html=True)
            field_label("Emergency Room")
            er_location = st.radio("Emergency Room", ["ER1", "ER2"], horizontal=True, label_visibility="collapsed")
            submitted = st.form_submit_button("🤖 Submit for CTAS Assessment")

        if submitted:
            if gender == "Select…":
                st.error("Please select gender before submitting.")
            elif not name.strip():
                st.error("Please enter the patient name before submitting.")
            elif not symptom.strip():
                st.error("Please describe the chief complaint before submitting.")
            elif not duration.strip():
                st.error("Please enter symptom duration before submitting.")
            else:
                duration_hours = parse_duration_hours(duration)
                triage_score, triage_label, reasons = assess_triage(
                    age=age,
                    pain=pain,
                    fever=37.0,
                    symptom_text=symptom,
                    duration_hours=duration_hours,
                    history=history,
                    er_location=er_location,
                )
                wait_minutes = estimate_wait_time(triage_score, 0)

                st.session_state["submitted_result"] = {
                    "name": name,
                    "age": age,
                    "gender": gender,
                    "er_location": er_location,
                    "triage_score": triage_score,
                    "triage_label": triage_label,
                    "reasons": reasons,
                    "wait_minutes": wait_minutes,
                    "symptom": symptom,
                    "history": history,
                }
                st.rerun()
        else:
            st.markdown(
                """
                <p class="helper-text">Fill out the form and submit to generate a CTAS-style result card, red flags, and a queue estimate.</p>
                """,
                unsafe_allow_html=True,
            )

    else:
        result = st.session_state["submitted_result"]
        badge_colors = {1: "#C0392B", 2: "#E67E22", 3: "#D4AC0D", 4: "#27AE60", 5: "#2980B9"}
        badge_icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}

        st.markdown(
            f"""
            <div style="margin-bottom:6px;font-size:13px;font-weight:600;color:var(--muted)">Patient: {result['name']}, {result['age']} y/o {result['gender']}</div>
            <div class="ctas-badge" style="background:{badge_colors[result['triage_score']]}">
              <span style="font-size:32px">{badge_icons[result['triage_score']]}</span>
              <div>
                CTAS {result['triage_score']}
                <small>{result['triage_label']}</small>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-section">
              <h4>Clinical Summary</h4>
              <p>{', '.join(result['reasons']).capitalize()}. Estimated wait time is about <strong>{result['wait_minutes']} minutes</strong> for {result['er_location']}.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="result-section">
              <h4>Red Flags</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        red_flags = []
        symptom_lower = result["symptom"].lower()
        if any(term in symptom_lower for term in ("chest pain", "shortness of breath", "bleeding", "stroke", "unconscious")):
            red_flags.append("High-risk symptom requires immediate clinician review.")
        if any(term in result["history"].lower() for term in ("heart", "diabetes", "asthma")):
            red_flags.append("Medical history may increase triage urgency.")
        if not red_flags:
            red_flags.append("No major red flags were detected in this demo review.")

        st.markdown(
            "<ul class='red-flags'>" + "".join(f"<li>{flag}</li>" for flag in red_flags) + "</ul>",
            unsafe_allow_html=True,
        )

        if st.button("← New Patient Check-In"):
            reset_patient()
            st.rerun()
