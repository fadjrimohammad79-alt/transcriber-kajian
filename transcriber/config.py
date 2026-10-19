"""
config.py — semua pengaturan transcriber di satu tempat.
Nilai bisa diubah lewat file .env (lihat .env.example) atau argumen run.py.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

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
BATCH_SIZE   = int(os.getenv("WHISPER_BATCH", "8"))         # 8 aman untuk RTX 4060 8 GB
BEAM_SIZE    = int(os.getenv("WHISPER_BEAM", "5"))
LANGUAGE     = os.getenv("WHISPER_LANG", "id")              # dikunci Bahasa Indonesia

# ── Backend transkripsi ──────────────────────────────────────────────
# auto  : GPU NVIDIA lokal bila ada → Groq API bila GROQ_API_KEY diisi → CPU lokal
# lokal : paksa GPU NVIDIA | groq : paksa Groq API | cpu : paksa CPU lokal (lambat)
BACKEND      = os.getenv("WHISPER_BACKEND", "auto").strip().lower() or "auto"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# ── Cek kualitas ─────────────────────────────────────────────────────
QC_LOW_LOGPROB      = float(os.getenv("QC_LOW_LOGPROB", "-1.0"))   # di bawah ini = model ragu
QC_HIGH_NO_SPEECH   = float(os.getenv("QC_HIGH_NO_SPEECH", "0.6")) # di atas ini = mungkin noise
QC_HIGH_COMPRESSION = float(os.getenv("QC_HIGH_COMPRESSION", "2.4"))  # teks berulang-ulang
QC_REPEAT_MIN       = int(os.getenv("QC_REPEAT_MIN", "3"))         # kalimat sama ≥3x berturut
# Ucapan normal ±12–16 huruf/detik. Potongan ≥10 detik dengan < 4 huruf/detik → kemungkinan ada yang terlewat.
QC_MIN_DUR_TERLEWAT  = float(os.getenv("QC_MIN_DUR_TERLEWAT", "10"))
QC_MIN_CHARS_PER_SEC = float(os.getenv("QC_MIN_CHARS_PER_SEC", "4"))
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


def force_utf8_output() -> None:
    """Cegah crash emoji saat output dialihkan ke file/pipe di Windows (cp1252)."""
    import sys
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


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
    lines = [l.strip() for l in read_text_any(path).splitlines() if l.strip() and not l.strip().startswith("#")]
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
