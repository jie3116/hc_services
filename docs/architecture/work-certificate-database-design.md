# Work Certificate Database Design

Dokumen ini adalah output Database Agent untuk modul Surat Keterangan Kerja. Desain ini menurunkan `docs/architecture/work-certificate-backend-architecture.md` menjadi model SQLAlchemy, rencana migration PostgreSQL, constraint, index, query pattern, rollback, dan risiko production.

## Requirement Summary and Assumptions

- Modul memakai Flask + SQLAlchemy + PostgreSQL.
- Satu permohonan Surat Keterangan Kerja punya satu pegawai, satu template snapshot, satu verifikator aktual, satu approver, dan maksimal satu dokumen issued.
- Approval dan issuing berjalan dalam satu use case aplikasi; status public akhir sukses adalah `issued`.
- Dokumen final immutable setelah issued. Koreksi dilakukan lewat request baru atau proses reissue terpisah yang belum masuk MVP.
- Retensi dokumen final dan audit trail adalah 3 tahun.
- SLA memakai 3 hari kalender.
- Volume awal diasumsikan ribuan sampai ratusan ribu request per tahun; semua list endpoint wajib paginated.
- Identity user global belum ada di schema ini, sehingga kolom `*_user_id` disimpan sebagai UUID tanpa foreign key lintas service sampai modul auth tersedia.

## Tables and SQLAlchemy Model Plan

Gunakan SQLAlchemy 2.x declarative style. Semua timestamp memakai `DateTime(timezone=True)` dan diisi oleh service dengan clock timezone-aware, dengan `server_default=func.now()` hanya untuk timestamp teknis yang aman.

### Enum Values

Enum disarankan dibuat sebagai PostgreSQL enum untuk integritas status:

- `employee_status`: `active`, `inactive`
- `work_certificate_request_status`: `draft`, `submitted`, `returned_to_employee`, `verified`, `returned_to_hc`, `issued`, `rejected`, `cancelled`
- `work_certificate_owner_role`: `employee`, `verifier`, `approver`
- `document_file_format`: `pdf`, `docx`

Catatan: status `approved` tidak disimpan sebagai status akhir request pada MVP karena arsitektur memodelkan approve + issue sebagai satu transaksi sukses. Event `approve` tetap dicatat di workflow event.

### `employees`

Purpose: master data minimum untuk render surat dan eligibility permohonan.

Columns:
- `id` UUID primary key.
- `employee_number` varchar(64) not null.
- `full_name` varchar(255) not null.
- `work_email` varchar(255) nullable.
- `unit` varchar(255) not null.
- `position_title` varchar(255) not null.
- `work_location` varchar(255) not null.
- `employment_type` varchar(64) not null.
- `start_date` date not null.
- `status` employee_status not null.
- `deactivated_at` timestamptz nullable.
- `supervisor_name` varchar(255) nullable.
- `created_at` timestamptz not null.
- `updated_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_employees`.
- Unique `uq_employees_employee_number`.
- Index `ix_employees_work_email` on `work_email`.
- Index `ix_employees_unit_full_name` on `(unit, full_name)`.
- Check `ck_employees_inactive_has_deactivated_at`: `(status = 'active' AND deactivated_at IS NULL) OR (status = 'inactive' AND deactivated_at IS NOT NULL)`.
- Check `ck_employees_start_before_deactivated`: `deactivated_at IS NULL OR deactivated_at::date >= start_date`.

Production note: eligibility inactive <= 1 month is time-relative, so enforce it in service logic, not check constraint.

### `certificate_templates`

Purpose: template aktif/nonaktif dan schema field tambahan untuk request baru.

Columns:
- `id` UUID primary key.
- `code` varchar(64) not null.
- `name` varchar(255) not null.
- `description` text nullable.
- `language` varchar(16) not null.
- `body_template` text not null.
- `required_placeholders` jsonb not null default `[]`.
- `additional_field_schema` jsonb not null default `{}`.
- `is_active` boolean not null default false.
- `version` integer not null.
- `created_by` UUID nullable.
- `updated_by` UUID nullable.
- `created_at` timestamptz not null.
- `updated_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_certificate_templates`.
- Unique `uq_certificate_templates_code`.
- Unique `uq_certificate_templates_code_version` on `(code, version)`.
- Check `ck_certificate_templates_version_positive`: `version > 0`.
- Check `ck_certificate_templates_language_not_blank`: `length(trim(language)) > 0`.
- Index `ix_certificate_templates_active_language` on `(is_active, language, name)`.

Production note: only one active template per `code` may be desired later. If business confirms versioned active templates by code, add partial unique index `WHERE is_active`; do not add it now without explicit rule because current architecture only says `code` unique.

### `work_certificate_requests`

Purpose: aggregate root untuk workflow permohonan.

Columns:
- `id` UUID primary key.
- `tracking_number` varchar(64) not null.
- `employee_id` UUID not null foreign key to `employees.id`.
- `template_id` UUID not null foreign key to `certificate_templates.id`.
- `template_snapshot` jsonb not null.
- `purpose` text not null.
- `language` varchar(16) not null.
- `additional_fields` jsonb not null default `{}`.
- `employee_note` text nullable.
- `status` work_certificate_request_status not null.
- `submitted_at` timestamptz nullable.
- `verified_at` timestamptz nullable.
- `verified_by` UUID nullable.
- `approver_id` UUID nullable.
- `approved_at` timestamptz nullable.
- `issued_at` timestamptz nullable.
- `rejected_at` timestamptz nullable.
- `cancelled_at` timestamptz nullable.
- `current_owner_role` work_certificate_owner_role nullable.
- `sla_due_at` timestamptz nullable.
- `sla_overdue_at` timestamptz nullable.
- `created_at` timestamptz not null.
- `updated_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_requests`.
- Foreign key `fk_wcr_employee_id_employees` with `ON DELETE RESTRICT`.
- Foreign key `fk_wcr_template_id_certificate_templates` with `ON DELETE RESTRICT`.
- Unique `uq_wcr_tracking_number`.
- Check `ck_wcr_purpose_length`: `length(trim(purpose)) BETWEEN 1 AND 1000`.
- Check `ck_wcr_employee_note_length`: `employee_note IS NULL OR length(employee_note) <= 2000`.
- Check `ck_wcr_submitted_timestamp`: `status <> 'submitted' OR submitted_at IS NOT NULL`.
- Check `ck_wcr_verified_fields`: `status <> 'verified' OR (verified_at IS NOT NULL AND verified_by IS NOT NULL AND approver_id IS NOT NULL)`.
- Check `ck_wcr_issued_fields`: `status <> 'issued' OR (approved_at IS NOT NULL AND issued_at IS NOT NULL)`.
- Check `ck_wcr_rejected_timestamp`: `status <> 'rejected' OR rejected_at IS NOT NULL`.
- Check `ck_wcr_cancelled_timestamp`: `status <> 'cancelled' OR cancelled_at IS NOT NULL`.
- Index `ix_wcr_employee_created_at` on `(employee_id, created_at DESC)`.
- Index `ix_wcr_status_updated_at` on `(status, updated_at DESC)`.
- Index `ix_wcr_approver_status` on `(approver_id, status)`.
- Index `ix_wcr_owner_sla_due` on `(current_owner_role, sla_due_at)` where `sla_due_at IS NOT NULL`.
- Index `ix_wcr_template_created_at` on `(template_id, created_at DESC)`.

Concurrency:
- Mutating workflow operations must select this row `FOR UPDATE`.
- Duplicate issue is prevented by request row lock and unique `work_certificate_issued_documents.request_id`.

### `work_certificate_workflow_events`

Purpose: append-only audit trail untuk workflow, termasuk download dan system events.

Columns:
- `id` UUID primary key.
- `request_id` UUID not null foreign key to `work_certificate_requests.id`.
- `actor_user_id` UUID nullable.
- `actor_role` varchar(64) not null.
- `action` varchar(64) not null.
- `from_status` varchar(64) nullable.
- `to_status` varchar(64) not null.
- `note` text nullable.
- `visible_to_employee` boolean not null default false.
- `metadata` jsonb not null default `{}`.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_workflow_events`.
- Foreign key `fk_wcwfe_request_id_wcr` with `ON DELETE RESTRICT`.
- Check `ck_wcwfe_note_length`: `note IS NULL OR length(note) <= 2000`.
- Index `ix_wcwfe_request_created_at` on `(request_id, created_at)`.
- Index `ix_wcwfe_created_at` on `(created_at)`.
- Index `ix_wcwfe_action_created_at` on `(action, created_at DESC)`.

Production note: keep `metadata` small. Do not store full document payload, rendered content, or secrets.

### `work_certificate_issued_documents`

Purpose: immutable metadata dokumen final.

Columns:
- `id` UUID primary key.
- `request_id` UUID not null foreign key to `work_certificate_requests.id`.
- `letter_number` varchar(64) not null.
- `letter_sequence_number` integer not null.
- `letter_year` integer not null.
- `issued_at` timestamptz not null.
- `approver_user_id` UUID not null.
- `approver_name` varchar(255) not null.
- `approver_position_title` varchar(255) not null.
- `barcode_payload_hash` varchar(128) not null.
- `content_hash` varchar(128) not null.
- `retention_expires_at` timestamptz not null.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_issued_documents`.
- Foreign key `fk_wcid_request_id_wcr` with `ON DELETE RESTRICT`.
- Unique `uq_wcid_request_id`.
- Unique `uq_wcid_letter_number`.
- Unique `uq_wcid_letter_year_sequence` on `(letter_year, letter_sequence_number)`.
- Check `ck_wcid_sequence_positive`: `letter_sequence_number > 0`.
- Check `ck_wcid_letter_year_range`: `letter_year BETWEEN 2000 AND 2999`.
- Check `ck_wcid_retention_after_issued`: `retention_expires_at > issued_at`.
- Index `ix_wcid_retention_expires_at` on `(retention_expires_at)`.

Immutability:
- Do not update this table from application code after insert.
- PostgreSQL trigger can enforce immutable fields after implementation stabilizes. If added, migration must document operational rollback because triggers can block repair operations.

### `work_certificate_document_files`

Purpose: storage metadata untuk file PDF dan DOCX.

Columns:
- `id` UUID primary key.
- `issued_document_id` UUID not null foreign key to `work_certificate_issued_documents.id`.
- `format` document_file_format not null.
- `storage_key` varchar(1024) not null.
- `mime_type` varchar(128) not null.
- `file_size_bytes` bigint not null.
- `sha256` varchar(64) not null.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_document_files`.
- Foreign key `fk_wcdf_issued_document_id_wcid` with `ON DELETE RESTRICT`.
- Unique `uq_wcdf_issued_document_format` on `(issued_document_id, format)`.
- Unique `uq_wcdf_storage_key`.
- Check `ck_wcdf_file_size_positive`: `file_size_bytes > 0`.
- Check `ck_wcdf_sha256_length`: `length(sha256) = 64`.
- Index `ix_wcdf_sha256` on `(sha256)`.

### `work_certificate_letter_sequences`

Purpose: allocator nomor surat tahunan.

Columns:
- `year` integer primary key.
- `last_number` integer not null default 0.
- `updated_at` timestamptz not null.

Constraints:
- Primary key `pk_work_certificate_letter_sequences`.
- Check `ck_wcls_year_range`: `year BETWEEN 2000 AND 2999`.
- Check `ck_wcls_last_number_non_negative`: `last_number >= 0`.

Allocation algorithm:
1. Insert row for current year if missing with `last_number = 0`.
2. Select row `FOR UPDATE`.
3. Increment `last_number`.
4. Use incremented value as `letter_sequence_number`.
5. Insert issued document in the same transaction.

### `work_certificate_verification_tokens`

Purpose: public barcode validation tanpa membocorkan PII.

Columns:
- `id` UUID primary key.
- `issued_document_id` UUID not null foreign key to `work_certificate_issued_documents.id`.
- `token_hash` varchar(128) not null.
- `public_code` varchar(128) not null.
- `expires_at` timestamptz nullable.
- `revoked_at` timestamptz nullable.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_verification_tokens`.
- Foreign key `fk_wcvt_issued_document_id_wcid` with `ON DELETE RESTRICT`.
- Unique `uq_wcvt_issued_document_id`.
- Unique `uq_wcvt_token_hash`.
- Unique `uq_wcvt_public_code`.
- Index `ix_wcvt_public_code_active` on `(public_code)` where `revoked_at IS NULL`.
- Check `ck_wcvt_expiry_after_created`: `expires_at IS NULL OR expires_at > created_at`.

Security note: store only hash of secret token. `public_code` must be opaque and unguessable enough for lookup; endpoint response stays minimal.

### `work_certificate_sla_events`

Purpose: event SLA untuk overdue/notification tracking.

Columns:
- `id` UUID primary key.
- `request_id` UUID not null foreign key to `work_certificate_requests.id`.
- `status` varchar(64) not null.
- `due_at` timestamptz not null.
- `overdue_at` timestamptz nullable.
- `notified_at` timestamptz nullable.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_work_certificate_sla_events`.
- Foreign key `fk_wcse_request_id_wcr` with `ON DELETE RESTRICT`.
- Check `ck_wcse_overdue_after_due`: `overdue_at IS NULL OR overdue_at >= due_at`.
- Check `ck_wcse_notified_after_created`: `notified_at IS NULL OR notified_at >= created_at`.
- Index `ix_wcse_request_created_at` on `(request_id, created_at DESC)`.
- Index `ix_wcse_due_at` on `(due_at)`.

### `notification_events`

Purpose: outbox ringan untuk notifikasi SLA atau workflow.

Columns:
- `id` UUID primary key.
- `event_type` varchar(64) not null.
- `recipient_user_id` UUID nullable.
- `recipient_role` varchar(64) nullable.
- `request_id` UUID nullable foreign key to `work_certificate_requests.id`.
- `payload` jsonb not null default `{}`.
- `status` varchar(32) not null default `pending`.
- `available_at` timestamptz not null.
- `processed_at` timestamptz nullable.
- `failed_at` timestamptz nullable.
- `failure_reason` text nullable.
- `created_at` timestamptz not null.

Constraints and indexes:
- Primary key `pk_notification_events`.
- Foreign key `fk_notification_events_request_id_wcr` with `ON DELETE SET NULL`.
- Check `ck_notification_events_status`: `status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')`.
- Check `ck_notification_events_failure_reason_length`: `failure_reason IS NULL OR length(failure_reason) <= 1000`.
- Index `ix_notification_events_pending` on `(status, available_at, created_at)` where `status = 'pending'`.
- Index `ix_notification_events_request_created_at` on `(request_id, created_at DESC)`.

## Migration Plan

Create one additive Alembic revision for MVP schema:

1. Enable UUID support if not already available:
   - Prefer application-generated UUIDs.
   - If DB defaults are needed, use `pgcrypto` and `gen_random_uuid()`.
2. Create PostgreSQL enum types.
3. Create tables in dependency order:
   - `employees`
   - `certificate_templates`
   - `work_certificate_requests`
   - `work_certificate_workflow_events`
   - `work_certificate_letter_sequences`
   - `work_certificate_issued_documents`
   - `work_certificate_document_files`
   - `work_certificate_verification_tokens`
   - `work_certificate_sla_events`
   - `notification_events`
4. Create indexes and partial indexes.
5. Seed is not part of this migration. Initial templates and sequence year rows should be separate controlled data migrations or admin operations.

Downgrade:
- Drop tables in reverse dependency order.
- Drop enum types after dependent tables are removed.
- Do not drop shared extensions such as `pgcrypto` in downgrade because other modules may use them.

Lock and downtime assessment:
- New empty tables are low risk.
- Enum creation is low risk.
- No existing table rewrite is required because MVP schema is additive.
- Future migrations adding `NOT NULL` columns to populated tables must use expand/backfill/contract.

## Backfill and Rollback Plan

MVP initial migration:
- No backfill required.
- Rollback can drop new tables before production data exists.

After production data exists:
- Dropping tables is destructive and requires explicit approval.
- Rollback application first if migration was already used by code.
- Data rollback for issued documents is generally not safe because letter numbers and audit trail are legal records. Prefer forward fix with repair migration.
- Large future backfills must run in batches, commit per batch, log counts, and expose progress.

## Query Pattern and Index Coverage

Employee request list:
- Filter `employee_id`, optional `status`, order `created_at DESC`, paginate.
- Covered by `ix_wcr_employee_created_at`; add `(employee_id, status, created_at DESC)` later only if status filtering dominates.

Verifier queue:
- Filter `status IN ('submitted', 'returned_to_hc')`, optional `unit`, optional overdue, order `updated_at DESC`.
- Base index `ix_wcr_status_updated_at` supports status queue. Unit filtering joins `employees`; use `employees.unit` index.

Approver queue:
- Filter `approver_id`, `status = 'verified'`, order `updated_at DESC`.
- Covered by `ix_wcr_approver_status`; consider `(approver_id, status, updated_at DESC)` if queue grows.

SLA scanner:
- Filter `sla_due_at <= now`, `sla_overdue_at IS NULL`, non-final status, lock rows in batches.
- Covered by partial `ix_wcr_owner_sla_due`.

Audit timeline:
- Filter `request_id`, order `created_at`.
- Covered by `ix_wcwfe_request_created_at`.

Public barcode validation:
- Lookup `public_code` where `revoked_at IS NULL`, join issued document.
- Covered by unique `public_code` and partial active index.

Retention job:
- Filter issued documents by `retention_expires_at <= now`.
- Covered by `ix_wcid_retention_expires_at`.

## Production Migration Risks

- Race condition nomor surat: must use transaction and `SELECT ... FOR UPDATE` on `work_certificate_letter_sequences`; never calculate next number by `max(letter_sequence_number)`.
- Partial external side effects: file rendering/storage is outside DB transaction. Render to temporary location before DB insert where possible, and use repair/admin flow for post-commit storage failures.
- Immutable legal data: avoid update paths for issued document metadata. Any repair update must be audited and limited.
- Public token leakage: never store raw validation token, never return employee PII from barcode validation endpoint.
- Enum evolution: adding status values later requires Alembic migration. Avoid adding `issue_failed` without ADR because it changes public state machine.
- Retention deletion: purging audit/document rows is destructive and must be a separate approved migration/job with dry-run counts.
- Index bloat: JSONB fields are not indexed initially. Add GIN indexes only after a proven query pattern exists.

## Test Plan

Migration tests:
- `alembic upgrade head`.
- Verify all tables, foreign keys, unique constraints, check constraints, and partial indexes exist.
- `alembic downgrade -1` on an empty database, then upgrade again.

Model/integration tests:
- Duplicate `employee_number` fails.
- Duplicate `tracking_number` fails.
- Invalid request timestamp/status combinations fail.
- Duplicate `issued_document.request_id` fails.
- Duplicate `(letter_year, letter_sequence_number)` fails.
- Duplicate `(issued_document_id, format)` fails.
- Two concurrent approval attempts produce one issued document and one letter number.
- SLA scanner query processes rows in pages/batches.

Performance tests when data volume exists:
- `EXPLAIN ANALYZE` verifier queue, approver queue, employee history, SLA scanner, public validation lookup.

## Handoff to Backend Implementation Agent

## Context
- Feature: Surat Keterangan Kerja database schema.
- Scope: SQLAlchemy models, Alembic migration, PostgreSQL constraints/indexes, audit, issued document metadata, SLA, notification outbox.
- Non-goals: auth user tables, physical file storage tables beyond metadata, certified digital signature, destructive retention purge job.

## Decisions
- Decision: use PostgreSQL enum for stable workflow/status fields.
- Reason: keeps invalid states out of the database.
- Decision: issue letter number through annual sequence row lock.
- Reason: prevents duplicate legal numbers under concurrent approval.
- Decision: keep raw validation token out of database.
- Reason: reduces impact if database content is exposed.
- Decision: avoid initial JSONB GIN indexes.
- Reason: no proven high-volume JSONB search pattern yet.

## Files/Modules
- Planned: `hc_services/modules/work_certificates/models.py`, Alembic revision under migration directory, migration tests.
- Changed: `docs/architecture/work-certificate-database-design.md`.

## Contracts
- API: no change from backend architecture.
- Database: tables and constraints in this document.
- UI: no direct database contract; UI consumes backend API only.

## Verification
- Tests run: documentation-only database design, no automated tests required.
- Tests still needed: Alembic upgrade/downgrade tests, constraint tests, concurrency test for issue transaction, queue query explain checks.

## Risks
- Blocking: project still needs Flask/SQLAlchemy/Alembic scaffolding before runnable migration can be created.
- Non-blocking: trigger-based immutability can be added later after repair flow policy is clear.
