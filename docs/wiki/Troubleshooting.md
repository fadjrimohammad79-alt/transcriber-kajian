# Troubleshooting

| Masalah | Penyebab / solusi |
|---|---|
| `No Python at '...\python.exe'` saat `.\run.bat` | `.venv` dibuat di PC/user lain. Jalankan ulang `.\setup_windows.bat` (mendeteksi dan membuat ulang), atau hapus folder `.venv` lebih dulu |
| `Python was not found ... Microsoft Store` | Python belum terpasang: `winget install -e --id Python.Python.3.12`, buka terminal baru, lalu `.\setup_windows.bat` |
| PowerShell: "running scripts is disabled" | Tidak perlu mengaktifkan venv; pakai `.\run.bat ...` |
| `cublas64_12.dll` / `cudnn` not found | `pip install --force-reinstall nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"` lalu `python check_gpu.py` |
| `nvidia-smi tidak ditemukan` / `CTranslate2 tidak melihat GPU CUDA` | Tidak ada GPU NVIDIA atau driver belum terpasang. Pakai Groq ([Tanpa GPU dan Groq](Tanpa-GPU-dan-Groq.md)) atau `--cpu` |
| `Backend: cpu` padahal ingin Groq | `GROQ_API_KEY` di `.env` masih kosong |
| `Groq HTTP 401` | Kunci salah/kedaluwarsa; buat ulang di console.groq.com |
| `Groq HTTP 429` | Batas pemakaian Groq tercapai; program menunggu dan mencoba ulang, bila tetap gagal jalankan nanti |
| `CUDA out of memory` | `--batch 4` (atau 2), atau `--model large-v3-turbo` |
| Download YouTube gagal / format tidak tersedia | `pip install -U yt-dlp`. Bila masih gagal, pasang Deno: `winget install DenoLand.Deno` |
| Video privat / batas usia / khusus member | Isi `YTDLP_COOKIES_BROWSER=firefox` di `.env` (login YouTube di Firefox dulu) |
| "Video sedang live / belum tayang" | Siaran langsung/premiere sengaja tidak diunduh. Jalankan ulang setelah siaran selesai diproses YouTube |
| `'list' is not recognized as an internal or external command` | URL berisi `&` terpecah oleh shell. Pakai file antrian, ID video, atau `python run.py "URL"` |
| "run.py lain sedang berjalan" (exit 4) | Hanya satu proses per folder. Tutup terminal lain yang sedang menjalankan program |
| `riwayat.json tidak bisa dibaca` (exit 5) | File dipegang program lain (editor, Excel, sinkronisasi OneDrive). Tutup/tunggu lalu jalankan ulang |
| `riwayat.json tidak bisa disimpan` | Terkunci sementara; dicoba ulang otomatis. Bila di akhir muncul `GAGAL disimpan`, video terakhir diproses ulang pada run berikutnya |
| File hasil terhapus tapi video dilewati | Video tercatat selesai di `riwayat.json`; pakai `--force` |
| Ganti model/prompt lalu ingin ulang | `--force` memakai audio di cache (tanpa unduh ulang) dan mengganti file hasil lama |
| Bacaan Arab (ayat, hadits, doa) hilang / tanda `TERLEWAT` | Pastikan `prompt_gaya.txt` ada, ringkas glosarium, atau coba `WHISPER_VAD=0` (lokal) / Groq |
| Banyak `HALUSINASI` di bagian hening | Normal untuk jeda panjang; hapus saat QC. Bila `WHISPER_VAD=0`, kembalikan ke `1` |
| Peringatan `.env: ... tidak valid` saat start | Nilai angka salah (bukan angka, `nan`, di luar batas); nilai bawaan dipakai. Perbaiki di `.env` |
| `Cache ... berisi video X, bukan Y` / audio bertabrakan nama | Dua ID video yang hanya beda huruf besar-kecil di Windows. Proses di folder audio terpisah atau di Linux |

Belum tertolong? Buka [issue](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues) dengan menyertakan
keluaran terminal (tanpa kunci API) dan baris `Backend:` di awal.
