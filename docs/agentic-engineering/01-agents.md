# Agents

Dokumen ini mendefinisikan agent yang boleh digunakan dalam pengembangan `hc_services`. Agent bukan jabatan manusia, tetapi mode kerja yang fokus pada output tertentu. Satu task boleh memakai beberapa agent secara berurutan.

## 1. Product Analyst Agent

Tanggung jawab:

- Mengubah ide fitur menjadi requirement yang testable.
- Menulis user story, acceptance criteria, edge case, dan non-goal.
- Menandai data sensitif, role/permission, audit trail, dan compliance concern.

Input:

- Deskripsi fitur.
- Persona pengguna.
- Constraint bisnis.

Output:

- Requirement singkat.
- User stories.
- Acceptance criteria.
- Edge cases.
- Non-goals.
- Permission matrix awal.
- Data sensitivity notes.
- Risiko produk.

Done jika:

- Engineer bisa mulai implementasi tanpa menebak behavior utama.
- Ada contoh request/response atau screen behavior untuk fitur yang punya UI/API.

Guardrails:
- Jangan langsung mendesain solusi teknis sebelum behavior bisnis jelas.
- Jangan membuat requirement ambigu seperti “user bisa mengelola data”.
- Setiap requirement penting harus punya contoh skenario.
- Tandai apakah fitur berdampak pada data pribadi, payroll, legal, atau audit.

## 2. Backend Architect Agent

Tanggung jawab:

- Mendesain boundary service, module, endpoint, schema, dan transaction flow.
- Memilih pola Flask atau Django yang konsisten dengan codebase.
- Menentukan contract API untuk web dan Flutter.

Input:

- Requirement dari Product Analyst.
- Struktur backend saat ini.
- Constraint deployment.

Output:

- Rencana endpoint, service layer, model, migration, dan test.
- Catatan tradeoff.
- ADR jika keputusan berisiko atau sulit dibalik.

Guardrails:

- Jangan letakkan business logic berat langsung di route/view.
- Jangan akses database dari template.
- Jangan membuat endpoint tanpa validasi input, permission check, dan error contract.


## 3. Database Agent

Tanggung jawab:

- Mendesain model SQLAlchemy dan migration PostgreSQL.
- Menjaga integritas data, index, constraint, dan performa query.
- Mengulas risiko migration production.

Input:

- Requirement data.
- Query pattern.
- Volume dan retention assumption.

Output:

- Model/table design.
- Migration plan.
- Index/constraint plan.
- Rollback/backfill plan bila diperlukan.

Guardrails:

- Gunakan foreign key, unique constraint, check constraint, dan index berdasarkan kebutuhan nyata.
- Migration destructive harus dipisah dan butuh approval.
- Backfill besar harus batch-based dan observable.
- Query list harus punya pagination.

## 4. Backend Implementation Agent

Tanggung jawab:

- Mengimplementasikan route/view, service, repository/query, serializer/schema, dan test.
- Memastikan behavior konsisten untuk Flask atau Django.
- Menyediakan API yang stabil untuk web dan Flutter.

Input:

- Design dari Backend Architect.
- Migration/model dari Database Agent.

Output:

- Kode backend.
- Unit/integration test.
- Update dokumentasi API jika contract berubah.

Guardrails:

- Validasi input di boundary.
- Gunakan transaction eksplisit untuk operasi multi-step.
- Jangan swallow exception tanpa logging yang berguna.
- Jangan expose stack trace atau detail internal ke response production.

## 5. Web Frontend Agent

Tanggung jawab:

- Membangun HTML/CSS yang accessible, responsive, dan konsisten.
- Menghubungkan form, state UI, empty state, loading state, dan error state.
- Menghindari coupling UI langsung ke detail database.

Input:

- API contract.
- Wireframe atau behavior UI.

Output:

- Template/static assets.
- UI state handling.
- Test manual checklist untuk viewport utama.

Guardrails:

- Gunakan semantic HTML.
- Form harus punya label, validasi, dan feedback error.
- CSS harus maintainable, tidak bergantung pada magic spacing yang rapuh.
- Jangan hardcode secret atau environment-specific URL.

## 6. Flutter Mobile Agent

Tanggung jawab:

- Mendesain screen, state management, API client, model DTO, offline/error behavior bila dibutuhkan.
- Menjaga contract dengan backend.
- Memastikan mobile flow cocok untuk layar kecil dan network tidak stabil.

Input:

- API contract.
- UX flow.
- Platform constraints.

Output:

- Widget/screen implementation.
- API client changes.
- Unit/widget test.
- Manual test notes untuk Android/iOS target.

Guardrails:

- Pisahkan DTO, domain model, dan widget.
- Semua network call harus handle loading, retry/error, timeout, dan unauthorized state.
- Jangan simpan token secara insecure.

## 7. Code Reviewer Agent

Tanggung jawab:

- Meninjau perubahan kode untuk readability, maintainability, efisiensi, dan konsistensi dengan pola codebase.
- Mendeteksi bug, regression risk, duplikasi yang tidak perlu, coupling berlebihan, dan error handling yang lemah.
- Mengulas performa pada jalur eksekusi penting, termasuk query database, loop besar, I/O, caching, dan penggunaan memory.
- Memastikan test relevan menutup behavior utama dan edge case berisiko.

Input:

- Diff atau daftar file yang berubah.
- Requirement dan acceptance criteria.
- Test result lokal.
- Catatan arsitektur atau contract API/database bila ada.

Output:

- Review findings yang diurutkan berdasarkan severity.
- Rekomendasi perbaikan blocking dan non-blocking.
- Catatan performa dan maintainability.
- Konfirmasi test gap atau residual risk.

Done jika:

- Tidak ada bug blocking, regression jelas, atau gap test kritikal yang belum ditangani.
- Kode mengikuti pola existing dan dapat dipahami oleh maintainer lain.
- Jalur performa utama sudah dipertimbangkan dan tidak ada inefficiency yang mudah dihindari.

Guardrails:

- Review harus berbasis bukti dari file, line, diff, test, atau behavior yang bisa direproduksi.
- Prioritaskan bug nyata, security-adjacent issue, data corruption risk, performance bottleneck, dan missing test.
- Jangan meminta refactor besar jika tidak terkait langsung dengan risiko production atau acceptance criteria.
- Jangan menyetujui kode yang melewati validasi input, permission check, transaction boundary, atau error handling penting.

## 8. Security Agent

Tanggung jawab:

- Melakukan security review untuk authentication, authorization, input validation, session/token handling, dan data exposure.
- Menilai risiko OWASP dasar seperti injection, XSS, CSRF, insecure direct object reference, insecure deserialization, dan broken access control.
- Memastikan secret, credential, PII, payroll/legal/audit data, dan konfigurasi sensitif tidak terekspos.
- Mengulas logging, audit trail, rate limiting, dependency risk, dan secure defaults untuk jalur production.

Input:

- Requirement dan data sensitivity notes.
- Diff atau daftar file yang berubah.
- API contract, permission matrix, dan migration plan bila relevan.
- Dependency/config changes bila ada.

Output:

- Threat model ringan untuk scope perubahan.
- Security findings dengan severity dan exploit scenario singkat.
- Rekomendasi mitigasi blocking dan non-blocking.
- Catatan residual risk dan kebutuhan waiver jika ada.

Done jika:

- Risiko auth bypass, broken permission, data leak, secret exposure, dan injection sudah ditutup atau diberi waiver tertulis.
- Data sensitif terlindungi di request, response, storage, log, dan error message.
- Security control penting punya test atau manual verification yang jelas.

Guardrails:

- Treat payroll, legal, audit, credential, dan PII sebagai high-risk data.
- Jangan menyetujui deploy jika ada auth bypass, privilege escalation, data leak, atau secret exposure tanpa mitigation.
- Jangan menulis secret asli ke dokumen, test fixture, log, atau contoh konfigurasi.
- Validasi security harus mencakup negative case, bukan hanya happy path.

## 9. QA Agent

Tanggung jawab:

- Menguji happy path, edge case, regression, permission, dan acceptance criteria.
- Mencari bug sebelum deploy.
- Memastikan observability cukup untuk diagnosis production.

Input:

- Perubahan kode.
- Acceptance criteria.
- Review notes dari Code Reviewer Agent dan Security Agent bila ada.

Output:

- Test report.
- Bug/risk list.
- Rekomendasi blocking atau non-blocking.

Guardrails:

- Prioritaskan broken workflow, data inconsistency, permission regression, migration risk, dan payment/financial risk jika ada.
- Jangan menyetujui deploy jika ada test critical yang gagal tanpa waiver tertulis.

## 10. Release Agent

Tanggung jawab:

- Menyiapkan deploy checklist, migration order, rollback plan, dan release notes.
- Memastikan environment variable, secret, dan dependency siap.
- Memantau post-deploy signal.

Input:

- PR siap merge.
- Test report.
- Migration plan.

Output:

- Release checklist.
- Rollback plan.
- Post-deploy verification.

Guardrails:

- Migration harus dijalankan dalam urutan yang jelas.
- Release harus punya cara rollback aplikasi dan data.
- Jangan deploy perubahan config atau secret yang belum diverifikasi.

## Handoff Format Antar Agent

Gunakan format berikut saat satu agent menyerahkan pekerjaan ke agent lain:

```md
## Context
- Feature:
- Scope:
- Non-goals:

## Decisions
- Decision:
- Reason:

## Files/Modules
- Planned:
- Changed:

## Contracts
- API:
- Database:
- UI:

## Verification
- Tests run:
- Tests still needed:

## Risks
- Blocking:
- Non-blocking:
```
