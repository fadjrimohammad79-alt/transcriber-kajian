"""
downloader.py — mengambil daftar video dari playlist dan mengunduh audionya dengan yt-dlp.

Hanya audio (bestaudio) yang diunduh, tanpa konversi: faster-whisper membaca
m4a/webm langsung lewat PyAV, jadi ffmpeg tidak wajib.
"""

import json
from pathlib import Path

import config
from antrian import clean_url, is_playlist, video_id

# Siaran yang belum selesai/diproses YouTube: jangan diunduh (bisa merekam tanpa henti
# atau menghasilkan audio terpotong).
SKIP_LIVE_STATUS = {"is_live": "sedang live", "is_upcoming": "belum tayang (jadwal premiere/live)",
                    "post_live": "baru selesai live, masih diproses YouTube"}


class VideoTidakSiap(RuntimeError):
    """Video live/upcoming — coba lagi nanti."""


class DownloadProgress:
    """Hook progres yt-dlp → progress bar tqdm (byte). Mati otomatis bila output bukan terminal."""

    def __init__(self, desc: str = "   ⬇️  Audio", show: bool = True):
        self.desc, self.show = desc, show
        self.bar = None
        self.last = 0

    def __call__(self, d: dict) -> None:
        status = d.get("status")
        if status not in ("downloading", "finished"):
            return
        if self.bar is None:
            from tqdm import tqdm
            self.bar = tqdm(total=None, unit="B", unit_scale=True, unit_divisor=1000, desc=self.desc,
                            disable=None if self.show else True)
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if total and self.bar.total != total:
            self.bar.total = int(total)
        done = int(d.get("downloaded_bytes") or 0)
        if done > self.last:
            self.bar.update(done - self.last)
            self.last = done
        if status == "finished":
            self.close()

    def close(self) -> None:
        if self.bar is not None:
            if self.bar.total and self.bar.n < self.bar.total:
                self.bar.update(self.bar.total - self.bar.n)
            self.bar.close()
            self.bar = None


def _ydl(opts: dict):
    import yt_dlp
    base = {"quiet": True, "no_warnings": True, "noprogress": True}
    if config.YTDLP_COOKIES_BROWSER:
        base["cookiesfrombrowser"] = (config.YTDLP_COOKIES_BROWSER,)
    base.update(opts)
    return yt_dlp.YoutubeDL(base)


def expand_urls(urls: list[str]) -> list[str]:
    """Ubah daftar URL (video/playlist) jadi daftar ID video unik, urutan dipertahankan.
    Playlist yang gagal dibuka hanya diberi peringatan, URL lain tetap diproses."""
    ids: list[str] = []
    for url in urls:
        url = clean_url(url)
        if is_playlist(url):
            try:
                with _ydl({"extract_flat": "in_playlist"}) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:  # noqa: BLE001
                print(f"   ⚠️  Playlist gagal dibuka, dilewati: {url}\n      {type(e).__name__}: {e}")
                continue
            entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
            if not entries:
                print(f"   ⚠️  Playlist kosong/privat: {url}")
            for entry in entries:
                if entry["id"] not in ids:
                    ids.append(entry["id"])
        else:
            vid = video_id(url)
            if vid is None:
                print(f"   ⚠️  Bukan URL video/playlist YouTube, dilewati: {url}")
            elif vid not in ids:
                ids.append(vid)
    return ids


def find_cached_audio(vid: str, audio_dir: Path) -> Path | None:
    for f in audio_dir.glob(f"{vid}.*"):
        if f.suffix not in (".part", ".ytdl", ".json", ".tmp") and f.stat().st_size > 0:
            return f
    return None


def _meta_path(vid: str, audio_dir: Path) -> Path:
    return audio_dir / f"{vid}.info.json"


def download_audio(vid: str, audio_dir: Path) -> tuple[Path, dict]:
    """Unduh audio satu video. Return (path_audio, metadata).
    Jika audio + metadata sudah ada di cache, tidak perlu internet sama sekali."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    cached = find_cached_audio(vid, audio_dir)
    mp = _meta_path(vid, audio_dir)
    if cached and mp.exists():
        try:
            return cached, json.loads(mp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass   # metadata rusak → ambil ulang

    url = f"https://www.youtube.com/watch?v={vid}"
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(audio_dir / "%(id)s.%(ext)s"),
        "retries": 5,
        "fragment_retries": 5,
    }
    progress = DownloadProgress()
    opts["progress_hooks"] = [progress]
    try:
        with _ydl(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            status = info.get("live_status")
            if status in SKIP_LIVE_STATUS:
                raise VideoTidakSiap(f"Video {SKIP_LIVE_STATUS[status]}. Coba lagi setelah siaran selesai.")
            if cached is None:
                ydl.extract_info(url, download=True)
    finally:
        progress.close()

    path = cached or find_cached_audio(vid, audio_dir)
    if path is None:
        raise RuntimeError(f"Audio untuk {vid} tidak ditemukan setelah download.")

    meta = {
        "video_id": vid,
        "judul": info.get("title", ""),
        "channel": info.get("channel") or info.get("uploader", ""),
        "tanggal_upload": info.get("upload_date", ""),   # YYYYMMDD
        "durasi_detik": info.get("duration") or 0,
        "url": f"https://youtu.be/{vid}",
    }
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, meta
