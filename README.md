# Transcriber Kajian

Transkripsi lokal video kajian YouTube (Windows + GPU NVIDIA) memakai faster-whisper `large-v3`,
dengan cek kualitas otomatis dan output `.json` / `.srt` / `.txt` per bab. Lihat
[`transcriber/README.md`](transcriber/README.md).

Mulai dari [Cara pakai (langkah demi langkah)](transcriber/README.md#cara-pakai-langkah-demi-langkah). Tanpa GPU NVIDIA, transkripsi bisa lewat Groq API (`--backend auto` memilih otomatis).

Notebook RAG (Second Brain Ustadz) dipindah ke repo/folder terpisah (`RAG-secondbrain`).

## Hasil

- `transcriber/hasil/Niat/` — transkrip mentah seri kajian Niat (Riyaadhush Shaalihiin).
- `transcriber/hasil/transkrip-revisi/` — transkrip hasil revisi + `LAPORAN_REVISI.md`.

## Catatan

Secret (`.env`, `api.txt`), virtualenv, dan cache audio tidak ikut di-commit (lihat `.gitignore`).
Salin `transcriber/.env.example` ke `transcriber/.env`.
