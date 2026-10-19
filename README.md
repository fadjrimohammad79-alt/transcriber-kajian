# Transcriber Kajian + Second Brain Ustadz (RAG)

Pipeline dua tahap untuk kajian YouTube:

1. **`transcriber/`** — transkripsi lokal (Windows + GPU NVIDIA) memakai faster-whisper `large-v3`,
   dengan cek kualitas otomatis dan output `.json` / `.srt` / `.txt` per bab. Lihat
   [`transcriber/README.md`](transcriber/README.md).
2. **`Second_Brain_Ustadz_RAG*.ipynb`** — notebook Colab (iterasi 2–6) yang membangun bot tanya-jawab
   RAG (BM25 + Claude) di atas transkrip, dengan sitasi link YouTube per detik.
   `Perbandingan_Pipeline_RAG.xlsx` membandingkan varian pipeline.

## Hasil

- `transcriber/hasil/Niat/` — transkrip mentah seri kajian Niat (Riyaadhush Shaalihiin).
- `transcriber/hasil/transkrip-revisi/` — transkrip hasil revisi + `LAPORAN_REVISI.md`.

## Catatan

Secret (`.env`, `api.txt`), virtualenv, dan cache audio tidak ikut di-commit (lihat `.gitignore`).
Salin `transcriber/.env.example` ke `transcriber/.env`. Isi `ANTHROPIC_API_KEY` lewat Colab Secrets.
