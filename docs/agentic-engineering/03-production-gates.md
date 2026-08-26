# Production Gates

Production gate adalah checklist yang harus dipenuhi sebelum perubahan dianggap layak deploy. Tidak semua item berlaku untuk setiap task, tetapi agent wajib menyebutkan item yang tidak relevan atau belum bisa diverifikasi.

## Gate 1: Requirement and Scope

- Acceptance criteria tertulis.
- Non-goal tertulis.
- Edge case utama tercakup.
- Breaking change ditandai.
- Data sensitif dan permission rule jelas.

## Gate 2: Backend Quality

- Business logic tidak menumpuk di route/view.
- Input tervalidasi di boundary.
- Response error konsisten dan tidak membocorkan detail internal.
- Permission/auth check diterapkan pada semua endpoint terkait.
- Transaction boundary jelas untuk operasi multi-step.
- Idempotency dipertimbangkan untuk endpoint create/update yang rawan retry.
- Pagination diterapkan untuk list endpoint.
- Logging cukup untuk investigasi tanpa membocorkan secret/PII.

## Gate 3: SQLAlchemy and PostgreSQL

- Model punya primary key, foreign key, dan constraint yang sesuai.
- Index dibuat untuk filter, join, dan ordering yang sering dipakai.
- Unique constraint dipakai untuk invariant bisnis.
- Timestamp memakai timezone-aware value.
- Migration diuji upgrade.
- Downgrade tersedia jika masuk akal.
- Migration destructive dipisah dari deploy aplikasi.
- Backfill besar berjalan batch-based.
- Query raw SQL memakai parameter binding.
- Tidak ada N+1 query pada path utama.

## Gate 4: Flask or Django

Untuk Flask:

- App factory atau struktur app konsisten jika proyek sudah memakai pola itu.
- Blueprint dipakai untuk module yang cukup besar.
- Config dibaca dari environment, bukan hardcoded.
- Request parsing dan validation konsisten.
- Error handler production tersedia.

Untuk Django:

- Model, manager/queryset, view, serializer/form mengikuti pola lokal.
- `manage.py check` lulus.
- Migration tidak dibuat manual tanpa alasan.
- Permission diterapkan di view/admin/API layer.
- Queryset memakai `select_related`/`prefetch_related` jika perlu.

## Gate 5: Web HTML/CSS

- HTML semantic.
- Form control punya label.
- Error message dekat dengan field terkait.
- Layout responsif untuk mobile dan desktop.
- Empty/loading/error state tersedia.
- Warna dan kontras cukup terbaca.
- Tidak ada secret atau URL environment hardcoded.
- CSS tidak membuat overlap pada viewport umum.

## Gate 6: Flutter

- API client punya timeout dan error mapping.
- Token/credential disimpan dengan mekanisme secure storage.
- State loading, empty, success, error, unauthorized tersedia.
- DTO parsing punya test untuk response utama dan error response.
- Widget penting punya widget test.
- `flutter analyze` lulus.
- `flutter test` lulus.

## Gate 7: Security

- Authenticated endpoint benar-benar butuh auth.
- Authorization berbasis owner/role dicek di server.
- CSRF dipertimbangkan untuk form web/session-based auth.
- CORS tidak wildcard untuk credentialed request.
- Password dan token tidak pernah dilog.
- Secret hanya lewat environment/secret manager.
- File upload, jika ada, membatasi type, size, dan storage path.
- SQL injection dicegah dengan ORM atau parameter binding.
- XSS dicegah dengan escaping template dan sanitasi input yang dirender sebagai HTML.

## Gate 8: Testing

- Unit test untuk business logic.
- Integration test untuk endpoint/service utama.
- Regression test untuk bug fix.
- Migration test untuk perubahan schema.
- Contract test atau sample response untuk API yang dipakai Flutter/web.
- Test data tidak bergantung pada urutan eksekusi test.

## Gate 9: Observability

- Health check tersedia untuk service.
- Error log punya correlation/request id jika infrastruktur mendukung.
- Metric penting dipertimbangkan: latency, error rate, DB error, queue lag jika ada.
- Audit log tersedia untuk aksi sensitif.
- Post-deploy smoke test jelas.

## Gate 10: Release and Rollback

- Release notes ringkas.
- Environment variable baru terdokumentasi.
- Dependency baru jelas alasannya.
- Migration order jelas.
- Rollback aplikasi jelas.
- Rollback data jelas atau limitation tertulis.
- Feature flag dipakai untuk perubahan berisiko jika memungkinkan.

## Production Readiness Template

Gunakan template ini di akhir task:

```md
## Production Readiness
- Requirement gate:
- Backend gate:
- Database gate:
- Web gate:
- Flutter gate:
- Security gate:
- Testing gate:
- Observability gate:
- Release gate:

## Commands Run
- Command:
- Result:

## Remaining Risk
- Risk:
- Owner/mitigation:
```

