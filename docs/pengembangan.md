# Pengembangan

## Menyiapkan lingkungan

```
git clone https://github.com/fadjrimohammad79-alt/transcriber-kajian.git
cd transcriber-kajian
.\setup_windows.bat                                       # .venv + library + .env
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # ruff
```

`.venv` tidak portabel: launcher di dalamnya menyimpan path absolut. Venv yang disalin dari PC lain akan gagal
dengan `No Python at ...`; `setup_windows.bat` mendeteksinya dan membuat ulang.

## Test dan lint (wajib bersih sebelum commit)

```
.venv\Scripts\ruff.exe check .                   # lint; --fix untuk perbaikan otomatis yang aman
.venv\Scripts\python.exe eval_test.py            # seluruh test, tanpa GPU/internet
```

- `eval_test.py` memuat puluhan test dalam beberapa grup (statis, antrian, downloader, transcriber ber-mock,
  kualitas, output, alur proses, backend/Groq, koreksi, config, edge case) dan **satu** test model sungguhan
  (`tiny`, CPU) yang di-SKIP bila model tidak bisa diunduh.
- **Test hermetik:** variabel `.env`/shell di PC itu (mis. `WHISPER_VAD=0`, `GROQ_API_KEY`) tidak memengaruhi hasil,
  karena nilai baku diatur sebelum `import config`. Jangan menambah test yang membaca `.env` sungguhan.
- **Test dokumentasi:** tautan relatif di README/`docs/` tidak boleh patah, dan setiap variabel `.env`, opsi
  perintah, tanda QC, kode keluar, modul, serta nilai bawaan angka harus tercantum dan cocok di dokumen.
  Menambah pengaturan baru tanpa memperbarui dokumen membuat test ini gagal (disengaja).
- Skrip publikasi wiki diuji sampai ke clone/commit/push terhadap repo bare lokal (tanpa jaringan).
- Groq API selalu di-mock (tidak ada panggilan jaringan dan tidak memakai kunci).
- Test menulis ke folder sementara dan membersihkannya sendiri (juga bila terhenti).
- Konfigurasi ruff ada di `pyproject.toml` (`E W F B BLE I UP SIM RUF`, panjang baris 120).

## Struktur kode

Lihat [Arsitektur](arsitektur.md) untuk peran modul. Prinsip yang dipegang:

- `config.py` adalah satu-satunya pembaca `.env`; modul lain membaca `config.X`.
- Fungsi murni (`quality.flag_segments`, `koreksi.terapkan`, `antrian.video_id`) mudah diuji; I/O jaringan
  dan GPU dibungkus di `downloader.py`, `transcriber.py`, `groq_transcriber.py`.
- `run.process()` menerima fungsi unduh/transkripsi sebagai parameter sehingga test memakai stub.

## Menambah sesuatu

| Tugas | Langkah |
|---|---|
| Tanda QC baru | Tambah di `quality.flag_segments` (+ ambang di `config.py`/`.env.example`), aturan status di `summarize` bila perlu, dokumentasikan di [Kontrol kualitas](kontrol-kualitas.md), tulis test |
| Aturan kamus koreksi | Tambah baris di `koreksi.txt`; `t_koreksi_kamus_asli` memastikan semua aturan valid dan tanpa rantai |
| Backend baru | Kelas dengan `transcribe(audio_path, hotwords, word_timestamps, show_progress) -> dict` yang mengembalikan struktur yang sama (`segments` + `durasi_audio` + `model`, ...); daftarkan di `resolve_backend` dan `factory` di `run.main` |
| Pengaturan `.env` | `config.py` (`_env_num` / `_env_bool` untuk validasi), `.env.example`, [Konfigurasi](konfigurasi.md), test |

## Jebakan yang sudah ditemukan (jangan diulang)

1. **Urutan import `gpu_setup`.** Harus dimuat **sebelum** `ctranslate2` / `faster_whisper` agar DLL CUDA terdaftar
   di Windows. `ruff --fix` pernah memindahkannya; urutan dikunci dengan `# isort: split` / `# noqa: I001`.
2. **File `.bat` wajib CRLF dan ASCII.** Ada test yang memeriksanya. Tulis dengan `\r\n` eksplisit.
3. **`%errorlevel%` di dalam blok `if ( ... )`** dibaca sebelum perintah jalan, sehingga kode keluar selalu 0.
   Pakai `goto` seperti di `run.bat`; test memeriksa pola ini.
4. **Pipeline batch faster-whisper menolak `vad_filter=False`** pada audio > 30 detik tanpa `clip_timestamps`.
5. **`&` di URL memecah perintah** lewat `run.bat` di PowerShell, walau dikutip. Pakai file antrian atau ID video.
6. **Segmen tidak lengkap.** JSON hasil edit tangan bisa tanpa `text`, atau bernilai `null`/`nan`; kode QC/SRT/TXT
   memakai pembaca aman (`_angka`, `_waktu`).
7. **`riwayat.json` terkunci sementara** (OneDrive/antivirus): penyimpanan dicoba ulang; membaca gagal -> `RiwayatError` (exit 5).
8. **Path di riwayat** relatif terhadap `hasil\`. Jangan menyimpan path absolut; cleanup hanya boleh menghapus file
   di dalam `hasil\`.
9. **Rahasia.** `GROQ_API_KEY` hanya di `.env` (ter-ignore). Pesan error yang dicetak/disimpan disamarkan; sapu
   repo dan riwayat git sebelum merilis bila ada keraguan.
10. **Windows tidak membedakan huruf besar-kecil nama file**, sedangkan ID video YouTube membedakannya. Dua ID yang
    hanya beda huruf besar-kecil bertabrakan di `audio\`; program memberi pesan jelas (kasus sangat jarang).

## Alur kerja Git

- Cabang `main`. Satu commit per perubahan yang koheren; pesan commit dalam bahasa Indonesia yang menjelaskan *mengapa*.
- Jangan commit: `.env`, `api.txt`, `.venv\`, `audio\`, `Niat_back\`, `graphify-out\`, `*.zip`, `riwayat.rusak-*.json`
  (sudah di `.gitignore`).
- Sebelum commit: `ruff check .` bersih dan `eval_test.py` lulus.
- `riwayat.json` dan `hasil\` ikut ter-track; bila dua PC memprosesnya bergantian, konflik merge mungkin terjadi
  (lihat [issue #10](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues/10)).
- Batasan kecil yang sudah diketahui dikumpulkan di
  [issue #12](https://github.com/fadjrimohammad79-alt/transcriber-kajian/issues/12).
