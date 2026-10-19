"""
antrian.py — membaca input URL dari perintah, file antrian per bab, atau playlist,
lalu mengubahnya jadi daftar video unik.

Format file antrian (antrian/bab_xxx.txt):
    # bab: Thaharah
    # kitab: Bulughul Maram
    https://youtu.be/AAAA
    https://youtube.com/playlist?list=CCCC
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass
class Antrian:
    bab: str = "Tanpa Bab"
    kitab: str = ""
    urls: list[str] = field(default_factory=list)


def parse_file(path: str | Path) -> Antrian:
    """Baca file antrian. Baris '# bab:' dan '# kitab:' jadi metadata."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File antrian tidak ditemukan: {path}")

    from config import read_text_any

    q = Antrian(bab=path.stem.replace("bab_", "").replace("_", " ").title())
    for raw in read_text_any(path).splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = re.match(r"#\s*(bab|kitab)\s*:\s*(.+)", line, re.IGNORECASE)
            if m:
                nilai = re.sub(r"(^|\s+)#.*$", "", m.group(2)).strip()   # '# bab: Niat  # catatan'; 'C# Dasar' utuh
                if nilai:
                    setattr(q, m.group(1).lower(), nilai)
            continue
        url = clean_url(line.split()[0])   # abaikan komentar setelah URL
        if url and url not in q.urls:
            q.urls.append(url)
    return q


def clean_url(url: str) -> str:
    """Buang tanda kutip/kurung/koma yang ikut tersalin, mis. <https://...> atau "https://...",.
    URL tanpa skema (youtu.be/xxx, www.youtube.com/...) diberi https://."""
    url = url.strip().strip("<>\"'`,;()[]").strip()
    if url and "://" not in url and re.match(r"(?i)^(www\.|m\.|music\.)?(youtu\.be|youtube\.com)/", url):
        url = "https://" + url
    return url


def video_id(url: str) -> str | None:
    """Ambil ID video 11 karakter dari berbagai bentuk URL YouTube. None jika bukan URL video."""
    url = clean_url(url)
    if _ID_RE.match(url):
        return url
    try:
        p = urlparse(url)
    except ValueError:
        return None
    host = (p.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        vid = p.path.lstrip("/").split("/")[0]
        return vid if _ID_RE.match(vid) else None
    if host in ("youtube.com", "music.youtube.com"):
        if p.path == "/watch":
            vid = parse_qs(p.query).get("v", [""])[0]
            return vid if _ID_RE.match(vid) else None
        m = re.match(r"^/(shorts|live|embed)/([A-Za-z0-9_-]{11})", p.path)
        if m:
            return m.group(2)
    return None


def is_playlist(url: str) -> bool:
    """True jika URL adalah halaman playlist (bukan video di dalam playlist)."""
    try:
        p = urlparse(clean_url(url))
    except ValueError:
        return False
    host = (p.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    return host in ("youtube.com", "music.youtube.com") and p.path == "/playlist" and "list" in parse_qs(p.query)


def youtube_link(vid: str, seconds: float = 0) -> str:
    """Link YouTube yang langsung lompat ke detik tertentu (untuk sitasi)."""
    t = int(max(0, seconds))
    return f"https://youtu.be/{vid}?t={t}" if t else f"https://youtu.be/{vid}"
