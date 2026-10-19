# Membaca hasil

## File yang dihasilkan

Di `hasil\<Bab>\` untuk tiap video:

| File | Untuk |
|---|---|
| `.txt` | Dibaca cepat. Tiap baris diawali `[mm:ss]`; baris bertanda diberi `⚠ TANDA` |
| `.srt` | Dicek di pemutar video |
| `.json` | Pipeline / RAG. Tiap segmen punya `link` YouTube yang lompat ke detiknya |

Format JSON lengkap: [Arsitektur](../arsitektur.md).

## Status video

| Status | Arti |
|---|---|
| `BAIK` | <= 5% segmen ditandai |
| `PERLU_CEK` | <= 20% ditandai, atau ada satu saja `TERLEWAT` / `NAMA_BOCOR` |
| `BURUK` | > 20% ditandai |

## Tanda pada segmen

| Tanda | Artinya | Tindakan |
|---|---|---|
| `RAGU` | Model tidak yakin | Dengarkan |
| `NOISE` | Mungkin bukan ucapan | Dengarkan / abaikan |
| `BERULANG` | Teks berulang di dalam segmen | Periksa |
| `HALUSINASI` | Kalimat sama >= 3x berturut-turut | Biasanya karangan di bagian hening; hapus |
| `FRASA_CURIGA` | Frasa khas halusinasi ("terima kasih telah menonton") | Hapus bila bukan ucapan |
| `TERLEWAT` | Segmen panjang tapi sedikit teks: kemungkinan ada bacaan yang tidak tertulis | Dengarkan; tulis manual |
| `MIRIP_PROMPT` | Teks hampir sama dengan contoh gaya/glosarium | Pastikan memang diucapkan (pembukaan khutbah), bukan bocoran prompt |
| `NAMA_BOCOR` | Nama penceramah muncul di teks (sering menempel pada kutipan ulama lain) | Ganti dengan nama ulama yang benar-benar dikutip |

Ambang dan cara kerja: [Kontrol kualitas](../kontrol-kualitas.md).

## Mendengarkan bagian yang ditandai

Link di JSON berbentuk `https://youtu.be/<id>?t=<detik>`. Contoh: https://youtu.be/hHn8Od5_oqs?t=200

## Jejak koreksi

Segmen yang diubah kamus `koreksi.txt` memiliki field `revisi` (`lama`, `baru`, `alasan`, `oleh`); jumlahnya di
`transkripsi.koreksi_otomatis`. Timestamp dan nomor segmen tidak pernah berubah oleh koreksi.
