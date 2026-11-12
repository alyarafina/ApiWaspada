# Direktori Penyimpanan Model Bobot YOLO (`ml/weights/`)

Tempatkan file hasil pelatihan model terbaik Anda dengan nama:

```
ml/weights/best.pt
```

## Kebijakan Integritas Model
- Aplikasi **ApiWaspada** **tidak menyertakan file `best.pt` palsu atau kosong**.
- Apabila `ml/weights/best.pt` belum tersedia di folder ini, backend FastAPI (`backend/app/services/ai_service.py`) secara otomatis berjalan dalam **Mode AI Belum Aktif (Graceful Fallback)** dan menampilkan status `"Deteksi gagal atau model belum tersedia"` secara transparan kepada pengguna maupun petugas.
- Setelah Anda menjalankan pelatihan melalui `ml/ApiWaspada_Training_YOLO.ipynb` atau `python ml/train.py`, bobot terbaik (`best.pt`) akan otomatis disalin ke folder ini dan modul deteksi AI pada aplikasi web akan langsung aktif tanpa perlu mengubah kode sumber.
