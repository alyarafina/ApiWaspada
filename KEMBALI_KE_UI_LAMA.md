# Cara kembali ke tampilan (UI) lama

UI baru = file `frontend/assets/css/ui-baru.css` + beranda yang ditata ulang.
UI lama disimpan di dua tempat: tag git `ui-lama` dan folder `_backup_frontend_sebelum_ui_baru/`.

## Cara 1 — pakai git (disarankan)

Jalankan di PowerShell, dari folder `ApiWaspada_argon_benerin`:

```
git checkout ui-lama -- frontend
```

Perintah ini mengembalikan semua file di `frontend/` persis seperti sebelum UI baru.
File `frontend/assets/css/ui-baru.css` boleh dihapus (sudah tidak dipakai).

## Cara 2 — tanpa git (salin manual)

1. Hapus folder `frontend`.
2. Salin folder `_backup_frontend_sebelum_ui_baru`, lalu ganti namanya menjadi `frontend`.

## Cara 3 — hanya matikan tema baru

Hapus baris berikut di setiap file `frontend/*.html`:

```
<link rel="stylesheet" href="/assets/css/ui-baru.css?v=20261113a" />
```

Catatan: cara ini mengembalikan warna dan gaya, tetapi susunan beranda tetap versi baru.
Untuk benar-benar kembali seperti semula, gunakan Cara 1 atau Cara 2.

Setelah kembali, muat ulang halaman di browser/HP (tarik ke bawah atau Ctrl+F5).
Server tidak perlu di-restart.
