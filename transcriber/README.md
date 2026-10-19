# 🎙️ Transcriber Kajian YouTube

Transkripsi video kajian YouTube ke teks secara lokal di PC (Windows + NVIDIA RTX 4060),
memakai model Whisper open source dari Hugging Face lewat **faster-whisper**.
Hasilnya siap diproses ke tahap berikutnya (Claude: rapikan, potong per topik, klasifikasi bab).

## Alur

```
URL / playlist / file antrian per bab
   → yt-dlp ambil audio saja (disimpan di audio\ sebagai cache)
   → faster-whisper di GPU (large-v3, bahasa dikunci "id", VAD, glosarium istilah)
   → cek kualitas otomatis (RAGU / NOISE / BERULANG / HALUSINASI / TERLEWAT / MIRIP_PROMPT / NAMA_BOCOR)
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
| `--backend auto` | Default: GPU NVIDIA lokal → Groq API (bila `GROQ_API_KEY` diisi) → CPU |
| `--backend groq` | Paksa Groq API (tanpa GPU; perlu internet & `GROQ_API_KEY`) |
| `--cpu` | Sama dengan `--backend cpu`: uji tanpa GPU (lambat) |

## Tanpa GPU NVIDIA: Groq API

Di PC/laptop/VPS tanpa GPU NVIDIA, transkripsi bisa dikirim ke **Groq** (model `whisper-large-v3`
yang sama, dijalankan di server Groq). Biaya ±$0.11 per jam audio (±$0.07 per episode 40 menit);
`--model large-v3-turbo` ±$0.04 per jam.

1. Buat API key di https://console.groq.com/keys
2. Isi di `.env`: `GROQ_API_KEY=gsk_...` (file `.env` tidak ikut di-commit)
3. Jalankan seperti biasa: `.\run.bat --file antrian\niat.txt`. Backend `auto` memilih Groq
   bila GPU NVIDIA tidak ditemukan (baris `⚙️ Backend:` di awal menunjukkan pilihannya).

Audio dikompres dulu ke Opus mono 16 kHz (±11 MB per jam) supaya muat batas upload 25 MB tier gratis;
audio yang lebih panjang dipotong otomatis. Cek kualitas tetap jalan. Perbedaan dengan lokal:
contoh gaya/glosarium dikirim sebagai `prompt` API (maks 224 token) dan pengaruhnya pada audio panjang
bisa lebih lemah daripada lokal (lokal: diberikan di setiap potongan ±30 detik); VAD lokal tidak dipakai;
`--words` tidak punya nilai `prob` per kata. Bandingkan beberapa hasil dengan versi lokal sebelum dipakai massal.

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

## Koreksi otomatis (`koreksi.txt`)

Glosarium *mencegah* salah eja; `koreksi.txt` *memperbaiki* yang tetap lolos. Setelah transkripsi,
setiap baris `salah => benar  # alasan` diterapkan ke teks (kata/frasa utuh, huruf besar-kecil diabaikan).
Setiap perubahan dicatat di segmen JSON: `"revisi": [{"lama", "baru", "alasan", "oleh": "koreksi.txt"}]`,
dan jumlahnya di `transkripsi.koreksi_otomatis`.

- Isi hanya kesalahan yang **selalu** salah (mis. `al-Dhahabi => adz-Dzahabi`, `ketakuan => ketakwaan`).
  Nama penceramah yang bocor **jangan** dimasukkan: penggantinya tergantung siapa yang dikutip (`NAMA_BOCOR`).
- Setelah QC manual menemukan salah eja baru, tambahkan barisnya supaya video berikutnya langsung benar.
- Terapkan ke hasil lama tanpa transkripsi ulang (file asli tidak diubah):
  ```
  .venv\Scripts\python.exe koreksi.py hasil\Niat          → hasil\Niat_koreksi\
  ```
  Kamus bawaan (dari `LAPORAN_REVISI.md`) menghasilkan 47 dari 55 revisi manual bab Niat persis sama,
  tanpa salah koreksi; 8 sisanya nama penceramah bocor yang ditandai `NAMA_BOCOR`.

## Membaca hasil

- **`.txt`**: setiap baris diawali waktu `[mm:ss]`. Baris bertanda perlu dicek tim QC dengan mendengarkan bagian itu:
  `RAGU` (model tidak yakin), `NOISE` (mungkin bukan ucapan), `BERULANG`, `HALUSINASI`
  (kalimat sama ≥3x berturut), `FRASA_CURIGA` (mis. "terima kasih telah menonton", khas halusinasi Whisper),
  `TERLEWAT` (potongan panjang tapi teksnya sangat sedikit: kemungkinan ada bacaan yang tidak tertulis),
  `MIRIP_PROMPT` (teks hampir sama persis dengan `prompt_gaya.txt`/glosarium: pastikan memang diucapkan
  ustadz, bukan "bocoran" contoh yang dikarang model saat hening; jika bocoran, hapus barisnya),
  `NAMA_BOCOR` (nama penceramah muncul di teks: Whisper sering menempelkannya ke kutipan ulama lain,
  mis. "al-imam Muhammad Nuzul Uthaymeen" padahal yang dikutip al-Utsaimin; ganti dengan nama yang benar).
  Nama diambil dari channel YouTube; isi `QC_NAMA_PEMBICARA` di `.env` untuk menimpanya (channel lembaga).
- **`.json`**: setiap segmen punya `link` YouTube yang langsung lompat ke detiknya,
  untuk sitasi jawaban bot nanti.
- **Status kualitas per video**: BAIK (≤5% ditandai) · PERLU_CEK (≤20%) · BURUK (>20%).
  Ada satu saja `TERLEWAT` atau `NAMA_BOCOR` → minimal PERLU_CEK, karena isi kajian bisa hilang
  atau atribusi kutipan salah.
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
