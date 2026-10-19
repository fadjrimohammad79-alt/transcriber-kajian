"""
config.py — semua pengaturan transcriber di satu tempat.
Nilai bisa diubah lewat file .env (lihat .env.example) atau argumen run.py.
"""

import json
import math
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent


def _env_num(name: str, default, cast, minimum=None, maximum=None):
    """Angka dari .env; nilai tidak valid (bukan angka, nan/inf, di luar batas) → peringatan + nilai
    bawaan, bukan crash saat import atau tanda QC yang diam-diam mati (mis. QC_LOW_LOGPROB=nan)."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return cast(default)
    try:
        val = cast(raw)
        ok = math.isfinite(val) and (minimum is None or val >= minimum) and (maximum is None or val <= maximum)
    except (ValueError, OverflowError):   # OverflowError: int ratusan digit → isfinite gagal
        ok = False
    if ok:
        return val
    batas = f" (batas {minimum if minimum is not None else '-inf'}..{maximum if maximum is not None else 'inf'})"
    # ASCII saja: dicetak saat import, sebelum force_utf8_output() (konsol cp1252 tidak crash)
    print(f"PERINGATAN .env: {name}={raw!a} tidak valid{batas}, memakai bawaan {default}")
    return cast(default)

_BENAR = {"1", "true", "yes", "y", "on", "ya", "aktif"}
_SALAH = {"0", "false", "no", "n", "off", "tidak", "nonaktif", "mati"}


def _env_bool(name: str, default: bool) -> bool:
    """Pilihan ya/tidak dari .env (1/0, true/false, on/off, ya/tidak); nilai lain → peringatan + bawaan."""
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in _BENAR:
        return True
    if raw in _SALAH:
        return False
    # ASCII saja: dicetak saat import, sebelum force_utf8_output()
    print(f"PERINGATAN .env: {name}={raw!a} bukan pilihan ya/tidak (1/0, true/false, on/off), "
          f"memakai bawaan {'1' if default else '0'}")
    return default


# ── Folder ───────────────────────────────────────────────────────────
DIR_ANTRIAN = BASE_DIR / "antrian"      # file daftar URL per bab
DIR_AUDIO   = BASE_DIR / "audio"        # audio hasil download (cache)
DIR_HASIL   = BASE_DIR / "hasil"        # transkrip JSON / SRT / TXT
FILE_RIWAYAT = BASE_DIR / "riwayat.json"
FILE_GLOSARIUM = BASE_DIR / "glosarium.txt"
FILE_PROMPT_GAYA = BASE_DIR / "prompt_gaya.txt"
FILE_KOREKSI = BASE_DIR / "koreksi.txt"            # kamus koreksi otomatis (salah => benar)

# ── Model ────────────────────────────────────────────────────────────
# large-v3        : paling akurat (default)
# large-v3-turbo  : ~2-3x lebih cepat, akurasi sedikit turun
# Bisa juga nama repo Hugging Face model CTranslate2, mis. "Systran/faster-whisper-large-v3"
MODEL_NAME   = os.getenv("WHISPER_MODEL", "large-v3")
DEVICE       = os.getenv("WHISPER_DEVICE", "cuda")          # cuda | cpu
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE", "float16")      # float16 (GPU) | int8 (CPU)
BATCH_SIZE   = _env_num("WHISPER_BATCH", 8, int, minimum=1)   # 8 aman untuk RTX 4060 8 GB
BEAM_SIZE    = _env_num("WHISPER_BEAM", 5, int, minimum=1)
LANGUAGE     = os.getenv("WHISPER_LANG", "id")              # dikunci Bahasa Indonesia
# VAD (Silero) menyaring bagian hening agar Whisper tidak berhalusinasi, tetapi bisa ikut memotong bacaan Arab
# yang dilantunkan/pelan. 0 = mati: audio dipotong tetap 30 detik (lihat README: bacaan Arab hilang).
VAD          = _env_bool("WHISPER_VAD", True)

# ── Backend transkripsi ──────────────────────────────────────────────
# auto  : GPU NVIDIA lokal bila ada → Groq API bila GROQ_API_KEY diisi → CPU lokal
# lokal : paksa GPU NVIDIA | groq : paksa Groq API | cpu : paksa CPU lokal (lambat)
BACKEND      = os.getenv("WHISPER_BACKEND", "auto").strip().lower() or "auto"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# ── Cek kualitas ─────────────────────────────────────────────────────
QC_LOW_LOGPROB      = _env_num("QC_LOW_LOGPROB", -1.0, float, maximum=0)   # di bawah ini = model ragu
QC_HIGH_NO_SPEECH   = _env_num("QC_HIGH_NO_SPEECH", 0.6, float, 0, 1)    # di atas ini = mungkin noise
QC_HIGH_COMPRESSION = _env_num("QC_HIGH_COMPRESSION", 2.4, float, minimum=0)  # teks berulang-ulang
QC_REPEAT_MIN       = _env_num("QC_REPEAT_MIN", 3, int, minimum=2)        # kalimat sama ≥3x berturut
# Ucapan normal ±12–16 huruf/detik. Potongan ≥10 detik dengan < 4 huruf/detik → kemungkinan ada yang terlewat.
QC_MIN_DUR_TERLEWAT  = _env_num("QC_MIN_DUR_TERLEWAT", 10, float, minimum=0.1)
QC_MIN_CHARS_PER_SEC = _env_num("QC_MIN_CHARS_PER_SEC", 4, float, minimum=0)
# Celah waktu antar segmen berurutan >= ini = kemungkinan ucapan hilang tanpa jejak (tanda CELAH).
# Transkrip lokal rata-rata 2 celah >= 5 detik per video (jeda wajar); 8 detik jarang tercapai jeda biasa.
QC_MIN_GAP_CELAH     = _env_num("QC_MIN_GAP_CELAH", 8, float, minimum=0.1)
# Nama penceramah untuk tanda NAMA_BOCOR, dipisah koma. Kosong = pakai nama channel YouTube.
# Bila diisi, menimpa nama channel (mis. channel lembaga, atau nama yang mirip nama sahabat/ulama).
QC_NAMA_PEMBICARA = [n.strip() for n in os.getenv("QC_NAMA_PEMBICARA", "").split(",") if n.strip()]


# Cookies browser untuk video yang butuh login/batas usia (kosong = tidak dipakai).
# Contoh: firefox. (Chrome di Windows sering gagal dibaca karena enkripsi cookie.)
YTDLP_COOKIES_BROWSER = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()


def read_text_any(path: Path) -> str:
    """Baca file teks dari Notepad: UTF-8 (dengan/tanpa BOM), fallback ANSI (cp1252)."""
    raw = Path(path).read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def read_json(path: Path):
    """Baca JSON buatan program: UTF-8 ketat, BOM (Notepad) diterima. TIDAK menebak cp1252:
    teks Arab/“ ” yang salah dibaca lalu tersimpan ulang akan rusak permanen.
    UnicodeDecodeError / json.JSONDecodeError (keduanya ValueError) diteruskan ke pemanggil."""
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def force_utf8_output() -> None:
    """Cegah crash emoji saat output dialihkan ke file/pipe di Windows (cp1252)."""
    import contextlib
    import sys
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, OSError, ValueError):   # stream tanpa reconfigure / sudah ditutup
            stream.reconfigure(encoding="utf-8", errors="replace")


# Batas hotwords di faster-whisper: setengah konteks Whisper (448 // 2 - 1 token); sisanya terpotong.
HOTWORDS_MAX_TOKENS = 223
# Prompt (contoh gaya + glosarium) berbagi ruang ±448 token dengan teks yang ditulis model per potongan
# 30 detik. Di atas batas ini, akhir potongan yang padat ucapan bisa terpotong.
PROMPT_RECOMMENDED_TOKENS = 150


def estimate_tokens(text: str) -> int:
    """Perkiraan kasar token Whisper untuk teks Indonesia/Arab-latin (~2.5 karakter per token)."""
    return int(len(text) / 2.5) + 1


def load_prompt_gaya(path: Path = FILE_PROMPT_GAYA) -> str:
    """Contoh gaya penulisan (transliterasi Arab-Latin). Baris # = komentar."""
    if not Path(path).exists():
        return ""
    lines = [s.strip() for s in read_text_any(path).splitlines() if s.strip() and not s.strip().startswith("#")]
    return " ".join(lines)


def build_prompt(gaya: str, glosarium: str) -> str:
    """Gabungkan contoh gaya + glosarium jadi satu prompt untuk model (gaya di depan:
    bila melebihi batas, yang terpotong adalah ujung glosarium, bukan contoh gayanya)."""
    parts = [p.strip() for p in (gaya, glosarium) if p and p.strip()]
    return " ".join(parts)


def load_glosarium(path: Path = FILE_GLOSARIUM) -> str:
    """Baca glosarium istilah (satu istilah per baris, # = komentar) → string untuk hotwords."""
    if not path.exists():
        return ""
    terms = []
    for line in read_text_any(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return ", ".join(terms)
