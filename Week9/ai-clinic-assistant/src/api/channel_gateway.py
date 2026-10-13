"""
Multi-Channel Gateway for City Care Clinics.
Handles routing for:
1. Web Chat (REST API / Streamlit Portal)
2. WhatsApp Gateway (Text & Voice Note transcripts)
3. Email Gateway (Booking receipts & SOAP briefs)
4. Automated Scheduled Reminders
"""

from typing import Dict, Any, List
from src.agents.supervisor_graph import ClinicSupervisorGraph
from src.mcp_servers.notifications_server import NotificationsMCPServer

class ChannelGateway:
    def __init__(self, graph: ClinicSupervisorGraph = None, notifications_mcp: NotificationsMCPServer = None):
        self.graph = graph or ClinicSupervisorGraph()
        self.notifications_mcp = notifications_mcp or NotificationsMCPServer()

    def process_incoming_message(
        self,
        patient_id: str,
        message_text: str,
        channel: str = "web", # "web", "whatsapp", "email"
        current_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Routes incoming patient message from any channel into the Supervisor Graph.
        """
        state = current_state or self.graph.create_initial_state(patient_id)
        
        # Format channel-specific header tag
        channel_prefix = f"[{channel.upper()}] "
        tagged_message = message_text
        
        # Execute Supervisor step
        updated_state = self.graph.step(state, user_message=tagged_message)
        
        # Get latest AI response message
        ai_messages = [m for m in updated_state.get("messages", []) if m["sender"] == "AI"]
        latest_reply = ai_messages[-1]["text"] if ai_messages else "Message processed."

        # Channel-specific outbound dispatch
        dispatch_status = "DELIVERED"
        if channel == "whatsapp":
            phone = updated_state.get("intake_form", {}).get("phone", "+92-300-1234567")
            self.notifications_mcp.send_whatsapp_message(phone, latest_reply)
            dispatch_status = "DISPATCHED_WHATSAPP"
        elif channel == "email":
            self.notifications_mcp.send_email_confirmation("patient@clinic.com", "Clinic Update", latest_reply)
            dispatch_status = "DISPATCHED_EMAIL"

        return {
            "channel": channel,
            "patient_id": patient_id,
            "reply_text": latest_reply,
            "dispatch_status": dispatch_status,
            "graph_state": updated_state
        }

if __name__ == "__main__":
    gateway = ChannelGateway()
    res = gateway.process_incoming_message("PAT-0012", "Mujhe kal se bukhar hai", channel="whatsapp")
    print("Channel Gateway Test Reply:", res["reply_text"])

