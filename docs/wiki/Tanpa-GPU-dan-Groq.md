# Tanpa GPU NVIDIA: Groq API

Whisper `large-v3` butuh GPU NVIDIA (CUDA) agar cepat. Di laptop AMD/Intel, PC tanpa GPU, atau VPS, ada dua pilihan:

| Pilihan | Kecepatan | Biaya | Catatan |
|---|---|---|---|
| **Groq API** (disarankan) | ±45x real-time (episode 40 menit ±1 menit) | ±$0,07 per episode (`large-v3`), ±$0,03 (`large-v3-turbo`) | Butuh internet dan kunci API |
| CPU lokal | Sangat lambat untuk `large-v3` | Gratis | Cocok hanya untuk uji, atau dijalankan semalaman |

## Memakai Groq

1. Buat kunci API di https://console.groq.com/keys.
2. Buka `.env` (dibuat otomatis oleh setup) dan isi `GROQ_API_KEY=gsk_...`. File `.env` tidak ikut di-commit.
3. Jalankan seperti biasa: `.\run.bat --file antrian\niat.txt`.

Dengan `WHISPER_BACKEND=auto` (bawaan), program memilih sendiri: GPU NVIDIA bila ada, lalu Groq bila kunci terisi,
lalu CPU. Baris `Backend:` di awal keluaran menunjukkan pilihannya. Untuk memaksa: `--backend groq`.

## Cara kerja singkat

Audio dikompres ke Opus mono 16 kHz (±11 MB per jam) agar muat batas upload 25 MB, dipotong otomatis bila lebih
panjang, dikirim ke Groq, lalu segmennya digabung. Tanda QC tetap berjalan seperti biasa.

## Yang berbeda dibanding lokal

- Segmen jauh lebih halus (±7 detik): link sitasi lebih presisi.
- Bacaan Arab cenderung lebih lengkap, tetapi transliterasinya kasar: **tetap QC manual**.
- Contoh gaya/glosarium dikirim sebagai satu `prompt` (maks. 224 token); pengaruhnya pada audio panjang bisa lebih lemah.
- Tidak memakai VAD lokal, jadi `WHISPER_VAD` diabaikan.
- Audio terkompres dikirim ke server Groq (pertimbangkan bila kontennya sensitif).
- Status QC tidak sebanding dengan lokal karena segmennya lebih pendek.

Hasil perbandingan terukur: [Temuan lokal vs Groq](../temuan-lokal-vs-groq.md). Rincian teknis:
[Backend & VAD](../backend-dan-vad.md).

## Keamanan kunci

- Simpan kunci hanya di `.env`; jangan ditempel di chat, issue, atau commit.
- Program tidak pernah mencetak kunci atau menyimpannya ke `riwayat.json` (disamarkan `***` bila muncul di pesan error).
- Bila kunci sempat bocor, cabut di console.groq.com dan buat yang baru.
