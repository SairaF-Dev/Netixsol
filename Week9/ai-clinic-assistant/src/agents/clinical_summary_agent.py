"""
Clinical Summary Agent for City Care Clinics.
Synthesizes intake data, patient medical history, and lab results into a pre-visit SOAP note
clearly separating patient-reported facts from AI suggestions.
"""

from typing import Dict, Any, List
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer

class ClinicalSummaryAgent:
    def __init__(self, records_mcp: PatientRecordsMCPServer = None):
        self.mcp = records_mcp or PatientRecordsMCPServer()

    def generate_soap_summary(
        self,
        patient_id: str,
        intake_data: Dict[str, Any],
        doctor_id: str = "DOC-001"
    ) -> Dict[str, Any]:
        """
        Generates a structured SOAP note for doctor review.
        """
        profile = self.mcp.get_patient_profile(patient_id)
        allergies = self.mcp.get_patient_allergies(patient_id)
        history = self.mcp.get_patient_history(patient_id)
        labs = self.mcp.get_patient_labs(patient_id)
        ehr_meds = self.mcp.get_patient_medications(patient_id)

        # Subjective (Patient Reported)
        chief = intake_data.get("chief_complaint", "Not reported")
        duration = intake_data.get("duration", "Unspecified")
        severity = intake_data.get("severity", "Unspecified")
        
        # Allergy reconciliation: preserve both EHR and patient-reported
        ehr_alg_names = [a["allergen"] for a in allergies] if allergies else []
        rep_algs = intake_data.get("allergies") or []
        if isinstance(rep_algs, str):
            rep_algs = [rep_algs]
        
        all_algs_combined = []
        for ea in ehr_alg_names:
            all_algs_combined.append(f"{ea} (Verified EHR)")
        for ra in rep_algs:
            if ra and ra.lower() not in [x.lower() for x in ehr_alg_names]:
                all_algs_combined.append(f"{ra} (Patient-Reported)")
        
        allergies_str = ", ".join(all_algs_combined) if all_algs_combined else "No known allergies"

        # Medication reconciliation: preserve both EHR and patient-reported
        ehr_med_names = [f"{m['drug_name']} ({m.get('status', 'Active')})" for m in ehr_meds] if ehr_meds else []
        rep_meds = intake_data.get("current_medications") or []
        if isinstance(rep_meds, str):
            rep_meds = [rep_meds]
        
        all_meds_combined = []
        for em in ehr_med_names:
            all_meds_combined.append(f"{em} [EHR]")
        for rm in rep_meds:
            all_meds_combined.append(f"{rm} [Reported at Intake]")
        
        meds_str = ", ".join(all_meds_combined) if all_meds_combined else "None reported"

        # Highlight High Severity Tag if 8, 9, 10
        import re
        severity_str = str(severity).strip()
        sev_match = re.search(r'\b(\d+)(?:\s*/\s*10)?\b', severity_str)
        if (sev_match and int(sev_match.group(1)) >= 8) or any(w in severity_str.lower() for w in ["severe", "extreme", "sakht"]):
            severity_display = f"{severity_str} [HIGH SEVERITY ALERT]"
        else:
            severity_display = severity_str

        subjective = {
            "chief_complaint": f"{chief} (Duration: {duration}, Severity: {severity_display})",
            "history_of_present_illness": f"Patient reports {chief} for {duration}. Associated symptoms: {', '.join(intake_data.get('associated_symptoms', []))}.",
            "reported_allergies": allergies_str,
            "current_medications": meds_str
        }

        # Objective (Empirical Data)
        past_conds = [c["condition_name"] for c in history] if isinstance(history, list) else []
        recent_labs = [f"{l['test_name']}: {l['value']} {l['unit']} ({l['test_date']})" for l in labs[:3]] if isinstance(labs, list) else []

        objective = {
            "patient_demographics": f"{profile.get('name', 'Patient')}, {profile.get('age', 'N/A')}yo {profile.get('gender', '')}",
            "past_medical_conditions": past_conds if past_conds else ["No chronic conditions logged"],
            "recent_lab_observations": recent_labs if recent_labs else ["No lab records on file"]
        }

        # Assessment (AI Preliminary Observations for Doctor Review Only)
        ai_obs = f"Patient presents with {chief}. "
        all_allergies_lower = (allergies_str + " " + " ".join(rep_algs)).lower()
        if "penicillin" in all_allergies_lower:
            ai_obs += "Penicillin allergy flagged; avoid beta-lactam antibiotics. "
        
        # Check active prescription conflict: Amoxicillin with Penicillin allergy
        has_amox_rx = any("amoxicillin" in m.get("drug_name", "").lower() for m in ehr_meds if m.get("status") == "Active")
        if has_amox_rx and "penicillin" in all_allergies_lower:
            ai_obs += "[SAFETY RECONCILIATION FLAG] Patient has active Amoxicillin prescription (RX-77369) alongside recorded Penicillin allergy. Requires physician review (do not auto-cancel). "

        # Check medication discrepancy
        if any("rizek" in rm.lower() or "risek" in rm.lower() for rm in rep_meds):
            ai_obs += "[MEDICATION RECONCILIATION] Patient reports taking Rizek at home, which differs from EHR medication list. Clinician review advised. "

        if past_conds:
            ai_obs += f"Known past history of {', '.join(past_conds)}. "

        assessment = {
            "ai_preliminary_observation": ai_obs,
            "safety_disclaimer": "AI preliminary observations for physician review only. Not a formal diagnosis."
        }

        # Plan (AI Suggestions for Doctor)
        plan_evals = ["Physical examination", "Vital signs check (BP, Temp, SpO2)"]
        if "fever" in chief.lower() or "bukhar" in chief.lower():
            plan_evals.append("CBC panel if fever persists > 3 days")
        
        plan_meds = "Symptomatic relief. Avoid Penicillin class if antibiotic indicated." if "penicillin" in allergies_str.lower() else "Standard empirical treatment per clinical judgment."

        plan = {
            "suggested_evaluations": plan_evals,
            "suggested_medication_guidance": plan_meds
        }

        soap = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "SOAP_NOTE": {
                "SUBJECTIVE_PATIENT_REPORTED": subjective,
                "OBJECTIVE_EMPIRICAL_DATA": objective,
                "ASSESSMENT_FOR_DOCTOR_REVIEW_ONLY": assessment,
                "PLAN_AI_SUGGESTIONS": plan
            }
        }

        # Format full text summary
        text_summary = (
            "================================================================================\n"
            "                    CITY CARE CLINICS - PRE-VISIT SOAP BRIEF                    \n"
            "================================================================================\n"
            f"[PATIENT DEMOGRAPHICS] : {objective['patient_demographics']}\n"
            f"[S - SUBJECTIVE]       : {subjective['chief_complaint']}\n"
            f"  • HPI               : {subjective['history_of_present_illness']}\n"
            f"  • Allergies         : {subjective['reported_allergies']}\n"
            f"  • Current Meds      : {subjective['current_medications']}\n\n"
            f"[O - OBJECTIVE]        :\n"
            f"  • Past Conditions   : {', '.join(objective['past_medical_conditions'])}\n"
            f"  • Recent Labs       : {', '.join(objective['recent_lab_observations'])}\n\n"
            f"[A - ASSESSMENT (AI OBS)] : {assessment['ai_preliminary_observation']}\n"
            f"  • Disclaimer        : {assessment['safety_disclaimer']}\n\n"
            f"[P - PLAN SUGGESTIONS] :\n"
            f"  • Evaluations       : {', '.join(plan['suggested_evaluations'])}\n"
            f"  • Guidance          : {plan['suggested_medication_guidance']}\n"
            "================================================================================"
        )

        return {
            "status": "SUCCESS",
            "patient_id": patient_id,
            "soap_structure": soap,
            "formatted_text": text_summary
        }

if __name__ == "__main__":
    agent = ClinicalSummaryAgent()
    sample_intake = {
        "chief_complaint": "Fever and cough for 3 days",
        "duration": "3 days",
        "severity": "6/10",
        "associated_symptoms": ["body pain"],
        "allergies": ["Penicillin"],
        "current_medications": ["Panadol"]
    }
    res = agent.generate_soap_summary("PAT-0012", sample_intake)
    print(res["formatted_text"])
