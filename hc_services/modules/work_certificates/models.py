from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from hc_services.extensions import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RequestStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RETURNED_TO_EMPLOYEE = "returned_to_employee"
    VERIFIED = "verified"
    RETURNED_TO_HC = "returned_to_hc"
    ISSUED = "issued"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

    FINAL = {ISSUED, REJECTED, CANCELLED}


class OwnerRole:
    EMPLOYEE = "employee"
    VERIFIER = "verifier"
    APPROVER = "approver"


class DocumentFormat:
    PDF = "pdf"
    DOCX = "docx"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    employee_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    work_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str] = mapped_column(String(255), nullable=False)
    position_title: Mapped[str] = mapped_column(String(255), nullable=False)
    work_location: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[str] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supervisor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    requests: Mapped[list[WorkCertificateRequest]] = relationship(back_populates="employee")

    __table_args__ = (
        CheckConstraint("status in ('active', 'inactive')", name="ck_employees_status"),
        CheckConstraint(
            "(status = 'active' and deactivated_at is null) or (status = 'inactive' and deactivated_at is not null)",
            name="ck_employees_inactive_has_deactivated_at",
        ),
        Index("ix_employees_work_email", "work_email"),
        Index("ix_employees_unit_full_name", "unit", "full_name"),
    )


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    required_placeholders: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    additional_field_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    requests: Mapped[list[WorkCertificateRequest]] = relationship(back_populates="template")

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_certificate_templates_code_version"),
        CheckConstraint("version > 0", name="ck_certificate_templates_version_positive"),
        Index("ix_certificate_templates_active_language", "is_active", "language", "name"),
    )


class WorkCertificateRequest(Base):
    __tablename__ = "work_certificate_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tracking_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("certificate_templates.id", ondelete="RESTRICT"), nullable=False)
    template_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    additional_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    employee_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RequestStatus.DRAFT)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_owner_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_overdue_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="requests")
    template: Mapped[CertificateTemplate] = relationship(back_populates="requests")
    events: Mapped[list[WorkflowEvent]] = relationship(back_populates="request", order_by="WorkflowEvent.created_at")
    issued_document: Mapped[IssuedDocument | None] = relationship(back_populates="request", uselist=False)

    __table_args__ = (
        CheckConstraint("length(trim(purpose)) between 1 and 1000", name="ck_wcr_purpose_length"),
        CheckConstraint("employee_note is null or length(employee_note) <= 2000", name="ck_wcr_employee_note_length"),
        Index("ix_wcr_employee_created_at", "employee_id", "created_at"),
        Index("ix_wcr_status_updated_at", "status", "updated_at"),
        Index("ix_wcr_approver_status", "approver_id", "status"),
        Index("ix_wcr_owner_sla_due", "current_owner_role", "sla_due_at"),
    )


class WorkflowEvent(Base):
    __tablename__ = "work_certificate_workflow_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    request_id: Mapped[str] = mapped_column(ForeignKey("work_certificate_requests.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    visible_to_employee: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request: Mapped[WorkCertificateRequest] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint("note is null or length(note) <= 2000", name="ck_wcwfe_note_length"),
        Index("ix_wcwfe_request_created_at", "request_id", "created_at"),
        Index("ix_wcwfe_created_at", "created_at"),
    )


class LetterNumberSequence(Base):
    __tablename__ = "work_certificate_letter_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("year between 2000 and 2999", name="ck_wcls_year_range"),
        CheckConstraint("last_number >= 0", name="ck_wcls_last_number_non_negative"),
    )


class IssuedDocument(Base):
    __tablename__ = "work_certificate_issued_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    request_id: Mapped[str] = mapped_column(ForeignKey("work_certificate_requests.id", ondelete="RESTRICT"), nullable=False, unique=True)
    letter_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    letter_sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    letter_year: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approver_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_position_title: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request: Mapped[WorkCertificateRequest] = relationship(back_populates="issued_document")
    files: Mapped[list[DocumentFile]] = relationship(back_populates="issued_document")
    verification_token: Mapped[VerificationToken | None] = relationship(back_populates="issued_document", uselist=False)

    __table_args__ = (
        UniqueConstraint("letter_year", "letter_sequence_number", name="uq_wcid_letter_year_sequence"),
        CheckConstraint("letter_sequence_number > 0", name="ck_wcid_sequence_positive"),
        CheckConstraint("letter_year between 2000 and 2999", name="ck_wcid_letter_year_range"),
        Index("ix_wcid_retention_expires_at", "retention_expires_at"),
    )


class DocumentFile(Base):
    __tablename__ = "work_certificate_document_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    issued_document_id: Mapped[str] = mapped_column(ForeignKey("work_certificate_issued_documents.id", ondelete="RESTRICT"), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    issued_document: Mapped[IssuedDocument] = relationship(back_populates="files")

    __table_args__ = (
        UniqueConstraint("issued_document_id", "format", name="uq_wcdf_issued_document_format"),
        CheckConstraint("format in ('pdf', 'docx')", name="ck_wcdf_format"),
        CheckConstraint("file_size_bytes > 0", name="ck_wcdf_file_size_positive"),
        CheckConstraint("length(sha256) = 64", name="ck_wcdf_sha256_length"),
    )


class VerificationToken(Base):
    __tablename__ = "work_certificate_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    issued_document_id: Mapped[str] = mapped_column(ForeignKey("work_certificate_issued_documents.id", ondelete="RESTRICT"), nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    public_code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    issued_document: Mapped[IssuedDocument] = relationship(back_populates="verification_token")


class SlaEvent(Base):
    __tablename__ = "work_certificate_sla_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    request_id: Mapped[str] = mapped_column(ForeignKey("work_certificate_requests.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overdue_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_wcse_request_created_at", "request_id", "created_at"),)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recipient_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("work_certificate_requests.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status in ('pending', 'processing', 'sent', 'failed', 'cancelled')", name="ck_notification_events_status"),
        Index("ix_notification_events_pending", "status", "available_at", "created_at"),
    )
