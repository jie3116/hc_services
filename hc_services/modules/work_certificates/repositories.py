from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from hc_services.modules.work_certificates.models import (
    CertificateTemplate,
    Employee,
    IssuedDocument,
    LetterNumberSequence,
    RequestStatus,
    VerificationToken,
    WorkCertificateRequest,
)


def paginate(stmt: Select, page_number: int, page_size: int):
    page_number = max(page_number, 1)
    page_size = min(max(page_size, 1), 100)
    return stmt.limit(page_size).offset((page_number - 1) * page_size)


class WorkCertificateRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_employee(self, employee_id: str) -> Employee | None:
        return self.session.get(Employee, employee_id)

    def get_template(self, template_id: str) -> CertificateTemplate | None:
        return self.session.get(CertificateTemplate, template_id)

    def list_templates(self, active: bool | None, language: str | None) -> list[CertificateTemplate]:
        stmt = select(CertificateTemplate).order_by(CertificateTemplate.name.asc())
        if active is not None:
            stmt = stmt.where(CertificateTemplate.is_active.is_(active))
        if language:
            stmt = stmt.where(CertificateTemplate.language == language)
        return list(self.session.scalars(stmt))

    def get_request(self, request_id: str) -> WorkCertificateRequest | None:
        stmt = (
            select(WorkCertificateRequest)
            .execution_options(populate_existing=True)
            .options(
                joinedload(WorkCertificateRequest.employee),
                joinedload(WorkCertificateRequest.template),
                selectinload(WorkCertificateRequest.events),
                selectinload(WorkCertificateRequest.issued_document).selectinload(IssuedDocument.files),
            )
            .where(WorkCertificateRequest.id == request_id)
        )
        return self.session.scalars(stmt).first()

    def list_requests(
        self,
        *,
        role: str,
        user_id: str,
        employee_id: str | None,
        status: str | None,
        page_number: int,
        page_size: int,
    ) -> list[WorkCertificateRequest]:
        stmt = (
            select(WorkCertificateRequest)
            .options(joinedload(WorkCertificateRequest.employee), joinedload(WorkCertificateRequest.template))
            .order_by(WorkCertificateRequest.created_at.desc())
        )
        if status:
            stmt = stmt.where(WorkCertificateRequest.status == status)
        if role == "employee":
            stmt = stmt.where(WorkCertificateRequest.employee_id == employee_id)
        elif role == "approver":
            stmt = stmt.where(WorkCertificateRequest.approver_id == user_id)
        elif role == "verifier":
            stmt = stmt.where(WorkCertificateRequest.status.in_([RequestStatus.SUBMITTED, RequestStatus.RETURNED_TO_HC]))
        elif role not in {"admin_hc", "auditor"}:
            stmt = stmt.where(False)
        return list(self.session.scalars(paginate(stmt, page_number, page_size)))

    def next_tracking_number(self, year: int) -> str:
        count = self.session.scalar(
            select(func.count()).select_from(WorkCertificateRequest).where(WorkCertificateRequest.tracking_number.like(f"SKK-{year}-%"))
        )
        return f"SKK-{year}-{int(count or 0) + 1:06d}"

    def allocate_letter_number(self, year: int) -> tuple[int, str]:
        sequence = self.session.get(LetterNumberSequence, year)
        if sequence is None:
            sequence = LetterNumberSequence(year=year, last_number=0)
            self.session.add(sequence)
            self.session.flush()
        sequence.last_number += 1
        self.session.flush()
        return sequence.last_number, f"{sequence.last_number:03d}/KP.204/KI-{year}"

    def get_token_by_public_code(self, public_code: str) -> VerificationToken | None:
        stmt = (
            select(VerificationToken)
            .options(joinedload(VerificationToken.issued_document))
            .where(VerificationToken.public_code == public_code, VerificationToken.revoked_at.is_(None))
        )
        return self.session.scalars(stmt).first()
