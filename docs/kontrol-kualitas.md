# Kontrol kualitas

Tujuan: tim QC cukup mendengarkan bagian yang **ditandai**, bukan seluruh kajian. Ada tiga lapis:

1. **Pencegahan** - `prompt_gaya.txt` dan `glosarium.txt` dikirim ke model.
2. **Perbaikan otomatis** - `koreksi.txt` mengganti salah eja yang sudah diketahui.
3. **Penandaan** - `quality.py` menandai segmen yang patut didengarkan.

## Tanda per segmen

| Tanda | Syarat | Yang perlu dilakukan |
|---|---|---|
| `RAGU` | `avg_logprob < -1.0` | Dengarkan; model tidak yakin |
| `NOISE` | `no_speech_prob > 0.6` | Mungkin bukan ucapan |
| `BERULANG` | `compression_ratio > 2.4` | Teks berulang di dalam segmen |
| `HALUSINASI` | Teks identik >= 3 segmen berturut-turut | Biasanya karangan model di bagian hening; hapus |
| `FRASA_CURIGA` | Memuat frasa khas halusinasi ("terima kasih telah menonton", "subtitle oleh", ...) | Hapus bila bukan ucapan |
| `TERLEWAT` | Durasi >= 10 detik, bukan `NOISE`, dan < 4 huruf/detik | Kemungkinan ada ucapan yang tidak tertulis (mis. bacaan Arab); dengarkan |
| `MIRIP_PROMPT` | >= 5 kata, >= 70% urut sama dengan prompt, atau >= 90% katanya kata prompt | Pastikan memang diucapkan (pembukaan khutbah) dan bukan "bocoran" prompt |
| `NAMA_BOCOR` | Memuat token khas nama penceramah | Ganti dengan nama ulama yang benar-benar dikutip |

Ambang dapat diubah lewat `QC_*` di `.env` ([Konfigurasi](konfigurasi.md)). Ambang
`TERLEWAT` dan `MIRIP_PROMPT` dihitung **per segmen**, sehingga hasilnya bergantung pada panjang
segmen tiap backend (lihat [Temuan](temuan-lokal-vs-groq.md)).

### Cara kerja `NAMA_BOCOR`

Whisper sering menempelkan nama penceramah (dari glosarium/konteks) ke kutipan ulama lain, misalnya
"al-imam Muhammad **Nuzul** Uthaymeen" padahal yang dikutip al-Utsaimin.

- Nama diambil dari **channel YouTube**, atau dari `QC_NAMA_PEMBICARA` bila diisi.
- Hanya **token khas** yang dipakai: >= 4 huruf dan bukan kata umum/gelar (`muhammad`, `bin`, `ustadz`, `syaikh`,
  `sunnah`, `radio`, ...). "Muhammad Nuzul Dzikri" menjadi `{nuzul, dzikri}`.
- Kata yang didahului `asbabun`, `wa`, `li`, `bi`, `fi` dikecualikan ("asbabun nuzul", "wa dzikri maatsirihim").
- Hanya **menandai**, tidak mengganti: penggantinya tergantung siapa yang dikutip.

## Status per video

| Status | Syarat |
|---|---|
| `BAIK` | <= 5% segmen ditandai |
| `PERLU_CEK` | <= 20% ditandai, **atau** ada satu saja `TERLEWAT` / `NAMA_BOCOR` |
| `BURUK` | > 20% ditandai |
| `KOSONG` | Tidak ada segmen |

`TERLEWAT` dan `NAMA_BOCOR` menaikkan status ke minimal `PERLU_CEK` karena isi kajian bisa hilang atau
atribusi kutipan salah.

## Kamus koreksi (`koreksi.txt`)

Format satu aturan per baris:

```
salah => benar  # alasan
```

- Dicocokkan per **kata/frasa utuh**, huruf besar-kecil diabaikan, semua jenis apostrof (' ’ ‘ `) dianggap sama.
  "Zahabi" tidak cocok di dalam "al-Zahabi" atau "Zahabiyah".
- Frasa terpanjang diterapkan lebih dulu; menjalankan dua kali tidak mengubah apa pun (idempoten).
- Aturan yang formatnya salah, duplikat, atau akan berulang tanpa henti (hasil mengandung polanya sendiri)
  ditolak dengan peringatan.
- Setiap perubahan dicatat di segmen: `"revisi": [{"lama", "baru", "alasan", "oleh": "koreksi.txt"}]`,
  jumlahnya di `transkripsi.koreksi_otomatis`. Timestamp dan `id` segmen **tidak berubah**.

**Isi hanya kesalahan yang selalu salah** (mis. `al-Dhahabi => adz-Dzahabi`, `ketakuan => ketakwaan`).
Jangan masukkan nama penceramah yang bocor.

Menerapkan kamus terbaru ke hasil lama tanpa transkripsi ulang (file asli tidak diubah):

```
python koreksi.py hasil\Niat          ->  hasil\Niat_koreksi\
```

Pada bab Niat, kamus bawaan menghasilkan 47 dari 55 revisi manual persis sama, tanpa salah koreksi; sisanya
adalah nama penceramah bocor yang ditandai `NAMA_BOCOR`.

## Glosarium vs kamus koreksi

| | `glosarium.txt` | `koreksi.txt` |
|---|---|---|
| Kapan | Sebelum transkripsi (dikirim sebagai prompt) | Sesudah transkripsi |
| Fungsi | Mencegah salah eja | Memperbaiki yang tetap lolos |
| Risiko | Memakan anggaran token prompt (<= ±150) | Tidak ada anggaran, tapi harus bebas ambigu |
| Cocok untuk | Istilah yang sering salah dengar | Varian salah yang terbukti muncul |

## Alur QC manual yang disarankan

1. Buka `.txt` video berstatus `PERLU_CEK` / `BURUK`; mulai dari baris bertanda `⚠`.
2. Dengarkan bagian itu lewat `link` di JSON (lompat ke detik segmen).
3. Perbaiki teks. Bila salah eja itu **selalu** salah, tambahkan ke `koreksi.txt` agar video berikutnya benar.
4. Bila sebuah istilah sering salah dengar sejak awal, pertimbangkan `glosarium.txt` (jaga anggaran token).
5. Hasil QC yang dikerjakan di luar program (mis. oleh Claude Desktop) disimpan terpisah dengan field
   `revisi` (`lama`, `baru`, `alasan`) per segmen dan `LAPORAN_REVISI.md`; file asli tidak diubah.

## Batasan yang diketahui

- Bacaan Arab yang **tidak tertranskripsi sama sekali** tidak bisa dideteksi dari teks; hanya `TERLEWAT`
  (segmen panjang tapi sedikit teks) yang memberi petunjuk. Satu-satunya kepastian adalah mendengarkan.
- `MIRIP_PROMPT` menandai pembukaan khutbah yang memang diucapkan (false positive pada backend Groq).
- `--words`: timestamp per kata tidak ikut dikoreksi kamus (hanya teks segmen).
