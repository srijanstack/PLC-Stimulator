from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_archive_has_five_bit_instructions():
    data = client.get("/api/archive").json()
    ids = {item["id"] for item in data["instructions"]}
    assert {"contact_no", "contact_nc", "coil_output", "coil_set", "coil_reset"} <= ids

def test_rejects_input_after_output():
    payload = {
        "project_name": "Invalid rung",
        "instructions": [
            {"instanceId": "1", "instructionId": "coil_output", "address": "Q0.0", "name": "Lamp"},
            {"instanceId": "2", "instructionId": "contact_no", "address": "I0.0", "name": "Start"},
        ],
    }
    response = client.put("/api/state", json=payload)
    assert response.status_code == 422
    assert "cannot appear after a coil" in response.json()["detail"]


def test_rejects_invalid_input_address():
    payload = {
        "project_name": "Invalid address",
        "instructions": [
            {"instanceId": "1", "instructionId": "contact_no", "address": "I0.8", "name": "Start"},
        ],
    }
    response = client.put("/api/state", json=payload)
    assert response.status_code == 422
    assert "I0.0 through I0.7" in response.json()["detail"]


def test_accepts_contacts_then_output():
    payload = {
        "project_name": "Valid rung",
        "instructions": [
            {"instanceId": "1", "instructionId": "contact_no", "address": "I0.7", "name": "Start"},
            {"instanceId": "2", "instructionId": "coil_output", "address": "Q0.7", "name": "Lamp"},
        ],
    }
    response = client.put("/api/state", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "saved"
