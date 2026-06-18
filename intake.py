"""
intake.py — QR Access and Intake Component
Saint John ER Pre-Triage System
Independent of AI triage and queue management.
"""

import uuid
import hashlib
from datetime import datetime

VALID_ER_LOCATIONS = ["ER1", "ER2"]
VALID_SEX_OPTIONS  = ["Male", "Female", "Other", "Prefer not to say"]

# Simulated on-site QR tokens (in production: server-generated, rotated daily)
QR_TOKENS = {
    "ER1": hashlib.sha256(b"SJRH-ER1-ONSITE").hexdigest(),
    "ER2": hashlib.sha256(b"SJRH-ER2-ONSITE").hexdigest(),
}

def _generate_patient_id(er_location: str) -> str:
    year   = datetime.now().year
    suffix = str(uuid.uuid4().int)[:4].zfill(4)
    return f"{er_location}-{year}-{suffix}"

def validate_qr(token: str, er_location: str) -> dict:
    if er_location not in VALID_ER_LOCATIONS:
        return {"valid": False, "message": f"Unknown ER '{er_location}'."}
    if token != QR_TOKENS[er_location]:
        return {"valid": False, "message": "QR code invalid or not scanned on-site."}
    return {"valid": True, "message": f"On-site QR validation passed for {er_location}."}

def select_er(er_location: str) -> dict:
    if er_location not in VALID_ER_LOCATIONS:
        return {"success": False, "er_location": None,
                "message": f"'{er_location}' is invalid. Choose ER1 or ER2."}
    return {"success": True, "er_location": er_location,
            "message": f"ER location confirmed: {er_location}."}

def submit_form(er_location, name, age, sex, chief_symptom,
                pain_level, symptom_duration, medical_history="") -> dict:
    errors = []
    if not name or not name.strip():
        errors.append("Name is required.")
    if not isinstance(age,int) or not(0<=age<=130):
        errors.append("Age must be 0–130.")
    if sex not in VALID_SEX_OPTIONS:
        errors.append("Invalid sex option.")
    if not chief_symptom or not chief_symptom.strip():
        errors.append("Chief symptom required.")
    if not isinstance(pain_level,int) or not(1<=pain_level<=10):
        errors.append("Pain level must be 1–10.")
    if not symptom_duration or not symptom_duration.strip():
        errors.append("Symptom duration required.")
    if er_location not in VALID_ER_LOCATIONS:
        errors.append("Invalid ER location.")

    if errors:
        return {"success": False, "patient_record": None, "errors": errors}

    return {
        "success": True,
        "patient_record": {
            "patient_id":       _generate_patient_id(er_location),
            "er_location":      er_location,
            "name":             name.strip(),
            "age":              age,
            "sex":              sex,
            "chief_symptom":    chief_symptom.strip(),
            "pain_level":       pain_level,
            "symptom_duration": symptom_duration.strip(),
            "medical_history":  medical_history.strip() or "None reported",
            "submitted_at":     datetime.now().isoformat(),
            "locked":           True
        },
        "errors": []
    }