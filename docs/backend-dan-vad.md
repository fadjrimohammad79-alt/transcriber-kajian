# Backend transkripsi dan VAD

## Memilih backend

`--backend` (atau `WHISPER_BACKEND` di `.env`):

| Nilai | Perilaku |
|---|---|
| `auto` (bawaan) | GPU NVIDIA terdeteksi -> **lokal**; jika tidak ada dan `GROQ_API_KEY` terisi -> **groq**; jika tidak -> **cpu** |
| `lokal` | Paksa faster-whisper di GPU NVIDIA (CUDA) |
| `groq` | Paksa Groq API (butuh internet dan `GROQ_API_KEY`; tidak butuh GPU) |
| `cpu` | faster-whisper di CPU (`int8`); sangat lambat untuk `large-v3` |

Baris pertama keluaran menunjukkan pilihan dan alasannya, mis.
`Backend: groq (GPU NVIDIA tidak ditemukan, GROQ_API_KEY ada)`.

Deteksi GPU memakai CTranslate2 (`get_cuda_device_count() > 0`). `python check_gpu.py` memberi diagnosis
lengkap (driver, DLL CUDA, CTranslate2, muat model) dan menyarankan Groq bila GPU belum siap.

## Backend Groq

Model yang sama (`whisper-large-v3`) dijalankan di server Groq lewat
`POST https://api.groq.com/openai/v1/audio/transcriptions` dengan `response_format=verbose_json`.

Langkah di `groq_transcriber.py`:

1. **Kompres** audio ke Opus mono 16 kHz, 24 kbps dengan PyAV (±11 MB per jam; tanpa dependensi baru).
2. **Potong** jika hasil encode melebihi 24 MB (batas upload tier gratis 25 MB): panjang potongan mulai 3600 detik,
   dibagi dua sampai muat (minimum 60 detik). Timestamp potongan digeser sesuai posisinya.
3. **Kirim** tiap potongan: `language=id`, `temperature=0`, `prompt` = contoh gaya + glosarium (maks. 224 token),
   `timestamp_granularities[]=segment` (+`word` bila `--words`).
4. **Gabung** segmen. Kolom `avg_logprob`, `no_speech_prob`, `compression_ratio` dari Groq dipakai apa adanya,
   jadi seluruh tanda QC tetap berjalan.

Ketahanan:

- HTTP 429 dan 5xx, serta timeout/putus koneksi, dicoba ulang sampai 3 kali (menghormati `retry-after`, maks. 300 detik).
- Error lain (mis. 401 kunci salah) langsung gagal dengan pesan jelas. API key tidak pernah dicetak atau disimpan;
  bila sebuah pesan error mengutipnya, diganti `***`.
- Tanpa dependensi tambahan: HTTP memakai `urllib` bawaan Python.

**Biaya** (harga publik Groq saat dokumen ini ditulis; cek ulang di halaman harga resmi): `whisper-large-v3`
sekitar **$0,111 per jam audio** (±$0,07 per episode 40 menit), `whisper-large-v3-turbo` sekitar $0,04 per jam.
Ada minimum penagihan 10 detik per permintaan.

**Perbedaan dibanding lokal:**

| Aspek | Lokal | Groq |
|---|---|---|
| Segmen | ±30-45 detik | ±6-8 detik (timestamp sitasi lebih presisi) |
| Prompt | Diberikan di setiap potongan ±30 detik | Satu `prompt` awal per permintaan; pengaruh pada audio panjang bisa lebih lemah |
| VAD | Silero (bisa dimatikan) | Tidak ada |
| `--words` | Ada `prob` per kata | `prob` bernilai `null` |
| Biaya | Gratis (listrik + GPU) | Berbayar per jam audio |
| Data | Tetap di komputer | Audio terkompres dikirim ke server Groq |

> Claude (API Anthropic) **tidak** menerima input audio, jadi tidak bisa dipakai untuk transkripsi suara ke teks.
> Claude hanya cocok untuk tahap sesudah transkripsi (merapikan teks, QC teks).

## VAD (`WHISPER_VAD`)

**VAD** (Voice Activity Detection, Silero) membuang bagian hening sebelum Whisper memproses audio, sehingga
mengurangi halusinasi di jeda. Efek sampingnya (dugaan, belum terbukti): bacaan Arab yang dilantunkan atau
pelan bisa ikut terbuang.

- `WHISPER_VAD=1` (bawaan): VAD aktif, dengan jeda minimal 700 ms.
- `WHISPER_VAD=0`: VAD mati. Audio dipotong **tetap 30 detik** (`clip_timestamps`), batch tetap dipakai
  sehingga kecepatan hampir sama. Ekor audio yang lebih pendek dari 0,1 detik dibuang karena Whisper
  berhalusinasi pada klip nyaris kosong.
- Hanya berlaku untuk backend lokal (GPU/CPU). Pada Groq program menampilkan catatan bahwa pengaturan ini diabaikan.
- Setiap hasil lokal mencatat `"vad": true/false` di `transkripsi`.

Mengapa tidak cukup `vad_filter=False`? Pipeline batch faster-whisper melempar
`RuntimeError: No clip timestamps found` bila VAD mati pada audio > 30 detik. Program menyediakan potongan tetap
sendiri untuk menghindarinya.

**Cara menguji hipotesis "VAD memotong bacaan Arab"** (butuh PC dengan GPU NVIDIA):

1. Jalankan satu video dengan `WHISPER_VAD=1` dan simpan hasilnya.
2. Isi `WHISPER_VAD=0`, jalankan ulang video yang sama dengan `--force`.
3. Bandingkan bagian bacaan Arab (ayat, shalawat, doa penutup) dan hitung tanda `HALUSINASI` / `FRASA_CURIGA`.

Tanpa VAD, halusinasi di bagian hening bisa naik; pada uji audio derau 75 detik dengan model kecil, VAD mati
menghasilkan segmen palsu sedangkan VAD aktif tidak menghasilkan apa pun. Karena itu `WHISPER_VAD=0` cocok untuk
uji bacaan Arab, bukan sebagai bawaan.
