"""
output.py — simpan hasil per video ke JSON (untuk pipeline), SRT (cek di pemutar video),
dan TXT (baca cepat), plus riwayat.json untuk mencegah duplikasi.
"""

import json
import math
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from antrian import youtube_link

MAX_BACA = 3   # percobaan membaca riwayat.json bila terkunci sementara

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
    ms = int(round(sec * 1000))  # noqa: RUF046 — numpy<2: round(np.float64) masih float → '{:02d}' error
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_clock(sec: float) -> str:
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _waktu(s: dict, key: str, default: float = 0.0) -> float:
    """Waktu segmen sebagai angka berhingga; hilang/null/nan/inf (JSON hasil edit tangan) → default."""
    v = s.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else default


def to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, s in enumerate(segments, 1):
        start = _waktu(s, "start")
        end = _waktu(s, "end", start)
        blocks.append(f"{i}\n{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n{s.get('text') or ''}\n")
    return "\n".join(blocks)


def to_txt(meta: dict, segments: list[dict]) -> str:
    lines = [
        f"Judul  : {meta.get('judul', '')}",
        f"URL    : {meta.get('url', '')}",
        f"Bab    : {meta.get('bab', '')}" + (f" | Kitab: {meta['kitab']}" if meta.get("kitab") else ""),
        "",
    ]
    for s in segments:
        mark = f"  ⚠ {','.join(map(str, s['flags']))}" if s.get("flags") else ""
        lines.append(f"[{fmt_clock(_waktu(s, 'start'))}] {s.get('text') or ''}{mark}")
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

def _nama_backup(path: Path) -> Path:
    """riwayat.rusak-YYYYmmdd-HHMMSS[-n].json — tidak pernah menimpa backup sebelumnya."""
    stempel = f"{path.stem}.rusak-{datetime.now():%Y%m%d-%H%M%S}"
    backup, n = path.with_name(f"{stempel}.json"), 1
    while backup.exists():   # rusak lagi di detik yang sama
        backup, n = path.with_name(f"{stempel}-{n}.json"), n + 1
    return backup


class RiwayatError(RuntimeError):
    """riwayat.json ada tetapi tidak bisa dibaca (terkunci sinkronisasi OneDrive / antivirus / editor,
    atau ternyata folder). Run dihentikan dengan pesan jelas, bukan traceback."""


def load_riwayat(path: Path, tunggu=time.sleep) -> dict:
    if not path.exists():
        return {}
    from config import read_json
    data = None
    for n in range(1, MAX_BACA + 1):
        try:
            data = read_json(path)   # UTF-8 ketat + BOM: teks tidak ditebak cp1252 lalu tersimpan rusak
            break
        except ValueError:
            break                    # JSON/encoding rusak → data None → di-backup di bawah
        except OSError as e:         # PermissionError: file dipegang program lain sebentar / path = folder
            if n == MAX_BACA or path.is_dir():
                raise RiwayatError(
                    f"{path.name} tidak bisa dibaca ({type(e).__name__}). Tutup program yang memakainya "
                    f"(editor/Excel/sinkronisasi OneDrive), lalu jalankan ulang: {path}") from e
            tunggu(0.3 * n)
    if not isinstance(data, dict):
        backup = _nama_backup(path)
        try:
            path.replace(backup)
        except OSError as e:
            raise RiwayatError(
                f"{path.name} rusak dan tidak bisa dipindah ke backup ({type(e).__name__}): {path}") from e
        print(f"⚠️  riwayat.json rusak, dipindah ke {backup.name}; mulai riwayat baru.")
        return {}
    valid = {k: v for k, v in data.items() if isinstance(v, dict)}
    if len(valid) != len(data):
        backup = _nama_backup(path)
        shutil.copy2(path, backup)   # entri yang dibuang hilang saat riwayat disimpan: simpan aslinya
        pesan = (f"{len(data) - len(valid)} entri tidak valid dihapus "
                 f"({', '.join(sorted(set(data) - set(valid)))[:80]}); file asli disalin ke {backup.name}.")
        try:
            save_riwayat(path, valid, tunggu=tunggu)   # langsung bersihkan: run berikutnya tanpa backup baru
        except PermissionError:
            pesan = pesan.replace("dihapus", "diabaikan (file terkunci, dibersihkan saat riwayat disimpan)")
        print(f"⚠️  riwayat.json: {pesan}")
    return valid


def save_riwayat(path: Path, data: dict, percobaan: int = 5, tunggu=time.sleep) -> None:
    """Simpan atomic (tulis .tmp lalu replace). PermissionError sementara (OneDrive/antivirus memegang
    file beberapa detik) dicoba ulang; gagal terus → PermissionError diteruskan ke pemanggil."""
    tmp = path.with_suffix(".tmp")
    isi = json.dumps(data, ensure_ascii=False, indent=2)
    for n in range(1, percobaan + 1):
        try:
            tmp.write_text(isi, encoding="utf-8")
            tmp.replace(path)   # atomic: riwayat tidak rusak kalau proses terhenti saat menulis
            return
        except PermissionError:
            if n == percobaan:
                raise
            tunggu(0.2 * n)
