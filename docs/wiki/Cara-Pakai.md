# Cara pakai

Semua perintah dijalankan dari folder repo (PowerShell atau CMD).

## 1. Buat file antrian per bab

Buat `antrian\bab_niat.txt`:

```
# bab: Niat
# kitab: Riyadhush Shalihin
https://youtu.be/hHn8Od5_oqs
https://youtube.com/playlist?list=XXXX
```

- `# bab:` dan `# kitab:` menjadi metadata (dan nama folder hasil). Komentar di belakang nilai dibuang.
- Satu URL per baris: video, `youtu.be`, atau playlist. Komentar setelah URL diabaikan.
- Boleh juga hanya **ID video** 11 karakter.

## 2. Jalankan

```
.\run.bat --file antrian\bab_niat.txt
```

Baris `Backend:` di awal menunjukkan mesin yang dipakai (lokal / groq / cpu). Setiap video menampilkan jumlah
segmen, koreksi kamus, dan status kualitas. **Ctrl+C aman**: video yang sudah selesai tetap tercatat; jalankan
ulang perintah yang sama untuk melanjutkan.

Alternatif tanpa file antrian:

```
.\run.bat hHn8Od5_oqs --bab "Niat"
.\run.bat "https://youtube.com/playlist?list=XXXX" --bab "Shalat"
```

> **Awas tanda `&` di URL.** Lewat `run.bat`, `&` memecah perintah di PowerShell walau URL dikutip. Pakai file
> antrian, ID video, atau `.venv\Scripts\python.exe run.py "URL"`.

## 3. Opsi yang sering dipakai

| Opsi | Fungsi |
|---|---|
| `--model large-v3-turbo` | 2-3x lebih cepat, akurasi sedikit turun |
| `--backend groq` | Paksa Groq (tanpa GPU) |
| `--force` | Ulangi video yang sudah selesai (mis. setelah ganti model/prompt) |
| `--words` | Simpan timestamp per kata |
| `--batch 4` | Turunkan bila GPU kehabisan memori |
| `--hapus-audio` | Hapus audio setelah selesai |

Daftar lengkap: [Konfigurasi](../konfigurasi.md).

## 4. Setelah selesai

1. Buka `hasil\<Bab>\*.txt`, mulai dari video berstatus **PERLU_CEK / BURUK**.
2. Dengarkan baris bertanda `⚠` ([Membaca hasil](Membaca-Hasil.md)).
3. Tambahkan salah eja yang *selalu* salah ke `koreksi.txt` supaya video berikutnya benar.
4. Menerapkan kamus terbaru ke hasil lama tanpa transkripsi ulang:
   `.venv\Scripts\python.exe koreksi.py hasil\Niat` (hasil ke `hasil\Niat_koreksi\`, file asli tidak diubah).

## 5. Menambah video

Tambahkan URL ke file antrian yang sama lalu jalankan lagi. Yang sudah selesai dilewati.
