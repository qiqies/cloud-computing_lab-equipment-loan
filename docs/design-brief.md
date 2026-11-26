# Design Brief: Phone Rental

**Nama:** Aqidatul Izzah | **NIM:** 24/533730/TK/59137 | **Track:** C (Serverless) | **Region:** us-east-1

## 1. Use case

Sistem rental HP. Operator mencatat penyewaan HP, melihat status sewa, memperbarui
status saat HP dikembalikan, dan menghapus catatan yang salah. Keterlambatan
dikenai denda harian. Masalah yang diselesaikan: pencatatan sewa manual mudah
hilang, dan denda sulit dihitung konsisten.

## 2. Solusi dan track

Track C (Serverless). Alasan: biaya mengikuti pemakaian (hemat kredit Learner Lab),
tidak ada server yang dikelola, dan setiap operasi dapat dipecah menjadi layanan
mandiri sesuai syarat arsitektur non-monolitik.

## 3. Arsitektur

Dua versi disajikan karena pembatasan izin di sandbox (lihat bagian 8).

**Arsitektur target** (`architecture-target.png`): Client -> API Gateway -> Lambda
-> DynamoDB, log ke CloudWatch.

**Varian sandbox yang dijalankan** (`architecture-sandbox.png`): Client -> Lambda
Function URL -> Lambda -> S3, log ke CloudWatch.

Alur (nomor pada diagram): (1) client mengirim request HTTPS, (2) diteruskan ke
fungsi Lambda sesuai operasi, (3) Lambda membaca atau menulis penyimpanan data,
(4) log dikirim ke CloudWatch. Respons kembali lewat jalur yang sama.

## 4. Pemecahan microservices

Satu Lambda per operasi (`createRental`, `getRental`, `updateRental`,
`deleteRental`), sehingga masing-masing dapat di-deploy, diskalakan, dan di-debug
terpisah. Pada varian sandbox, tiap fungsi memiliki Function URL sendiri.
Rencana pengembangan: service katalog `Phone` (stok dan ketersediaan HP) dan
service notifikasi keterlambatan.

## 5. Entitas data: Rental

| Atribut       | Tipe              | Keterangan                        |
| ------------- | ----------------- | --------------------------------- |
| rentalId      | String            | UUID, dibuat otomatis oleh Lambda |
| phoneModel    | String            | Model HP yang disewa              |
| renterName    | String            | Nama penyewa                      |
| renterContact | String            | Kontak penyewa                    |
| rentDate      | String (ISO 8601) | Tanggal mulai sewa                |
| dueDate       | String (ISO 8601) | Batas pengembalian                |
| dailyRate     | Number            | Tarif sewa per hari (Rp)          |
| status        | String            | `RENTED` atau `RETURNED`          |
| returnDate    | String atau null  | Tanggal kembali                   |
| lateFee       | Number            | Denda keterlambatan (Rp)          |

Penyimpanan: tabel DynamoDB `Rentals` (target) atau objek JSON
`rentals/{rentalId}.json` di bucket S3 (sandbox).

**Aturan denda:** `lateDays = max(0, returnDate - dueDate)`;
`lateFee = lateDays x dailyRate x 2`. Contoh: tarif Rp 50.000, jatuh tempo
2026-11-29, dikembalikan 2026-12-01 -> terlambat 2 hari -> denda 2 x 100.000 =
Rp 200.000. `updateRental` menghitung dan menyimpan `returnDate` serta `lateFee`
saat status menjadi `RETURNED` (diimplementasikan dan diuji).

## 6. Endpoint CRUD

| Operasi | Route (target)         | Fungsi       | Sukses | Gagal    |
| ------- | ---------------------- | ------------ | ------ | -------- |
| Create  | `POST /rentals`        | createRental | 201    | 400      |
| Read    | `GET /rentals/{id}`    | getRental    | 200    | 404      |
| Update  | `PUT /rentals/{id}`    | updateRental | 200    | 400, 404 |
| Delete  | `DELETE /rentals/{id}` | deleteRental | 200    | 404      |

Contoh `POST /rentals`:

```json
{
  "phoneModel": "Iphone 18 Pro Max",
  "renterName": "Cici Marici",
  "renterContact": "081234567890",
  "rentDate": "2026-11-26",
  "dueDate": "2026-11-29",
  "dailyRate": 300000
}
```

Respons 201 berisi data di atas ditambah `rentalId` (UUID), `status: "RENTED"`,
`returnDate: null`, dan `lateFee: 0`. Body tidak lengkap atau tidak valid
(tarif bukan angka positif, format tanggal salah, `dueDate` sebelum `rentDate`)
menghasilkan 400. Id yang tidak ada menghasilkan 404 (`Rental not found`).

Pada varian sandbox, `id` dikirim lewat query string (`?id=<rentalId>`) karena Function URL
tidak punya path parameter. Method HTTP tidak dicek oleh kode; pemisahan method per route
baru terjadi pada arsitektur target (API Gateway).

Contoh `PUT /rentals/{id}` (HP dikembalikan):

```json
{ "status": "RETURNED", "returnDate": "2026-12-01" }
```

## 7. IAM dan keamanan

- Semua Lambda memakai `LabRole` bawaan Learner Lab (pembuatan role baru dibatasi).
  Rencana produksi: role terpisah dengan izin minimal per fungsi.
- Bucket S3 tidak publik. Akses data hanya lewat Lambda.
- Function URL dengan auth `NONE` hanya untuk pengujian dan sudah dihapus setelah bukti
  diambil. Produksi seharusnya memakai autentikasi.
- Data kontak penyewa hanya berupa data contoh. Kredensial AWS tidak disimpan di repo.

## 8. Batasan sandbox dan rencana

Pada percobaan, role `voclabs` ditolak untuk `dynamodb:CreateTable`, pembuatan REST
API, dan pembuatan HTTP API di API Gateway (bukti: `evidence/01` sampai `03`).
Layanan yang berhasil dipakai: Lambda, Lambda Function URL, dan S3. Karena itu
implementasi memakai varian sandbox, sedangkan arsitektur target tetap menjadi
desain acuan.

Status implementasi: keempat operasi CRUD berjalan dan teruji pada varian sandbox, lewat
test event Lambda dan lewat Function URL dengan Postman (bukti: `evidence/04` sampai
`42`, dan video demo). Pengujian mencakup 201 dan 400 (create), 200 dan 404 (get),
200 dan 400 (update, termasuk perhitungan `lateFee`), serta 200 dan 404 (delete).

Batasan yang diketahui:

1. arsitektur target belum bisa dijalankan karena izin sandbox.
2. Function URL tidak memisahkan method per route.
3. tidak ada autentikasi, karena
   Function URL hanya dibuka sementara untuk pengujian.
4. belum ada cek ketersediaan HP
   (rencana: service katalog `Phone`).
