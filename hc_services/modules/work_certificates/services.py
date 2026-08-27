from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hc_services.modules.work_certificates.errors import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from hc_services.modules.work_certificates.models import (
    CertificateTemplate,
    DocumentFile,
    DocumentFormat,
    Employee,
    IssuedDocument,
    OwnerRole,
    RequestStatus,
    VerificationToken,
    WorkflowEvent,
    WorkCertificateRequest,
    utcnow,
)
from hc_services.modules.work_certificates.repositories import WorkCertificateRepository


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: str
    employee_id: str | None = None
    full_name: str | None = None
    position_title: str | None = None


def add_years_approx(value, years: int):
    return value + timedelta(days=365 * years)


class WorkCertificateService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = WorkCertificateRepository(session)

    def create_employee(self, data: dict) -> Employee:
        employee = Employee(**data, status="active")
        self.session.add(employee)
        self._commit_or_conflict("Nomor induk pegawai sudah digunakan.")
        return employee

    def create_template(self, data: dict, user: CurrentUser) -> CertificateTemplate:
        if user.role != "admin_hc":
            raise ForbiddenError("Hanya Admin HC yang dapat membuat template.")
        template = CertificateTemplate(**data, created_by=user.user_id, updated_by=user.user_id, version=1)
        self.session.add(template)
        self._commit_or_conflict("Kode template sudah digunakan.")
        return template

    def list_templates(self, active: bool | None, language: str | None) -> list[CertificateTemplate]:
        return self.repo.list_templates(active, language)

    def create_request(self, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        if user.role != "employee" or not user.employee_id:
            raise ForbiddenError("Hanya pegawai yang dapat membuat permohonan.")

        employee = self._require_employee(user.employee_id)
        self._ensure_employee_can_create(employee)
        template = self._require_template(data["template_id"])
        if not template.is_active:
            raise BusinessRuleError("Template tidak aktif.", "template_id")
        if template.language != data["language"]:
            raise ValidationError("Bahasa tidak didukung oleh template.", "language")
        self._validate_additional_fields(template, data["additional_fields"])

        now = utcnow()
        request = WorkCertificateRequest(
            tracking_number=self.repo.next_tracking_number(now.year),
            employee_id=employee.id,
            template_id=template.id,
            template_snapshot={
                "id": template.id,
                "code": template.code,
                "name": template.name,
                "language": template.language,
                "version": template.version,
                "body_template": template.body_template,
                "required_placeholders": template.required_placeholders,
                "additional_field_schema": template.additional_field_schema,
            },
            purpose=data["purpose"],
            language=data["language"],
            additional_fields=data["additional_fields"],
            employee_note=data["employee_note"],
            status=RequestStatus.DRAFT,
        )
        self.session.add(request)
        self.session.flush()
        self._add_event(request, user, "create_draft", None, RequestStatus.DRAFT, visible_to_employee=True)
        self._commit_or_conflict("Nomor tracking sudah digunakan.")
        return self.repo.get_request(request.id)

    def submit_request(self, request_id: str, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        self._ensure_employee_owner(request, user)
        if request.status not in {RequestStatus.DRAFT, RequestStatus.RETURNED_TO_EMPLOYEE}:
            raise ConflictError("Permohonan tidak dapat dikirim pada status saat ini.")
        self._ensure_employee_can_create(request.employee)
        self._validate_additional_fields(request.template, request.additional_fields)

        now = utcnow()
        old_status = request.status
        request.status = RequestStatus.SUBMITTED
        request.submitted_at = now
        request.current_owner_role = OwnerRole.VERIFIER
        request.sla_due_at = now + timedelta(days=3)
        request.sla_overdue_at = None
        self._add_event(request, user, "submit", old_status, request.status, visible_to_employee=True)
        self.session.commit()
        return self.repo.get_request(request.id)

    def verify_request(self, request_id: str, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        if user.role != "verifier":
            raise ForbiddenError("Hanya verifikator yang dapat memverifikasi permohonan.")
        request = self._require_request(request_id)
        if request.status not in {RequestStatus.SUBMITTED, RequestStatus.RETURNED_TO_HC}:
            raise ConflictError("Permohonan tidak dapat diverifikasi pada status saat ini.")

        now = utcnow()
        old_status = request.status
        request.status = RequestStatus.VERIFIED
        request.verified_at = now
        request.verified_by = user.user_id
        request.approver_id = data["approver_id"]
        request.current_owner_role = OwnerRole.APPROVER
        request.sla_due_at = now + timedelta(days=3)
        request.sla_overdue_at = None
        self._add_event(request, user, "verify", old_status, request.status, data.get("note"), visible_to_employee=False)
        self.session.commit()
        return self.repo.get_request(request.id)

    def approve_request(self, request_id: str, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        if user.role != "approver" or request.approver_id != user.user_id:
            raise ForbiddenError("Approver hanya dapat menyetujui permohonan yang ditugaskan kepadanya.")
        if request.status != RequestStatus.VERIFIED:
            raise ConflictError("Permohonan tidak dapat disetujui pada status saat ini.")
        if request.issued_document is not None:
            raise ConflictError("Dokumen sudah diterbitkan.")

        now = utcnow()
        sequence, letter_number = self.repo.allocate_letter_number(now.year)
        approver_name = user.full_name or "Approver"
        approver_position = user.position_title or "Approver"
        public_code = secrets.token_urlsafe(24)
        token_hash = hashlib.sha256(public_code.encode("utf-8")).hexdigest()
        barcode_hash = hashlib.sha256(f"{request.id}:{letter_number}:{token_hash}".encode("utf-8")).hexdigest()
        content_hash = hashlib.sha256(f"{request.id}:{letter_number}:{request.template_snapshot}".encode("utf-8")).hexdigest()

        issued_document = IssuedDocument(
            request_id=request.id,
            letter_number=letter_number,
            letter_sequence_number=sequence,
            letter_year=now.year,
            issued_at=now,
            approver_user_id=user.user_id,
            approver_name=approver_name,
            approver_position_title=approver_position,
            barcode_payload_hash=barcode_hash,
            content_hash=content_hash,
            retention_expires_at=add_years_approx(now, 3),
        )
        self.session.add(issued_document)
        self.session.flush()

        for format_name, mime_type in [
            (DocumentFormat.PDF, "application/pdf"),
            (DocumentFormat.DOCX, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ]:
            file_hash = hashlib.sha256(f"{issued_document.id}:{format_name}:{content_hash}".encode("utf-8")).hexdigest()
            self.session.add(
                DocumentFile(
                    issued_document_id=issued_document.id,
                    format=format_name,
                    storage_key=f"work-certificates/{request.id}/{letter_number.replace('/', '_')}.{format_name}",
                    mime_type=mime_type,
                    file_size_bytes=1,
                    sha256=file_hash,
                )
            )

        self.session.add(
            VerificationToken(
                issued_document_id=issued_document.id,
                token_hash=token_hash,
                public_code=public_code,
            )
        )

        old_status = request.status
        request.status = RequestStatus.ISSUED
        request.approved_at = now
        request.issued_at = now
        request.current_owner_role = None
        request.sla_due_at = None
        request.sla_overdue_at = None
        self._add_event(request, user, "approve", old_status, RequestStatus.ISSUED, data.get("note"), visible_to_employee=False)
        self._add_event(request, user, "issue_document", RequestStatus.VERIFIED, RequestStatus.ISSUED, visible_to_employee=True)
        self._commit_or_conflict("Dokumen sudah diterbitkan atau nomor surat bentrok.")
        return self.repo.get_request(request.id)

    def return_to_employee(self, request_id: str, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        if user.role != "verifier":
            raise ForbiddenError("Hanya verifikator yang dapat mengembalikan permohonan.")
        request = self._require_request(request_id)
        if request.status not in {RequestStatus.SUBMITTED, RequestStatus.RETURNED_TO_HC}:
            raise ConflictError("Permohonan tidak dapat dikembalikan ke pegawai pada status saat ini.")
        old_status = request.status
        request.status = RequestStatus.RETURNED_TO_EMPLOYEE
        request.current_owner_role = OwnerRole.EMPLOYEE
        request.sla_due_at = None
        self._add_event(request, user, "return_to_employee", old_status, request.status, data["note"], data["visible_to_employee"])
        self.session.commit()
        return self.repo.get_request(request.id)

    def return_to_hc(self, request_id: str, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        if user.role != "approver" or request.approver_id != user.user_id:
            raise ForbiddenError("Approver hanya dapat mengembalikan permohonan yang ditugaskan kepadanya.")
        if request.status != RequestStatus.VERIFIED:
            raise ConflictError("Permohonan tidak dapat dikembalikan ke HC pada status saat ini.")
        old_status = request.status
        request.status = RequestStatus.RETURNED_TO_HC
        request.current_owner_role = OwnerRole.VERIFIER
        request.sla_due_at = utcnow() + timedelta(days=3)
        self._add_event(request, user, "return_to_hc", old_status, request.status, data["note"], visible_to_employee=False)
        self.session.commit()
        return self.repo.get_request(request.id)

    def reject_request(self, request_id: str, data: dict, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        if user.role not in {"verifier", "admin_hc"}:
            raise ForbiddenError("Hanya verifikator atau Admin HC yang dapat menolak permohonan.")
        if request.status not in {RequestStatus.SUBMITTED, RequestStatus.RETURNED_TO_HC, RequestStatus.VERIFIED}:
            raise ConflictError("Permohonan tidak dapat ditolak pada status saat ini.")
        old_status = request.status
        request.status = RequestStatus.REJECTED
        request.rejected_at = utcnow()
        request.current_owner_role = None
        request.sla_due_at = None
        self._add_event(request, user, "reject", old_status, request.status, data["note"], visible_to_employee=True)
        self.session.commit()
        return self.repo.get_request(request.id)

    def cancel_request(self, request_id: str, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        self._ensure_employee_owner(request, user)
        if request.status not in {RequestStatus.DRAFT, RequestStatus.RETURNED_TO_EMPLOYEE}:
            raise ConflictError("Permohonan tidak dapat dibatalkan pada status saat ini.")
        old_status = request.status
        request.status = RequestStatus.CANCELLED
        request.cancelled_at = utcnow()
        request.current_owner_role = None
        request.sla_due_at = None
        self._add_event(request, user, "cancel", old_status, request.status, visible_to_employee=True)
        self.session.commit()
        return self.repo.get_request(request.id)

    def get_request_for_user(self, request_id: str, user: CurrentUser) -> WorkCertificateRequest:
        request = self._require_request(request_id)
        self._ensure_can_read(request, user)
        return request

    def list_requests(self, user: CurrentUser, status: str | None, page_number: int, page_size: int) -> list[WorkCertificateRequest]:
        return self.repo.list_requests(
            role=user.role,
            user_id=user.user_id,
            employee_id=user.employee_id,
            status=status,
            page_number=page_number,
            page_size=page_size,
        )

    def validate_public_code(self, public_code: str) -> dict:
        token = self.repo.get_token_by_public_code(public_code)
        if token is None or token.issued_document is None:
            raise NotFoundError("Kode verifikasi tidak ditemukan.")
        document = token.issued_document
        return {
            "valid": True,
            "letter_number": document.letter_number,
            "issued_at": document.issued_at.isoformat(),
            "document_type": "Surat Keterangan Kerja",
            "approver_position_title": document.approver_position_title,
        }

    def _require_employee(self, employee_id: str) -> Employee:
        employee = self.repo.get_employee(employee_id)
        if employee is None:
            raise NotFoundError("Pegawai tidak ditemukan.")
        return employee

    def _require_template(self, template_id: str) -> CertificateTemplate:
        template = self.repo.get_template(template_id)
        if template is None:
            raise NotFoundError("Template tidak ditemukan.")
        return template

    def _require_request(self, request_id: str) -> WorkCertificateRequest:
        request = self.repo.get_request(request_id)
        if request is None:
            raise NotFoundError("Permohonan tidak ditemukan.")
        return request

    def _ensure_employee_owner(self, request: WorkCertificateRequest, user: CurrentUser):
        if user.role != "employee" or user.employee_id != request.employee_id:
            raise ForbiddenError("Pegawai hanya dapat mengakses permohonannya sendiri.")

    def _ensure_can_read(self, request: WorkCertificateRequest, user: CurrentUser):
        if user.role == "employee" and user.employee_id == request.employee_id:
            return
        if user.role == "approver" and request.approver_id == user.user_id:
            return
        if user.role in {"verifier", "admin_hc", "auditor"}:
            return
        raise ForbiddenError("Tidak memiliki akses ke permohonan ini.")

    def _ensure_employee_can_create(self, employee: Employee):
        if employee.status == "active":
            return
        if employee.deactivated_at and employee.deactivated_at >= utcnow() - timedelta(days=31):
            return
        raise BusinessRuleError("Pegawai nonaktif melewati batas 1 bulan tidak dapat membuat permohonan baru.")

    def _validate_additional_fields(self, template: CertificateTemplate, additional_fields: dict):
        schema = template.additional_field_schema or {}
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise ValidationError("Schema field tambahan template tidak valid.", "additional_field_schema")
        for field in required:
            if field not in additional_fields or additional_fields[field] in (None, ""):
                raise ValidationError("Field tambahan wajib diisi.", f"additional_fields.{field}")

    def _add_event(
        self,
        request: WorkCertificateRequest,
        user: CurrentUser,
        action: str,
        from_status: str | None,
        to_status: str,
        note: str | None = None,
        visible_to_employee: bool = False,
    ):
        self.session.add(
            WorkflowEvent(
                request_id=request.id,
                actor_user_id=user.user_id,
                actor_role=user.role,
                action=action,
                from_status=from_status,
                to_status=to_status,
                note=note,
                visible_to_employee=visible_to_employee,
            )
        )

    def _commit_or_conflict(self, message: str):
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(message) from exc
