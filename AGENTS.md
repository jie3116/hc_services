# Agentic Engineering Guide

Dokumen ini adalah entry point untuk menggunakan agentic engineering di proyek `hc_services`.
Tujuannya: setiap agent bekerja dengan konteks yang cukup, menghasilkan perubahan kecil yang dapat diaudit, dan hanya mengusulkan kode yang layak masuk jalur production setelah melewati quality gates.

## Stack Proyek

- Backend: Flask atau Django
- ORM/data access: SQLAlchemy
- Database: PostgreSQL
- Web frontend: HTML dan CSS
- Mobile frontend: Flutter

Jika implementasi aktual memilih Flask atau Django, gunakan satu framework utama untuk service yang sama. Jangan mencampur Flask dan Django di boundary yang sama kecuali ada alasan arsitektural yang tertulis di ADR.

## Prinsip Kerja Agent

1. Baca konteks sebelum mengubah kode.
2. Ubah scope sekecil mungkin untuk menyelesaikan acceptance criteria.
3. Tulis atau perbarui test bersama perubahan behavior.
4. Jalankan verifikasi lokal yang relevan sebelum menyatakan selesai.
5. Jangan menyentuh secret, credential, data production, atau migration destructive tanpa approval eksplisit.
6. Catat tradeoff teknis yang berdampak ke production di dokumen atau PR.

## Dokumen Agentic Engineering

- [Agents](docs/agentic-engineering/01-agents.md): daftar agent, tanggung jawab, input, output, dan batasan.
- [Workflow](docs/agentic-engineering/02-workflow.md): alur kerja dari requirement sampai deploy.
- [Production Gates](docs/agentic-engineering/03-production-gates.md): checklist kualitas untuk backend, database, web, dan mobile.
- [Prompts and Runbooks](docs/agentic-engineering/04-prompts-and-runbooks.md): template prompt dan runbook kerja harian.

## Definition of Done

Sebuah perubahan dianggap selesai hanya jika:

- Acceptance criteria terpenuhi.
- Test relevan ada dan lulus.
- Migration database aman, reversible bila memungkinkan, dan tidak merusak data.
- Error handling, logging, dan security baseline sudah dipertimbangkan.
- Dokumentasi developer diperbarui jika behavior, setup, API, atau workflow berubah.
- Risiko deploy dan rollback jelas.

## Instruksi Singkat Untuk Agent

Gunakan format kerja ini pada setiap task:

1. Ringkas requirement dan asumsi.
2. Identifikasi file dan boundary yang akan disentuh.
3. Buat rencana singkat.
4. Implementasikan perubahan.
5. Jalankan test/lint/format yang relevan.
6. Laporkan hasil, file yang berubah, dan sisa risiko.

