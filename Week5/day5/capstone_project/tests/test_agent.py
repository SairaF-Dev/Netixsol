import requests
import time

BASE_URL = "http://127.0.0.1:8000"


def print_response(title, response):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print("Status Code:", response.status_code)

    try:
        print(response.json())
    except Exception:
        print(response.text)


# ============================================================
# TEST 1: NORMAL INCIDENT
# ============================================================

incident = {
    "incident_id": "INC-TEST-001",
    "service_name": "User_Auth_API",
    "repository": "SairaF-Dev/sre-agent-capstone",
    "description": "Login API is returning 500 errors and database connections appear exhausted."
}

print("\n🚀 Sending incident...")

response = requests.post(
    f"{BASE_URL}/webhook/incident",
    json=incident,
    timeout=60
)

print_response(
    "TEST 1 — INCIDENT INVESTIGATION",
    response
)


# ============================================================
# TEST 2: HUMAN APPROVAL
# ============================================================

if response.status_code == 200:

    print("\n👤 Sending HUMAN APPROVAL...")

    approval = {
        "incident_id": "INC-TEST-001",
        "approved": True
    }

    response = requests.post(
        f"{BASE_URL}/webhook/approve",
        json=approval,
        timeout=60
    )

    print_response(
        "TEST 2 — HUMAN APPROVAL",
        response
    )


# ============================================================
# TEST 3: NEW INCIDENT + HUMAN REJECTION
# ============================================================

incident_2 = {
    "incident_id": "INC-TEST-002",
    "service_name": "Payment_Gateway",
    "repository": "octocat/Hello-World",
    "description": "Payment webhook delivery is timing out."
}

print("\n🚀 Sending second incident...")

response = requests.post(
    f"{BASE_URL}/webhook/incident",
    json=incident_2,
    timeout=60
)

print_response(
    "TEST 3 — SECOND INCIDENT",
    response
)


if response.status_code == 200:

    print("\n👤 Sending HUMAN REJECTION...")

    approval = {
        "incident_id": "INC-TEST-002",
        "approved": False
    }

    response = requests.post(
        f"{BASE_URL}/webhook/approve",
        json=approval,
        timeout=60
    )

    print_response(
        "TEST 4 — HUMAN REJECTION",
        response
    )


# ============================================================
# TEST 5: INVALID INPUT
# ============================================================

print("\n🧪 Testing invalid input...")

invalid_incident = {
    "incident_id": "X",
    "service_name": "",
    "repository": "invalid repository",
    "description": "bad"
}

response = requests.post(
    f"{BASE_URL}/webhook/incident",
    json=invalid_incident,
    timeout=30
)

print_response(
    "TEST 5 — INPUT VALIDATION",
    response
)


# ============================================================
# TEST 6: UNKNOWN INCIDENT APPROVAL
# ============================================================

print("\n🧪 Testing unknown incident approval...")

approval = {
    "incident_id": "INC-DOES-NOT-EXIST",
    "approved": True
}

response = requests.post(
    f"{BASE_URL}/webhook/approve",
    json=approval,
    timeout=30
)

print_response(
    "TEST 6 — UNKNOWN INCIDENT",
    response
)


print("\n" + "=" * 70)
print("✅ BASIC TESTING FINISHED")
print("=" * 70)