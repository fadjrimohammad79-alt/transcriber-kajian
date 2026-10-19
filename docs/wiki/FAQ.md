# FAQ

### Cara memasang dari GitHub? Apa itu `npx`?
Dengan `git clone` lalu `.\setup_windows.bat` ([Instalasi](Instalasi.md)). `npx` adalah alat Node.js untuk
menjalankan paket JavaScript; proyek ini Python, jadi `npx`/`npm` tidak dipakai.

### Video-nya disimpan di mana?
Video tidak diunduh. Program hanya mengunduh **audio** (m4a) ke `audio\<id-video>.m4a`, sebagai cache (tidak ikut
di-commit). Untuk mendengar bagian tertentu, buka link YouTube di JSON: `https://youtu.be/<id>?t=<detik>`.

### Bisakah Claude (API Anthropic) dipakai untuk transkripsi suara?
Tidak: API Claude tidak menerima input audio. Untuk suara ke teks dipakai Whisper (lokal atau Groq). Claude cocok
untuk tahap sesudahnya, misalnya merapikan teks dan QC teks.

### Mana yang lebih baik, lokal atau Groq?
Belum bisa disimpulkan "lebih akurat". Pada dua video yang diuji, isinya hampir sama (93% kemiripan pada video dengan model
yang sama). Groq menangkap lebih banyak bacaan Arab dan punya timestamp jauh lebih presisi; pada satu video Groq
melewatkan ±29 detik bicara Indonesia. Rinciannya: [Temuan lokal vs Groq](../temuan-lokal-vs-groq.md).

### Mengapa hasil lokal dan Groq berbeda?
Beda model/versi, beda cara memotong audio (lokal ±30-45 detik per segmen dengan VAD, Groq ±7 detik tanpa VAD),
dan beda cara prompt dipakai. Sebagian besar selisih hanya gaya penulisan (*nggak/gak/tidak*, angka vs kata).

### Berapa biayanya?
Lokal gratis (listrik + GPU). Groq sekitar $0,111 per jam audio untuk `large-v3` (±$0,07 per episode 40 menit) dan
$0,04 per jam untuk turbo; cek ulang harga resmi. 20 episode bab Niat ≈ $1,5.

### Berapa lama satu episode?
Terukur untuk episode 39-42 menit: GPU NVIDIA RTX 4060 dengan `large-v3-turbo` ±20 detik, dengan `large-v3` ±11 menit
(639 detik pada satu pengukuran); Groq ±1 menit; CPU sangat lama.

### Apa itu `NAMA_BOCOR`?
Whisper kadang menempelkan nama penceramah ke kutipan ulama lain ("al-imam Muhammad Nuzul Uthaymeen" padahal
yang dikutip al-Utsaimin). Segmen seperti itu ditandai; penggantinya harus dipilih manual karena bergantung siapa yang
dikutip. Jangan masukkan nama penceramah ke glosarium.

### Kapan menambah `glosarium.txt`, kapan `koreksi.txt`?
`glosarium.txt` mencegah salah eja sejak awal tetapi memakan anggaran token prompt (<= ±150). `koreksi.txt` memperbaiki
sesudahnya tanpa anggaran, namun hanya untuk kesalahan yang *selalu* salah. Lihat [Kontrol kualitas](../kontrol-kualitas.md).

### Bisakah dijalankan di VPS?
Ya (Linux). Tanpa GPU gunakan Groq. Kendalanya, YouTube sering memblokir IP datacenter; lihat bagian Linux/VPS di
[Instalasi](Instalasi.md). Dukungan resmi sedang dilacak di Issues.

### Aman menaruh kunci Groq di `.env`?
Ya, `.env` ter-ignore git. Jangan menempelnya di chat, issue, atau commit. Lihat
[Tanpa GPU dan Groq](Tanpa-GPU-dan-Groq.md).

### Mengapa `WHISPER_VAD=0`?
Untuk menguji dugaan bahwa VAD lokal memotong bacaan Arab yang dilantunkan. Bukan untuk pemakaian sehari-hari karena
halusinasi di bagian hening bisa naik. Lihat [Backend & VAD](../backend-dan-vad.md).
