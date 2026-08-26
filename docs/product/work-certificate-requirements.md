# Work Certificate Request Requirements

Dokumen ini adalah output Product Analyst Agent untuk modul pengelolaan permohonan Surat Keterangan Kerja. Fokus dokumen ini adalah behavior bisnis yang testable, bukan desain teknis final.

## Context

- Feature: aplikasi untuk mengelola permohonan Surat Keterangan Kerja oleh pegawai, verifikasi oleh staf Human Capital, approval oleh pejabat, dan penerbitan dokumen final yang dapat diunduh pegawai.
- Scope MVP: master data pegawai, template surat, workflow permohonan, verifikasi, approval, generate dokumen final, barcode approver, tracking status, dan history.
- Non-goals MVP: tanda tangan elektronik tersertifikasi, integrasi HRIS eksternal, payroll, SK jabatan massal, pengiriman email/SMS/WhatsApp otomatis, dan mobile offline mode.

## Personas

- Pegawai: mengajukan permohonan, memilih template sesuai kebutuhan, melihat tracking status, membaca catatan pengembalian, mengirim revisi, melihat history, dan mengunduh surat yang sudah approved.
- Staf Human Capital atau Verifikator: memeriksa data permohonan dan master data pegawai, mengembalikan permohonan untuk revisi, menolak bila tidak valid, atau meneruskan ke approver.
- Pejabat Approver: menyetujui atau mengembalikan permohonan berdasarkan hasil verifikasi dan kewenangan.
- Admin HC: mengelola master data pegawai, template surat, pejabat approver, dan konfigurasi nomor surat.
- Auditor: melihat riwayat status, catatan verifikasi, approval, nomor surat, dan jejak unduhan tanpa mengubah data.

## Assumptions

- Identitas pegawai sudah tersedia melalui login dan terhubung ke satu record master data pegawai.
- Satu permohonan menghasilkan satu surat final setelah approved.
- Barcode approver minimal berisi data verifikasi dokumen seperti request id, nomor surat, approver id atau nama jabatan, timestamp approval, dan URL atau token validasi dokumen.
- Format nomor surat resmi adalah `[nomor urut]/KP.204/KI-[TAHUN]`, dengan nomor urut unik per tahun kalender.
- Template surat memakai placeholder dari master data pegawai dan field permohonan.
- Workflow MVP memakai satu verifikator dan satu approver untuk setiap permohonan.
- Approval MVP memakai barcode sebagai penanda validasi approval, bukan tanda tangan gambar atau tanda tangan elektronik tersertifikasi.
- Dokumen final tersedia dalam format PDF dan DOCX.
- Retensi dokumen dan audit trail adalah 3 tahun sejak dokumen issued atau sejak permohonan mencapai status final.
- Permohonan yang menunggu proses lebih dari SLA 3 hari perlu masuk mekanisme notifikasi atau eskalasi.

## Core Requirements

### R1 - Master Data Pegawai

Sistem menyimpan master data pegawai sebagai sumber pengisian template surat.

Data minimum:
- Nomor induk pegawai.
- Nama lengkap.
- Email kerja.
- Unit kerja.
- Jabatan.
- Lokasi kerja.
- Tipe hubungan kerja.
- Tanggal mulai bekerja.
- Status pegawai.
- Nama atasan atau pejabat terkait bila diperlukan template.

Acceptance criteria:
- Admin HC dapat membuat, melihat, mengubah, menonaktifkan, dan mencari data pegawai.
- Nomor induk pegawai unik dan tidak boleh kosong.
- Pegawai hanya dapat melihat data dirinya yang relevan untuk permohonan.
- Perubahan master data yang memengaruhi surat tercatat di audit trail.
- Data pegawai nonaktif tidak hilang dari history permohonan lama.
- Pegawai nonaktif masih dapat membuat permohonan baru maksimal 1 bulan setelah tanggal dinonaktifkan; setelah periode itu pegawai hanya dapat mengakses history dan mengunduh dokumen yang masih tersedia sesuai retensi.

### R2 - Template Surat

Sistem menyimpan beberapa template Surat Keterangan Kerja yang dapat dipilih pegawai sesuai kebutuhan.

Contoh jenis template:
- Surat keterangan kerja umum.
- Surat keterangan untuk pengajuan visa.
- Surat keterangan untuk bank atau kredit.
- Surat keterangan pengalaman kerja atau paklaring bila diizinkan policy.

Acceptance criteria:
- Admin HC dapat membuat, mengubah, mengaktifkan, dan menonaktifkan template.
- Template aktif dapat dipilih oleh pegawai saat membuat permohonan.
- Template nonaktif tidak bisa dipilih untuk permohonan baru, tetapi tetap dapat dipakai untuk render ulang dokumen lama.
- Sistem menolak template yang memiliki placeholder wajib tetapi tidak tersedia sumber datanya.
- Perubahan template tidak mengubah isi dokumen final yang sudah issued.

### R3 - Pengajuan Permohonan

Pegawai mengisi form permohonan dan mengirimkannya ke verifikator.

Field minimum:
- Jenis atau template surat.
- Tujuan penggunaan surat.
- Bahasa surat bila didukung.
- Data tambahan khusus template.
- Catatan pemohon.

Acceptance criteria:
- Pegawai dapat membuat draft permohonan sebelum dikirim.
- Pegawai dapat mengirim permohonan jika field wajib lengkap dan master data minimum tersedia.
- Setelah dikirim, status berubah menjadi `submitted` dan masuk antrean verifikator.
- Pegawai tidak dapat mengubah permohonan yang sudah `submitted`, kecuali setelah dikembalikan untuk revisi.
- Sistem menampilkan nomor tracking permohonan setelah submit.

### R4 - Verifikasi Human Capital

Verifikator memeriksa permohonan sebelum diteruskan ke pejabat approver.

Acceptance criteria:
- Verifikator dapat melihat detail permohonan, master data pegawai yang dipakai, preview surat, dan history.
- Verifikator dapat mengembalikan permohonan ke pegawai dengan catatan wajib.
- Verifikator dapat menolak permohonan dengan alasan wajib jika permohonan tidak sesuai policy.
- Verifikator dapat meneruskan permohonan ke approver jika data valid.
- Verifikator meneruskan setiap permohonan ke satu approver yang berlaku untuk workflow tersebut.
- Setiap aksi verifikator tercatat dengan user, waktu, aksi, status sebelum, status sesudah, dan catatan.

### R5 - Approval Pejabat

Pejabat approver menyetujui atau mengembalikan permohonan.

Acceptance criteria:
- Approver hanya melihat permohonan yang dikirim kepadanya atau sesuai kewenangannya.
- Approver dapat melihat preview surat sebelum approve.
- Approver dapat mengembalikan permohonan ke verifikator dengan catatan wajib.
- Approver dapat approve permohonan sehingga status berubah menjadi `approved`.
- Setelah approve, sistem menerbitkan surat final, menetapkan nomor surat, tanggal terbit, data approver, dan barcode approver.
- Approval tidak membutuhkan tanda tangan gambar pada MVP; validasi approval direpresentasikan melalui barcode pada dokumen final.

### R6 - Generate dan Download Surat

Permohonan yang approved menghasilkan Surat Keterangan Kerja final yang dapat diunduh pegawai.

Acceptance criteria:
- Surat final hanya dapat diunduh setelah status `issued`.
- Pegawai hanya dapat mengunduh surat miliknya sendiri.
- Verifikator, approver terkait, admin HC, dan auditor dapat melihat atau mengunduh sesuai permission.
- Surat final berisi data dari template, master pegawai, field permohonan, nomor surat, tanggal terbit, pejabat approver, dan barcode.
- Sistem menyediakan unduhan dokumen final dalam format PDF dan DOCX.
- Dokumen final bersifat immutable; koreksi dilakukan melalui proses reissue atau permohonan baru.
- Sistem mencatat event download dengan user, waktu, dan request id.

### R7 - Tracking Status dan History

Pegawai dapat melihat tracking status dan history permohonan.

Acceptance criteria:
- Pegawai dapat melihat daftar permohonan miliknya dengan status terbaru.
- Detail permohonan menampilkan timeline status dari draft sampai issued atau rejected.
- Timeline menampilkan tanggal, aktor, status, dan catatan yang boleh dilihat pegawai.
- Catatan internal HC dapat disembunyikan dari pegawai jika ditandai internal.
- History tetap tersedia walaupun pegawai sudah nonaktif, sesuai retensi dokumen perusahaan.
- Dokumen dan audit trail tersedia selama 3 tahun sesuai kebijakan retensi.

### R8 - SLA dan Notifikasi

Sistem memantau permohonan yang menunggu tindakan terlalu lama agar proses penerbitan surat tidak tertahan tanpa perhatian.

Acceptance criteria:
- SLA setiap tahap tunggu adalah 3 hari kalender sejak status terakhir berubah.
- Sistem menandai permohonan sebagai melewati SLA jika tidak diproses dalam 3 hari kalender.
- Sistem mengirim atau menyiapkan notifikasi untuk owner tahap berjalan saat permohonan mendekati atau melewati SLA.
- Admin HC dan verifikator dapat memfilter daftar permohonan yang melewati SLA.
- Event notifikasi atau eskalasi SLA tercatat di audit trail.

## Workflow Status

Status utama:

| Status | Owner | Description |
| --- | --- | --- |
| `draft` | Pegawai | Permohonan dibuat tetapi belum dikirim. |
| `submitted` | Verifikator | Permohonan dikirim dan menunggu verifikasi HC. |
| `returned_to_employee` | Pegawai | HC mengembalikan permohonan untuk revisi. |
| `verified` | Approver | HC menyatakan data valid dan meneruskan ke approver. |
| `returned_to_hc` | Verifikator | Approver mengembalikan permohonan ke HC. |
| `approved` | Sistem | Approver menyetujui permohonan. |
| `issued` | Pegawai | Dokumen final sudah dibuat dan siap diunduh. |
| `rejected` | Final | Permohonan ditolak oleh HC atau approver. |
| `cancelled` | Final | Permohonan dibatalkan oleh pegawai sebelum final. |

Allowed transitions:

| From | Action | To | Actor |
| --- | --- | --- | --- |
| `draft` | Submit | `submitted` | Pegawai |
| `draft` | Cancel | `cancelled` | Pegawai |
| `submitted` | Return | `returned_to_employee` | Verifikator |
| `submitted` | Reject | `rejected` | Verifikator |
| `submitted` | Verify and send | `verified` | Verifikator |
| `returned_to_employee` | Resubmit | `submitted` | Pegawai |
| `returned_to_employee` | Cancel | `cancelled` | Pegawai |
| `verified` | Return to HC | `returned_to_hc` | Approver |
| `verified` | Approve | `approved` | Approver |
| `returned_to_hc` | Return to employee | `returned_to_employee` | Verifikator |
| `returned_to_hc` | Resend to approver | `verified` | Verifikator |
| `approved` | Issue document | `issued` | Sistem |

## User Stories

### US1 - Pegawai Membuat Permohonan

Sebagai pegawai, saya ingin memilih template surat dan mengisi form permohonan agar saya dapat meminta Surat Keterangan Kerja sesuai kebutuhan.

Acceptance criteria:
- Given pegawai login dan memiliki master data aktif, when membuka form permohonan, then sistem menampilkan template aktif.
- Given pegawai sudah nonaktif kurang dari atau sama dengan 1 bulan sejak tanggal dinonaktifkan, when membuka form permohonan, then sistem tetap mengizinkan pembuatan permohonan baru.
- Given pegawai sudah nonaktif lebih dari 1 bulan sejak tanggal dinonaktifkan, when membuka form permohonan, then sistem menolak pembuatan permohonan baru dan hanya mengizinkan akses history sesuai permission.
- Given field wajib belum lengkap, when pegawai submit, then sistem menampilkan validasi per field.
- Given form valid, when pegawai submit, then permohonan tersimpan dengan status `submitted` dan nomor tracking tampil.

### US2 - Pegawai Melihat Tracking

Sebagai pegawai, saya ingin melihat status dan history permohonan agar saya tahu proses sedang berada di tahap mana.

Acceptance criteria:
- Given pegawai memiliki permohonan, when membuka halaman history, then sistem menampilkan daftar permohonan miliknya.
- Given permohonan memiliki catatan pengembalian, when pegawai membuka detail, then sistem menampilkan catatan yang ditujukan ke pegawai.
- Given ada catatan internal HC, when pegawai membuka timeline, then catatan internal tidak ditampilkan.

### US3 - Verifikator Memeriksa Permohonan

Sebagai verifikator HC, saya ingin memeriksa permohonan dan master data pegawai agar hanya permohonan valid yang dikirim ke approver.

Acceptance criteria:
- Given permohonan berstatus `submitted`, when verifikator membuka antrean, then permohonan tampil di daftar verifikasi.
- Given data belum sesuai, when verifikator memilih return, then catatan wajib diisi dan status menjadi `returned_to_employee`.
- Given data valid, when verifikator memilih kirim ke approver, then status menjadi `verified` dan permohonan masuk antrean approver.

### US4 - Approver Menyetujui Permohonan

Sebagai pejabat approver, saya ingin melihat preview surat dan menyetujui permohonan agar surat final dapat diterbitkan.

Acceptance criteria:
- Given permohonan berstatus `verified`, when approver membuka detail, then preview surat ditampilkan.
- Given approver menyetujui, when sistem memproses approval, then status menjadi `approved` lalu `issued` jika dokumen final berhasil dibuat.
- Given dokumen berhasil diterbitkan, when pegawai membuka detail permohonan, then sistem menyediakan download PDF dan DOCX.
- Given dokumen gagal dibuat, when approval sudah tercatat, then sistem menampilkan status gagal issue yang dapat ditangani admin tanpa kehilangan audit approval.

### US5 - Pegawai Mengunduh Surat

Sebagai pegawai, saya ingin mengunduh surat yang sudah approved agar dapat menggunakan dokumen resmi perusahaan.

Acceptance criteria:
- Given permohonan berstatus `issued`, when pegawai membuka detail, then tombol download tersedia.
- Given permohonan belum `issued`, when pegawai membuka detail, then tombol download tidak tersedia.
- Given pegawai mencoba akses surat milik pegawai lain, when request download dikirim, then sistem menolak dengan error unauthorized atau forbidden.

### US6 - Admin HC Mengelola Template

Sebagai Admin HC, saya ingin mengelola template surat agar perusahaan dapat menyediakan format surat sesuai kebutuhan pegawai.

Acceptance criteria:
- Given admin membuat template dengan placeholder valid, when disimpan, then template dapat diaktifkan.
- Given template sudah pernah dipakai dokumen issued, when admin mengubah template, then perubahan hanya berlaku untuk permohonan baru.
- Given admin menonaktifkan template, when pegawai membuat permohonan baru, then template tersebut tidak tampil.

## Permission Matrix

| Capability | Pegawai | Verifikator HC | Approver | Admin HC | Auditor |
| --- | --- | --- | --- | --- | --- |
| View own requests | Yes | No | No | Yes | Read |
| Create request | Yes, including inactive up to 1 month after deactivation | On behalf if allowed | No | On behalf if allowed | No |
| Edit draft request | Own only | No | No | Yes | No |
| Submit request | Own only | No | No | Yes | No |
| Verify request | No | Yes | No | Yes | No |
| Return to employee | No | Yes | No | Yes | No |
| Return to HC | No | No | Yes | No | No |
| Approve request | No | No | Yes | No | No |
| Reject request | No | Yes | Yes if configured | Yes | No |
| Download issued document | Own only | Related requests | Related approvals | Yes | Read |
| Manage employee master | No | Limited read | No | Yes | Read |
| Manage templates | No | No | No | Yes | Read |
| View audit trail | Own visible events | Related workflow | Own approvals | Yes | Yes |

## Data Sensitivity Notes

- PII high risk: nomor induk pegawai, nama, email, unit, jabatan, lokasi, tanggal mulai kerja, dan data tambahan yang dimasukkan pegawai.
- Legal/audit high risk: surat final, nomor surat, approval, barcode, timeline, catatan return/reject, dan event download.
- Access control wajib berbasis owner dan role. Pegawai tidak boleh membaca permohonan atau dokumen pegawai lain.
- Audit log tidak boleh menyimpan data rahasia yang tidak diperlukan, misalnya full payload dokumen atau file final dalam bentuk text.
- Barcode tidak boleh menjadi satu-satunya kontrol akses. Jika barcode memuat URL validasi, endpoint validasi harus membatasi data yang ditampilkan ke publik.
- Dokumen final dan audit trail disimpan selama 3 tahun, lalu mengikuti proses arsip atau purge yang disetujui policy perusahaan.

## Edge Cases

- Master data pegawai tidak lengkap untuk template yang dipilih.
- Template aktif dihapus atau dinonaktifkan saat permohonan masih berjalan.
- Approver berubah jabatan setelah dokumen issued.
- Nomor surat sudah reserved tetapi generate dokumen gagal.
- Pegawai mengirim dua permohonan dengan kebutuhan yang sama dalam waktu berdekatan.
- Pegawai nonaktif ingin mengunduh ulang surat yang pernah issued.
- Pegawai nonaktif membuat permohonan baru dalam 1 bulan setelah tanggal dinonaktifkan.
- Pegawai nonaktif mencoba membuat permohonan baru setelah lewat 1 bulan dari tanggal dinonaktifkan.
- Verifikator atau approver mencoba memproses permohonan yang sudah berubah status oleh aktor lain.
- Catatan return kosong.
- File final hilang atau storage gagal saat download.
- Barcode dipindai oleh pihak eksternal.
- Permohonan melewati SLA 3 hari karena owner tahap belum mengambil tindakan.

## Non-Goals

- Sistem tidak menentukan legalitas akhir isi surat tanpa validasi policy perusahaan.
- Sistem tidak mengirim dokumen ke pihak ketiga.
- Sistem tidak menyimpan tanda tangan digital tersertifikasi pada MVP.
- Sistem tidak membuat workflow approval multi-level kecuali dikonfigurasi sebagai fase lanjutan.
- Sistem tidak melakukan sinkronisasi otomatis dengan HRIS eksternal pada MVP.
- Sistem tidak memakai tanda tangan gambar approver pada MVP; approval direpresentasikan dengan barcode validasi.

## Example Screen Behavior

### Employee Request Form

- Menampilkan dropdown template aktif.
- Menampilkan field tujuan penggunaan dan catatan.
- Menampilkan field tambahan berdasarkan template yang dipilih.
- Menampilkan preview data pegawai yang akan dipakai di surat.
- Submit disabled atau menampilkan error jika field wajib belum lengkap.

### Employee Tracking Detail

- Menampilkan nomor tracking, jenis surat, status terkini, tanggal submit, dan tanggal issued jika ada.
- Menampilkan timeline status.
- Menampilkan catatan return yang dapat dibaca pegawai.
- Menampilkan tombol download PDF dan DOCX hanya untuk status `issued`.

### HC Verification Queue

- Menampilkan daftar permohonan `submitted` dan `returned_to_hc`.
- Mendukung filter status, tanggal submit, unit kerja, template, SLA terlewati, dan keyword pegawai.
- Detail menampilkan preview surat, master data, catatan pemohon, dan tombol return, reject, atau send to approver.

### Approver Queue

- Menampilkan daftar permohonan `verified`.
- Detail menampilkan preview surat, ringkasan pegawai, catatan verifikator, dan tombol approve atau return to HC.

## Example API Behavior

Catatan: bentuk endpoint final akan ditentukan Backend Architect Agent. Contoh ini hanya untuk memperjelas behavior.

Create request:

```http
POST /api/work-certificate-requests
Content-Type: application/json

{
  "template_id": "template_general",
  "purpose": "Pengajuan KPR",
  "language": "id",
  "additional_fields": {
    "recipient": "Bank ABC"
  },
  "employee_note": "Mohon diterbitkan untuk kebutuhan administrasi bank."
}
```

Successful response:

```json
{
  "id": "wcr_123",
  "tracking_number": "SKK-2026-000123",
  "status": "submitted",
  "submitted_at": "2026-08-26T09:30:00+07:00"
}
```

Return by verifier:

```http
POST /api/work-certificate-requests/wcr_123/return-to-employee
Content-Type: application/json

{
  "note": "Tujuan penggunaan surat perlu dibuat lebih spesifik.",
  "visible_to_employee": true
}
```

Approve by approver:

```http
POST /api/work-certificate-requests/wcr_123/approve
Content-Type: application/json

{
  "note": "Disetujui."
}
```

Issued document metadata example:

```json
{
  "id": "wcr_123",
  "status": "issued",
  "letter_number": "001/KP.204/KI-2026",
  "issued_at": "2026-08-26T10:15:00+07:00",
  "available_formats": ["pdf", "docx"]
}
```

Download final document:

```http
GET /api/work-certificate-requests/wcr_123/document?format=pdf
GET /api/work-certificate-requests/wcr_123/document?format=docx
```

## Product Risks

- Salah isi master data dapat menghasilkan surat legal yang keliru.
- Permission yang lemah dapat membocorkan data pegawai atau surat resmi.
- Nomor surat dan approval yang tidak immutable dapat menimbulkan risiko audit.
- Barcode validasi yang terlalu terbuka dapat membocorkan data pegawai ke pihak eksternal.
- Template tanpa kontrol placeholder dapat menyebabkan dokumen final rusak atau kosong.
- Race condition pada approval dan nomor surat dapat menghasilkan dokumen ganda atau nomor duplikat.
- Retensi 3 tahun perlu proses arsip atau purge yang aman agar dokumen legal tidak hilang terlalu cepat atau tersimpan lebih lama dari policy.
- SLA 3 hari membutuhkan definisi channel notifikasi final dan job scheduler yang reliable.

## Open Questions

- Channel notifikasi SLA yang dipakai pada MVP perlu diputuskan: in-app, email, atau kombinasi.
- Apakah perhitungan SLA 3 hari memakai hari kalender atau hari kerja perlu dikonfirmasi bila kebijakan perusahaan berubah; requirement saat ini memakai hari kalender.

## Handoff to Backend Architect Agent

## Context
- Feature: Surat Keterangan Kerja request workflow.
- Scope: master pegawai, template, request, verification, approval, issued document, barcode, tracking, history.
- Non-goals: certified digital signature, HRIS integration, external delivery, multi-level approval beyond basic configuration.

## Decisions
- Decision: MVP memakai workflow satu verifikator dan satu approver.
- Reason: alur pengguna yang diberikan hanya membutuhkan verifikasi HC sebelum approval pejabat.
- Decision: format nomor surat adalah `[nomor urut]/KP.204/KI-[TAHUN]`.
- Reason: mengikuti format resmi perusahaan yang sudah diputuskan.
- Decision: approval memakai barcode, bukan tanda tangan gambar atau tanda tangan elektronik tersertifikasi pada MVP.
- Reason: barcode cukup untuk validasi approval MVP dan tanda tangan elektronik menjadi fase lanjutan bila dibutuhkan.
- Decision: pegawai nonaktif masih dapat membuat permohonan baru sampai 1 bulan setelah dinonaktifkan.
- Reason: memberi masa transisi administratif setelah status pegawai berubah.
- Decision: dokumen final tersedia sebagai PDF dan DOCX.
- Reason: kebutuhan pengguna mencakup format final siap pakai dan format dokumen yang dapat dibuka sebagai arsip kerja.
- Decision: retensi dokumen dan audit trail adalah 3 tahun.
- Reason: mengikuti keputusan retensi bisnis.
- Decision: SLA permohonan menunggu adalah 3 hari dan perlu notifikasi.
- Reason: mencegah permohonan tertahan terlalu lama tanpa tindak lanjut.
- Decision: dokumen issued immutable.
- Reason: nomor surat, approval, dan dokumen final adalah data legal/audit.

## Files/Modules
- Planned: backend module for work certificate requests, employee master, templates, document generation, audit trail, web screens, optional Flutter screens.
- Changed: docs/product/work-certificate-requirements.md.

## Contracts
- API: sample behavior tersedia di bagian Example API Behavior; endpoint final perlu ditentukan Backend Architect Agent.
- Database: perlu model employee, certificate_template, work_certificate_request, workflow_event, issued_document, barcode_validation_token atau document_verification, SLA marker/notification event, dan retention metadata.
- UI: form pegawai, tracking detail, HC queue, approver queue, template admin, employee master admin.

## Verification
- Tests run: documentation-only change, no automated tests required.
- Tests still needed: acceptance tests untuk workflow, permission negative cases, template placeholder validation, document generation PDF/DOCX, barcode validation, batas pembuatan permohonan pegawai nonaktif 1 bulan, SLA 3 hari, dan retensi 3 tahun.

## Risks
- Blocking: channel notifikasi SLA dan mekanisme scheduler perlu dipilih sebelum implementasi production.
- Non-blocking: multi-level approval dan integrasi tanda tangan elektronik dapat direncanakan sebagai fase lanjutan.
