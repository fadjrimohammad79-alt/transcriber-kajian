"""
output.py — simpan hasil per video ke JSON (untuk pipeline), SRT (cek di pemutar video),
dan TXT (baca cepat), plus riwayat.json untuk mencegah duplikasi.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from antrian import youtube_link


_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_name(text: str, max_len: int = 60) -> str:
    """Nama folder/file aman untuk Windows (karakter terlarang, nama khusus, titik/spasi di akhir)."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text[:max_len].strip().rstrip(". ")
    if not text:
        return "tanpa_nama"
    if text.split(".")[0].upper() in _WIN_RESERVED:
        text = "_" + text
    return text


def fmt_srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_clock(sec: float) -> str:
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, s in enumerate(segments, 1):
        blocks.append(f"{i}\n{fmt_srt_time(s['start'])} --> {fmt_srt_time(s['end'])}\n{s['text']}\n")
    return "\n".join(blocks)


def to_txt(meta: dict, segments: list[dict]) -> str:
    lines = [
        f"Judul  : {meta.get('judul', '')}",
        f"URL    : {meta.get('url', '')}",
        f"Bab    : {meta.get('bab', '')}" + (f" | Kitab: {meta['kitab']}" if meta.get("kitab") else ""),
        "",
    ]
    for s in segments:
        mark = f"  ⚠ {','.join(s['flags'])}" if s.get("flags") else ""
        lines.append(f"[{fmt_clock(s['start'])}] {s['text']}{mark}")
    return "\n".join(lines) + "\n"


def save_result(out_root: Path, meta: dict, result: dict, quality: dict) -> dict:
    """Tulis JSON + SRT + TXT. Return dict path file."""
    vid = meta["video_id"]
    folder = out_root / safe_name(meta.get("bab") or "Tanpa Bab")
    folder.mkdir(parents=True, exist_ok=True)

    tanggal = meta.get("tanggal_upload", "")
    stem = f"{tanggal + '_' if tanggal else ''}{vid}_{safe_name(meta.get('judul', ''), 40)}"

    segments = result["segments"]
    for s in segments:
        s["link"] = youtube_link(vid, s["start"])

    doc = {
        "video": meta,
        "transkripsi": {k: v for k, v in result.items() if k != "segments"},
        "kualitas": quality,
        "diproses_pada": datetime.now().isoformat(timespec="seconds"),
        "segments": segments,
    }

    paths = {
        "json": folder / f"{stem}.json",
        "srt": folder / f"{stem}.srt",
        "txt": folder / f"{stem}.txt",
    }
    paths["json"].write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["srt"].write_text(to_srt(segments), encoding="utf-8")
    paths["txt"].write_text(to_txt(meta, segments), encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


# ── Riwayat ──────────────────────────────────────────────────────────

def load_riwayat(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(".rusak.json")
        path.replace(backup)
        print(f"⚠️  riwayat.json rusak, dipindah ke {backup.name}; mulai riwayat baru.")
        return {}


def save_riwayat(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)   # atomic: riwayat tidak rusak kalau proses terhenti saat menulis
