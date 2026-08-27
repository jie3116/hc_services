from __future__ import annotations

from hc_services.extensions import SessionLocal
from hc_services.modules.work_certificates.models import VerificationToken


ADMIN_HEADERS = {"X-User-Id": "admin-1", "X-User-Role": "admin_hc"}
VERIFIER_HEADERS = {"X-User-Id": "verifier-1", "X-User-Role": "verifier"}
APPROVER_HEADERS = {
    "X-User-Id": "approver-1",
    "X-User-Role": "approver",
    "X-User-Name": "Budi Approver",
    "X-User-Position": "Head of Human Capital",
}


def json(response):
    return response.get_json()


def create_employee(client):
    response = client.post(
        "/api/v1/work-certificates/employees",
        headers=ADMIN_HEADERS,
        json={
            "employee_number": "EMP001",
            "full_name": "Andi Saputra",
            "work_email": "andi@example.test",
            "unit": "Finance",
            "position_title": "Finance Analyst",
            "work_location": "Jakarta",
            "employment_type": "permanent",
            "start_date": "2024-01-01",
            "supervisor_name": "Siti Manager",
        },
    )
    assert response.status_code == 201
    return json(response)["data"]


def create_template(client):
    response = client.post(
        "/api/v1/work-certificates/admin/templates",
        headers=ADMIN_HEADERS,
        json={
            "code": "general",
            "name": "Surat Keterangan Kerja Umum",
            "language": "id",
            "body_template": "Nama: {{ employee.full_name }}",
            "required_placeholders": ["employee.full_name"],
            "additional_field_schema": {"required": ["recipient"]},
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return json(response)["data"]


def employee_headers(employee_id: str):
    return {"X-User-Id": "employee-user-1", "X-User-Role": "employee", "X-Employee-Id": employee_id}


def test_work_certificate_happy_path_issues_document_and_validates_barcode(client):
    employee = create_employee(client)
    template = create_template(client)

    create_response = client.post(
        "/api/v1/work-certificates/requests",
        headers=employee_headers(employee["id"]),
        json={
            "template_id": template["id"],
            "purpose": "Pengajuan KPR",
            "language": "id",
            "additional_fields": {"recipient": "Bank ABC"},
            "employee_note": "Mohon diproses.",
        },
    )
    assert create_response.status_code == 201
    request_id = json(create_response)["data"]["id"]
    assert json(create_response)["data"]["status"] == "draft"

    submit_response = client.post(f"/api/v1/work-certificates/requests/{request_id}/submit", headers=employee_headers(employee["id"]))
    assert submit_response.status_code == 200
    assert json(submit_response)["data"]["status"] == "submitted"
    assert json(submit_response)["data"]["allowed_actions"] == []

    verify_response = client.post(
        f"/api/v1/work-certificates/requests/{request_id}/verify",
        headers=VERIFIER_HEADERS,
        json={"approver_id": "approver-1", "note": "Valid."},
    )
    assert verify_response.status_code == 200
    assert json(verify_response)["data"]["status"] == "verified"

    approve_response = client.post(
        f"/api/v1/work-certificates/requests/{request_id}/approve",
        headers=APPROVER_HEADERS,
        json={"note": "Disetujui."},
    )
    assert approve_response.status_code == 200
    approved_data = json(approve_response)["data"]
    assert approved_data["status"] == "issued"
    assert approved_data["issued_document"]["letter_number"].endswith("/KP.204/KI-2026")
    assert approved_data["issued_document"]["available_formats"] == ["docx", "pdf"]

    download_response = client.get(
        f"/api/v1/work-certificates/requests/{request_id}/documents/pdf",
        headers=employee_headers(employee["id"]),
    )
    assert download_response.status_code == 200
    assert download_response.mimetype == "application/pdf"

    token = SessionLocal().query(VerificationToken).first()
    public_response = client.get(f"/api/v1/work-certificates/verify/{token.public_code}")
    assert public_response.status_code == 200
    public_data = json(public_response)["data"]
    assert public_data == {
        "valid": True,
        "letter_number": approved_data["issued_document"]["letter_number"],
        "issued_at": public_data["issued_at"],
        "document_type": "Surat Keterangan Kerja",
        "approver_position_title": "Head of Human Capital",
    }
    assert "full_name" not in public_data


def test_employee_cannot_read_another_employee_request(client):
    employee = create_employee(client)
    template = create_template(client)
    create_response = client.post(
        "/api/v1/work-certificates/requests",
        headers=employee_headers(employee["id"]),
        json={
            "template_id": template["id"],
            "purpose": "Pengajuan visa",
            "language": "id",
            "additional_fields": {"recipient": "Embassy"},
        },
    )
    request_id = json(create_response)["data"]["id"]

    response = client.get(
        f"/api/v1/work-certificates/requests/{request_id}",
        headers=employee_headers("00000000-0000-0000-0000-000000000999"),
    )
    assert response.status_code == 403
    assert json(response)["errors"][0]["code"] == "forbidden"


def test_missing_required_additional_field_returns_validation_error(client):
    employee = create_employee(client)
    template = create_template(client)

    response = client.post(
        "/api/v1/work-certificates/requests",
        headers=employee_headers(employee["id"]),
        json={
            "template_id": template["id"],
            "purpose": "Pengajuan KPR",
            "language": "id",
            "additional_fields": {},
        },
    )
    assert response.status_code == 400
    assert json(response)["errors"][0]["field"] == "additional_fields.recipient"
