# Model bobot YOLO (`ml/weights/`)

File model disimpan lewat **Git LFS** (lihat `.gitattributes`). Setelah clone, jalankan
`git lfs pull` bila file `.pt` masih berupa penunjuk kecil (sekitar 130 byte).

| File | Ukuran | Keterangan | Kunci di aplikasi |
|---|---|---|---|
| `fire_n.pt` | 6 MB | YOLOv8 Nano, D-Fire Dataset. Paling cepat. | `fire_n` |
| `fire_m.pt` | 52 MB | YOLOv8 Medium, D-Fire Dataset. Seimbang, model default. | `fire_m` |
| `fire_l.pt` | 88 MB | YOLOv8 Large, D-Fire Dataset. Paling teliti. | `fire_l` |
| `best.pt` | 6 MB | Model hasil pelatihan tim ApiWaspada (`ml/train.py` / notebook). | `best` |

Model default diatur dengan `YOLO_DEFAULT_MODEL` di `.env` (bawaan: `fire_m`).

## Sumber dan lisensi

`fire_n.pt`, `fire_m.pt`, dan `fire_l.pt` berasal dari repositori
*wildfire-detection* karya Alim Tleuliyev (demo: wildfire-detection.streamlit.app),
dilatih pada D-Fire Dataset, dan dirilis dengan lisensi MIT. Teks lisensi lengkap ada di
`LICENSE-fire-models.txt` dan wajib disertakan setiap kali file ini dibagikan.

`best.pt` adalah hasil pelatihan sendiri.
