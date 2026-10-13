"""
Records Agent for City Care Clinics.
Queries patient medical records and lab observations via the patient-records MCP server
and answers patient questions in plain, non-diagnostic UrduLish.
"""

from typing import Dict, Any, List
from src.mcp_servers.patient_records_server import PatientRecordsMCPServer

class RecordsAgent:
    def __init__(self, records_mcp: PatientRecordsMCPServer = None):
        self.mcp = records_mcp or PatientRecordsMCPServer()

    def answer_patient_query(self, patient_id: str, query: str) -> Dict[str, Any]:
        """
        Queries records and generates a factual, simple UrduLish answer.
        """
        profile = self.mcp.get_patient_profile(patient_id)
        allergies = self.mcp.get_patient_allergies(patient_id)
        history = self.mcp.get_patient_history(patient_id)
        labs = self.mcp.get_patient_labs(patient_id)

        query_lower = query.lower()

        # Handle allergy query
        if any(w in query_lower for w in ["allergy", "allergic"]):
            if not allergies:
                ans = f"Aap ke record ke mutabiq aap ko kisi dawa se allergy logged nahi hai."
            else:
                alg_names = ", ".join([a["allergen"] for a in allergies])
                ans = f"Aap ke record ke mutabiq aap ko in cheezon se allergy hai: {alg_names}."
            return {"status": "SUCCESS", "urdulish_response": ans, "raw_data": allergies}

        # Handle lab test query
        if any(w in query_lower for w in ["lab", "report", "test", "sugar", "hba1c", "blood"]):
            if not labs:
                ans = "Aap ki file mein filhal koi recent lab test results logged nahi hain."
            else:
                latest = labs[0]
                ans = (
                    f"Aap ki pichli lab report ({latest['test_date']}) mein {latest['test_name']} ka result "
                    f"{latest['value']} {latest['unit']} tha (Normal range: {latest['reference_range']}). "
                    f"Report details doctor sahab ko review ke liye available hain."
                )
            return {"status": "SUCCESS", "urdulish_response": ans, "raw_data": labs}

        # Handle past history query
        if any(w in query_lower for w in ["history", "pichla", "disease", "condition", "illness"]):
            if not history:
                ans = "Aap ki file mein koi chronic disease ya past condition logged nahi hai."
            else:
                cond_names = ", ".join([c["condition_name"] for c in history])
                ans = f"Aap ke past record mein in conditions ka اندراج hai: {cond_names}."
            return {"status": "SUCCESS", "urdulish_response": ans, "raw_data": history}

        # Default summary
        ans = (
            f"Assalam-o-Alaikum {profile.get('name', 'Patient')}! Aap ki medical file active hai. "
            f"Aap ki file mein {len(history)} past conditions aur {len(labs)} lab records majood hain."
        )
        return {"status": "SUCCESS", "urdulish_response": ans, "raw_data": profile}

if __name__ == "__main__":
    agent = RecordsAgent()
    print(agent.answer_patient_query("PAT-0012", "Mera pichla lab test kaisa tha?"))

