# Instalasi

Panduan untuk **Windows** (11/10). Proyek ini program **Python**, bukan paket Node.js: `npx` / `npm` tidak dipakai.

## 1. Prasyarat

```
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12
```

Tutup dan buka lagi terminal setelahnya. Python yang didukung: 3.10-3.12 (64-bit).

Bila punya GPU NVIDIA, cukup pastikan **driver NVIDIA** terbaru terpasang. CUDA Toolkit tidak perlu dipasang
terpisah; library CUDA/cuDNN ikut terpasang lewat pip.

## 2. Ambil kode

```
git clone https://github.com/fadjrimohammad79-alt/transcriber-kajian.git
cd transcriber-kajian
```

Repo ini **private**: saat clone akan muncul jendela login GitHub di browser (pakai akun pemilik repo), atau
login dulu dengan `gh auth login`.

## 3. Setup sekali

```
.\setup_windows.bat
```

Skrip ini membuat `.venv`, memasang library, menyalin `.env.example` menjadi `.env`, lalu menjalankan
`check_gpu.py`.

- **Ada GPU NVIDIA:** hasil akhirnya **GPU siap**. Model `large-v3` (±3 GB) diunduh otomatis saat pertama kali dipakai.
- **Tanpa GPU NVIDIA:** `check_gpu` melaporkan GPU belum siap; lanjut ke [Tanpa GPU dan Groq](Tanpa-GPU-dan-Groq.md).
- **`.venv` rusak** (disalin dari PC lain): setup mendeteksi dan membuatnya ulang.

> Setup memasang ±1,5 GB library CUDA walau tidak ada GPU NVIDIA. Pemisahan opsionalnya dilacak di
> [issue #6](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues/6).

## 4. Coba

```
.\run.bat check                         # diagnosis GPU
.\run.bat --file antrian\niat.txt       # transkripsi dari file antrian
```

Setiap kali memakai, buka terminal di folder repo dan pakai `.\run.bat` (tidak perlu mengaktifkan venv).

## Memperbarui

```
git pull
.\setup_windows.bat        # bila requirements.txt berubah
```

## Yang ikut dan tidak ikut ter-clone

Ikut: kode, `koreksi.txt`, `glosarium.txt`, `prompt_gaya.txt`, `antrian\`, hasil transkrip di `hasil\`, dan
`riwayat.json` (path-nya relatif, jadi tetap valid di PC lain; video yang sudah selesai dilewati).

Tidak ikut: `.env` (berisi kunci), `.venv\`, dan `audio\` (diunduh ulang bila perlu).

## Linux / VPS

Kode sudah berjalan di Linux (`python run.py ...`), tetapi belum ada skrip setup khusus. Ringkasnya:

```
sudo apt install python3-venv ffmpeg git
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env     # isi WHISPER_BACKEND / GROQ_API_KEY sesuai kebutuhan
.venv/bin/python run.py --file antrian/niat.txt
```

YouTube sering memblokir IP datacenter ("Sign in to confirm you're not a bot"). Solusi sementara: unduh
audio di PC lalu salin `audio/<id>.m4a` dan `audio/<id>.info.json` ke VPS. Dukungan resmi dilacak di
[issue #7](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues/7).
