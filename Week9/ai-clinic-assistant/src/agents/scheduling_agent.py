"""
Scheduling Agent for City Care Clinics.
Maps triage output & patient preferences to specialty doctor availability,
presents options in polite UrduLish, and executes bookings via the scheduling MCP server.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.mcp_servers.scheduling_server import SchedulingMCPServer
from src.mcp_servers.notifications_server import NotificationsMCPServer

class SchedulingAgent:
    def __init__(self, scheduling_mcp: SchedulingMCPServer = None, notifications_mcp: NotificationsMCPServer = None):
        self.mcp = scheduling_mcp or SchedulingMCPServer()
        self.notifications_mcp = notifications_mcp or NotificationsMCPServer()

    def suggest_options(self, triage_info: Dict[str, Any], city: str = "Lahore", preferred_doctor_id: str = None, patient_id: str = None, preferred_specialty: str = None) -> Dict[str, Any]:
        """
        Suggests available doctors and open slots based on triage output, patient city, and preferences.
        """
        specialty = preferred_specialty or triage_info.get("recommended_specialty", "General Medicine")
        urgency = triage_info.get("urgency_level", "Routine")

        doctors = self.mcp.find_doctors(specialty=specialty, city=city)
        if not doctors:
            # Fallback to any branch in city
            doctors = self.mcp.find_doctors(city=city)
        if not doctors and city != "Lahore":
            # Fallback to central clinic branch in Lahore
            doctors = self.mcp.find_doctors(specialty=specialty, city="Lahore") or self.mcp.find_doctors(city="Lahore")

        if not doctors:
            return {
                "status": "NO_DOCTORS",
                "urdulish_response": f"Afsoos, {city} mein filhal {specialty} ke doctors available nahi hain."
            }

        # Find doctor and date with available slots
        selected_doctor = None
        target_date = None
        slots = []

        candidate_list = list(doctors)
        if preferred_doctor_id:
            candidate_list = [d for d in doctors if d["id"] == preferred_doctor_id] + [d for d in doctors if d["id"] != preferred_doctor_id]

        for cand in candidate_list:
            for day_offset in range(1, 6):
                dt_str = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                cand_slots = self.mcp.check_available_slots(cand["id"], dt_str)
                if patient_id and cand_slots:
                    existing_appts = self.mcp.get_patient_appointments(patient_id)
                    booked_by_pat = {
                        a["time_slot"] for a in existing_appts
                        if a.get("appointment_date") == dt_str and a.get("status") != "Cancelled"
                    }
                    cand_slots = [s for s in cand_slots if s not in booked_by_pat]
                if cand_slots:
                    selected_doctor = cand
                    target_date = dt_str
                    slots = cand_slots
                    break
            if selected_doctor and slots:
                break

        if not selected_doctor or not slots:
            selected_doctor = candidate_list[0]
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            slots = []

        tomorrow = target_date

        if not slots:
            return {
                "status": "NO_SLOTS",
                "urdulish_response": f"Afsoos, {selected_doctor['name']} ke paas {tomorrow} ko koi open slot available nahi hai."
            }

        doc_name = selected_doctor["name"]
        branch_name = selected_doctor["branch_name"]
        fee = selected_doctor["fee_pkr"]

        spec_tag = f" ({specialty})" if specialty.lower() not in doc_name.lower() else ""
        options_msg = (
            f"{doc_name}{spec_tag} {tomorrow} ko {branch_name} ({city}) mein available hain. "
            f"Available slots: {', '.join(slots[:2])}. Fee: PKR {fee:,}. "
            f"Kya main aap ki appointment confirm kar doon?"
        )

        return {
            "status": "OPTIONS_FOUND",
            "doctor": selected_doctor,
            "proposed_date": tomorrow,
            "available_slots": slots,
            "urdulish_response": options_msg
        }

    def confirm_booking(
        self,
        patient_id: str,
        doctor_id: str,
        branch_id: str,
        date_str: str,
        time_slot: str,
        urgency: str = "Routine",
        chief_complaint: str = None
    ) -> Dict[str, Any]:
        """
        Executes booking via scheduling MCP server.
        """
        # Verify date is not in past
        today_str = datetime.now().strftime("%Y-%m-%d")
        if date_str < today_str:
            return {
                "status": "ERROR",
                "message": "Cannot book appointments in past dates.",
                "urdulish_response": "Afsoos, maazi (past) ki tareekh par appointment book nahi ki ja sakti."
            }

        booking_res = self.mcp.book_appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            branch_id=branch_id,
            date_str=date_str,
            time_slot=time_slot,
            urgency=urgency,
            complaint=chief_complaint
        )

        if booking_res.get("status") == "ERROR":
            return {
                "status": "ERROR",
                "message": booking_res.get("message", "Booking failed"),
                "conflict_type": booking_res.get("conflict_type"),
                "urdulish_response": f"Appointment confirm nahi ho saki: {booking_res.get('message')}"
            }

        apt_id = booking_res["appointment_id"]

        # Retrieve Doctor & Branch Details
        conn = self.mcp._get_connection()
        doc_row = conn.execute(
            "SELECT p.name as doctor_name, p.specialty, b.name as branch_name, b.city "
            "FROM practitioners p JOIN branches b ON p.branch_id = b.id WHERE p.id = ?",
            (doctor_id,)
        ).fetchone()
        conn.close()

        doc_name = doc_row["doctor_name"] if doc_row else "Consultant Physician"
        doc_spec = doc_row["specialty"] if doc_row else "General Medicine"
        branch_name = doc_row["branch_name"] if doc_row else "Main Clinic Branch"
        branch_city = doc_row["city"] if doc_row else "Lahore"
        
        spec_tag = f" ({doc_spec})" if doc_spec.lower() not in doc_name.lower() else ""
        # Dispatch email confirmation via HTTPS API (Port 443)
        email_res = self.notifications_mcp.send_email_confirmation(
            email=f"{patient_id.lower()}@patient.clinic.pk",
            subject=f"Appointment Confirmed with {doc_name} - {apt_id}",
            body_text=f"Your appointment ({apt_id}) with {doc_name}{spec_tag} at {branch_name} has been confirmed for {date_str} at {time_slot}. Please arrive 15 minutes before your scheduled time."
        )

        msg = (
            f"Aap ki appointment confirm ho gayi hai. "
            f"Doctor: {doc_name}{spec_tag} | Branch: {branch_name}, {branch_city} | "
            f"Appointment ID: {apt_id} | Date: {date_str} | Slot: {time_slot}. "
            f"Please 15 min pehle clinic reception par pohnch jayein."
        )

        booking_res["doctor_name"] = doc_name
        booking_res["doctor_specialty"] = doc_spec
        booking_res["branch_name"] = branch_name

        return {
            "status": "CONFIRMED",
            "booking_details": booking_res,
            "doctor_name": doc_name,
            "doctor_specialty": doc_spec,
            "branch_name": branch_name,
            "appointment_date": date_str,
            "time_slot": time_slot,
            "email_status": email_res.get("status"),
            "urdulish_response": msg
        }

    def handle_scheduling_query(self, state: Dict[str, Any], user_message: str) -> tuple[str, Dict[str, Any]]:
        """
        Handles patient inquiries about available slots, rescheduling, and cancellations after booking.
        """
        import re
        msg_lower = user_message.lower().strip()
        appt_data = state.get("appointment_data") or {}
        b_details = appt_data.get("booking_details") or {}
        
        appt_id = b_details.get("appointment_id") or appt_data.get("appointment_id") or "APT-D8A325"
        doc_id = b_details.get("doctor_id") or appt_data.get("doctor_id") or "DOC-101"
        doc_name = b_details.get("doctor_name") or appt_data.get("doctor_name") or "Dr. Bilal Ahmed"
        doc_spec = b_details.get("doctor_specialty") or appt_data.get("doctor_specialty") or "General Medicine"
        branch_name = b_details.get("branch_name") or appt_data.get("branch_name") or "DHA Branch, Lahore"
        current_date = b_details.get("appointment_date") or appt_data.get("appointment_date") or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        current_slot = b_details.get("time_slot") or appt_data.get("time_slot") or "10:00 AM"
        patient_id = state.get("patient_id", "PAT-1001")

        # 0. Polite Acknowledgment / Gratitude
        is_thanks = any(w in msg_lower for w in ["shukriya", "shukria", "thank", "thanks", "theek hai", "thik hai", "ok", "okay", "bohot shukriya", "allah hafiz", "khuda hafiz"]) and not any(w in msg_lower for w in ["slot", "time", "reschedule", "change", "cancel", "bajey", "baje", "available", "koi aur", "doosra", "nahi a", "nai a"])
        if is_thanks:
            reply = (
                f"Aap ka bohot shukriya! MedCare Clinic aap ki sehat aur aafiyat ke liye hamesha hazir hai. "
                f"Agar aap ko mazeed koi madad darkaar ho toh zaroor bataiye ga. Allah Hafiz!"
            )
            return reply, state

        # 1. Cancellation Request
        is_cancel = any(w in msg_lower for w in ["cancel", "mansookh", "nahi aana", "nai aana", "tabiyat theek ho gayi", "behtar ho gayi"]) and not any(w in msg_lower for w in ["slot", "time", "reschedule", "aur koi", "doosra", "change"])
        if is_cancel and appt_id:
            self.mcp.cancel_appointment(appt_id)
            if "booking_details" in appt_data:
                state["appointment_data"]["booking_details"]["status"] = "Cancelled"
            state["appointment_data"]["status"] = "Cancelled"
            reply = (
                f"Aap ki appointment ({appt_id}) {doc_name} ke sath cancel kar di gayi hai. "
                "Agar aap ko future mein dobara appointment chahiye ho toh humein zaroor batayein. "
                "MedCare Clinic aap ki mukammal sehat ke liye dua-go hai!"
            )
            return reply, state

        # 2. Check for Specific Slot Selection in message
        all_standard_slots = ["09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "02:30 PM", "04:00 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM"]
        chosen_slot = None
        for s in all_standard_slots:
            if s.lower() in msg_lower:
                # Check if this slot was explicitly negated (e.g. "10:00 AM nahi aa sakti")
                is_negated = bool(re.search(rf'(?:nahi|nai|not|cant|cannot)\s+.*{re.escape(s.lower())}|{re.escape(s.lower())}\s+.*(?:nahi|nai|not)', msg_lower))
                if not is_negated:
                    chosen_slot = s
                    break
        
        if not chosen_slot:
            # Check other patterns, skipping negated times
            def not_neg(pat_str):
                return not re.search(rf'(?:nahi|nai|not)\s+.*{pat_str}|{pat_str}\s+.*(?:nahi|nai|not)', msg_lower)

            if re.search(r'\b10[:\.]?30\b', msg_lower) and not_neg(r'10[:\.]?30'):
                chosen_slot = "10:30 AM"
            elif re.search(r'\b11[:\.]?00\b|\b11\s*baje|\b11\s*bajey|\b11\s*am\b', msg_lower) and not_neg(r'11'):
                chosen_slot = "11:00 AM"
            elif re.search(r'\b11[:\.]?30\b', msg_lower) and not_neg(r'11[:\.]?30'):
                chosen_slot = "11:30 AM"
            elif re.search(r'\b2[:\.]?30\b|\b02[:\.]?30\b', msg_lower) and not_neg(r'2[:\.]?30'):
                chosen_slot = "02:30 PM"
            elif re.search(r'\b4[:\.]?00\b|\b4\s*baje|\b4\s*bajey|\b04[:\.]?00\b', msg_lower) and not_neg(r'4'):
                chosen_slot = "04:00 PM"
            elif re.search(r'\b5[:\.]?00\b|\b5\s*baje|\b5\s*bajey|\b05[:\.]?00\b', msg_lower) and not_neg(r'5'):
                chosen_slot = "05:00 PM"
            elif re.search(r'\b5[:\.]?30\b|\b05[:\.]?30\b', msg_lower) and not_neg(r'5[:\.]?30'):
                chosen_slot = "05:30 PM"
            elif re.search(r'\b6[:\.]?00\b|\b6\s*baje|\b6\s*bajey|\b06[:\.]?00\b', msg_lower) and not_neg(r'6'):
                chosen_slot = "06:00 PM"
            elif re.search(r'\b6[:\.]?30\b|\b06[:\.]?30\b', msg_lower) and not_neg(r'6[:\.]?30'):
                chosen_slot = "06:30 PM"

        is_already_cancelled = appt_data.get("status") == "Cancelled" or b_details.get("status") == "Cancelled"
        if is_already_cancelled and not chosen_slot and not any(w in msg_lower for w in ["slot", "available", "time", "dobara", "rebook", "booking", "pehla", "doosra"]):
            reply = (
                "Aap ki appointment pehle hi cancel ho chuki hai. "
                "Agar aap dobara booking karna chahte hain ya kisi naye masle ke liye consultation chahte hain, "
                "toh baraye meharbani apni alamaat batayein."
            )
            return reply, state

        # Extract requested date if patient mentioned a specific date or relative day
        requested_date = None
        
        # 1. ISO format: 2026-10-14, 2026/10/14, 2026.10.14
        m_iso = re.search(r'\b(202\d[-/\.]\d{1,2}[-/\.]\d{1,2})\b', msg_lower)
        if m_iso:
            raw_d = m_iso.group(1).replace('/', '-').replace('.', '-')
            try:
                parts = raw_d.split('-')
                requested_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            except Exception:
                pass

        # 2. DD-MM-YYYY format: 14-10-2026, 14/10/2026
        if not requested_date:
            m_dmy = re.search(r'\b(\d{1,2})[-/\.](\d{1,2})[-/\.](202\d)\b', msg_lower)
            if m_dmy:
                try:
                    requested_date = f"{m_dmy.group(3)}-{int(m_dmy.group(2)):02d}-{int(m_dmy.group(1)):02d}"
                except Exception:
                    pass

        # 3. Day of month: e.g. "14 ko", "14 tareekh", "14th", "14 october"
        if not requested_date:
            m_day = re.search(r'\b(\d{1,2})(?:\s*ko|\s*tareekh|\s*tarikh|th|st|nd|rd|\s+october|\s+oct)\b', msg_lower)
            if m_day:
                try:
                    day_num = int(m_day.group(1))
                    if 1 <= day_num <= 31:
                        cur_dt = datetime.strptime(current_date, "%Y-%m-%d")
                        requested_date = f"{cur_dt.year}-{cur_dt.month:02d}-{day_num:02d}"
                except Exception:
                    pass

        # 4. Relative terms: "kal" (tomorrow), "parso" / "parson" (day after tomorrow)
        if not requested_date:
            try:
                cur_dt = datetime.strptime(current_date, "%Y-%m-%d")
            except Exception:
                cur_dt = datetime.now()
            if re.search(r'\b(parso|parson|parson ko|day after tomorrow)\b', msg_lower):
                requested_date = (cur_dt + timedelta(days=2)).strftime("%Y-%m-%d")
            elif re.search(r'\b(kal|tomorrow|agle din|agle roz)\b', msg_lower):
                requested_date = (cur_dt + timedelta(days=1)).strftime("%Y-%m-%d")

        if requested_date:
            state["proposed_reschedule_date"] = requested_date
        target_date = state.get("proposed_reschedule_date") or current_date

        # If user picked a slot: execute reschedule on target_date
        if chosen_slot and (chosen_slot != current_slot or target_date != current_date):
            conn = self.mcp._get_connection()
            conn.execute(
                "UPDATE appointments SET time_slot = ?, appointment_date = ?, status = 'Scheduled' WHERE id = ?",
                (chosen_slot, target_date, appt_id)
            )
            conn.commit()
            conn.close()

            # Update state
            state["appointment_data"]["time_slot"] = chosen_slot
            state["appointment_data"]["appointment_date"] = target_date
            if "booking_details" in state["appointment_data"]:
                state["appointment_data"]["booking_details"]["time_slot"] = chosen_slot
                state["appointment_data"]["booking_details"]["appointment_date"] = target_date

            # Dispatch live email confirmation
            pat_email = f"{patient_id.lower()}@patient.clinic.pk"
            email_body = (
                f"Your appointment ({appt_id}) with {doc_name} ({doc_spec}) at {branch_name} "
                f"has been rescheduled to {target_date} at {chosen_slot}. "
                f"Please arrive 15 minutes before your scheduled appointment."
            )
            self.notifications_mcp.send_email_confirmation(
                email=pat_email,
                subject=f"Appointment Rescheduled - {doc_name} ({appt_id})",
                body_text=email_body
            )

            reply = (
                f"Aap ki appointment reschedule kar di gayi hai.\n\n"
                f"• **Doctor:** {doc_name} ({doc_spec})\n"
                f"• **Branch:** {branch_name}\n"
                f"• **Appointment ID:** {appt_id}\n"
                f"• **Date:** {target_date}\n"
                f"• **Naya Slot:** {chosen_slot}\n\n"
                f"Nayi confirmation email aap ke email address par bhej di gayi hai. "
                f"Baraye meharbani scheduled waqt se 15 minute pehle clinic reception par pohnch jayein."
            )
            return reply, state

        # 3. Request for Alternate Slots / Reschedule Options
        check_date = requested_date if requested_date else (state.get("proposed_reschedule_date") or current_date)
        open_slots = self.mcp.check_available_slots(doc_id, check_date)
        alternate_slots = [s for s in open_slots if not (s == current_slot and check_date == current_date)]
        
        if not alternate_slots:
            try:
                base_dt = datetime.strptime(check_date, "%Y-%m-%d")
            except Exception:
                base_dt = datetime.now()
            next_date = (base_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            next_slots = self.mcp.check_available_slots(doc_id, next_date)
            slots_list_str = "\n".join([f"• **{s}**" for s in next_slots[:5]])
            state["appointment_data"]["available_alternate_slots"] = next_slots[:5]
            state["proposed_reschedule_date"] = next_date
            reply = (
                f"{check_date} ko {doc_name} ke tamam slots booked hain. "
                f"Lekin agle din ({next_date}) ko yeh slots available hain:\n\n"
                f"{slots_list_str}\n\n"
                f"In mein se jo time convenient ho, bata dein ya neeche se select kar lein. Main book kar deti hoon."
            )
            return reply, state

        slots_list_str = "\n".join([f"• **{s}**" for s in alternate_slots[:5]])
        state["appointment_data"]["available_alternate_slots"] = alternate_slots[:5]

        if check_date != current_date:
            reply = (
                f"Ji bilkul! **{check_date}** ko {doc_name} ke paas yeh slots available hain:\n\n"
                f"{slots_list_str}\n\n"
                f"In mein se jo time convenient ho, bata dein ya neeche se select kar lein. Main book kar deti hoon."
            )
        else:
            reply = (
                f"Ji bilkul, koi masla nahi! {doc_name} ke paas **{current_date}** ko yeh doosray slots available hain:\n\n"
                f"{slots_list_str}\n\n"
                f"In mein se jo time convenient ho, bata dein ya neeche se select kar lein. Main book kar deti hoon."
            )
        return reply, state

if __name__ == "__main__":
    agent = SchedulingAgent()
    triage = {"recommended_specialty": "Paediatrics", "urgency_level": "Routine"}
    opts = agent.suggest_options(triage, city="Lahore")
    print("Suggested Options:\n", opts["urdulish_response"])

