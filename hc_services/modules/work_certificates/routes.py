from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from hc_services.extensions import SessionLocal
from hc_services.modules.work_certificates.errors import ApiError
from hc_services.modules.work_certificates.models import DocumentFormat
from hc_services.modules.work_certificates.schemas import (
    employee_summary,
    issued_document_summary,
    parse_approve_payload,
    parse_create_request,
    parse_employee_payload,
    parse_note_payload,
    parse_template_payload,
    parse_verify_payload,
    request_detail,
    request_summary,
    template_summary,
)
from hc_services.modules.work_certificates.services import CurrentUser, WorkCertificateService

bp = Blueprint("work_certificates", __name__)


def envelope(data=None, meta=None, errors=None, status=200):
    return jsonify({"data": data, "meta": meta or {}, "errors": errors or []}), status


def current_user() -> CurrentUser:
    return CurrentUser(
        user_id=request.headers.get("X-User-Id", "anonymous"),
        role=request.headers.get("X-User-Role", "employee"),
        employee_id=request.headers.get("X-Employee-Id"),
        full_name=request.headers.get("X-User-Name"),
        position_title=request.headers.get("X-User-Position"),
    )


def service() -> WorkCertificateService:
    return WorkCertificateService(SessionLocal())


def page_params() -> tuple[int, int]:
    page_number = int(request.args.get("page[number]", "1"))
    page_size = int(request.args.get("page[size]", "20"))
    return page_number, min(page_size, 100)


@bp.errorhandler(ApiError)
def handle_api_error(error: ApiError):
    SessionLocal.rollback()
    payload = {
        "code": error.code,
        "message": error.message,
        "field": error.field,
    }
    return envelope(None, errors=[payload], status=error.status_code)


@bp.errorhandler(ValueError)
def handle_value_error(error: ValueError):
    SessionLocal.rollback()
    return envelope(None, errors=[{"code": "validation_error", "message": str(error), "field": None}], status=400)


@bp.get("/templates")
def list_templates():
    active_arg = request.args.get("active")
    active = None if active_arg is None else active_arg.lower() == "true"
    templates = service().list_templates(active=active, language=request.args.get("language"))
    return envelope([template_summary(template) for template in templates])


@bp.post("/admin/templates")
def create_template():
    template = service().create_template(parse_template_payload(request.get_json(silent=True)), current_user())
    return envelope(template_summary(template), status=201)


@bp.post("/employees")
def create_employee():
    user = current_user()
    if user.role != "admin_hc":
        from hc_services.modules.work_certificates.errors import ForbiddenError

        raise ForbiddenError("Hanya Admin HC yang dapat membuat pegawai.")
    employee = service().create_employee(parse_employee_payload(request.get_json(silent=True)))
    return envelope(employee_summary(employee), status=201)


@bp.get("/requests")
def list_requests():
    page_number, page_size = page_params()
    requests = service().list_requests(current_user(), request.args.get("status"), page_number, page_size)
    return envelope(
        [request_summary(item) for item in requests],
        meta={"page": {"number": page_number, "size": page_size}},
    )


@bp.post("/requests")
def create_request():
    created = service().create_request(parse_create_request(request.get_json(silent=True)), current_user())
    return envelope(request_summary(created), status=201)


@bp.get("/requests/<request_id>")
def get_request(request_id: str):
    user = current_user()
    item = service().get_request_for_user(request_id, user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/submit")
def submit_request(request_id: str):
    user = current_user()
    item = service().submit_request(request_id, user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/verify")
def verify_request(request_id: str):
    user = current_user()
    item = service().verify_request(request_id, parse_verify_payload(request.get_json(silent=True)), user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/approve")
def approve_request(request_id: str):
    user = current_user()
    item = service().approve_request(request_id, parse_approve_payload(request.get_json(silent=True)), user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/return-to-employee")
def return_to_employee(request_id: str):
    user = current_user()
    item = service().return_to_employee(request_id, parse_note_payload(request.get_json(silent=True), True), user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/return-to-hc")
def return_to_hc(request_id: str):
    user = current_user()
    item = service().return_to_hc(request_id, parse_note_payload(request.get_json(silent=True), False), user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/reject")
def reject_request(request_id: str):
    user = current_user()
    item = service().reject_request(request_id, parse_note_payload(request.get_json(silent=True), True), user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.post("/requests/<request_id>/cancel")
def cancel_request(request_id: str):
    user = current_user()
    item = service().cancel_request(request_id, user)
    return envelope(request_detail(item, user.role, user.user_id, user.employee_id))


@bp.get("/requests/<request_id>/documents/<format_name>")
def download_document(request_id: str, format_name: str):
    if format_name not in {DocumentFormat.PDF, DocumentFormat.DOCX}:
        from hc_services.modules.work_certificates.errors import ValidationError

        raise ValidationError("Format dokumen tidak didukung.", "format")
    item = service().get_request_for_user(request_id, current_user())
    document = item.issued_document
    if item.status != "issued" or document is None:
        from hc_services.modules.work_certificates.errors import ConflictError

        raise ConflictError("Dokumen belum tersedia.")
    file = next((candidate for candidate in document.files if candidate.format == format_name), None)
    if file is None:
        from hc_services.modules.work_certificates.errors import NotFoundError

        raise NotFoundError("File dokumen tidak ditemukan.")
    body = f"{document.letter_number}\n{item.employee.full_name}\n".encode("utf-8")
    return Response(body, mimetype=file.mime_type, headers={"X-Letter-Number": document.letter_number})


@bp.get("/verify/<public_code>")
def verify_public_code(public_code: str):
    return envelope(service().validate_public_code(public_code))
