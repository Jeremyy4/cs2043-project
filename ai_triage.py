"""
ai_triage.py
------------
AI Triage Component for the Saint John ER Pre-Triage System.

Responsibilities:
    - build_prompt   : Formats the patient record into a structured AI prompt.
    - call_api       : Sends the prompt to Claude and returns the raw response.
    - parse_report   : Parses the JSON response into a structured triage report.
    - confirm_level  : Allows a doctor/nurse to confirm or adjust the AI's CTAS level.

CTAS Levels:
    1 - Resuscitation  : Immediate (life-threatening)
    2 - Emergent       : Within 15 minutes
    3 - Urgent         : Within 30 minutes
    4 - Less Urgent    : Within 60 minutes
    5 - Non-Urgent     : Within 120 minutes
"""

import json
import os
from datetime import datetime
from typing import Optional

# anthropic is optional for local quick-testing; handle missing package gracefully
try:
    import anthropic
except ImportError:  # pragma: no cover - optional dependency
    anthropic = None

# ─────────────────────────────────────────────
# Anthropic client (reads ANTHROPIC_API_KEY from environment)
# Create client if the anthropic package is available and an API key is present.
# Otherwise, leave `client` as None and fall back to a lightweight local heuristic
# for quick testing.
# ─────────────────────────────────────────────
client = None
if anthropic is not None and os.environ.get("ANTHROPIC_API_KEY"):
    try:
        # Newer anthropic clients may expose different constructors; try common one.
        client = getattr(anthropic, "Anthropic", None) or getattr(anthropic, "Client", None)
        if callable(client):
            client = client()
        else:
            client = None
    except Exception as e:
        # SDK construction can fail in version-dependent ways (auth, config, etc.)
        # Broad catch is intentional here so a bad client setup never crashes the app —
        # but we log it instead of silently swallowing it.
        print(f"[WARN] Could not initialize Anthropic client: {e}")
        client = None

# ─────────────────────────────────────────────
# System prompt — instructs Claude to act as a CTAS triage assistant
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are a Canadian Triage and Acuity Scale (CTAS) triage assistant for an emergency department in Saint John, New Brunswick, Canada.

Your job is to analyze patient intake data and assign the most appropriate CTAS priority level.

CTAS LEVEL DEFINITIONS:
- Level 1 (Resuscitation) : Life-threatening condition requiring immediate intervention.
  Examples: cardiac arrest, severe respiratory failure, uncontrolled hemorrhage.

- Level 2 (Emergent)      : Potentially life-threatening; must be seen within 15 minutes.
  Examples: chest pain with cardiac history, stroke symptoms, severe pain (8–10/10).

- Level 3 (Urgent)        : Potentially serious; must be seen within 30 minutes.
  Examples: moderate pain, persistent vomiting, mild shortness of breath.

- Level 4 (Less Urgent)   : Conditions that could worsen without care; seen within 60 minutes.
  Examples: minor lacerations, mild pain, urinary symptoms, minor infections.

- Level 5 (Non-Urgent)    : Non-urgent conditions; can wait up to 120 minutes or be redirected
  to a walk-in clinic. Examples: routine prescription refill, mild cold symptoms.

RULES:
- Always err on the side of caution. When in doubt between two levels, assign the higher urgency.
- Consider the patient's age and medical history when assigning a level.
- You MUST respond ONLY with a valid JSON object — no preamble, no markdown, no explanation outside the JSON.

REQUIRED JSON FORMAT:
{
  "ctas_level": <integer 1–5>,
  "clinical_summary": "<one clear paragraph explaining your reasoning>",
  "red_flags": ["<flag1>", "<flag2>"]
}

If there are no red flags, return an empty list: "red_flags": []
"""


# ─────────────────────────────────────────────
# build_prompt
# ─────────────────────────────────────────────
def build_prompt(patient_record: dict) -> str:
    """
    Formats a patient record dictionary into a structured user message for the AI.

    Args:
        patient_record (dict): The locked patient intake record from session state.

    Returns:
        str: A formatted prompt string ready to send to Claude.
    """
    return f"""Please assess the following patient and assign a CTAS level.

--- PATIENT INTAKE ---
Patient ID      : {patient_record.get("patient_id", "N/A")}
ER Location     : {patient_record.get("er_location", "N/A")}
Name            : {patient_record.get("name", "Unknown")}
Age             : {patient_record.get("age", "Unknown")}
Sex             : {patient_record.get("sex", "Unknown")}
Chief Symptom   : {patient_record.get("chief_symptom", "Not provided")}
Pain Level      : {patient_record.get("pain_level", "Not provided")} / 10
Symptom Duration: {patient_record.get("symptom_duration", "Not provided")}
Medical History : {patient_record.get("medical_history", "None reported")}
----------------------

Respond with only the JSON object described in your instructions."""


# ─────────────────────────────────────────────
# call_api
# ─────────────────────────────────────────────
def call_api(patient_record: dict) -> Optional[dict]:
    """
    Sends the patient record to the Claude API and returns a parsed triage report.

    Args:
        patient_record (dict): The locked patient intake record.

    Returns:
        dict | None: A triage report dict on success, or None if the call fails.
    """
    # If no client or no API key, use a safe local heuristic for quick testing.
    if client is None or not os.environ.get("ANTHROPIC_API_KEY"):
        print("[WARN] Anthropic client not available or ANTHROPIC_API_KEY not set — using local heuristic for quick testing.")

        # Simple heuristic to produce a plausible CTAS suggestion as JSON.
        chief = str(patient_record.get("chief_symptom", "")).lower()
        pain = patient_record.get("pain_level") or 0
        try:
            age = int(patient_record.get("age") or 0)
        except (ValueError, TypeError):
            age = 0

        # Basic rules (not clinical advice) for generating a quick mock response:
        if any(k in chief for k in ["cardiac", "no breathing", "not breathing", "unconscious", "collapse"]):
            ctas = 1
            red_flags = ["life-threatening presentation"]
        elif any(k in chief for k in ["stroke", "slurred", "face droop", "weakness on one side"]):
            ctas = 2
            red_flags = ["possible stroke"]
        elif "chest" in chief or pain >= 8:
            ctas = 2
            red_flags = ["severe chest pain"]
        elif pain >= 6 or age >= 75:
            ctas = 3
            red_flags = []
        elif pain >= 3:
            ctas = 4
            red_flags = []
        else:
            ctas = 5
            red_flags = []

        mock_response = {
            "ctas_level": ctas,
            "clinical_summary": f"Heuristic: chief symptom '{patient_record.get('chief_symptom', 'N/A')}', pain {pain}, age {age}.",
            "red_flags": red_flags,
        }

        return parse_report(json.dumps(mock_response), patient_record.get("patient_id", "UNKNOWN"))

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[  # type: ignore
                {
                    "role": "user",
                    "content": build_prompt(patient_record)
                }
            ]
        )

        # Robust extraction of the text portion from the response object/dict.
        raw_response = None
        try:
            content = getattr(message, "content", None)
            if isinstance(content, list) and len(content) > 0:
                first = content[0]
                # anthropic SDK sometimes wraps text in .text
                raw_response = getattr(first, "text", None) or (first.get("text") if isinstance(first, dict) else None)
            elif isinstance(content, str):
                raw_response = content
        except (AttributeError, KeyError, TypeError):
            raw_response = None

        if not raw_response:
            # Fallback to stringifying the whole response
            raw_response = str(message)

        raw_response = raw_response.strip()
        return parse_report(raw_response, patient_record.get("patient_id", "UNKNOWN"))

    except anthropic.APIConnectionError:
        print("[ERROR] Could not connect to the Anthropic API. Check your internet connection.")
        return None

    except anthropic.AuthenticationError:
        print("[ERROR] Invalid API key. Check your ANTHROPIC_API_KEY environment variable.")
        return None

    except anthropic.RateLimitError:
        print("[ERROR] Rate limit reached. Please wait before retrying.")
        return None

    except anthropic.APIStatusError as ase:
        print(f"[ERROR] API returned status {ase.status_code}: {ase.message}")
        return None

    except Exception as e:
        # Last-resort safety net after all known Anthropic exceptions above —
        # intentionally broad so an unexpected SDK/runtime error never crashes
        # patient intake. Always logged, never silently swallowed.
        print(f"[ERROR] Unexpected error during API call: {e}")
        return None


# ─────────────────────────────────────────────
# parse_report
# ─────────────────────────────────────────────
def parse_report(raw_response: str, patient_id: str) -> Optional[dict]:
    """
    Parses the Claude JSON response into a structured triage report object.

    Args:
        raw_response (str): The raw text returned by the Claude API.
        patient_id   (str): The patient ID to attach to the report.

    Returns:
        dict | None: A structured triage report on success, or None if parsing fails.
    """
    try:
        parsed = json.loads(raw_response)

        ctas_level = int(parsed.get("ctas_level"))
        if ctas_level not in range(1, 6):
            raise ValueError(f"CTAS level out of range: {ctas_level}")

        triage_report = {
            "patient_id":          patient_id,
            "ai_ctas_level":       ctas_level,
            "ai_clinical_summary": parsed.get("clinical_summary", "").strip(),
            "ai_red_flags":        parsed.get("red_flags", []),
            # Fields to be filled in by the doctor at confirm_level step
            "confirmed_ctas_level": None,
            "doctor_note":          None,
            "confirmed_by":         None,
            "confirmed_at":         None,
        }

        return triage_report

    except json.JSONDecodeError as e:
        print(f"[ERROR] Could not parse AI response as JSON: {e}")
        print(f"[DEBUG] Raw response was: {raw_response}")
        return None

    except (KeyError, ValueError, TypeError) as e:
        print(f"[ERROR] Unexpected structure in AI response: {e}")
        return None


# ─────────────────────────────────────────────
# confirm_level
# ─────────────────────────────────────────────
def confirm_level(
        triage_report: dict,
        confirmed_by: str,
        confirmed_level: Optional[int] = None,
        doctor_note: str = ""
) -> dict:
    """
    Allows a doctor or nurse to confirm or adjust the AI-assigned CTAS level.

    The original AI level is always preserved in ai_ctas_level for audit purposes.
    The confirmed level is stored separately in confirmed_ctas_level.

    Args:
        triage_report   (dict)         : The triage report produced by parse_report.
        confirmed_by    (str)          : Name of the doctor or nurse confirming.
        confirmed_level (int, optional): Override level (1–5). If None, AI level is accepted.
        doctor_note     (str)          : Optional clinical note from the doctor.

    Returns:
        dict: The updated triage report with confirmation details filled in.

    Raises:
        ValueError: If the confirmed CTAS level is outside the 1–5 range.
    """
    if confirmed_level is None:
        confirmed_level = triage_report["ai_ctas_level"]

    if confirmed_level not in range(1, 6):
        raise ValueError(f"Invalid CTAS level: {confirmed_level}. Must be between 1 and 5.")

    triage_report["confirmed_ctas_level"] = confirmed_level
    triage_report["confirmed_by"]         = confirmed_by
    triage_report["doctor_note"]          = doctor_note.strip()
    triage_report["confirmed_at"]         = datetime.now().isoformat()

    return triage_report


# ─────────────────────────────────────────────
# Quick test — run this file directly to verify
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Sample patient record matching the data design from the project document
    sample_patient = {
        "patient_id":        "ER1-2026-0042",
        "er_location":       "ER1",
        "name":              "John Smith",
        "age":               54,
        "sex":               "Male",
        "chief_symptom":     "Chest pain radiating to left arm",
        "pain_level":        8,
        "symptom_duration":  "45 minutes",
        "medical_history":   "Hypertension, Type 2 diabetes",
        "submitted_at":      "2026-06-05T10:23:14",
        "locked":            True
    }

    print("─── Sending patient to AI triage agent ───")
    report = call_api(sample_patient)

    if report:
        print("\n─── AI Triage Report ───")
        print(json.dumps(report, indent=2))

        # Simulate doctor confirming the level
        confirmed = confirm_level(
            triage_report=report,
            confirmed_by="Dr. A. Lee",
            confirmed_level=None,   # None = accept AI level
            doctor_note="Confirmed. ECG ordered immediately."
        )

        print("\n─── After Doctor Confirmation ───")
        print(json.dumps(confirmed, indent=2))
    else:
        print("\n[FAILED] Triage report could not be generated.")