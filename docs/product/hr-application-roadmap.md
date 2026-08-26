# HR Application Roadmap

Dokumen ini adalah hasil tahap awal Product Analyst Agent untuk mengubah kebutuhan aplikasi HR menjadi scope bertahap yang bisa dilanjutkan oleh Backend Architect, Database, Backend Implementation, Web Frontend, Flutter Mobile, Security, QA, dan Release Agent.

## Context

- Feature: aplikasi HR untuk pengelolaan pegawai, kontrak kerja, surat keterangan kerja/paklaring, Smart HC berbasis dokumen, payroll berbasis performance, dan penerbitan SK jabatan massal.
- Scope awal: web backend dan web UI admin/pegawai. Flutter disiapkan sebagai consumer API, tetapi implementasi mobile dapat masuk fase terpisah.
- Non-goals awal: integrasi bank/payroll disbursement, tanda tangan elektronik tersertifikasi, AI menjawab tanpa basis dokumen resmi, dan perubahan data payroll tanpa audit trail.

## Assumptions

- Framework backend utama belum dipilih. Sesuai workflow, Backend Architect Agent harus memutuskan Flask atau Django sebelum membuat struktur besar.
- Database target PostgreSQL dengan SQLAlchemy sesuai AGENTS.md.
- Data pegawai, kontrak, paklaring, payroll, dan SK adalah data sensitif. Semua modul butuh role-based authorization dan audit log.
- Aturan PKWT harus dikonfirmasi ulang dengan legal/internal HC sebelum production. Baseline awal mengacu pada PP No. 35 Tahun 2021 yang mengatur PKWT, perpanjangan, pencatatan, dan kompensasi PKWT.
- Smart HC harus menggunakan retrieval dari dokumen perusahaan yang disetujui, bukan jawaban bebas tanpa sumber.

## Personas

- Pegawai: melihat data pribadi yang diizinkan, mengajukan paklaring/surat keterangan kerja, melihat status pengajuan, dan nanti bertanya ke Smart HC.
- Admin HC: mengelola master pegawai, kontrak PKWT/PKWTT, dokumen, payroll process, SK, dan review pengajuan.
- Pejabat Approver: menyetujui paklaring, SK, dan perubahan sensitif sesuai kewenangan.
- Payroll/Compensation Admin: mengelola komponen performance, simulasi kenaikan gaji, approval, dan finalisasi payroll adjustment.
- Auditor/Internal Control: membaca audit trail dan laporan tanpa mengubah data operasional.

## Phased Delivery

### Phase 0 - Foundation

Goal:
- Menetapkan framework utama, auth, role/permission, audit log, struktur module, dan quality gates.

Relevant agents:
- Product Analyst Agent untuk finalisasi scope MVP.
- Backend Architect Agent untuk keputusan Flask/Django dan API boundary.
- Database Agent untuk model identitas, role, audit log, dan migration baseline.
- Security Agent untuk baseline auth, PII, payroll, dan audit.

Acceptance criteria:
- Ada keputusan framework utama yang tertulis.
- Ada role awal: employee, hc_admin, approver, payroll_admin, auditor, super_admin.
- Semua endpoint sensitif wajib authenticated dan authorized.
- Audit log mencatat create/update/delete/approve/reject untuk data sensitif.

### Phase 1 - Master Data Pegawai

Goal:
- Mengelola data pegawai PKWT dan PKWTT dengan CRUD, pencarian, filter, dan riwayat status kerja.

Core data:
- Employee: nomor induk, nama, NIK terenkripsi/terproteksi, email, unit kerja, jabatan, lokasi kerja, status aktif.
- Employment: tipe hubungan kerja PKWT/PKWTT, tanggal mulai, tanggal akhir bila ada, status, alasan perubahan.
- Organization: unit kerja, jabatan, atasan, lokasi.

Acceptance criteria:
- Admin HC dapat membuat, melihat, mengubah, menonaktifkan pegawai.
- List pegawai mendukung pagination, filter status kerja, tipe hubungan kerja, unit kerja, dan keyword.
- Pegawai hanya bisa melihat data miliknya sesuai permission.
- Perubahan data sensitif tercatat di audit log.
- Delete fisik tidak dilakukan untuk pegawai yang sudah punya transaksi; gunakan status inactive/archived.

Edge cases:
- Nomor induk duplikat ditolak.
- Email duplikat ditolak jika dipakai untuk login.
- Pegawai pindah unit/jabatan tidak menghapus riwayat lama.
- Data pegawai yang pernah masuk payroll tidak boleh dihapus.

### Phase 2 - PKWT Contract Compliance

Goal:
- Mengelola kontrak PKWT baru dan perpanjangan dengan kontrol kepatuhan.

Core behavior:
- Membuat kontrak PKWT baru.
- Membuat perpanjangan PKWT dari kontrak aktif.
- Menghitung total akumulasi durasi PKWT per pegawai.
- Memberikan warning/blocker jika aturan konfigurasi compliance dilanggar.
- Menyimpan dokumen kontrak dan metadata pencatatan.

Compliance baseline:
- PKWT berdasarkan jangka waktu dan perpanjangannya perlu dikontrol agar tidak melewati batas regulasi yang berlaku.
- Baseline awal: PP No. 35 Tahun 2021 mengatur PKWT dan batas waktu/perpanjangan; beberapa sumber resmi/ringkasan hukum menyebut akumulasi PKWT berdasarkan jangka waktu paling lama 5 tahun.
- Aplikasi harus memakai configuration table untuk rule compliance agar bisa diperbarui tanpa edit kode saat regulasi berubah.
- Hasil validasi aplikasi adalah compliance aid, bukan pengganti review legal.

Acceptance criteria:
- Admin HC dapat membuat kontrak PKWT baru untuk pegawai.
- Admin HC dapat memperpanjang kontrak PKWT dengan relasi ke kontrak sebelumnya.
- Sistem menghitung total durasi kontrak dan menampilkan status: compliant, warning, blocked.
- Sistem menolak perpanjangan yang melewati rule blocking kecuali ada override beralasan dan role khusus.
- Semua override compliance wajib punya alasan, approver, timestamp, dan audit trail.
- Reminder kontrak berakhir tersedia berdasarkan threshold configurable, misalnya H-90, H-60, H-30.

Edge cases:
- Periode kontrak overlap untuk pegawai yang sama ditolak.
- Tanggal akhir sebelum tanggal mulai ditolak.
- Perpanjangan tidak boleh dibuat dari kontrak yang bukan kontrak terakhir kecuali ada koreksi data berotorisasi.
- PKWTT tidak boleh masuk flow perpanjangan PKWT.

### Phase 3 - Paklaring / Surat Keterangan Kerja

Goal:
- Pegawai mengajukan surat keterangan kerja atau paklaring, direview admin, lalu disetujui pejabat.

Workflow:
- Draft/submitted by employee.
- Reviewed/returned/rejected by HC admin.
- Approved/rejected by approver.
- Issued after approval.

Acceptance criteria:
- Pegawai dapat mengajukan permohonan dengan jenis surat, tujuan, dan informasi pendukung.
- Admin HC dapat review, meminta revisi, atau meneruskan ke approver.
- Pejabat dapat approve/reject dengan catatan.
- Dokumen final memiliki nomor surat, tanggal terbit, pejabat penandatangan, dan template yang sesuai.
- Status dan riwayat komentar dapat dilihat oleh pemohon.

Edge cases:
- Pegawai nonaktif hanya dapat mengajukan paklaring jika policy perusahaan mengizinkan.
- Pengajuan yang sudah issued tidak bisa diedit; koreksi harus membuat versi/reissue.
- Nomor surat harus unik dan tidak lompat tanpa audit bila nomor sudah reserved.

### Phase 4 - SK Jabatan Massal

Goal:
- Menerbitkan satu SK yang ditujukan ke banyak pegawai, misalnya kenaikan jabatan atau penunjukan jabatan.

Acceptance criteria:
- Admin HC dapat membuat draft SK dengan tipe SK, nomor, tanggal berlaku, template, dan daftar pegawai penerima.
- Sistem memvalidasi setiap penerima punya data jabatan/unit yang diperlukan.
- Pejabat dapat approve satu dokumen SK massal.
- Setelah approved, perubahan jabatan/penunjukan dapat diterapkan efektif pada tanggal berlaku.
- Setiap pegawai penerima punya riwayat SK dan perubahan jabatan.

Edge cases:
- Satu pegawai tidak boleh menerima perubahan jabatan yang overlap pada tanggal efektif sama tanpa override.
- Menghapus penerima setelah approval tidak boleh dilakukan; gunakan addendum/revisi.
- Perubahan organisasi massal harus transactional.

### Phase 5 - Salary Increase Based on Performance

Goal:
- Menggantikan proses Excel untuk kenaikan gaji berbasis performance dengan workflow terkontrol.

Core behavior:
- Import atau input performance rating.
- Define salary increase matrix/rule.
- Simulasi kenaikan.
- Review budget dan exception.
- Approval berjenjang.
- Finalisasi effective salary.

Acceptance criteria:
- Payroll admin dapat membuat salary review cycle.
- Sistem menghitung rekomendasi kenaikan berdasarkan rating, compa-ratio/range, budget, dan rule yang dikonfigurasi.
- Exception dari rekomendasi wajib punya alasan dan approval.
- Output final dapat diekspor untuk kebutuhan payroll downstream.
- Semua perubahan salary punya audit trail dan tidak terlihat oleh role non-payroll.

Edge cases:
- Pegawai tanpa rating masuk bucket exception.
- Budget overrun harus terlihat sebelum approval.
- Cycle yang sudah finalized tidak bisa diubah langsung; koreksi lewat adjustment terpisah.
- Data salary tidak boleh tampil di modul pegawai umum.

### Phase 6 - Smart HC

Goal:
- Menyediakan media tanya jawab kebijakan perusahaan berbasis dokumen.

Acceptance criteria:
- Admin HC dapat mengunggah/mengelola dokumen kebijakan yang disetujui.
- Sistem mengindeks dokumen dan menjawab dengan sumber rujukan.
- Jawaban AI harus menampilkan disclaimer jika dokumen tidak cukup.
- Pegawai hanya mendapat jawaban dari dokumen yang boleh diakses oleh role/unitnya.
- Pertanyaan dan jawaban dicatat untuk monitoring tanpa membocorkan data sensitif ke log.

Edge cases:
- Dokumen sudah tidak berlaku harus tidak dipakai untuk jawaban aktif.
- Pertanyaan tentang payroll pribadi tidak dijawab dari dokumen umum.
- Jawaban tanpa sumber harus ditolak atau ditandai tidak tersedia.

## Permission Matrix Initial

| Capability | Employee | HC Admin | Approver | Payroll Admin | Auditor | Super Admin |
| --- | --- | --- | --- | --- | --- | --- |
| View own profile | Yes | Yes | Yes | Yes | Read | Yes |
| Manage employee master | No | Yes | No | Limited read | Read | Yes |
| Manage PKWT contract | No | Yes | Approve override only | No | Read | Yes |
| Request paklaring | Yes | On behalf | No | No | Read | Yes |
| Review paklaring | No | Yes | No | No | Read | Yes |
| Approve paklaring/SK | No | No | Yes | No | Read | Yes |
| Manage salary review | No | No | No | Yes | Read masked | Yes |
| View salary detail | Own only if policy allows | No by default | No by default | Yes | Masked/read as approved | Yes |
| Manage Smart HC documents | No | Yes | Approve if required | No | Read | Yes |
| View audit log | No | Limited own workflow | Limited own approvals | Limited payroll | Yes | Yes |

## Data Sensitivity Notes

- PII high risk: NIK, alamat, tanggal lahir, kontak pribadi, dokumen identitas.
- Legal/audit high risk: kontrak PKWT, paklaring, SK, approval, override compliance.
- Payroll high risk: gaji, performance rating, rekomendasi kenaikan, exception, budget.
- AI high risk: dokumen kebijakan internal, pertanyaan pegawai, akses berbasis role/unit.

## Agent Execution Plan

1. Product Analyst Agent: finalisasi MVP phase 0-2, user stories detail, acceptance criteria, dan non-goals.
2. Backend Architect Agent: pilih Flask atau Django, desain module boundary, API contract, auth, dan transaction flow.
3. Database Agent: desain schema SQLAlchemy/PostgreSQL, migration plan, constraint, index, dan audit tables.
4. Security Agent: threat model untuk PII, payroll, legal document, approval, dan AI document access.
5. Backend Implementation Agent: implementasi endpoint/service/model/test per fase kecil.
6. Web Frontend Agent: implementasi UI admin/pegawai sesuai contract per modul.
7. Flutter Mobile Agent: implementasi mobile setelah API stabil atau minimal untuk employee self-service.
8. Code Reviewer Agent: review diff dan test gap sebelum merge.
9. QA Agent: uji acceptance criteria, permission, regression, dan workflow.
10. Release Agent: deploy checklist, migration order, rollback, dan smoke test.

## Recommended MVP

MVP sebaiknya dibatasi ke Phase 0 sampai Phase 3:

- Foundation auth/role/audit.
- CRUD pegawai PKWT/PKWTT.
- PKWT baru/perpanjangan dengan compliance rule configurable.
- Paklaring workflow sampai issued.

Payroll, SK massal, dan Smart HC tetap didesain agar model awal tidak menutup jalan, tetapi implementasinya dilakukan setelah master pegawai dan workflow approval stabil.

## Open Questions

- Backend utama akan memakai Flask atau Django?
- Apakah aplikasi pertama hanya web, atau Flutter employee self-service harus masuk MVP?
- Sumber kebenaran data pegawai saat ini dari Excel, HRIS lama, atau input manual?
- Apakah nomor surat mengikuti format perusahaan yang sudah ada?
- Siapa saja pejabat approver dan apakah approval perlu multi-level?
- Apakah payroll hanya menghitung rekomendasi kenaikan atau juga memproses slip gaji?
- Apakah perusahaan punya dokumen kebijakan dalam format PDF/DOCX yang siap dijadikan sumber Smart HC?

## References

- PP No. 35 Tahun 2021 pada BPK: https://peraturan.bpk.go.id/Details/161904/pp-no-35-tahun-2021

