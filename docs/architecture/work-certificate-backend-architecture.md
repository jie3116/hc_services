# Work Certificate Backend Architecture

Dokumen ini adalah output Backend Architect Agent untuk modul Surat Keterangan Kerja. Desain ini menerjemahkan requirement produk menjadi boundary service, module, endpoint, schema, dan transaction flow yang bisa dipakai oleh Database Agent, Backend Implementation Agent, Web Frontend Agent, dan Flutter Mobile Agent.

## Requirement Summary

- Pegawai membuat dan melacak permohonan Surat Keterangan Kerja.
- Verifikator HC memeriksa, mengembalikan, menolak, atau meneruskan permohonan.
- Satu permohonan hanya melewati satu verifikator dan satu approver.
- Approver menyetujui atau mengembalikan permohonan ke HC.
- Setelah approval, sistem menerbitkan dokumen immutable dalam PDF dan DOCX.
- Nomor surat final memakai format `[nomor urut]/KP.204/KI-[TAHUN]`.
- Approval divalidasi melalui barcode, bukan tanda tangan gambar atau e-signature tersertifikasi pada MVP.
- Pegawai nonaktif masih boleh membuat permohonan baru maksimal 1 bulan setelah tanggal dinonaktifkan.
- Retensi dokumen dan audit trail adalah 3 tahun.
- Permohonan yang menunggu lebih dari SLA 3 hari kalender perlu notifikasi atau eskalasi.

## Framework Decision

Gunakan Flask sebagai framework backend utama.

Reason:
- Requirement proyek menetapkan SQLAlchemy sebagai ORM/data access.
- Codebase saat ini belum memiliki struktur Django atau Flask yang dominan; `main.py` masih berupa sample script.
- Flask + SQLAlchemy menjaga boundary service eksplisit dan menghindari dua ORM aktif bila memilih Django.
- Modul ini cocok dengan app factory, blueprint API, service layer, repository/query layer, dan transaction boundary eksplisit.

Non-decision:
- Jangan mencampur Django untuk service yang sama kecuali ada ADR baru yang menjelaskan migrasi framework.

## Service Boundary

Modul `work_certificates` bertanggung jawab atas:
- Employee master read/write minimum untuk kebutuhan surat.
- Template surat dan validasi placeholder.
- Permohonan Surat Keterangan Kerja.
- Workflow verification dan approval.
- Reservasi nomor surat dan penerbitan dokumen.
- Barcode validation token.
- Audit trail workflow, download, SLA, dan retention metadata.

Di luar boundary modul:
- Authentication dan session/token identity.
- Role assignment global.
- File storage provider fisik.
- Scheduler runtime.
- Email/WhatsApp/SMS provider.
- Certified digital signature.

Integrasi internal dilakukan melalui interface:
- `CurrentUserProvider`: user id, employee id, roles.
- `FileStorage`: simpan, baca, dan hapus/arsip file dokumen.
- `DocumentRenderer`: render DOCX dan PDF dari template snapshot.
- `BarcodeProvider`: generate barcode image/value dari verification token.
- `NotificationPort`: kirim atau enqueue notifikasi SLA.
- `Clock`: waktu server yang timezone-aware.

## Proposed Modules

```text
hc_services/
  app.py
  config.py
  extensions.py
  modules/
    work_certificates/
      __init__.py
      routes.py
      schemas.py
      models.py
      services.py
      repositories.py
      permissions.py
      state_machine.py
      numbering.py
      document_generation.py
      barcode.py
      sla.py
      retention.py
      errors.py
      tests/
```

Responsibilities:
- `routes.py`: HTTP boundary, auth extraction, schema validation, response mapping.
- `schemas.py`: request/response DTO using Marshmallow or Pydantic; choose one globally during implementation.
- `models.py`: SQLAlchemy ORM entities.
- `services.py`: business use cases and transaction orchestration.
- `repositories.py`: query helpers, pagination, row locking.
- `permissions.py`: owner and role checks.
- `state_machine.py`: allowed transitions and status guards.
- `numbering.py`: annual letter number allocation.
- `document_generation.py`: immutable template snapshot rendering to DOCX/PDF.
- `barcode.py`: validation token and barcode payload builder.
- `sla.py`: due date calculation, overdue marker, notification enqueue.
- `retention.py`: retention eligibility and archive/purge planning.

## Domain Model

Core entities:
- `Employee`
- `CertificateTemplate`
- `WorkCertificateRequest`
- `WorkflowEvent`
- `IssuedDocument`
- `DocumentFile`
- `LetterNumberSequence`
- `DocumentVerificationToken`
- `SlaEvent`
- `NotificationEvent`

Recommended SQLAlchemy table names:
- `employees`
- `certificate_templates`
- `work_certificate_requests`
- `work_certificate_workflow_events`
- `work_certificate_issued_documents`
- `work_certificate_document_files`
- `work_certificate_letter_sequences`
- `work_certificate_verification_tokens`
- `work_certificate_sla_events`
- `notification_events`

## Schema Plan

### employees

Fields:
- `id` UUID primary key.
- `employee_number` varchar unique not null.
- `full_name` varchar not null.
- `work_email` varchar nullable, indexed.
- `unit` varchar not null.
- `position_title` varchar not null.
- `work_location` varchar not null.
- `employment_type` varchar not null.
- `start_date` date not null.
- `status` enum `active`, `inactive` not null.
- `deactivated_at` timestamptz nullable.
- `supervisor_name` varchar nullable.
- `created_at`, `updated_at`.

Rules:
- Employee can create a request when `status = active`.
- Employee can create a request when `status = inactive` and `deactivated_at >= now - interval '1 month'`.
- Inactive employees after that window retain history/download access according to permission and retention.

### certificate_templates

Fields:
- `id` UUID primary key.
- `code` varchar unique not null.
- `name` varchar not null.
- `description` text nullable.
- `language` varchar not null.
- `body_template` text or storage reference not null.
- `required_placeholders` jsonb not null default `[]`.
- `additional_field_schema` jsonb not null default `{}`.
- `is_active` boolean not null default false.
- `version` integer not null.
- `created_at`, `updated_at`, `created_by`, `updated_by`.

Rules:
- Template changes only affect new requests.
- Issued documents use request-time template snapshot.

### work_certificate_requests

Fields:
- `id` UUID primary key.
- `tracking_number` varchar unique not null.
- `employee_id` UUID foreign key not null.
- `template_id` UUID foreign key not null.
- `template_snapshot` jsonb not null.
- `purpose` text not null.
- `language` varchar not null.
- `additional_fields` jsonb not null default `{}`.
- `employee_note` text nullable.
- `status` enum not null.
- `submitted_at` timestamptz nullable.
- `verified_at` timestamptz nullable.
- `verified_by` UUID nullable.
- `approver_id` UUID nullable.
- `approved_at` timestamptz nullable.
- `issued_at` timestamptz nullable.
- `rejected_at` timestamptz nullable.
- `cancelled_at` timestamptz nullable.
- `current_owner_role` enum nullable.
- `sla_due_at` timestamptz nullable.
- `sla_overdue_at` timestamptz nullable.
- `created_at`, `updated_at`.

Indexes:
- `(employee_id, created_at desc)`.
- `(status, updated_at desc)`.
- `(approver_id, status)`.
- `(current_owner_role, sla_due_at)`.

### work_certificate_workflow_events

Fields:
- `id` UUID primary key.
- `request_id` UUID foreign key not null.
- `actor_user_id` UUID nullable for system events.
- `actor_role` varchar not null.
- `action` varchar not null.
- `from_status` varchar nullable.
- `to_status` varchar not null.
- `note` text nullable.
- `visible_to_employee` boolean not null default false.
- `metadata` jsonb not null default `{}`.
- `created_at` timestamptz not null.

Indexes:
- `(request_id, created_at)`.
- `(created_at)` for retention jobs.

### work_certificate_issued_documents

Fields:
- `id` UUID primary key.
- `request_id` UUID unique foreign key not null.
- `letter_number` varchar unique not null.
- `letter_sequence_number` integer not null.
- `letter_year` integer not null.
- `issued_at` timestamptz not null.
- `approver_user_id` UUID not null.
- `approver_name` varchar not null.
- `approver_position_title` varchar not null.
- `barcode_payload_hash` varchar not null.
- `content_hash` varchar not null.
- `retention_expires_at` timestamptz not null.
- `created_at` timestamptz not null.

Constraints:
- Unique `(letter_year, letter_sequence_number)`.
- `letter_number` must be immutable after insert.

### work_certificate_document_files

Fields:
- `id` UUID primary key.
- `issued_document_id` UUID foreign key not null.
- `format` enum `pdf`, `docx` not null.
- `storage_key` varchar not null.
- `mime_type` varchar not null.
- `file_size_bytes` bigint not null.
- `sha256` varchar not null.
- `created_at` timestamptz not null.

Constraint:
- Unique `(issued_document_id, format)`.

### work_certificate_letter_sequences

Fields:
- `year` integer primary key.
- `last_number` integer not null default 0.
- `updated_at` timestamptz not null.

Use `SELECT ... FOR UPDATE` inside issue transaction to allocate the next annual sequence.

### work_certificate_verification_tokens

Fields:
- `id` UUID primary key.
- `issued_document_id` UUID unique foreign key not null.
- `token_hash` varchar unique not null.
- `public_code` varchar unique not null.
- `expires_at` timestamptz nullable.
- `revoked_at` timestamptz nullable.
- `created_at` timestamptz not null.

Public validation endpoint must return minimal document validity metadata only.

### work_certificate_sla_events

Fields:
- `id` UUID primary key.
- `request_id` UUID foreign key not null.
- `status` varchar not null.
- `due_at` timestamptz not null.
- `overdue_at` timestamptz nullable.
- `notified_at` timestamptz nullable.
- `created_at` timestamptz not null.

## API Contract

Base path: `/api/v1/work-certificates`

Response envelope:

```json
{
  "data": {},
  "meta": {},
  "errors": []
}
```

Error envelope:

```json
{
  "data": null,
  "meta": {
    "request_id": "req_abc"
  },
  "errors": [
    {
      "code": "validation_error",
      "message": "Input tidak valid.",
      "field": "purpose"
    }
  ]
}
```

Common HTTP statuses:
- `400`: invalid input.
- `401`: unauthenticated.
- `403`: forbidden.
- `404`: resource not found or inaccessible.
- `409`: invalid state transition, stale version, duplicate/locked number conflict.
- `422`: business rule violation.
- `500`: unexpected server error with generic message.

Pagination query:
- `page[number]`, `page[size]`.
- Default page size 20, max 100.

### Employee APIs

List active templates:

```http
GET /api/v1/work-certificates/templates?active=true&language=id
```

Create draft:

```http
POST /api/v1/work-certificates/requests
Content-Type: application/json

{
  "template_id": "018f2e5b-4e7b-7000-9000-111111111111",
  "purpose": "Pengajuan KPR",
  "language": "id",
  "additional_fields": {
    "recipient": "Bank ABC"
  },
  "employee_note": "Mohon diterbitkan untuk kebutuhan administrasi bank."
}
```

Response `201`:

```json
{
  "data": {
    "id": "018f2e5b-4e7b-7000-9000-222222222222",
    "tracking_number": "SKK-2026-000123",
    "status": "draft",
    "sla_due_at": null,
    "created_at": "2026-08-27T09:00:00+07:00"
  },
  "meta": {},
  "errors": []
}
```

Submit draft:

```http
POST /api/v1/work-certificates/requests/{request_id}/submit
```

List own requests:

```http
GET /api/v1/work-certificates/requests?status=issued&page[number]=1&page[size]=20
```

Get request detail:

```http
GET /api/v1/work-certificates/requests/{request_id}
```

Update returned draft/revision:

```http
PATCH /api/v1/work-certificates/requests/{request_id}
Content-Type: application/json

{
  "purpose": "Pengajuan KPR di Bank ABC",
  "additional_fields": {
    "recipient": "Bank ABC"
  },
  "employee_note": "Revisi tujuan sesuai catatan HC."
}
```

Cancel non-final request:

```http
POST /api/v1/work-certificates/requests/{request_id}/cancel
```

Download issued document:

```http
GET /api/v1/work-certificates/requests/{request_id}/documents/pdf
GET /api/v1/work-certificates/requests/{request_id}/documents/docx
```

### Verifier HC APIs

Verification queue:

```http
GET /api/v1/work-certificates/verifier/requests?status=submitted&unit=Finance&overdue=true&page[number]=1&page[size]=20
```

Return to employee:

```http
POST /api/v1/work-certificates/requests/{request_id}/return-to-employee
Content-Type: application/json

{
  "note": "Tujuan penggunaan surat perlu dibuat lebih spesifik.",
  "visible_to_employee": true
}
```

Reject:

```http
POST /api/v1/work-certificates/requests/{request_id}/reject
Content-Type: application/json

{
  "note": "Permohonan tidak sesuai policy perusahaan."
}
```

Verify and send to approver:

```http
POST /api/v1/work-certificates/requests/{request_id}/verify
Content-Type: application/json

{
  "approver_id": "018f2e5b-4e7b-7000-9000-333333333333",
  "note": "Data pegawai dan tujuan penggunaan valid."
}
```

### Approver APIs

Approver queue:

```http
GET /api/v1/work-certificates/approver/requests?status=verified&page[number]=1&page[size]=20
```

Return to HC:

```http
POST /api/v1/work-certificates/requests/{request_id}/return-to-hc
Content-Type: application/json

{
  "note": "Mohon cek kembali jabatan pegawai."
}
```

Approve:

```http
POST /api/v1/work-certificates/requests/{request_id}/approve
Content-Type: application/json

{
  "note": "Disetujui."
}
```

Response `200`:

```json
{
  "data": {
    "id": "018f2e5b-4e7b-7000-9000-222222222222",
    "status": "issued",
    "issued_document": {
      "letter_number": "001/KP.204/KI-2026",
      "issued_at": "2026-08-27T10:15:00+07:00",
      "available_formats": ["pdf", "docx"]
    }
  },
  "meta": {},
  "errors": []
}
```

### Admin HC APIs

Manage employees:

```http
GET /api/v1/work-certificates/employees?keyword=andi&page[number]=1&page[size]=20
POST /api/v1/work-certificates/employees
GET /api/v1/work-certificates/employees/{employee_id}
PATCH /api/v1/work-certificates/employees/{employee_id}
POST /api/v1/work-certificates/employees/{employee_id}/deactivate
```

Manage templates:

```http
GET /api/v1/work-certificates/admin/templates?page[number]=1&page[size]=20
POST /api/v1/work-certificates/admin/templates
GET /api/v1/work-certificates/admin/templates/{template_id}
PATCH /api/v1/work-certificates/admin/templates/{template_id}
POST /api/v1/work-certificates/admin/templates/{template_id}/activate
POST /api/v1/work-certificates/admin/templates/{template_id}/deactivate
```

SLA/admin monitoring:

```http
GET /api/v1/work-certificates/admin/requests?overdue=true&page[number]=1&page[size]=20
GET /api/v1/work-certificates/admin/sla-events?request_id={request_id}
```

### Auditor APIs

```http
GET /api/v1/work-certificates/audit/events?request_id={request_id}&page[number]=1&page[size]=20
GET /api/v1/work-certificates/audit/issued-documents?letter_number=001%2FKP.204%2FKI-2026
```

### Public Barcode Validation API

```http
GET /api/v1/work-certificates/verify/{public_code}
```

Response must not expose sensitive employee payload:

```json
{
  "data": {
    "valid": true,
    "letter_number": "001/KP.204/KI-2026",
    "issued_at": "2026-08-27T10:15:00+07:00",
    "document_type": "Surat Keterangan Kerja",
    "approver_position_title": "Head of Human Capital"
  },
  "meta": {},
  "errors": []
}
```

## Web and Flutter Contract Notes

Use the same REST API for server-rendered web and Flutter.

Client expectations:
- Every mutation returns the latest request status and relevant timestamps.
- Every list endpoint is paginated and supports stable sorting by newest first.
- UI must rely on `allowed_actions` from detail responses instead of hardcoding transition rules.
- Detail responses include `timeline` with employee-visible filtering applied by backend.
- Download links are exposed only when status is `issued` and current user has permission.
- Flutter should use the same DTO fields as web and handle `401`, `403`, `409`, and `422` distinctly.

Request detail response shape:

```json
{
  "data": {
    "id": "018f2e5b-4e7b-7000-9000-222222222222",
    "tracking_number": "SKK-2026-000123",
    "status": "submitted",
    "purpose": "Pengajuan KPR",
    "language": "id",
    "template": {
      "id": "018f2e5b-4e7b-7000-9000-111111111111",
      "name": "Surat Keterangan Kerja Umum"
    },
    "employee": {
      "employee_number": "EMP001",
      "full_name": "Andi Saputra",
      "unit": "Finance",
      "position_title": "Finance Analyst",
      "work_location": "Jakarta"
    },
    "sla_due_at": "2026-08-30T09:00:00+07:00",
    "issued_document": null,
    "timeline": [
      {
        "action": "submit",
        "to_status": "submitted",
        "note": null,
        "created_at": "2026-08-27T09:00:00+07:00"
      }
    ],
    "allowed_actions": ["cancel"]
  },
  "meta": {},
  "errors": []
}
```

## Permission Rules

Permission checks must be enforced in service layer and route layer.

Rules:
- Pegawai can only read and mutate their own requests.
- Pegawai can create when active or inactive within 1 month after `deactivated_at`.
- Pegawai cannot mutate `submitted`, `verified`, `approved`, `issued`, `rejected`, or `cancelled` requests.
- Verifikator can process `submitted` and `returned_to_hc`.
- Approver can process only requests assigned to their `approver_id`.
- Admin HC can manage employee master and templates; workflow override should be explicit and audited.
- Auditor has read-only access to audit and issued document metadata.
- Public barcode validation never grants document download.

## Transaction Flows

### Create Draft

1. Start transaction.
2. Resolve current employee and validate active/inactive-within-1-month rule.
3. Load active template and validate required placeholders/additional fields.
4. Snapshot template metadata and body.
5. Generate unique tracking number.
6. Insert request with status `draft`.
7. Insert workflow event `create_draft`.
8. Commit.

### Submit

1. Start transaction.
2. Lock request row by id.
3. Check owner permission and status `draft` or `returned_to_employee`.
4. Revalidate input completeness and employee eligibility.
5. Set status `submitted`, `submitted_at`, `current_owner_role = verifier`.
6. Set `sla_due_at = now + 3 calendar days`.
7. Insert workflow event `submit`.
8. Commit.

### Verify And Send To Approver

1. Start transaction.
2. Lock request row by id.
3. Check verifier permission and status `submitted` or `returned_to_hc`.
4. Validate approver is eligible and exactly one approver is assigned.
5. Set status `verified`, `verified_by`, `verified_at`, `approver_id`.
6. Set `current_owner_role = approver`.
7. Reset `sla_due_at = now + 3 calendar days`, clear `sla_overdue_at`.
8. Insert workflow event `verify`.
9. Commit.

### Return To Employee

1. Start transaction.
2. Lock request row by id.
3. Check verifier permission and status `submitted` or `returned_to_hc`.
4. Require non-empty note.
5. Set status `returned_to_employee`, `current_owner_role = employee`.
6. Clear `sla_due_at` because owner is employee revision.
7. Insert workflow event with `visible_to_employee = true`.
8. Commit.

### Return To HC

1. Start transaction.
2. Lock request row by id.
3. Check approver assignment and status `verified`.
4. Require non-empty note.
5. Set status `returned_to_hc`, `current_owner_role = verifier`.
6. Reset `sla_due_at = now + 3 calendar days`.
7. Insert workflow event `return_to_hc`.
8. Commit.

### Reject

1. Start transaction.
2. Lock request row by id.
3. Check verifier permission for `submitted` or approver permission for `verified` if configured.
4. Require non-empty note.
5. Set status `rejected`, set `rejected_at`, clear owner and SLA.
6. Insert workflow event `reject`.
7. Commit.

### Approve And Issue

Run approval and issue in one application service transaction. If document rendering uses external storage and cannot participate in DB transaction, render to temporary storage first, then commit DB metadata, then finalize storage keys with compensating cleanup for failures.

1. Start transaction.
2. Lock request row by id.
3. Check approver assignment and status `verified`.
4. Allocate letter sequence with `SELECT ... FOR UPDATE` on `work_certificate_letter_sequences` for current year.
5. Build `letter_number = padded_sequence + "/KP.204/KI-" + year`.
6. Create barcode validation token and barcode payload.
7. Render DOCX and PDF from immutable template snapshot.
8. Store files and calculate hashes.
9. Insert `issued_document` and two `document_files`.
10. Set request status `issued`, `approved_at`, `issued_at`, clear owner and SLA.
11. Insert workflow events `approve` and `issue_document`.
12. Commit.

Failure handling:
- If rendering fails before DB commit, rollback and keep request in `verified`; write operational log.
- If storage finalize fails after DB commit, mark document file unavailable through an admin repair flow; do not lose approval audit.
- Duplicate issue must be prevented by unique `issued_documents.request_id` and row lock.

### SLA Scanner

1. Scheduler runs periodically, for example hourly.
2. Query requests with `sla_due_at <= now`, final statuses excluded, and `sla_overdue_at is null`.
3. Lock selected rows in batches.
4. Set `sla_overdue_at = now`.
5. Insert `sla_event`.
6. Enqueue `notification_event` for current owner role.
7. Commit per batch.

### Retention Job

1. Scheduler runs daily.
2. Select issued documents and workflow events past `retention_expires_at`.
3. Archive or purge according to company policy.
4. Record retention action metadata.
5. Never delete employee master data required to explain retained workflow history before related retention expires.

## State Machine

Allowed transitions:

| From | Action | To | Actor |
| --- | --- | --- | --- |
| `draft` | `submit` | `submitted` | Pegawai |
| `draft` | `cancel` | `cancelled` | Pegawai |
| `submitted` | `return_to_employee` | `returned_to_employee` | Verifikator |
| `submitted` | `reject` | `rejected` | Verifikator |
| `submitted` | `verify` | `verified` | Verifikator |
| `returned_to_employee` | `resubmit` | `submitted` | Pegawai |
| `returned_to_employee` | `cancel` | `cancelled` | Pegawai |
| `verified` | `return_to_hc` | `returned_to_hc` | Approver |
| `verified` | `approve` | `issued` | Approver + Sistem |
| `returned_to_hc` | `return_to_employee` | `returned_to_employee` | Verifikator |
| `returned_to_hc` | `verify` | `verified` | Verifikator |

Implementation note:
- Requirement product lists `approved` before `issued`, but API should expose final successful approval as `issued` when document generation succeeds in the same use case.
- If implementation needs an intermediate status for repair, add `issue_failed` through ADR because it changes the externally visible state machine.

## Validation Rules

- `purpose` required, trimmed, max length 1000.
- `employee_note` optional, max length 2000.
- `language` must be supported by selected template.
- `additional_fields` must match template `additional_field_schema`.
- Return/reject note required, max length 2000.
- Download format must be `pdf` or `docx`.
- Template placeholder validation must run before activation and before request creation.
- Public barcode code must be opaque and unguessable.

## Test Plan

Unit tests:
- State transition matrix.
- Employee inactive 1-month eligibility.
- Letter number formatter and annual sequence allocation.
- Placeholder validation.
- SLA due date and overdue rules.
- Permission helper negative cases.

Integration tests:
- Create draft, submit, verify, approve, issue, download PDF/DOCX.
- Return to employee and resubmit.
- Return to HC and resend to approver.
- Reject by verifier.
- Forbidden read/download for another employee.
- Approver cannot approve request assigned to another approver.
- Duplicate approve request returns `409` and does not create duplicate letter number.
- Public barcode validation returns minimal data only.

Migration tests:
- Unique constraints for employee number, tracking number, letter number, and `(letter_year, sequence_number)`.
- Index coverage for queues and history lists.

## Tradeoffs

- Flask is selected because SQLAlchemy is mandatory and the codebase has no existing Django app. If the organization later standardizes on Django, this should be captured in a separate ADR before implementation.
- Approval and issue are modeled as one use case to reduce externally visible half-final states. This requires careful handling around file rendering/storage because files are outside the database transaction.
- Public barcode validation is intentionally minimal to reduce PII exposure.
- SLA uses 3 calendar days based on the latest product requirement; switching to business days affects `sla.py`, tests, and possibly scheduler behavior.

## Handoff to Database Agent

## Context
- Feature: Surat Keterangan Kerja backend architecture.
- Scope: Flask API, SQLAlchemy models, PostgreSQL schema, workflow, document issue, barcode validation, SLA, retention.
- Non-goals: certified digital signature, external HRIS sync, third-party document delivery, multi-level approval.

## Decisions
- Decision: gunakan Flask + SQLAlchemy.
- Reason: sesuai stack SQLAlchemy dan belum ada codebase Django existing.
- Decision: satu request memakai satu verifikator dan satu approver.
- Reason: sesuai keputusan produk MVP.
- Decision: letter number allocated at issue time with annual row lock.
- Reason: menjaga nomor surat resmi unik dan audit-safe.
- Decision: PDF dan DOCX dibuat sebagai immutable issued files.
- Reason: dokumen final harus tersedia dalam kedua format.

## Files/Modules
- Planned: `hc_services/modules/work_certificates/*`, migration files, tests.
- Changed: `docs/architecture/work-certificate-backend-architecture.md`.

## Contracts
- API: REST under `/api/v1/work-certificates` with shared contract for web and Flutter.
- Database: tables listed in Schema Plan with row locks, unique constraints, indexes, and retention metadata.
- UI: clients consume request detail, timeline, `allowed_actions`, queue filters, and document download endpoints.

## Verification
- Tests run: documentation-only architecture change, no automated tests required.
- Tests still needed: unit, integration, permission, migration, and SLA scanner tests listed in Test Plan.

## Risks
- Blocking: notification channel and scheduler implementation must be selected before production build.
- Non-blocking: issue failure repair flow may need an ADR if external storage failure states are exposed to users.
