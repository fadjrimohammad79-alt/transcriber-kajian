# Catatan data aturan
- `kamus_ejaan_kbbi.tsv` : dipakai otomatis. HANYA bentuk yang sudah dicek ke KBBI daring (kolom `status` = terverifikasi).
- `kamus_belum_diverifikasi.tsv` : TIDAK dipakai kecuali `--termasuk-belum-verifikasi`. Pindahkan baris ke kamus utama setelah dicek di KBBI Daring (kbbi.kemdikbud.go.id).
- `singkatan.tsv` : semua singkatan ditulis lengkap (instruksi pemilik korpus). Baris ber-"syarat konteks" hanya jalan bila konteks cocok.
- `aturan_kontekstual.tsv` : salah-dengar yang pola dan konteksnya sempit; semuanya tingkat B (dicatat di `revisi`, dapat dibalik).
- Aksara Arab dan kutipan Latin Arab TIDAK diubah (instruksi pemilik: biarkan Latin).
