# Memublikasikan docs/wiki ke wiki GitHub (repo <repo>.wiki.git).
#   -DryRun : hanya menulis ulang tautan ke folder sementara dan melaporkan hasilnya (tanpa jaringan)
# Syarat mode sungguhan: tab Wiki aktif dan halaman pertama sudah dibuat sekali lewat web.
# Skrip ini sengaja ASCII murni agar terbaca benar oleh Windows PowerShell 5.1.
param(
    [switch]$DryRun,
    [string]$Owner = "fadjrimohammad79-alt",
    [string]$Repo = "transcriber-kajian",
    [string]$Branch = "main"
)
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $src "..\..")).Path
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("wiki_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$utf8 = New-Object System.Text.UTF8Encoding($false)
$base = "https://github.com/$Owner/$Repo/blob/$Branch/docs"

function Tulis($m) { Write-Host $m }

try {
    if ($DryRun) {
        New-Item -ItemType Directory -Path $tmp | Out-Null
        $wiki = $tmp
    } else {
        $wiki = Join-Path $tmp "wiki"
        git clone "https://github.com/$Owner/$Repo.wiki.git" $wiki
        if ($LASTEXITCODE -ne 0) {
            throw "Clone wiki gagal. Pastikan tab Wiki aktif dan halaman pertama sudah dibuat lewat web (lihat docs/wiki/README.md)."
        }
    }

    $total = 0
    foreach ($f in Get-ChildItem -LiteralPath $src -Filter *.md -File) {
        if ($f.Name -eq "README.md") { continue }
        $teks = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
        $naik = [regex]::Matches($teks, '\]\(\.\./([A-Za-z0-9_.-]+\.md)\)').Count
        $dalam = [regex]::Matches($teks, '\]\((?!http)([A-Za-z0-9_-]+)\.md\)').Count
        $teks = [regex]::Replace($teks, '\]\(\.\./([A-Za-z0-9_.-]+\.md)\)', ('](' + $base + '/$1)'))
        $teks = [regex]::Replace($teks, '\]\((?!http)([A-Za-z0-9_-]+)\.md\)', ']($1)')
        [System.IO.File]::WriteAllText((Join-Path $wiki $f.Name), $teks, $utf8)
        $total += $naik + $dalam
        Tulis ("  {0,-24} {1} tautan antar-halaman, {2} tautan ke docs/" -f $f.Name, $dalam, $naik)
    }

    $sisa = 0
    foreach ($f in Get-ChildItem -LiteralPath $wiki -Filter *.md -File) {
        $sisa += [regex]::Matches([System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8), '\]\((?!http)[^)]*\.md\)').Count
    }
    Tulis "Tautan ditulis ulang: $total | tautan .md relatif yang tersisa: $sisa"
    if ($sisa -ne 0) { throw "Masih ada tautan .md relatif yang tidak diubah." }

    if ($DryRun) {
        Tulis "DryRun selesai (tidak ada yang dikirim)."
    } else {
        $sha = (git -C $repoRoot rev-parse --short HEAD)
        git -C $wiki add -A
        git -C $wiki diff --cached --quiet
        if ($LASTEXITCODE -eq 0) { Tulis "Wiki sudah mutakhir; tidak ada perubahan."; return }
        git -C $wiki commit -m "Perbarui wiki dari docs/wiki ($sha)"
        git -C $wiki push
        if ($LASTEXITCODE -ne 0) { throw "Push wiki gagal." }
        Tulis "Wiki dipublikasikan."
    }
}
finally {
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
}
