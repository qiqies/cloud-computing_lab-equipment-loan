# Cloud Computing: Phone Rental

Proyek individu Cloud Computing (AWS), Week 12: Design & AWS Setup.
Sistem rental HP berbasis serverless (Track C).

- **Nama:** Aqidatul Izzah
- **NIM:** 24/533730/TK/59137
- **Track:** C (Serverless)
- **Runtime:** Python (AWS Lambda)
- **Region:** us-east-1

## Ringkasan

Pengguna dapat mencatat penyewaan HP, melihat statusnya, memperbarui status saat
HP dikembalikan (termasuk denda jika terlambat), dan menghapus catatan. Setiap
operasi CRUD dibuat sebagai satu fungsi Lambda terpisah (microservices, bukan
monolitik).

## Arsitektur

Ada dua versi karena pembatasan izin di AWS Learner Lab sandbox.

### 1. Arsitektur target (desain)

Client -> API Gateway -> Lambda (satu fungsi per operasi) -> DynamoDB (tabel `Rentals`),
log ke CloudWatch. Diagram: [`docs/architecture-target.png`](docs/architecture-target.png)

### 2. Varian sandbox (yang dijalankan)

Client -> Lambda Function URL -> Lambda (satu fungsi per operasi) -> S3
(bucket `phone-rental-533730`), log ke CloudWatch.
Diagram: [`docs/architecture-sandbox.png`](docs/architecture-sandbox.png)

### Alasan varian sandbox

| Aksi | Hasil | Bukti |
|---|---|---|
| `dynamodb:CreateTable` | Ditolak | `evidence/01-error-dynamodb-createtable.png` |
| `apigateway:POST` pada `/restapis` (REST API) | Ditolak | `evidence/02-error-apigw-rest-api.png` |
| `apigateway:PUT` pada `/apis` (HTTP API) | Ditolak | `evidence/03-error-apigw-http-api.png` |

Layanan yang berhasil dipakai: Lambda, Lambda Function URL, dan S3. Karena itu
DynamoDB diganti S3 dan API Gateway diganti Function URL pada implementasi.

## Entitas `Rental`

| Atribut | Tipe | Keterangan |
|---|---|---|
| rentalId | String | UUID, dibuat otomatis oleh Lambda |
| phoneModel | String | Model HP, misalnya "Samsung Galaxy A15" |
| renterName | String | Nama penyewa |
| renterContact | String | Kontak penyewa (nomor HP/email) |
| rentDate | String (ISO 8601) | Tanggal mulai sewa |
| dueDate | String (ISO 8601) | Batas pengembalian |
| dailyRate | Number | Tarif sewa per hari (Rp) |
| status | String | `RENTED` atau `RETURNED` |
| returnDate | String atau null | Tanggal kembali, diisi saat `RETURNED` |
| lateFee | Number | Denda keterlambatan (Rp), default 0 |

Penyimpanan varian sandbox: satu objek JSON per sewa dengan key
`rentals/{rentalId}.json`.

**Aturan denda:** `lateDays = max(0, returnDate - dueDate)` (hari),
`lateFee = lateDays x dailyRate x 2`. Dihitung dan disimpan oleh `updateRental` saat status
diubah ke `RETURNED` (sudah diimplementasikan dan diuji).

## Endpoint CRUD

| Operasi | Route (target) | Fungsi Lambda | Sukses | Gagal |
|---|---|---|---|---|
| Create | `POST /rentals` | `createRental` | 201 | 400 |
| Read | `GET /rentals/{id}` | `getRental` | 200 | 404 |
| Update | `PUT /rentals/{id}` | `updateRental` | 200 | 400, 404 |
| Delete | `DELETE /rentals/{id}` | `deleteRental` | 200 | 404 |

Pada varian sandbox, setiap fungsi memiliki Function URL sendiri dan id dikirim lewat
query string (`?id=<rentalId>`). Karena itu method HTTP tidak dicek oleh kode; pemisahan
method per route baru terjadi pada arsitektur target (API Gateway).

## Struktur repo

```
.
├── docs/        diagram arsitektur dan design brief
├── evidence/    screenshot dan bukti pengujian AWS
├── src/         kode Lambda (satu folder per fungsi)
│   ├── createRental/
│   ├── getRental/
│   ├── updateRental/
│   └── deleteRental/
└── README.md
```

## Bukti AWS

Semua screenshot ada di folder `evidence/` (akun, Lab ID, email, dan Function URL
sudah ditutup).

| No | Bukti | File |
|---|---|---|
| 01-03 | Error izin: DynamoDB `CreateTable`, REST API, HTTP API | `01-error-dynamodb-createtable`, `02-error-apigw-rest-api`, `03-error-apigw-http-api` |
| 04-06 | Bucket S3 `phone-rental-533730` (form, terbuat, Block Public Access) | `04-s3-create-bucket-form`, `05-s3-bucket-created`, `06-s3-block-public-access` |
| 07-13 | `rental-createRental`: form, kode, env var, LabRole, tes 201 dan 400, objek di S3 | `07-lambda-create-form` sampai `13-s3-object-created` |
| 14-17 | `rental-getRental`: kode, env var, tes 200 dan 404 | `14-lambda-getRental-code` sampai `17-lambda-getRental-test-404` |
| 18-22 | `rental-updateRental`: kode, env var, tes 200 (lateFee 200000) dan 400, get setelah update | `18-lambda-updateRental-code` sampai `22-lambda-getRental-after-update` |
| 23-27 | `rental-deleteRental`: kode, env var, tes 200 dan 404, S3 setelah hapus | `23-lambda-deleteRental-code` sampai `27-s3-after-delete` |
| 28-31 | Konfigurasi Function URL empat fungsi (auth NONE, URL ditutup sebagian) | `28-function-url-createRental` sampai `31-function-url-deleteRental` |
| 32-34 | Postman Create: 201, objek di S3, 400 | `32-postman-create-201` sampai `34-postman-create-400` |
| 35-36 | Postman Get: 200 dan 404 | `35-postman-get-200`, `36-postman-get-404` |
| 37-39 | Postman Update: 200, 400, get setelah update | `37-postman-put-200` sampai `39-postman-get-after-update` |
| 40-41 | Postman Delete: 200 dan 404 | `40-postman-delete-200`, `41-postman-delete-404` |
| 42 | Function URL sudah dihapus setelah pengujian | `42-function-url-deleted` |

Video demo (3 menit): <link video>

## Rencana deployment

Varian sandbox (sudah dijalankan untuk keempat fungsi):

1. Buat bucket S3 `phone-rental-533730` (Block all public access aktif).
2. Buat empat fungsi Lambda Python (`rental-createRental`, `rental-getRental`,
   `rental-updateRental`, `rental-deleteRental`) dengan role `LabRole` dan environment
   variable `BUCKET_NAME`.
3. Uji tiap fungsi dengan test event di console Lambda.
4. Buat Function URL per fungsi, uji dengan Postman, ambil bukti, lalu hapus Function URL.

Arsitektur target (jika izin tersedia): tabel DynamoDB `Rentals` (on-demand), Lambda
per operasi dengan `LabRole`, REST API di API Gateway dengan Lambda proxy integration.
Kode Lambda sudah membaca `pathParameters.id`, sehingga tinggal mengganti penyimpanan
dari S3 ke DynamoDB.

## Status

- [x] Struktur repo
- [x] Diagram arsitektur dan design brief
- [x] Bucket S3
- [x] Lambda `createRental` (tes 201 dan 400)
- [x] Lambda `getRental` (tes 200 dan 404)
- [x] Lambda `updateRental` (tes 200 dan 400, denda keterlambatan)
- [x] Lambda `deleteRental` (tes 200 dan 404)
- [x] Uji CRUD lewat Function URL dan Postman
- Catatan: DynamoDB dan API Gateway diblokir di sandbox

## Keamanan

- Semua Lambda memakai `LabRole` bawaan Learner Lab (pembuatan role baru dibatasi).
- Bucket S3 tidak publik.
- Function URL dengan auth `NONE` hanya untuk pengujian, URL-nya tidak
  dipublikasikan di repo ini, dan sudah dihapus setelah bukti diambil.
- Kredensial AWS tidak disimpan di repo (lihat `.gitignore`).