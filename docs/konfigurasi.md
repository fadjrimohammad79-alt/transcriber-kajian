# Konfigurasi

Pengaturan dibaca dari file **`.env`** (salin dari `.env.example`; tidak ikut di-commit) lalu dari argumen
perintah. Argumen perintah menang atas `.env`. Nilai angka yang tidak valid (bukan angka, `nan`, di luar
batas) menghasilkan peringatan dan nilai bawaan dipakai; program tidak crash.

## Pengaturan `.env`

### Transkripsi

| Variabel | Bawaan | Arti |
|---|---|---|
| `WHISPER_MODEL` | `large-v3` | `large-v3` (paling akurat) atau `large-v3-turbo` (2-3x lebih cepat). Di Groq: dipetakan ke `whisper-large-v3` / `whisper-large-v3-turbo`; nama lain (mis. repo Hugging Face) memakai `whisper-large-v3` |
| `WHISPER_BACKEND` | `auto` | `auto` (GPU NVIDIA -> Groq bila `GROQ_API_KEY` ada -> CPU), `lokal`, `groq`, `cpu` |
| `GROQ_API_KEY` | kosong | Kunci dari console.groq.com. Hanya dibaca untuk backend Groq |
| `WHISPER_DEVICE` | `cuda` | `cuda` atau `cpu` (backend lokal) |
| `WHISPER_COMPUTE` | `float16` | `float16` (GPU) atau `int8` (CPU) |
| `WHISPER_BATCH` | `8` | Ukuran batch GPU, minimal 1. Turunkan ke 4 bila VRAM habis |
| `WHISPER_BEAM` | `5` | Lebar beam search, minimal 1 |
| `WHISPER_LANG` | `id` | Bahasa dikunci agar tidak salah deteksi saat bacaan Arab |
| `WHISPER_VAD` | `1` | `1` = penyaring hening aktif; `0` = mati (potongan tetap 30 detik). Hanya backend lokal. Lihat [Backend & VAD](backend-dan-vad.md) |

Nilai ya/tidak diterima dalam bentuk `1/0`, `true/false`, `on/off`, `ya/tidak`.

### Kontrol kualitas

| Variabel | Bawaan | Batas | Arti |
|---|---|---|---|
| `QC_LOW_LOGPROB` | `-1.0` | <= 0 | `avg_logprob` di bawah ini = `RAGU` |
| `QC_HIGH_NO_SPEECH` | `0.6` | 0..1 | `no_speech_prob` di atas ini = `NOISE` |
| `QC_HIGH_COMPRESSION` | `2.4` | >= 0 | `compression_ratio` di atas ini = `BERULANG` |
| `QC_REPEAT_MIN` | `3` | >= 2 | Kalimat sama berturut-turut sebanyak ini = `HALUSINASI` |
| `QC_MIN_DUR_TERLEWAT` | `10` | >= 0,1 | Durasi minimum (detik) segmen yang dicek `TERLEWAT` |
| `QC_MIN_CHARS_PER_SEC` | `4` | >= 0 | Huruf per detik di bawah ini = `TERLEWAT` |
| `QC_MIN_GAP_CELAH` | `8` | >= 0,1 | Jeda (detik) antar segmen berurutan yang ditandai `CELAH` |
| `QC_NAMA_PEMBICARA` | kosong | - | Nama penceramah (pisah koma) untuk `NAMA_BOCOR`. Kosong = pakai nama channel YouTube; bila diisi, **menimpa** nama channel |

### Lain-lain

| Variabel | Arti |
|---|---|
| `YTDLP_COOKIES_BROWSER` | Mis. `firefox`, untuk video yang butuh login/batas usia. Chrome di Windows sering gagal karena enkripsi cookie |

## Opsi perintah

```
python run.py [URL ...] [--file ANTRIAN] [--bab NAMA] [--kitab NAMA] [--model M]
              [--batch N] [--backend auto|lokal|groq|cpu] [--cpu] [--words]
              [--force] [--hapus-audio]
```

| Opsi | Fungsi |
|---|---|
| `URL ...` | URL video / playlist, atau cukup ID video 11 karakter |
| `--file F` | File antrian; boleh diulang (`--file a.txt --file b.txt`) |
| `--bab`, `--kitab` | Menimpa `# bab:` / `# kitab:` di file antrian |
| `--model M` | `large-v3` atau `large-v3-turbo`; backend lokal juga menerima nama repo Hugging Face (Groq memetakannya ke `whisper-large-v3`) |
| `--batch N` | Ukuran batch GPU |
| `--backend B` | Memilih mesin transkripsi (lihat tabel di atas) |
| `--cpu` | Sama dengan `--backend cpu` |
| `--words` | Simpan timestamp per kata (di Groq tanpa nilai `prob`) |
| `--force` | Ulangi video yang sudah selesai; file hasil lama dihapus bila namanya berubah |
| `--hapus-audio` | Hapus audio setelah selesai (hemat disk) |

Perintah lain:

| Perintah | Fungsi |
|---|---|
| `.\run.bat check` / `python check_gpu.py [--full]` | Diagnosis GPU NVIDIA (`--full` ikut memuat `large-v3`) |
| `python koreksi.py <folder> [--out F] [--kamus K]` | Menerapkan `koreksi.txt` ke hasil lama; keluaran ke `<folder>_koreksi` |
| `python eval_test.py` | Menjalankan seluruh test |

> **URL berisi `&`:** lewat `run.bat`, `&` memecah perintah di PowerShell (walau dikutip) dan di CMD (bila tidak
> dikutip). Pakai file antrian, ID video saja, atau panggil `python run.py "..."` langsung.

## Kode keluar

| Kode | Arti |
|---|---|
| 0 | Semua video selesai (atau tidak ada yang perlu diproses) |
| 1 | Input salah (tidak ada URL/antrian, file antrian tidak ada, `--backend groq` tanpa kunci); untuk `check`: GPU belum siap |
| 2 | Ada video yang gagal |
| 3 | Model gagal dimuat |
| 4 | `run.py` lain sedang berjalan di folder yang sama |
| 5 | `riwayat.json` tidak bisa dibaca (terkunci / folder) |
| 130 | Dihentikan dengan Ctrl+C |

## File pendukung

| File | Fungsi |
|---|---|
| `antrian\*.txt` | Daftar URL per bab. Baris `# bab: ...` dan `# kitab: ...` jadi metadata; komentar `# ...` di belakang nilai dibuang; satu URL per baris, komentar setelah URL diabaikan |
| `prompt_gaya.txt` | Contoh bacaan Arab dalam huruf Latin (pembukaan khutbah). Tanpa ini model berhenti menulis saat bacaan Arab |
| `glosarium.txt` | Istilah yang sering salah eja, satu per baris. **Jangan** isi nama penceramah |
| `koreksi.txt` | Kamus `salah => benar  # alasan`; lihat [Kontrol kualitas](kontrol-kualitas.md) |
| `riwayat.json` | Catatan video yang sudah selesai; lihat [Arsitektur](arsitektur.md) |
| `audio\` | Cache audio + metadata (tidak ikut di-commit) |

**Anggaran token prompt:** `prompt_gaya.txt` + `glosarium.txt` dikirim ke model di setiap potongan. Jaga
gabungannya **<= ±150 token** (program menampilkan perkiraan). Batas keras: 223 token (faster-whisper) dan
224 token (Groq); di atasnya ujung glosarium terpotong (faster-whisper) atau Groq menolak dengan HTTP 400,
sehingga program memendekkan prompt sendiri untuk Groq (ujung glosarium dibuang). Perkiraan program (`huruf / 2,5`) diukur dengan
tokenizer Whisper asli dan meleset kurang dari 3% untuk prompt saat ini.
