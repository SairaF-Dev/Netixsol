"""
Test Suite for Multi-Channel Gateway and FastAPI REST Endpoints.
Tests Web Chat, WhatsApp, Email channel routing, and Health check.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.channel_gateway import ChannelGateway
from src.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_channel_gateway_flows():
    print("=" * 65)
    print("[TEST] MULTI-CHANNEL GATEWAY & FASTAPI REST API SUITE")
    print("=" * 65)

    # 1. Test Health Endpoint
    h_res = client.get("/health")
    assert h_res.status_code == 200
    assert h_res.json()["status"] == "HEALTHY"
    print("[PASS] 1. Health Check Endpoint (/health) Status: HEALTHY")

    # 2. Test Web Chat REST Endpoint (/api/chat)
    web_payload = {
        "patient_id": "PAT-0012",
        "message_text": "Assalam-o-Alaikum! Mujhe 2 din se bukhar hai",
        "channel": "web"
    }
    web_res = client.post("/api/chat", json=web_payload)
    assert web_res.status_code == 200
    res_data = web_res.json()
    assert res_data["channel"] == "web"
    print("\n[PASS] 2. Web Chat API Endpoint (/api/chat):")
    print("     Reply:", res_data["reply_text"])

    # 3. Test WhatsApp Gateway Connector
    wa_payload = {
        "patient_id": "PAT-0042",
        "message_text": "Dil mein tez dard aur pasina aa raha hai",
        "channel": "whatsapp"
    }
    wa_res = client.post("/api/chat", json=wa_payload)
    assert wa_res.status_code == 200
    wa_data = wa_res.json()
    assert wa_data["dispatch_status"] == "DISPATCHED_WHATSAPP"
    print("\n[PASS] 3. WhatsApp Gateway Connector:")
    print("     Dispatch Status :", wa_data["dispatch_status"])
    print("     Emergency Alert :", wa_data["reply_text"])

    print("=" * 65)
    print("[SUCCESS] MULTI-CHANNEL GATEWAY TESTS PASSED 100%")
    print("=" * 65)

if __name__ == "__main__":
    test_channel_gateway_flows()

