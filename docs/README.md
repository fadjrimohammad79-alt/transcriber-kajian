# Dokumentasi

Dokumentasi teknis proyek **Transcriber Kajian**. Untuk memulai cepat, baca [README](../README.md)
di halaman depan repo. Halaman di sini lebih dalam dan ditujukan bagi yang ingin memahami,
menyetel, atau mengembangkan program.

| Dokumen | Isi |
|---|---|
| [Arsitektur](arsitektur.md) | Alur data, peran tiap modul, format keluaran (JSON/SRT/TXT), `riwayat.json`, keputusan desain |
| [Konfigurasi](konfigurasi.md) | Semua pengaturan `.env`, opsi perintah, kode keluar, dan file pendukung (`glosarium.txt`, `koreksi.txt`, ...) |
| [Kontrol kualitas](kontrol-kualitas.md) | Tanda QC, ambang batas, status video, kamus koreksi, alur QC manual |
| [Backend & VAD](backend-dan-vad.md) | Memilih GPU lokal / Groq / CPU, cara kerja Groq, opsi `WHISPER_VAD` |
| [Temuan: lokal vs Groq](temuan-lokal-vs-groq.md) | Hasil perbandingan dua video bab Niat beserta batas kesimpulannya |
| [Pengembangan](pengembangan.md) | Struktur kode, menjalankan test dan ruff, jebakan yang sudah ditemukan |
| [Wiki (panduan pengguna)](wiki/Home.md) | Halaman bergaya wiki GitHub; lihat [cara memublikasikan](wiki/README.md) |

## Peta cepat

```
URL / playlist / file antrian
  -> yt-dlp (audio saja, cache di audio\)
  -> transkripsi Whisper large-v3   [GPU NVIDIA | Groq API | CPU]
  -> koreksi kamus (koreksi.txt)
  -> tanda QC + status video
  -> hasil\<Bab>\*.json / .srt / .txt   +   riwayat.json
```

Isu yang sedang terbuka dan rencana pekerjaan dilacak di
[Issues](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues).
