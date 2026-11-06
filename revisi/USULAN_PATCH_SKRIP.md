# Usulan patch skrip pipeline (Fase 7) - BELUM diterapkan

Tidak ada skrip inti yang diubah. Ini daftar usulan bagi pemilik repo; tiap butir dapat diterima/ditolak terpisah.

## 1. `config.py` / `quality.py` - ambang QC tidak pernah menyala
- `QC_LOW_LOGPROB=-1.0`, `QC_HIGH_NO_SPEECH=0.6`, `QC_HIGH_COMPRESSION=2.4` sama dengan ambang bawaan decoder Whisper. Segmen yang melewati ambang itu sudah dibuang/diulang decoder sendiri, sehingga flag RAGU dan NOISE praktis tidak pernah muncul.
- Di 21 video Taubat: `avg_logprob` terendah hanya -0,52 dan `no_speech_prob` tertinggi 0,21. Tidak ada satu pun flag RAGU/NOISE.
- Usulan: kalibrasi ambang dari sebaran data nyata (mis. persentil terendah 2-3% per video) atau naikkan ke sekitar `-0.45` untuk RAGU; atur lewat `.env`. `revisi_batch.py` memakai `--ambang-logprob -0.45` sebagai pengganti sementara.

## 2. `koreksi.txt` - bentrok dengan KBBI (rujukan tunggal ejaan menurut pemilik korpus)
Lihat bagian "Bentrok" di `LAPORAN_REVISI.md` (dibuat otomatis dengan `--koreksi koreksi.txt`). Contoh: `salawat => shalawat`, `istiqomah => istiqamah`, `gibah => ghibah`, `hadit => hadith`, `jaman sekalian => jamaah sekalian`.
Usulan: ganti ke bentuk KBBI (selawat, istikamah, gibah, hadis, jemaah) SETELAH tiap bentuk dicek di KBBI Daring, atau hapus dan serahkan ke `revisi_batch.py`. Aturan khusus nama orang (Shalih al-Utsaimin dst.) tetap dipertahankan.

## 3. `koreksi.py` - urutan dan lingkup
- Pastikan `koreksi.txt` tidak menyentuh kutipan Arab-Latin dan nama orang; `revisi_batch.py` melindungi `bin/ibnu/Syaikh ... Shalih` dari aturan `saleh`.
- Usulan: jalankan `revisi_batch.py` setelah `koreksi.py`; keluaran `revisi[]` memakai skema yang sama ({lama, baru, alasan, oleh}) ditambah `tingkat`.

## 4. Notebook RAG (`Second_Brain_Ustadz_RAG6`)
- Bidang `dalil` hasil ekstraksi LLM hanya "rujukan yang DISEBUT". Usulan: tambahkan bidang terpisah `dalil_terverifikasi` dari `dalil_inventaris.json` (status, teks resmi, terjemah Kemenag, `usulan_ganti_arab`) dan jangan menimpa ucapan ustaz.
- Saat menjawab, hanya kutip sumber yang berstatus `terverifikasi-arab-cocok`, `terselesaikan-dari-penyebutan`, atau `terkenali-dari-bacaan-arab`; untuk `tanpa-rujukan-eksplisit` / `hanya-disebut` nyatakan "ustaz tidak menyebut sumbernya".
- `PETA_EJAAN_CONTOH` (normalisasi saat query) dapat dibangkitkan dari `data/kamus_*.tsv` agar pencarian tetap menemukan bentuk lama (taubat/tobat, jamaah/jemaah).
- `FLAG_DIBUANG={HALUSINASI, FRASA_CURIGA, NOISE}`: gunakan gerbang per video dari `ringkasan.json` (TAHAN/LULUS_BERSYARAT/LULUS) sebelum ingest.

## 5. Prompt `prompt_gaya.txt`
Prompt Whisper memuat "ketakwaan" dll. dan bentuk Latin-Arab; tidak perlu diubah. Catatan: segmen berflag MIRIP_PROMPT di awal video (salam pembuka) sebaiknya diperiksa terhadap audio karena teks mirip prompt.
