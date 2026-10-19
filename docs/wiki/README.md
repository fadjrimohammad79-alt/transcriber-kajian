# Halaman wiki

Folder ini berisi panduan pengguna dalam **format wiki GitHub** (`Home.md`, `_Sidebar.md`, nama halaman dengan
tanda hubung). Semuanya bisa dibaca langsung di sini; tautan antar-halaman memakai `.md` agar berfungsi di repo.

## Mengapa belum ada di tab Wiki?

GitHub **tidak menyediakan wiki untuk repo private di paket Free**. Pada 19 Oktober 2026 repo ini private,
`has_wiki` tetap `false` walau diaktifkan lewat API, dan repo `transcriber-kajian.wiki.git` tidak terbentuk.
Pilihan (keputusan pemilik repo):

1. Tetap memakai folder ini sebagai wiki (tanpa biaya, ikut riwayat git, bisa ditinjau lewat pull request).
2. Naik ke GitHub Pro/Team agar tab Wiki tersedia untuk repo private, lalu publikasikan dengan skrip di bawah.
3. Menjadikan repo public. Pertimbangkan dulu isinya: `hasil\` memuat transkrip kajian dan `riwayat.json`.

## Memublikasikan ke wiki sungguhan

Syarat: tab Wiki aktif di Settings -> Features, dan **halaman pertama sudah dibuat sekali lewat web**
(tombol "Create the first page"; repo `.wiki.git` baru terbentuk setelahnya).

```
powershell -ExecutionPolicy Bypass -File docs\wiki\publikasikan.ps1 -DryRun    # lihat hasil penulisan ulang tautan
powershell -ExecutionPolicy Bypass -File docs\wiki\publikasikan.ps1            # clone wiki, salin, commit, push
```

Skrip menyalin semua `*.md` di folder ini ke repo wiki dan menyesuaikan tautan:

- `[teks](Halaman.md)` menjadi `[teks](Halaman)`;
- `[teks](../dokumen.md)` menjadi tautan absolut ke `docs/dokumen.md` di cabang `main`.

`README.md` ini tidak ikut dipublikasikan. Setelah publikasi, jadikan **folder ini atau wiki** sebagai satu-satunya
sumber agar tidak berbeda; bila wiki dipakai, hapus folder ini dan perbarui tautan di `docs/README.md`.
