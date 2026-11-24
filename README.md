# Cloud Computing: Lab Equipment Loan

Sistem peminjaman alat lab/kampus berbasis serverless.

- **Nama:** Aqidatul Izzah
- **NIM:** 24/533730/TK/59137

## Arsitektur

API Gateway -> Lambda (satu fungsi per operasi CRUD) -> DynamoDB.
Diagram: `docs/architecture.png` (menyusul).

## Entitas `Loan`

| Atribut | Tipe | Keterangan |
|---|---|---|
| loanId | String (PK) | UUID |
| equipmentName | String | Nama alat |
| borrowerName | String | Nama peminjam |
| borrowDate | String (ISO 8601) | Tanggal pinjam |
| dueDate | String (ISO 8601) | Batas pengembalian |
| status | String | BORROWED / RETURNED |

## Endpoint CRUD

| Operasi | Route | Fungsi |
|---|---|---|
| Create | POST /loans | createLoan |
| Read | GET /loans/{id} | getLoan |
| Update | PUT /loans/{id} | updateLoan |
| Delete | DELETE /loans/{id} | deleteLoan |

## Struktur repo

- `docs/` : diagram dan design brief
- `evidence/` : screenshot dan output tes AWS
- `src/` : kode Lambda (satu folder per fungsi)
