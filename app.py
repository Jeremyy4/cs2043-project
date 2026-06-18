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


def field_label(text):
    st.markdown(
        f"<div class='field-label' style='color:#000000 !important;font-size:1rem;font-weight:800;margin:14px 0 8px;display:block;'>{text}</div>",
        unsafe_allow_html=True,
    )


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
    .stApp {
      background: var(--bg);
    }
    header[data-testid="stHeader"] {
      background: var(--accent);
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
    }
    .browser-banner code {
      background: #fff;
      border: 1px solid #FFD54F;
      border-radius: 6px;
      padding: 2px 6px;
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
    }
    .red-flags {
      list-style: none;
      padding-left: 0;
    }
    .red-flags li {
      font-size: 14px;
      padding: 6px 10px;
      background: #FFF0F0;
      border-left: 3px solid var(--red);
      border-radius: 0 6px 6px 0;
      margin-bottom: 6px;
    }
    .red-flags li::before { content: "🚩 "; }
    .helper-text {
      color: var(--muted);
      font-size: 0.92rem;
    }
    .field-label {
      color: #000000 !important;
      font-size: 1rem;
      font-weight: 800;
      margin: 14px 0 8px;
      display: block;
    }
    div[data-testid="stForm"] .field-label,
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
    div[data-testid="stWidgetLabel"] p,
    div[data-testid="stWidgetLabel"] span,
    div[data-baseweb="radio"] *,
    div[data-baseweb="slider"] * {
      color: #000000 !important;
    }
    div[data-baseweb="radio"] label,
    div[data-baseweb="radio"] span {
      color: #000000 !important;
      opacity: 1 !important;
      font-weight: 600;
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
    div[data-testid="stForm"] button[kind="formSubmit"],
    div[data-testid="stForm"] button[type="submit"] {
      background: #f7c6d0 !important;
      color: #000000 !important;
      border: 1px solid #e58ca3 !important;
      font-weight: 800 !important;
    }
    div[data-testid="stForm"] button[kind="formSubmit"]:hover,
    div[data-testid="stForm"] button[type="submit"]:hover {
      background: #f3b7c5 !important;
      color: #000000 !important;
      border: 1px solid #e58ca3 !important;
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

st.markdown(
    """
    <div class="browser-banner">
      <strong>Browser note:</strong>
      <span>This Streamlit app opens in your web browser, so the intake form and results feel like a normal browser app instead of a server dashboard.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.05, 0.95], gap="large")

with left_col:
    st.markdown(
        """
        <div class="card">
          <div class="card-title">CTAS Priority Scale</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="legend">
          <div class="legend-item"><span class="dot" style="background:#C0392B"></span> 1 · Resuscitation</div>
          <div class="legend-item"><span class="dot" style="background:#E67E22"></span> 2 · Emergent</div>
          <div class="legend-item"><span class="dot" style="background:#D4AC0D"></span> 3 · Urgent</div>
          <div class="legend-item"><span class="dot" style="background:#27AE60"></span> 4 · Less Urgent</div>
          <div class="legend-item"><span class="dot" style="background:#2980B9"></span> 5 · Non-Urgent</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    with st.form("patient_form"):
        st.markdown('<div class="card"><div class="card-title">Patient Information</div>', unsafe_allow_html=True)
        field_label("Full Name")
        name = st.text_input("Full Name", placeholder="e.g. Jane Smith", label_visibility="collapsed")
        field_label("Age")
        age = st.number_input("Age", min_value=0, max_value=120, value=30, label_visibility="collapsed")
        field_label("Gender")
        gender = st.selectbox("Gender", ["Select…", "Male", "Female", "Other"], label_visibility="collapsed")
        field_label("Pain Level")
        pain = st.slider("Pain Level", 1, 10, 5, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">Symptoms</div>', unsafe_allow_html=True)
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
        field_label("Medical History (optional)")
        history = st.text_area(
            "Medical History (optional)",
            placeholder="e.g. hypertension, diabetes, allergies…",
            height=90,
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">Visit Details</div>', unsafe_allow_html=True)
        field_label("Emergency Room")
        er_location = st.radio("Emergency Room", ["ER1", "ER2"], horizontal=True, label_visibility="collapsed")
        field_label("People Ahead in Queue")
        queue_size = st.number_input("People Ahead in Queue", min_value=0, value=6, label_visibility="collapsed")
        submitted = st.form_submit_button("Submit for CTAS Assessment")
        st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown(
        """
        <div class="card">
          <div class="card-title">Result</div>
        """,
        unsafe_allow_html=True,
    )

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
            triage_score, triage_label, reasons = assess_triage(
                age=age,
                pain=pain,
                fever=37.0,
                symptom_text=symptom,
                duration_hours=2.0 if "hour" in duration.lower() else 6.0,
                history=history,
                er_location=er_location,
            )
            wait_minutes = estimate_wait_time(triage_score, queue_size)

            badge_colors = {1: "#C0392B", 2: "#E67E22", 3: "#D4AC0D", 4: "#27AE60", 5: "#2980B9"}
            badge_icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "🔵"}

            st.markdown(
                f"""
                <div style="margin-bottom:6px;font-size:13px;font-weight:600;color:var(--text)">Patient: {name}, {age} y/o {gender}</div>
                <div class="ctas-badge" style="background:{badge_colors[triage_score]}">
                  <span style="font-size:32px">{badge_icons[triage_score]}</span>
                  <div>
                    CTAS {triage_score}
                    <small>{triage_label}</small>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="result-section">
                  <h4>Clinical Summary</h4>
                  <p>{', '.join(reasons).capitalize()}. Estimated wait time is about <strong>{wait_minutes} minutes</strong> for {er_location}.</p>
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
            symptom_lower = symptom.lower()
            if any(term in symptom_lower for term in ("chest pain", "shortness of breath", "bleeding", "stroke", "unconscious")):
                red_flags.append("High-risk symptom requires immediate clinician review.")
            if any(term in history.lower() for term in ("heart", "diabetes", "asthma")):
                red_flags.append("Medical history may increase triage urgency.")
            if not red_flags:
                red_flags.append("No major red flags were detected in this demo review.")

            st.markdown(
                "<ul class='red-flags'>" + "".join(f"<li>{flag}</li>" for flag in red_flags) + "</ul>",
                unsafe_allow_html=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <p class="helper-text">Fill out the form on the left and submit to generate a CTAS-style result card, red flags, and a queue estimate.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
