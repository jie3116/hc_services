# Agentic Engineering Workflow

Workflow ini dirancang agar agent menghasilkan kode yang siap masuk jalur production, bukan hanya prototype. Gunakan workflow ini untuk fitur baru, perbaikan bug, refactor berisiko, dan perubahan database.

## Phase 0: Intake

Agent utama harus mengklarifikasi:

- Masalah yang diselesaikan.
- Pengguna atau sistem yang terdampak.
- Acceptance criteria.
- Non-goal.
- Risiko data, security, dan downtime.
- Target platform: backend, web, mobile, atau kombinasi.

Output:

- Task brief 5-15 baris.
- Scope yang eksplisit.
- Daftar asumsi.

## Phase 1: Discovery

Langkah:

1. Baca struktur repo.
2. Cari pola existing untuk route/view, model, migration, template, static asset, test, dan mobile layer.
3. Identifikasi dependency dan command verifikasi.
4. Catat file yang akan disentuh.

Output:

- Map singkat area kode.
- Risiko integrasi.
- Rencana test.

Stop condition:

- Jika framework utama belum jelas, agent harus menanyakan keputusan Flask atau Django sebelum membuat struktur aplikasi besar.

## Phase 2: Design

Backend design harus mencakup:

- Endpoint atau view.
- Request/response contract.
- Permission/auth rule.
- Service layer behavior.
- SQLAlchemy model dan transaction boundary.
- PostgreSQL constraint, index, dan migration.

Web design harus mencakup:

- Template/page yang terdampak.
- UI states: loading, empty, success, validation error, server error.
- Accessibility baseline.

Flutter design harus mencakup:

- Screen/widget boundary.
- API client method.
- DTO/model.
- State management.
- Offline/timeout/error behavior.

Output:

- Implementation plan.
- Test plan.
- Rollback consideration.

## Phase 3: Implementation

Aturan implementasi:

- Buat perubahan kecil dan terarah.
- Ikuti pola lokal sebelum memperkenalkan abstraksi baru.
- Jangan menambah dependency tanpa alasan kuat.
- Jangan membuat migration yang mengunci table besar tanpa strategi.
- Jangan mengubah contract API tanpa update web/mobile consumer.

Urutan umum:

1. Tambah atau update test yang menggambarkan behavior.
2. Tambah model/migration jika perlu.
3. Implementasikan service/business logic.
4. Implementasikan route/view/API.
5. Implementasikan web atau Flutter consumer.
6. Update dokumentasi.

## Phase 4: Verification

Minimal verification untuk backend Python:

```powershell
python -m pytest
python -m compileall .
```

Jika memakai Django:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Jika memakai Flask:

```powershell
python -m pytest
python -m flask --app <app_module> routes
```

Jika memakai SQLAlchemy/Alembic:

```powershell
alembic current
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Jika memakai Flutter:

```powershell
flutter analyze
flutter test
```

Jika ada web UI:

- Cek viewport mobile dan desktop.
- Cek form validation.
- Cek empty, loading, success, dan error state.
- Cek keyboard navigation untuk form penting.

## Phase 5: Review

Review agent harus mengecek:

- Bug behavior.
- Missing test.
- Security issue.
- Race condition.
- N+1 query.
- Migration risk.
- API backward compatibility.
- Error handling dan logging.
- UI broken state.

Review output harus berbentuk:

```md
## Findings
- Severity:
- File/line:
- Issue:
- Fix:

## Test Gaps
- Gap:
- Impact:

## Release Risk
- Risk:
- Mitigation:
```

## Phase 6: Release

Release agent harus memastikan:

- Semua gate lulus.
- Migration order jelas.
- Config dan environment variable tersedia.
- Rollback app jelas.
- Rollback data jelas atau limitation tertulis.
- Post-deploy smoke test tersedia.

Post-deploy smoke test:

- Health check.
- Login/auth flow jika ada.
- Endpoint utama.
- Query database utama.
- Web page utama.
- Flutter flow utama untuk build yang dirilis.

## Phase 7: Learn

Setelah deploy:

- Catat incident atau near miss.
- Update checklist jika ada bug yang lolos.
- Tambahkan regression test.
- Update ADR jika keputusan arsitektur berubah.

## Workflow Cepat Berdasarkan Jenis Task

Bug fix kecil:

1. Reproduce.
2. Tambah regression test.
3. Fix.
4. Jalankan test terkait.
5. Review risiko deploy.

Fitur backend:

1. Intake.
2. API/database design.
3. Test.
4. Implementation.
5. Migration verification.
6. API docs.

Fitur web:

1. UI behavior.
2. API contract.
3. Template/static implementation.
4. Responsive/accessibility check.
5. Backend integration test jika form mengubah data.

Fitur Flutter:

1. Screen flow.
2. API contract.
3. DTO/client/state.
4. Widget/unit test.
5. Device/manual test.

Perubahan database:

1. Data model review.
2. Migration plan.
3. Backfill plan.
4. Downtime/lock assessment.
5. Upgrade/downgrade test.
6. Release sequencing.

