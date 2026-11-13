# ApiWaspada: sistem desain

## Brief (fase 0)

- **Subjek:** ApiWaspada, layanan pelaporan dugaan kebakaran untuk Kota Jambi (prototype lomba).
- **Pengguna:** warga yang melihat api atau asap (di HP, sering panik, sering di luar ruangan),
  petugas verifikasi (laptop dan HP), juri lomba.
- **Tugas situs:** laporan terkirim dalam kurang dari 1 menit (foto + titik lokasi), lalu warga
  bisa melacak statusnya. Kedua: membangun rasa percaya bahwa laporan benar-benar ditindaklanjuti.
- **Aset:** logo pin peta berisi api (gradasi merah ke jingga), palet 4 warna dari pemilik.
- **Bahasa:** Indonesia. **Batasan:** HTML/CSS/JS biasa yang dilayani FastAPI (bukan framework),
  harus jalan di HP kelas menengah dan di jaringan seluler.
- **Asumsi:** tidak ada foto asli kejadian; gambar tidak dikarang. Angka laporan selalu dari API.

## Konsep (fase 1)

| | A. Titik api (tempat + bahan) | B. Pin yang dijatuhkan (logo) | C. Tiga ketukan (sistem formal) |
|---|---|---|---|
| Ide | Situs dibaca seperti papan pantau titik api Kota Jambi: setiap laporan warga adalah satu titik berkoordinat | Semua aksi adalah menjatuhkan pin di peta | Seluruh situs disusun sebagai tiga ketukan: foto, titik, kirim |
| Anchor | Jambi akrab dengan "titik api" (hotspot karhutla di musim kemarau); aplikasi ini memang menyimpan koordinat | logo berbentuk pin | alur lapor yang pendek |
| Signature | pin logo berdenyut di koordinat Kota Jambi di peta hero, cincin denyut = titik yang sedang dipantau | pin jatuh dan memantul saat tombol lapor ditekan | progres tiga ketukan di setiap halaman |
| O / F / Fe / P | 4 / 5 / 5 / 2 | 3 / 4 / 4 / 4 | 3 / 3 / 5 / 4 |

**Pilih A.** Paling melekat ke Jambi dan ke data aplikasi (koordinat nyata, jumlah titik nyata),
dan murah dibangun dengan Leaflet yang sudah ada. Diambil dari C untuk halaman lapor: progres
Foto / Keterangan / Lokasi yang sudah ada dipertahankan.

```
Idea:        Setiap laporan warga adalah satu titik api di peta Kota Jambi.
Metaphor:    Papan pantau titik api (hotspot) saat musim kemarau.
Signature:   Pin logo berdenyut di koordinat pusat Kota Jambi di peta hero; titik laporan nyata di sekitarnya.
Emotion:     Tenang dan sigap: "ada yang memantau, laporan saya sampai".
Motion verb: Naik seperti panas (hover: isian naik dari bawah; panah bergerak ke kanan atas; reveal naik 12 px).
Screenshot:  Hero terbelah: judul besar di kiri, peta dengan pin logo berdenyut di kanan.
```

Tes generik: model biasa akan membuat hero gelap bergradasi dengan blob api dan tombol bulat
merah. Yang diubah: hero terang, peta nyata sebagai gambar utama, tanpa gradasi dekoratif, tanpa
tombol bulat SOS, label kecil hanya untuk data nyata (koordinat, kode laporan).

## Sistem (fase 2)

### Palet (dari pemilik)
| Peran | Hex | Pakai |
|---|---|---|
| `bara` (curtain/field) | #60241E | blok gelap (darurat, footer), judul besar |
| `merah` (aksi) | #95271D | tombol utama, tautan; putih di atasnya 8.6:1 |
| `mawar` (aksen kedua) | #B34A44 | cincin fokus, garis aktif, ikon |
| `jingga` (sinyal) | #E77B49 | denyut titik, sorotan di atas `bara` saja (bukan teks di latar terang) |
| `ground` | #F6F4F3 | latar halaman, abu netral (bukan krem) |
| `ink` | #21130F | teks isi; 15:1 di atas ground |
| `muted` | #6A5550 | teks kedua; 6:1 di atas ground |
| `line` | #60241E 14% | garis rambut |
Warna status (menunggu, diverifikasi, selesai, ditolak) tetap amber/biru/hijau/abu karena itu
makna fungsional, bukan identitas.

### Tipe
- **Plus Jakarta Sans** (Tokotype, dibuat untuk identitas kota Jakarta): satu keluarga untuk
  display dan teks. Display 800, tracking -0.04em, leading 0.95. Teks 16 sampai 17 px, leading 1.55.
- **JetBrains Mono** 500 hanya untuk data: koordinat, kode laporan (AW-...), angka nomor darurat.
- Skala: display `clamp(2.5rem, 1.1rem + 5.6vw, 5.5rem)`, h2 `clamp(1.6rem, 1.1rem + 1.8vw, 2.6rem)`.

### Grid dan ritme
- 12 kolom di desktop (gutter 24 px), 4 di HP (gutter 16 px). Hero: teks kolom 1 sampai 5, peta 6 sampai 12.
- Ritme seksi: rapat (hero ke darurat), normal (langkah), lega (daftar menu), finale (footer).

### Bentuk
- Satu aturan radius: 12 px untuk kotak, tombol, input, peta. Pil (999 px) hanya untuk chip status.
- Tanpa bayangan dekoratif. Kedalaman dari garis rambut dan blok warna.

### Gerak
- Ease `cubic-bezier(.2,.7,.2,1)`, 380 ms untuk isian, 240 ms untuk panah.
- Tombol utama: isian `bara` naik dari bawah (transform scaleY). Tautan nav: garis bawah tergambar.
  Baris menu: latar naik + panah ke kanan atas. Panah: geser 4 px.
- Idle: cincin denyut di pin hero (titik yang dipantau). Mati saat reduced motion.
- Antarhalaman: View Transitions bawaan browser (konten naik 12 px dan memudar), mati saat reduced motion.
- Tanpa loader, tanpa WebGL (situs layanan darurat: kecepatan lebih penting dari teater).

### Komposisi beranda
```
HP (390)                         Desktop (1440)
[logo ApiWaspada      113]       [logo   Beranda Lapor Lacak Peta Panduan   Petugas 113]
[H1 Lihat api atau asap?  ]      [H1 besar          |  PETA + pin berdenyut           ]
[  Kirim titiknya.        ]      [lead              |  koordinat -1.6101 103.6131     ]
[lead                     ]      [Laporkan titik api|  3 chip jumlah nyata            ]
[Laporkan titik api  (btn)]      [Lacak laporan ->  |                                 ]
[status layanan . AI      ]      [status            |                                 ]
[PETA 300px + pin + chip  ]      [=== blok bara: Ada orang terjebak? 113 112 110 ===]
[== blok bara: darurat ===]      [Cara melapor: 4 langkah berurutan, garis penghubung]
[langkah 1-4 vertikal     ]      [Daftar indeks: Lacak / Peta / Panduan (baris penuh)]
[indeks Lacak/Peta/Panduan]      [catatan AI]
[catatan AI               ]      [footer bara]
[footer bara              ]
```
