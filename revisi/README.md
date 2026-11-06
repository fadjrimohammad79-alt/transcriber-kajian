# revisi/ - revisi batch transkrip kajian untuk korpus RAG

Alat untuk merevisi hasil transkripsi (`hasil/<Bab>/*.json`) menjadi `hasil/<Bab>_revisi/` tanpa mengubah file asli.

```bash
python revisi/revisi_batch.py --masuk hasil/Taubat --keluar hasil/Taubat_revisi --koreksi koreksi.txt
```

Keluaran: per video `.json/.txt/.srt` (revisi), `dalil_inventaris.json/.csv`, `titik_dengar.md`, `LAPORAN_REVISI.md`, `ringkasan.json`.

- Ejaan: KBBI sebagai rujukan tunggal; hanya aturan berstatus `terverifikasi` yang dijalankan. Kandidat lain di `data/kamus_belum_diverifikasi.tsv` (aktifkan dengan `--termasuk-belum-verifikasi` setelah dicek).
- Semua singkatan ditulis lengkap (`data/singkatan.tsv`). Arab tetap Latin; aksara Arab tidak disentuh.
- Dalil: dicocokkan dengan mushaf (quran-json) dan Riyadhush Shalihin; ini kecocokan teks, bukan penilaian derajat hadis atau hukum.
- Perbarui rujukan: `python revisi/build_rujukan.py --quran-dir <quran-json/dist> --hadith-json <riyad_assalihin.json> --keluar revisi/rujukan`.
- Skrip idempoten: dijalankan ulang pada keluarannya menghasilkan 0 perubahan.
