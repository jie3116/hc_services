from __future__ import annotations

from datetime import date, datetime
from typing import Any

from hc_services.modules.work_certificates.errors import ValidationError
from hc_services.modules.work_certificates.models import (
    CertificateTemplate,
    DocumentFile,
    Employee,
    IssuedDocument,
    RequestStatus,
    WorkCertificateRequest,
    WorkflowEvent,
)


def require_json_object(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body JSON harus berupa object.")
    return payload


def required_string(payload: dict, field: str, max_length: int) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Field wajib diisi.", field)
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(f"Field maksimal {max_length} karakter.", field)
    return value


def optional_string(payload: dict, field: str, max_length: int) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError("Field harus berupa string.", field)
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ValidationError(f"Field maksimal {max_length} karakter.", field)
    return value


def optional_object(payload: dict, field: str) -> dict:
    value = payload.get(field, {})
    if not isinstance(value, dict):
        raise ValidationError("Field harus berupa object.", field)
    return value


def parse_create_request(payload: Any) -> dict:
    payload = require_json_object(payload)
    return {
        "template_id": required_string(payload, "template_id", 36),
        "purpose": required_string(payload, "purpose", 1000),
        "language": required_string(payload, "language", 16),
        "additional_fields": optional_object(payload, "additional_fields"),
        "employee_note": optional_string(payload, "employee_note", 2000),
    }


def parse_note_payload(payload: Any, default_visible: bool) -> dict:
    payload = require_json_object(payload)
    visible = payload.get("visible_to_employee", default_visible)
    if not isinstance(visible, bool):
        raise ValidationError("Field harus berupa boolean.", "visible_to_employee")
    return {
        "note": required_string(payload, "note", 2000),
        "visible_to_employee": visible,
    }


def parse_verify_payload(payload: Any) -> dict:
    payload = require_json_object(payload)
    return {
        "approver_id": required_string(payload, "approver_id", 36),
        "note": optional_string(payload, "note", 2000),
    }


def parse_approve_payload(payload: Any) -> dict:
    payload = require_json_object(payload)
    return {"note": optional_string(payload, "note", 2000)}


def parse_employee_payload(payload: Any) -> dict:
    payload = require_json_object(payload)
    start_date_value = required_string(payload, "start_date", 10)
    try:
        parsed_start_date = date.fromisoformat(start_date_value)
    except ValueError as exc:
        raise ValidationError("Format tanggal harus YYYY-MM-DD.", "start_date") from exc
    return {
        "employee_number": required_string(payload, "employee_number", 64),
        "full_name": required_string(payload, "full_name", 255),
        "work_email": optional_string(payload, "work_email", 255),
        "unit": required_string(payload, "unit", 255),
        "position_title": required_string(payload, "position_title", 255),
        "work_location": required_string(payload, "work_location", 255),
        "employment_type": required_string(payload, "employment_type", 64),
        "start_date": parsed_start_date,
        "supervisor_name": optional_string(payload, "supervisor_name", 255),
    }


def parse_template_payload(payload: Any) -> dict:
    payload = require_json_object(payload)
    required_placeholders = payload.get("required_placeholders", [])
    additional_field_schema = payload.get("additional_field_schema", {})
    if not isinstance(required_placeholders, list):
        raise ValidationError("Field harus berupa array.", "required_placeholders")
    if not isinstance(additional_field_schema, dict):
        raise ValidationError("Field harus berupa object.", "additional_field_schema")
    return {
        "code": required_string(payload, "code", 64),
        "name": required_string(payload, "name", 255),
        "description": optional_string(payload, "description", 4000),
        "language": required_string(payload, "language", 16),
        "body_template": required_string(payload, "body_template", 20000),
        "required_placeholders": required_placeholders,
        "additional_field_schema": additional_field_schema,
        "is_active": bool(payload.get("is_active", False)),
    }


def iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def employee_summary(employee: Employee) -> dict:
    return {
        "id": employee.id,
        "employee_number": employee.employee_number,
        "full_name": employee.full_name,
        "unit": employee.unit,
        "position_title": employee.position_title,
        "work_location": employee.work_location,
        "status": employee.status,
    }


def template_summary(template: CertificateTemplate) -> dict:
    return {
        "id": template.id,
        "code": template.code,
        "name": template.name,
        "language": template.language,
        "is_active": template.is_active,
        "version": template.version,
    }


def file_summary(file: DocumentFile) -> dict:
    return {
        "format": file.format,
        "mime_type": file.mime_type,
        "file_size_bytes": file.file_size_bytes,
        "sha256": file.sha256,
    }


def issued_document_summary(document: IssuedDocument | None) -> dict | None:
    if document is None:
        return None
    return {
        "letter_number": document.letter_number,
        "issued_at": iso(document.issued_at),
        "available_formats": sorted([file.format for file in document.files]),
        "files": [file_summary(file) for file in document.files],
    }


def workflow_event_summary(event: WorkflowEvent, include_internal: bool = False) -> dict | None:
    if not include_internal and not event.visible_to_employee:
        return None
    return {
        "action": event.action,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "note": event.note if (include_internal or event.visible_to_employee) else None,
        "created_at": iso(event.created_at),
    }


def allowed_actions_for(request: WorkCertificateRequest, role: str, user_id: str, employee_id: str | None) -> list[str]:
    if role == "employee" and employee_id == request.employee_id:
        if request.status in {RequestStatus.DRAFT, RequestStatus.RETURNED_TO_EMPLOYEE}:
            return ["submit", "cancel"]
        return []
    if role == "verifier" and request.status in {RequestStatus.SUBMITTED, RequestStatus.RETURNED_TO_HC}:
        return ["return_to_employee", "reject", "verify"]
    if role == "approver" and request.status == RequestStatus.VERIFIED and request.approver_id == user_id:
        return ["return_to_hc", "approve"]
    if role == "admin_hc":
        return ["read"]
    return []


def request_summary(request: WorkCertificateRequest) -> dict:
    return {
        "id": request.id,
        "tracking_number": request.tracking_number,
        "status": request.status,
        "purpose": request.purpose,
        "language": request.language,
        "sla_due_at": iso(request.sla_due_at),
        "created_at": iso(request.created_at),
        "updated_at": iso(request.updated_at),
    }


def request_detail(request: WorkCertificateRequest, role: str, user_id: str, employee_id: str | None) -> dict:
    include_internal = role in {"verifier", "approver", "admin_hc", "auditor"}
    timeline = [workflow_event_summary(event, include_internal) for event in request.events]
    return {
        **request_summary(request),
        "additional_fields": request.additional_fields,
        "employee_note": request.employee_note,
        "submitted_at": iso(request.submitted_at),
        "verified_at": iso(request.verified_at),
        "issued_at": iso(request.issued_at),
        "employee": employee_summary(request.employee),
        "template": template_summary(request.template),
        "issued_document": issued_document_summary(request.issued_document),
        "timeline": [event for event in timeline if event is not None],
        "allowed_actions": allowed_actions_for(request, role, user_id, employee_id),
    }
