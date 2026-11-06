# Sumber rujukan & lisensi

Berkas di folder ini dibangun ulang oleh `build_rujukan.py` dari dataset terbuka. Jangan disunting manual.

| Berkas | Isi | Sumber | Lisensi |
|---|---|---|---|
| `surat.json` | 114 surah: nomor, nama Arab, transliterasi, arti, jumlah ayat | quran-json 3.1.2 (npm `quran-json`) | CC-BY-SA 4.0 (teks Arab: Tanzil; terjemah Indonesia: Kemenag RI; transliterasi: Tanzil) |
| `quran_ringkas.json` | 6.236 ayat: Arab, transliterasi, terjemah Indonesia | quran-json 3.1.2 | CC-BY-SA 4.0 - wajib atribusi + berbagi serupa bila didistribusikan ulang |
| `riyadhush_shalihin_ringkas.json` | 1.896 hadis Riyadhush Shalihin: Arab + terjemah Inggris | hadith-json (data Sunnah.com), `db/by_book/other_books/riyad_assalihin.json` | ISC (kode/format); teks bersumber Sunnah.com - cek ketentuan situs bila dipublikasikan |

## Keputusan edisi/penomoran Riyadhush Shalihin

- Dataset memakai penomoran `idInBook` (1-1896) dan bagian "Bunga Rampai" (kitab 'Miscellany') yang mencakup Bab Taubat.
- Penomoran yang dipakai ustaz di seri ini (hadis ke-8, 12, 13...21) = `idInBook - 1217`. Dicek ke perawi yang disebut ustaz: ke-8 Abu Musa Al-Asy'ari, ke-12 Abdullah bin Umar, ke-19 Zirr bin Hubaisy (Shafwan bin 'Assal), ke-21 Ka'b bin Malik - **cocok 11 dari 11 titik uji (ke-13 sampai ke-21 ditambah ke-8 dan ke-12)**.
- Ustaz sendiri menyebut penomoran cetakan lain ("hadis 19 ... buku hadisnya ke-42"; "ke-21 atau ke-22 sesuai cetakan"). Karena itu nomor tidak dijadikan satu-satunya kunci: pencocokan utama lewat isi (bacaan Arab). Penyebutan nomor bercetakan lain ditandai `nomor-edisi-lain`.
- Terjemah Inggris di dataset hanya untuk membantu pemeriksa; terjemah Indonesia hadis belum tersedia di rujukan ini.

## Ejaan
KBBI (rujukan tunggal ejaan). Hanya kata yang sudah dicek ke KBBI daring berstatus `terverifikasi` di `data/kamus_ejaan_kbbi.tsv`.
