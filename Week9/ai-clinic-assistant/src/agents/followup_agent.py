"""
Follow-up Agent for City Care Clinics.
Creates post-visit reminder plans (medications & lab test dates), generates proactive UrduLish
check-in messages, and evaluates patient feedback to trigger escalation for worsening symptoms.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.mcp_servers.notifications_server import NotificationsMCPServer

class FollowupAgent:
    def __init__(self, notifications_mcp: NotificationsMCPServer = None):
        self.notif_mcp = notifications_mcp or NotificationsMCPServer()

    def create_reminder_plan(
        self,
        appointment_id: str,
        patient_name: str,
        medications: List[Dict[str, Any]],
        follow_up_days: int = 14
    ) -> Dict[str, Any]:
        """
        Creates an automated schedule for medication reminders and follow-up consultation dates.
        """
        reminders = []
        
        # Schedule daily medication reminders
        for med in medications:
            drug = med.get("drug_name", "Medication")
            freq = med.get("frequency_per_day", 2)
            
            reminders.append({
                "type": "Medication Reminder",
                "timing": "09:00 AM (Morning)",
                "message": f"Assalam-o-Alaikum {patient_name}! Dawai ka waqt: {drug} (1 tablet after breakfast)."
            })
            if freq >= 2:
                reminders.append({
                    "type": "Medication Reminder",
                    "timing": "09:00 PM (Evening)",
                    "message": f"Assalam-o-Alaikum {patient_name}! Dawai ka waqt: {drug} (1 tablet after dinner)."
                })

        # Schedule follow-up visit reminder
        follow_up_date = (datetime.now() + timedelta(days=follow_up_days)).strftime("%Y-%m-%d")
        reminders.append({
            "type": "Follow-up Consultation Reminder",
            "date": follow_up_date,
            "message": f"Assalam-o-Alaikum {patient_name}! Aap ki {follow_up_days}-day follow-up consultation due hai ({follow_up_date})."
        })

        # Register task in notifications MCP & dispatch email summary
        self.notif_mcp.schedule_reminder(appointment_id)
        email_res = self.notif_mcp.send_email_confirmation(
            email=f"{patient_name.lower().replace(' ', '.')}@patient.clinic.pk",
            subject=f"Post-Visit Care & Medication Plan - {appointment_id}",
            body_text=f"Dear {patient_name}, your post-visit care plan and medication reminders have been created. Next follow-up is due on {follow_up_date}."
        )

        return {
            "appointment_id": appointment_id,
            "patient_name": patient_name,
            "total_reminders_enqueued": len(reminders),
            "email_status": email_res.get("status"),
            "reminder_plan": reminders
        }

    def generate_checkin_message(self, patient_name: str, doctor_name: str, days_post_visit: int = 2) -> str:
        """
        Generates a proactive UrduLish check-in message.
        """
        return (
            f"Assalam-o-Alaikum {patient_name} sahib! Main City Care Clinics se aap ki AI assistant baat kar rahi hoon. "
            f"{days_post_visit} din pehle aap ka checkup {doctor_name} ke paas tha. "
            f"Umeed hai aap dawai time par le rahe hain. Ab aap ki tabiyat kaisi hai?"
        )

    def evaluate_patient_feedback(self, feedback_text: str) -> Dict[str, Any]:
        """
        Evaluates patient check-in response.
        If patient reports worsening symptoms, sets needs_escalation = True.
        """
        fb_lower = feedback_text.lower()

        worsening_keywords = ["kharab", "worse", "ziada", "vomiting", "ulti", "chakkar", "side effect", "sakht", "rehna hai", "dard badh"]
        recovering_keywords = ["theek", "better", "aaram", "improving", "fine", "alhamdulillah", "good", "shukriya"]

        if any(w in fb_lower for w in worsening_keywords) and not any(w in fb_lower for w in recovering_keywords):
            return {
                "status": "WORSENING",
                "needs_escalation": True,
                "urgency": "Urgent",
                "escalation_message": (
                    "⚠️ PATIENT ALERT: Patient reports worsening symptoms post-visit. "
                    "Routing to Triage / Clinical Nurse for immediate phone follow-up."
                ),
                "urdulish_reply": "Aap ki tabiyat sun kar pareshani hui. Main ne aap ki report clinic nurse aur doctor ko alert kar di hai, wo jald aap se rabta karenge."
            }

        return {
            "status": "RECOVERING",
            "needs_escalation": False,
            "urgency": "Routine",
            "escalation_message": None,
            "urdulish_reply": "Yeh sun kar bohot khushi hui ke aap behtar hain! Dawai ka course mukammal karein. Apna khayal rakhein, Allah Hafiz."
        }

if __name__ == "__main__":
    agent = FollowupAgent()
    print("Check-in Message:", agent.generate_checkin_message("Tariq Mahmood", "Dr. Ahmed"))
    print("Feedback Eval (Worse):", agent.evaluate_patient_feedback("Tabiyat pehle se ziada kharab hai aur ultiyan ho rahi hain"))

