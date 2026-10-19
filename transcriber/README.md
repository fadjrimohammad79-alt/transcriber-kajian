# 🎙️ Transcriber Kajian YouTube

Transkripsi video kajian YouTube ke teks secara lokal di PC (Windows + NVIDIA RTX 4060),
memakai model Whisper open source dari Hugging Face lewat **faster-whisper**.
Hasilnya siap diproses ke tahap berikutnya (Claude: rapikan, potong per topik, klasifikasi bab).

## Alur

```
URL / playlist / file antrian per bab
   → yt-dlp ambil audio saja (disimpan di audio\ sebagai cache)
   → faster-whisper di GPU (large-v3, bahasa dikunci "id", VAD, glosarium istilah)
   → cek kualitas otomatis (RAGU / NOISE / BERULANG / HALUSINASI / TERLEWAT / MIRIP_PROMPT)
   → hasil\<Bab>\  : .json (untuk pipeline) + .srt (cek di pemutar) + .txt (baca cepat)
   → riwayat.json  : video yang sudah selesai otomatis dilewati
```

## Setup sekali (Windows)

1. Install **Python 3.10–3.12 (64-bit)** dari python.org, centang *Add python.exe to PATH*.
2. Pastikan **driver NVIDIA** terbaru terpasang (tidak perlu install CUDA Toolkit terpisah;
   library CUDA/cuDNN ikut terpasang lewat pip).
3. Ekstrak folder ini, buka terminal (PowerShell atau CMD) di dalamnya, lalu jalankan:
   ```
   .\setup_windows.bat
   ```
   (Di PowerShell, file di folder saat ini wajib diawali `.\`)
   Script ini membuat virtual environment, menginstall library, lalu menjalankan `check_gpu.py`.
   Pastikan hasil akhirnya **🎉 GPU siap!**

Setiap kali mau memakai, buka terminal di folder ini dan pakai `.\run.bat` (tidak perlu aktivasi venv).
Semua contoh `python run.py ...` di bawah bisa diganti `.\run.bat ...`, dan `.\run.bat check` untuk cek GPU.

> Pertama kali dijalankan, model large-v3 (~3 GB) diunduh otomatis dari Hugging Face,
> lalu tersimpan di cache. Selanjutnya berjalan offline (kecuali download YouTube).

## Cara memasukkan URL

**A. Langsung di perintah**
```
python run.py https://youtu.be/AAAA https://youtu.be/BBBB --bab "Thaharah"
```

**B. File antrian per bab (disarankan)** — buat file di folder `antrian\`, contoh `antrian\bab_thaharah.txt`:
```
# bab: Thaharah
# kitab: Bulughul Maram
https://youtu.be/AAAA
https://youtu.be/BBBB
https://youtube.com/playlist?list=CCCC
```
```
python run.py --file antrian\bab_thaharah.txt
```
Tambah video baru → tambahkan URL di file yang sama, jalankan ulang. Yang sudah selesai dilewati.

**C. Playlist**
```
python run.py "https://youtube.com/playlist?list=XXXX" --bab "Shalat"
```

## Opsi berguna

| Opsi | Fungsi |
|---|---|
| `--model large-v3-turbo` | 2–3x lebih cepat, akurasi sedikit turun |
| `--batch 4` | Turunkan jika muncul error *out of memory* |
| `--words` | Simpan timestamp per kata |
| `--force` | Ulang video yang sudah selesai (mis. setelah ganti model) |
| `--hapus-audio` | Hapus audio setelah selesai (hemat disk) |
| `--cpu` | Uji tanpa GPU (lambat) |

## Contoh gaya & glosarium

Dua file ini digabung dan diberikan ke model di **setiap potongan audio ±30 detik**:

- **`prompt_gaya.txt`**: contoh bacaan Arab dalam huruf Latin (pembukaan khutbah). Tanpa ini,
  model yang dikunci ke Bahasa Indonesia cenderung **berhenti menulis** saat ustadz membaca
  bahasa Arab, sehingga sisa potongan itu hilang (terjadi pada video Niat: pembukaan setelah salam hilang).
- **`glosarium.txt`**: istilah yang sering salah eja, satu per baris (mis. `shiratal mustaqim`).

**Jaga gabungan keduanya ≤ ±150 token** (`run.py` menampilkan perkiraannya). Prompt berbagi ruang
±448 token dengan teks yang ditulis model per potongan; prompt yang terlalu panjang membuat
akhir potongan yang padat ucapan terpotong. Isi glosarium hanya dengan istilah yang memang
terbukti salah eja di hasil, bukan semua istilah yang mungkin muncul.

## Membaca hasil

- **`.txt`**: setiap baris diawali waktu `[mm:ss]`. Baris bertanda perlu dicek tim QC dengan mendengarkan bagian itu:
  `RAGU` (model tidak yakin), `NOISE` (mungkin bukan ucapan), `BERULANG`, `HALUSINASI`
  (kalimat sama ≥3x berturut), `FRASA_CURIGA` (mis. "terima kasih telah menonton", khas halusinasi Whisper),
  `TERLEWAT` (potongan panjang tapi teksnya sangat sedikit: kemungkinan ada bacaan yang tidak tertulis),
  `MIRIP_PROMPT` (teks hampir sama persis dengan `prompt_gaya.txt`/glosarium: pastikan memang diucapkan
  ustadz, bukan "bocoran" contoh yang dikarang model saat hening; jika bocoran, hapus barisnya).
- **`.json`**: setiap segmen punya `link` YouTube yang langsung lompat ke detiknya,
  untuk sitasi jawaban bot nanti.
- **Status kualitas per video**: BAIK (≤5% ditandai) · PERLU_CEK (≤20%) · BURUK (>20%).
  Ada satu saja `TERLEWAT` → minimal PERLU_CEK, karena isi kajian bisa hilang.
- Prompt yang dipakai tersimpan di `.json` (`transkripsi.prompt`), supaya hasil bisa ditelusuri setelah prompt diubah.

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `cublas64_12.dll` / `cudnn` not found | `pip install --force-reinstall nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"` lalu `python check_gpu.py` |
| `Python was not found ... Microsoft Store` | Python belum terpasang: `winget install -e --id Python.Python.3.12`, tutup & buka lagi terminal, lalu `.\setup_windows.bat` |
| PowerShell: "running scripts is disabled" saat aktivasi venv | Tidak perlu aktivasi: pakai `.\run.bat ...` |
| `CUDA out of memory` | `--batch 4` (atau 2), atau `--model large-v3-turbo` |
| Download YouTube gagal / format tidak tersedia | `pip install -U yt-dlp`. Jika masih gagal, install Deno (`winget install DenoLand.Deno`), yang dipakai yt-dlp untuk membaca halaman YouTube |
| Bacaan Arab (ayat, hadits, doa) hilang dari transkrip / tanda `TERLEWAT` | Pastikan `prompt_gaya.txt` ada; tambahkan contoh transliterasi bacaan yang sering dibaca ustadz; ringkas glosarium |
| Banyak segmen HALUSINASI di bagian hening | Normal untuk jeda panjang; bagian itu cukup dihapus saat QC |
| "Video sedang live / belum tayang" | Video live/premiere sengaja tidak diunduh. Jalankan ulang setelah siaran selesai diproses YouTube |
| Video privat / batas usia / khusus member | Isi `YTDLP_COOKIES_BROWSER=firefox` di `.env` (login YouTube di Firefox dulu) |
| "run.py lain sedang berjalan" | Hanya satu proses boleh jalan per folder. Tutup jendela terminal lain |
| File hasil terhapus tapi video dilewati | Video tercatat selesai di `riwayat.json`; pakai `--force` |
| Ganti model lalu ingin ulang | `--force` memakai audio di cache (tanpa unduh ulang) dan mengganti file hasil lama |

## Catatan perilaku

- Satu video gagal (privat, dihapus, error GPU) **tidak menghentikan** video lain. Jalankan ulang perintah
  yang sama untuk mencoba yang gagal saja.
- **Ctrl+C** aman: video yang sudah selesai tetap tercatat.
- Satu video hanya tercatat di satu bab (bab pertama yang memprosesnya).
- URL `watch?v=...&list=...` dianggap **satu video**; untuk seluruh playlist pakai link `playlist?list=...`.
- Audio dan metadata disimpan di `audio\`, jadi transkripsi ulang tidak butuh internet.

## Uji

```
python eval_test.py
```
61 test logika & edge case (tanpa GPU/internet) + 1 test model sungguhan bila model bisa diunduh.
