# Temuan: transkripsi lokal (GPU) vs Groq

Perbandingan dua video bab Niat (kajian Riyadhush Shalihin), 19 Oktober 2026. Dokumen ini mencatat
**apa yang terukur, apa yang belum terbukti**, dan pekerjaan lanjutan yang diperlukan.

## Bahan dan metode

| | Video 01 (`hHn8Od5_oqs`, 39 menit) | Video 02 (`4AdGaNVQt0c`, 42 menit) |
|---|---|---|
| Lokal | `large-v3-turbo`, RTX 4060 | `large-v3`, RTX 4060 |
| Groq | `whisper-large-v3` | `whisper-large-v3` |
| Kesetaraan | **Model berbeda** | Model sama (perbandingan bersih) |

- Prompt lokal (10 Okt) memuat nama ustadz; prompt Groq (19 Okt) memakai glosarium terbaru tanpa nama.
  Kedua video tidak mengandung kebocoran nama sehingga tidak memengaruhi hasil.
- Kamus `koreksi.txt` diterapkan ke **kedua** sisi sebelum dibandingkan.
- Teks dibandingkan pada tingkat kata (urutan kata), teks per jendela waktu (dibagi proporsional karena panjang
  segmen berbeda), dan bagian yang hanya ada di satu sisi.
- Hasil QC Claude Desktop (`transkrip-revisi`) dipakai sebagai referensi sebagian: **bukan kunci jawaban**,
  karena diturunkan dari keluaran lokal dan hanya memperbaiki teks yang sudah tertulis.

## Hasil

| | Video 01 (lokal turbo / Groq) | Video 02 (lokal / Groq) |
|---|---|---|
| Segmen | 51 / 265 | 66 / 321 |
| Median durasi segmen | 44 dtk / 7 dtk | 36 dtk / 6 dtk |
| Jumlah kata | 2.714 / 2.752 | 3.418 / 3.480 |
| Kemiripan urutan kata | 91,5% | 93,3% |
| Total teks Groq vs lokal | +2,0% | +0,1% |
| Salah eja yang ada di kamus | 6 / 0 | 8 / 2 |
| Status QC | BAIK / PERLU_CEK (3,0%) | BAIK / BAIK (0,3%) |
| Waktu proses | 19,6 dtk / 51 dtk | 639 dtk / 56 dtk |

### 1. Isi hampir sama

Tidak ada jendela 2 menit yang selisih teksnya besar. Sekitar 8-12% kata berbeda, tetapi sebagian besar adalah
gaya penulisan (*nggak* / *gak* / *tidak*, *SAW* / *sallallahu alaihi wa sallam*, angka vs kata).

### 2. Groq menangkap lebih banyak bacaan Arab

Kata ekstra yang hanya ada di satu sisi, bacaan Arab dilatinkan: video 01 **Groq +58 / lokal +0**,
video 02 **Groq +30 / lokal +4**.

- Video 01: ayat di 0:40 (An-Nahl 18), Ali Imran 140 di 3:20, Yunus 58 di 29:10, doa penutup di 38:50.
- Video 02: shalawat di 0:50 dan 1:12, kutipan ayat di 14:03, doa penutup di 41:47.

Karena video 02 memakai model yang sama di kedua sisi, penyebabnya kemungkinan **bukan model**. Dugaan:
VAD lokal memotong bacaan yang dilantunkan (belum diuji; lihat [Backend & VAD](backend-dan-vad.md)).
Transliterasi Groq sering kacau (mis. doa penutup video 01), jadi bacaan Arab tetap wajib di-QC manual.

### 3. Groq kehilangan sebagian bicara Indonesia (video 01)

Segmen 37:55-38:24 (29 detik) hanya berisi "Terima kasih banyak.", dan satu kalimat di sekitar 36:30 tidak ada,
sedangkan lokal mencatatnya (lokal +49 kata Indonesia vs Groq +9). Flag `TERLEWAT` Groq menangkap yang 29 detik
itu. Di video 02 tidak ada kehilangan serupa.

### 4. Titik koreksi QC (14 titik pada video 01 dan 02)

Apakah Groq membuat salah yang sama dengan lokal pada titik yang QC koreksi?

| Hasil Groq | Jumlah |
|---|---|
| Benar, ejaan standar | 3 ("madzhab Syafi'i", "Riyadhush Shalihin" x2) |
| Benar, ejaan varian | 3 ("siratul mustaqim", "ad-Dhahabi" x2) |
| Salah, diperbaiki kamus | 2 |
| Salah, sama seperti lokal | 4 ("Soe Bukhari", "Soe Muslim", "suhaim muslim", "Halim Ad-Dzahabi") |
| Salah, lebih buruk | 1 ("imam nuzabih") |
| Tidak pasti | 1 (40:01, perlu didengar) |

"Riyadhush Shalihin" benar di Groq (2 dari 2) padahal ada di prompt kedua backend; "adz-Dzahabi" tidak
sebanding karena baru ditambahkan ke glosarium setelah QC. Varian baru dari Groq sudah masuk `koreksi.txt`.

### 5. Segmen halus mengubah perilaku tanda QC

Dengan segmen ±7 detik, `TERLEWAT` Groq menandai 6 segmen di video 01; hanya 1 yang kehilangan isi sungguhan
(37:55), sisanya kalimat pendek di segmen dengan jeda panjang. `MIRIP_PROMPT` menandai pembukaan khutbah yang
memang diucapkan. **Status QC tidak sebanding antar backend.**

## Kesimpulan yang boleh ditarik

- Groq **layak sebagai cadangan** saat tidak ada GPU NVIDIA, dengan timestamp sitasi yang jauh lebih presisi.
- Groq **menangkap lebih banyak bacaan Arab**, tetapi transliterasinya kasar.
- Belum bisa disimpulkan bahwa Groq **lebih akurat**: sampel hanya 2 dari 20 video, video 01 membandingkan model
  berbeda, dan tidak ada kunci jawaban yang diverifikasi dengan mendengarkan audio.

## Pekerjaan lanjutan

Dilacak di Issues: uji `WHISPER_VAD=0` di PC GPU, ukur WER dengan kunci jawaban manual (model dan prompt sama),
investigasi segmen Indonesia yang hilang di Groq, dan penyetelan `TERLEWAT` / `MIRIP_PROMPT` untuk segmen halus.
