# 🎙️ Transcriber Kajian YouTube

Mengubah video kajian YouTube menjadi teks memakai model Whisper `large-v3`, lengkap dengan cek kualitas
otomatis agar tim QC cukup memeriksa bagian yang ditandai. Transkripsi berjalan di **GPU NVIDIA lokal**
(faster-whisper) atau lewat **Groq API** bila tidak ada GPU NVIDIA. Hasilnya siap diproses ke tahap berikutnya
(Claude: rapikan, potong per topik, klasifikasi bab).

> Notebook RAG (Second Brain Ustadz) yang memakai hasil transkrip ini ada di repo/folder terpisah `RAG-secondbrain`.

**Dokumentasi:** [panduan pengguna (wiki)](docs/wiki/Home.md) ·
[dokumentasi teknis](docs/README.md) ·
[temuan lokal vs Groq](docs/temuan-lokal-vs-groq.md) ·
[Issues](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues)

## Daftar isi

1. [Cara kerja](#cara-kerja)
2. [Mulai cepat](#mulai-cepat)
3. [Instalasi](#instalasi)
4. [Memasukkan video](#memasukkan-video)
5. [Menjalankan](#menjalankan)
6. [Membaca hasil](#membaca-hasil)
7. [Memperbaiki hasil](#memperbaiki-hasil)
8. [Tanpa GPU NVIDIA: Groq API](#tanpa-gpu-nvidia-groq-api)
9. [Troubleshooting](#troubleshooting)
10. [Catatan perilaku dan kode keluar](#catatan-perilaku-dan-kode-keluar)
11. [Pengembangan: uji dan lint](#pengembangan-uji-dan-lint)

## Cara kerja

```
URL / playlist / file antrian per bab
   → yt-dlp ambil audio saja (disimpan di audio\ sebagai cache)
   → transkripsi Whisper large-v3 (bahasa dikunci "id", contoh gaya + glosarium istilah)
        backend auto: GPU NVIDIA lokal → Groq API (bila GROQ_API_KEY ada) → CPU lokal
   → koreksi otomatis dari koreksi.txt (salah eja yang sudah diketahui, tercatat di field "revisi")
   → cek kualitas otomatis (RAGU / NOISE / BERULANG / HALUSINASI / TERLEWAT / CELAH / MIRIP_PROMPT / NAMA_BOCOR)
   → hasil\<Bab>\  : .json (untuk pipeline) + .srt (cek di pemutar) + .txt (baca cepat)
   → riwayat.json  : video yang sudah selesai otomatis dilewati
```

## Mulai cepat

Di PC Windows yang sudah punya Git dan Python 3.12 (jika belum, lihat [Instalasi](#instalasi)):

```
git clone https://github.com/fadjrimohammad79-alt/transcriber-kajian.git
cd transcriber-kajian
.\setup_windows.bat            # sekali: venv + library + .env, lalu cek GPU
.\run.bat check                # "🎉 GPU siap!" = transkripsi lokal gratis; bila tidak, lihat Groq di bawah
.\run.bat --file antrian\niat.txt
```

Lalu buka `hasil\<Bab>\*.txt` dan mulai dari video berstatus **PERLU_CEK / BURUK**
([Membaca hasil](#membaca-hasil)).

Alur kerja lengkap untuk satu bab:

1. **Siapkan antrian**: file `antrian\bab_xxx.txt` berisi URL ([Memasukkan video](#memasukkan-video)).
2. **Jalankan**: `.\run.bat --file antrian\bab_xxx.txt`. Baris `⚙️ Backend:` di awal menunjukkan mesin yang
   dipakai (lokal / groq / cpu). Boleh dihentikan dengan Ctrl+C; jalankan ulang perintah yang sama untuk
   melanjutkan (video yang sudah selesai dilewati).
3. **Periksa** baris bertanda di `hasil\<Bab>\` dengan mendengarkan bagiannya.
4. **Perbaiki sumber kesalahan** (`koreksi.txt`, `glosarium.txt`) supaya video berikutnya lebih baik
   ([Memperbaiki hasil](#memperbaiki-hasil)).
5. **Tambah video baru**: tambahkan URL di file antrian yang sama, jalankan lagi. Untuk mengulang video yang
   sudah selesai (mis. setelah ganti model atau prompt) tambahkan `--force`.

## Instalasi

### Prasyarat

- **Python 3.10–3.12 (64-bit)**, dengan *Add python.exe to PATH* tercentang.
- **Git** (untuk clone).
- **GPU NVIDIA** (opsional): cukup driver NVIDIA terbaru. Tidak perlu CUDA Toolkit terpisah; library
  CUDA/cuDNN ikut terpasang lewat pip. Tanpa GPU NVIDIA, lihat [Groq API](#tanpa-gpu-nvidia-groq-api).

Di PC baru, pasang keduanya (sekali), lalu **tutup dan buka lagi terminal**:

```
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12
```

### Pasang dari GitHub

Proyek ini program **Python** (bukan paket Node.js): dipasang dengan `git clone` lalu skrip setup.
`npx` / `npm` tidak dipakai.

1. Clone repo dan masuk ke foldernya:
   ```
   git clone https://github.com/fadjrimohammad79-alt/transcriber-kajian.git
   cd transcriber-kajian
   ```
   Repo ini **private**: saat clone akan muncul jendela login GitHub di browser (pakai akun pemilik repo),
   atau login dulu lewat `gh auth login`.
2. Jalankan setup (di PowerShell, file di folder saat ini wajib diawali `.\`):
   ```
   .\setup_windows.bat
   ```
   Script ini membuat virtual environment, memasang library, membuat `.env`, lalu menjalankan `check_gpu.py`.
   Hasil akhir **🎉 GPU siap!** berarti transkripsi lokal siap dipakai.
3. Tanpa GPU NVIDIA: isi `GROQ_API_KEY` di `.env` ([Groq API](#tanpa-gpu-nvidia-groq-api)).

Setiap kali memakai, buka terminal di folder ini dan pakai `.\run.bat` (tidak perlu aktivasi venv).
Semua contoh `python run.py ...` di bawah bisa diganti `.\run.bat ...`; `.\run.bat check` untuk cek GPU.

> Pertama kali dijalankan, model large-v3 (~3 GB) diunduh otomatis dari Hugging Face dan tersimpan di
> cache. Selanjutnya berjalan offline (kecuali unduhan YouTube).

**Ikut ter-clone:** kode, `koreksi.txt`, `glosarium.txt`, `prompt_gaya.txt`, folder `antrian\`, hasil
transkrip di `hasil\`, dan `riwayat.json` (path-nya relatif, jadi tetap valid di PC lain; video yang sudah
selesai dilewati). **Tidak ikut:** `.env` (berisi key), `.venv\`, dan `audio\` (diunduh ulang bila perlu).

**Memperbarui** PC yang sudah terpasang: `git pull`, lalu `.\setup_windows.bat` lagi bila `requirements.txt`
berubah. Script itu juga mendeteksi `.venv` yang rusak (mis. disalin dari PC lain) dan membuatnya ulang.

## Memasukkan video

**A. File antrian per bab (disarankan)**: buat file di folder `antrian\`, mis. `antrian\bab_thaharah.txt`:

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

**B. Langsung di perintah**

```
python run.py https://youtu.be/AAAA https://youtu.be/BBBB --bab "Thaharah"
```

**C. Playlist**

```
python run.py "https://youtube.com/playlist?list=XXXX" --bab "Shalat"
```

> **Awas tanda `&` di URL** (mis. `watch?v=ID&list=...`). Lewat `run.bat`, `&` memecah perintah di PowerShell
> **walau URL dikutip** (juga di CMD bila tidak dikutip): bagian setelah `&` dijalankan sebagai perintah terpisah
> dan muncul `'list' is not recognized`. Aman: (1) taruh URL di file antrian, (2) cukup **ID video**
> 11 karakter: `.\run.bat hHn8Od5_oqs`, atau (3) panggil Python langsung:
> `.venv\Scripts\python.exe run.py "https://...&list=..."`.

URL `watch?v=...&list=...` dianggap **satu video**; untuk seluruh playlist pakai link `playlist?list=...`.

## Menjalankan

```
.\run.bat --file antrian\niat.txt
```

Tiap video menampilkan jumlah segmen, koreksi kamus (`🩹`), dan status kualitas.

| Opsi | Fungsi |
|---|---|
| `--file ANTRIAN` | Baca URL dari file antrian |
| `--bab "Nama"` / `--kitab "Nama"` | Nama bab / kitab; menimpa `# bab:` / `# kitab:` di file antrian |
| `--model large-v3-turbo` | 2–3x lebih cepat, akurasi sedikit turun |
| `--batch 4` | Turunkan jika muncul error *out of memory* |
| `--words` | Simpan timestamp per kata |
| `--force` | Ulang video yang sudah selesai (mis. setelah ganti model) |
| `--hapus-audio` | Hapus audio setelah selesai (hemat disk) |
| `--backend auto` | Default: GPU NVIDIA lokal → Groq API (bila `GROQ_API_KEY` diisi) → CPU |
| `--backend groq` | Paksa Groq API (tanpa GPU; perlu internet & `GROQ_API_KEY`) |
| `--cpu` | Sama dengan `--backend cpu`: uji tanpa GPU (lambat) |

Pengaturan lain (ambang QC, VAD, nama penceramah) ada di `.env`; daftar lengkapnya di
[docs/konfigurasi.md](docs/konfigurasi.md).

## Membaca hasil

Hasil per video ada di `hasil\<Bab>\`:

- **`.txt`**: baca cepat; setiap baris diawali waktu `[mm:ss]`, baris bermasalah diberi tanda.
- **`.srt`**: cek di pemutar video.
- **`.json`**: untuk pipeline; setiap segmen punya `link` YouTube yang langsung lompat ke detiknya (untuk sitasi
  jawaban bot nanti). Prompt yang dipakai tersimpan di `transkripsi.prompt`, supaya hasil bisa ditelusuri
  setelah prompt diubah.

### Status kualitas per video

| Status | Arti |
|---|---|
| `BAIK` | ≤5% segmen ditandai |
| `PERLU_CEK` | ≤20% ditandai, atau ada satu saja `TERLEWAT`, `CELAH`, atau `NAMA_BOCOR` (isi kajian bisa hilang atau atribusi kutipan salah) |
| `BURUK` | >20% ditandai |

Mulailah dari video `PERLU_CEK` / `BURUK`, lalu **dengarkan** bagian yang ditandai.

### Arti tanda

| Tanda | Artinya | Yang dilakukan |
|---|---|---|
| `NAMA_BOCOR` | Nama penceramah muncul di teks. Whisper sering menempelkannya ke kutipan ulama lain (mis. "al-imam Muhammad Nuzul Uthaymeen" padahal yang dikutip al-Utsaimin) | Ganti dengan nama ulama yang benar-benar dikutip. Nama diambil dari channel YouTube; isi `QC_NAMA_PEMBICARA` di `.env` untuk menimpanya (channel lembaga) |
| `TERLEWAT` | Potongan panjang tapi teksnya sangat sedikit: kemungkinan ada bacaan yang tidak tertulis | Dengarkan; tulis manual bila perlu |
| `CELAH` | Jeda ≥8 detik tanpa segmen sebelum baris ini: ucapan di jeda itu hilang tanpa jejak | Dengarkan jeda itu; tulis manual bila perlu |
| `FRASA_CURIGA` | Memuat frasa khas halusinasi Whisper (mis. "terima kasih telah menonton") | Hapus bila bukan ucapan |
| `HALUSINASI` | Kalimat sama ≥3x berturut-turut | Biasanya karangan model saat hening; hapus |
| `MIRIP_PROMPT` | Teks hampir sama persis dengan `prompt_gaya.txt`/glosarium | Pastikan memang diucapkan ustadz (pembukaan khutbah), bukan "bocoran" contoh yang dikarang model saat hening; jika bocoran, hapus barisnya |
| `RAGU` | Model tidak yakin | Dengarkan |
| `NOISE` | Mungkin bukan ucapan | Dengarkan; hapus bila bukan ucapan |
| `BERULANG` | Teks berulang di dalam segmen | Periksa dan rapikan |

Rincian syarat dan ambang tiap tanda: [docs/kontrol-kualitas.md](docs/kontrol-kualitas.md).

## Memperbaiki hasil

Ada tiga alat; pakai berurutan dari yang mencegah sampai yang memperbaiki.

### 1. Contoh gaya dan glosarium (mencegah)

Dua file ini digabung dan diberikan ke model di **setiap potongan audio ±30 detik**:

- **`prompt_gaya.txt`**: contoh bacaan Arab dalam huruf Latin (pembukaan khutbah). Tanpa ini, model yang
  dikunci ke Bahasa Indonesia cenderung **berhenti menulis** saat ustadz membaca bahasa Arab, sehingga sisa
  potongan itu hilang (terjadi pada video Niat: pembukaan setelah salam hilang).
- **`glosarium.txt`**: istilah yang sering salah eja, satu per baris (mis. `shiratal mustaqim`).

**Jaga gabungan keduanya ≤ ±150 token** (`run.py` menampilkan perkiraannya). Prompt berbagi ruang ±448 token
dengan teks yang ditulis model per potongan; prompt yang terlalu panjang membuat akhir potongan yang padat
ucapan terpotong. Isi glosarium hanya dengan istilah yang memang terbukti salah eja di hasil, bukan semua
istilah yang mungkin muncul. **Jangan** masukkan nama penceramah ke glosarium (lihat `NAMA_BOCOR`).

### 2. Koreksi otomatis (`koreksi.txt`) (memperbaiki)

Glosarium *mencegah* salah eja; `koreksi.txt` *memperbaiki* yang tetap lolos. Setelah transkripsi, setiap
baris `salah => benar  # alasan` diterapkan ke teks (kata/frasa utuh, huruf besar-kecil diabaikan). Setiap
perubahan dicatat di segmen JSON: `"revisi": [{"lama", "baru", "alasan", "oleh": "koreksi.txt"}]`, dan
jumlahnya di `transkripsi.koreksi_otomatis`.

- Isi hanya kesalahan yang **selalu** salah (mis. `al-Dhahabi => adz-Dzahabi`, `ketakuan => ketakwaan`).
  Nama penceramah yang bocor **jangan** dimasukkan: penggantinya tergantung siapa yang dikutip (`NAMA_BOCOR`).
- Setelah QC manual menemukan salah eja baru, tambahkan barisnya supaya video berikutnya langsung benar.
- Terapkan ke hasil lama tanpa transkripsi ulang (file asli tidak diubah):
  ```
  .venv\Scripts\python.exe koreksi.py hasil\Niat          → hasil\Niat_koreksi\
  ```
  Kamus bawaan (dari `LAPORAN_REVISI.md`) menghasilkan 47 dari 55 revisi manual bab Niat persis sama, tanpa
  salah koreksi; 8 sisanya nama penceramah bocor yang ditandai `NAMA_BOCOR`.

### 3. Bacaan Arab hilang? Coba matikan VAD (backend lokal)

Backend lokal memakai **VAD** (penyaring bagian hening, Silero) agar Whisper tidak berhalusinasi di jeda.
Dugaan (belum terbukti): VAD juga bisa memotong bacaan Arab yang dilantunkan atau pelan. Pada perbandingan
dua video bab Niat, Groq (tanpa VAD) menangkap ayat, shalawat, dan doa penutup yang dilewati lokal.
Untuk mengujinya di PC GPU:

1. Di `.env` isi `WHISPER_VAD=0` (bawaan `1` = aktif).
2. Ulangi satu video: `.\run.bat --force https://youtu.be/hHn8Od5_oqs` (atau lewat file antrian).
3. Bandingkan dengan hasil sebelumnya: apakah bacaan Arab muncul? Apakah tanda `HALUSINASI` /
   `FRASA_CURIGA` bertambah di bagian hening?

Tanpa VAD, audio dipotong tetap 30 detik (batch tetap dipakai, kecepatan sama) dan program menampilkan
peringatan saat model dimuat. Setiap hasil mencatat `"vad": true/false` di `transkripsi`. Opsi ini tidak
berlaku untuk Groq (Groq tidak memakai VAD lokal). Kembalikan ke `1` bila halusinasi mengganggu.

## Tanpa GPU NVIDIA: Groq API

Di PC/laptop/VPS tanpa GPU NVIDIA, transkripsi bisa dikirim ke **Groq** (model `whisper-large-v3` yang sama,
dijalankan di server Groq). Biaya ±$0.11 per jam audio (±$0.07 per episode 40 menit); `--model
large-v3-turbo` ±$0.04 per jam. Tanpa key, program tetap jalan di CPU tetapi jauh lebih lambat.

1. Buat API key di https://console.groq.com/keys
2. Isi di `.env`: `GROQ_API_KEY=gsk_...` (file `.env` tidak ikut di-commit)
3. Jalankan seperti biasa: `.\run.bat --file antrian\niat.txt`. Backend `auto` memilih Groq bila GPU NVIDIA
   tidak ditemukan (baris `⚙️ Backend:` di awal menunjukkan pilihannya).

Audio dikompres dulu ke Opus mono 16 kHz (±11 MB per jam) supaya muat batas upload 25 MB tier gratis; audio
yang lebih panjang dipotong otomatis. Cek kualitas tetap jalan. Perbedaan dengan lokal:

- contoh gaya/glosarium dikirim sebagai `prompt` API (maks 224 token; yang lebih panjang dipendekkan otomatis)
  dan pengaruhnya pada audio panjang bisa lebih lemah daripada lokal (lokal: diberikan di setiap potongan
  ±30 detik);
- VAD lokal tidak dipakai;
- `--words` tidak punya nilai `prob` per kata.

Bandingkan beberapa hasil dengan versi lokal sebelum dipakai massal
([temuan](docs/temuan-lokal-vs-groq.md)).

## Troubleshooting

| Masalah | Solusi |
|---|---|
| `cublas64_12.dll` / `cudnn` not found | `pip install --force-reinstall nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"` lalu `python check_gpu.py` |
| `Python was not found ... Microsoft Store` | Python belum terpasang: `winget install -e --id Python.Python.3.12`, tutup & buka lagi terminal, lalu `.\setup_windows.bat` |
| `No Python at '...\python.exe'` saat `.\run.bat` | `.venv` dibuat di PC/user lain. Hapus folder `.venv` lalu jalankan `.\setup_windows.bat` lagi |
| PowerShell: "running scripts is disabled" saat aktivasi venv | Tidak perlu aktivasi: pakai `.\run.bat ...` |
| `CUDA out of memory` | `--batch 4` (atau 2), atau `--model large-v3-turbo` |
| Download YouTube gagal / format tidak tersedia | `pip install -U yt-dlp`. Jika masih gagal, install Deno (`winget install DenoLand.Deno`), yang dipakai yt-dlp untuk membaca halaman YouTube |
| "Video sedang live / belum tayang" | Video live/premiere sengaja tidak diunduh. Jalankan ulang setelah siaran selesai diproses YouTube |
| Video privat / batas usia / khusus member | Isi `YTDLP_COOKIES_BROWSER=firefox` di `.env` (login YouTube di Firefox dulu) |
| Bacaan Arab (ayat, hadits, doa) hilang dari transkrip / tanda `TERLEWAT` | Pastikan `prompt_gaya.txt` ada; tambahkan contoh transliterasi bacaan yang sering dibaca ustadz; ringkas glosarium. Backend lokal: coba `WHISPER_VAD=0` ([penjelasan](#3-bacaan-arab-hilang-coba-matikan-vad-backend-lokal)) atau pakai Groq |
| Banyak segmen HALUSINASI di bagian hening | Normal untuk jeda panjang; bagian itu cukup dihapus saat QC |
| "run.py lain sedang berjalan" | Hanya satu proses boleh jalan per folder. Tutup jendela terminal lain |
| File hasil terhapus tapi video dilewati | Video tercatat selesai di `riwayat.json`; pakai `--force` |
| Ganti model lalu ingin ulang | `--force` memakai audio di cache (tanpa unduh ulang) dan mengganti file hasil lama |
| `⚙️ Backend: cpu` padahal ingin Groq | `GROQ_API_KEY` di `.env` masih kosong |
| `Groq HTTP 401` | API key salah/kedaluwarsa → buat ulang di console.groq.com |
| `Groq HTTP 429` | Batas pemakaian Groq tercapai; program menunggu & mencoba ulang otomatis, bila tetap gagal jalankan ulang nanti |
| `riwayat.json tidak bisa dibaca` (exit 5) | File dipegang program lain: editor, Excel, atau sinkronisasi OneDrive yang sedang berjalan. Tutup/tunggu sinkronisasi selesai, lalu jalankan ulang |
| `riwayat.json tidak bisa disimpan` | Terkunci sementara; dicoba lagi otomatis setelah video berikutnya. Bila di akhir muncul `GAGAL disimpan`, video terakhir diproses ulang pada run berikutnya |

## Catatan perilaku dan kode keluar

- Satu video gagal (privat, dihapus, error GPU) **tidak menghentikan** video lain. Jalankan ulang perintah
  yang sama untuk mencoba yang gagal saja.
- **Ctrl+C** aman: video yang sudah selesai tetap tercatat.
- Satu video hanya tercatat di satu bab (bab pertama yang memprosesnya).
- Audio dan metadata disimpan di `audio\`, jadi transkripsi ulang tidak butuh internet.

**Kode keluar (untuk otomasi, mis. n8n):**

| Kode | Arti |
|---|---|
| 0 | Semua video selesai (atau tidak ada yang perlu diproses) |
| 1 | Input salah: tidak ada URL/antrian, file antrian tidak ada, `--backend groq` tanpa `GROQ_API_KEY`; untuk `.\run.bat check`: GPU belum siap |
| 2 | Ada video yang gagal (jalankan ulang untuk mencoba yang gagal saja) |
| 3 | Model gagal dimuat (CUDA/DLL, internet, nama model) |
| 4 | `run.py` lain sedang berjalan di folder ini |
| 5 | `riwayat.json` tidak bisa dibaca (terkunci) |
| 130 | Dihentikan dengan Ctrl+C |

## Pengembangan: uji dan lint

```
.venv\Scripts\python.exe eval_test.py
```

Puluhan test logika & edge case (tanpa GPU/internet; Groq API di-mock; juga memeriksa dokumentasi tetap
sinkron dengan kode) + 1 test model sungguhan bila model bisa diunduh. Laporan akhir menampilkan
`Total / PASS / FAIL`. Test tidak terpengaruh isi `.env` (mis. `WHISPER_VAD=0`, `GROQ_API_KEY`), jadi aman
dijalankan di PC mana pun.

**Lint (ruff)**: wajib bersih sebelum commit. Aturan ada di `pyproject.toml`.

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt     (sekali)
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe check --fix .                                 (perbaiki otomatis yang aman)
```

Catatan: `import gpu_setup` harus tetap **sebelum** `ctranslate2`/`faster_whisper` (mendaftarkan DLL CUDA di
Windows). Urutannya dikunci dengan `# isort: split` / `# noqa: I001`; jangan dihapus saat merapikan import.
Panduan pengembangan lengkap: [docs/pengembangan.md](docs/pengembangan.md).
