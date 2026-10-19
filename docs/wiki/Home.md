# Transcriber Kajian

Program untuk mengubah video kajian YouTube menjadi **teks berstempel waktu** dengan Whisper `large-v3`,
siap diproses ke tahap berikutnya (rapikan, potong per topik, tanya-jawab/RAG).

- Berjalan **lokal** di PC dengan GPU NVIDIA (gratis), atau lewat **Groq API** bila tidak ada GPU NVIDIA
  (±$0,07 per episode 40 menit), atau di CPU (lambat).
- Menghasilkan `.json` (untuk pipeline, setiap segmen punya link YouTube ke detiknya), `.srt`, dan `.txt`.
- Menandai bagian yang perlu didengarkan tim QC (ragu, noise, halusinasi, bacaan Arab terlewat, nama penceramah
  yang salah menempel pada kutipan ulama).
- Memperbaiki salah eja yang sudah diketahui lewat kamus `koreksi.txt`.

## Mulai dari mana?

| Saya ingin... | Baca |
|---|---|
| Memasang di komputer baru | [Instalasi](Instalasi.md) |
| Menjalankan transkripsi pertama | [Cara pakai](Cara-Pakai.md) |
| Memahami hasil dan tanda QC | [Membaca hasil](Membaca-Hasil.md) |
| Memakai komputer tanpa GPU NVIDIA | [Tanpa GPU dan Groq](Tanpa-GPU-dan-Groq.md) |
| Mengatasi error | [Troubleshooting](Troubleshooting.md) |
| Pertanyaan umum | [FAQ](FAQ.md) |

Dokumentasi teknis (arsitektur, konfigurasi lengkap, pengembangan) ada di folder
[`docs`](../README.md) pada repo.

## Gambaran alur

```
URL / playlist / file antrian per bab
  -> unduh audio saja (yt-dlp)
  -> transkripsi Whisper (GPU NVIDIA / Groq / CPU)
  -> koreksi kamus -> tanda QC
  -> hasil\<Bab>\*.json, *.srt, *.txt
```

## Status

Seri kajian *Riyadhush Shalihin* bab Niat (20 video) sudah ditranskripsi dan di-QC. Pekerjaan yang masih
terbuka (uji bacaan Arab tanpa VAD, perbandingan akurasi lokal vs Groq, tahap QC otomatis, dukungan VPS Linux)
dilacak di Issues repo.
