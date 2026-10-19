"""
quality.py — cek kualitas otomatis per segmen, supaya tim QC cukup
memeriksa bagian yang ditandai, bukan seluruh transkrip.

Tanda:
  RAGU        : avg_logprob rendah (model tidak yakin)
  NOISE       : no_speech_prob tinggi (kemungkinan bukan ucapan)
  BERULANG    : compression_ratio tinggi (teks berulang di dalam segmen)
  HALUSINASI  : kalimat sama muncul ≥N kali berturut-turut
  FRASA_CURIGA: frasa yang sering "dikarang" Whisper saat hening/musik
                (mis. "terima kasih telah menonton", "subtitle oleh ...")
  TERLEWAT    : potongan panjang tapi teksnya sangat sedikit — kemungkinan ada ucapan yang
                tidak tertulis (mis. bacaan Arab yang dilewati model). Dengarkan bagian ini.
  MIRIP_PROMPT: teks segmen hampir sama dengan contoh gaya / glosarium. Bisa memang diucapkan
                (pembukaan khutbah), bisa juga "bocoran" prompt yang dikarang model saat hening.
  NAMA_BOCOR  : nama penceramah muncul di teks. Whisper sering menempelkannya ke kutipan ulama lain
                (mis. "al-imam Muhammad Nuzul Uthaymeen" padahal yang dikutip al-Utsaimin).
                Bisa juga memang diucapkan (perkenalan MC): dengarkan bagian ini.

Status video minimal PERLU_CEK bila ada TERLEWAT (ada ucapan yang mungkin hilang dari transkrip)
atau NAMA_BOCOR (atribusi kutipan bisa salah).
"""

import math
import re
from difflib import SequenceMatcher

import config

# Frasa yang sering muncul sebagai halusinasi Whisper Bahasa Indonesia (dari data subtitle).
FRASA_CURIGA = (
    "terima kasih telah menonton", "terima kasih sudah menonton", "terima kasih telah mendengarkan",
    "sampai jumpa di video", "jangan lupa like", "jangan lupa subscribe", "subtitle oleh",
    "subtitles by", "terjemahan oleh", "amara.org", "diterjemahkan oleh",
)


def _angka(v, default: float = 0.0) -> float:
    """Angka berhingga dari nilai segmen; hilang/null/teks/nan/inf → default (tidak crash)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


def _norm(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _mirip_prompt(text: str, prompt_words: list[str], prompt_set: set[str]) -> bool:
    """Segmen ≥5 kata yang ≥70% isinya potongan urut prompt, atau ≥90% katanya kata prompt."""
    words = _norm(text).split()
    if len(words) < 5 or not prompt_words:
        return False
    blocks = SequenceMatcher(None, words, prompt_words, autojunk=False).get_matching_blocks()
    urut = sum(b.size for b in blocks if b.size >= 2)
    if urut / len(words) >= 0.7:
        return True
    return len(words) >= 6 and sum(w in prompt_set for w in words) / len(words) >= 0.9


# Kata umum dalam nama/gelar: tidak cukup khas untuk menandai nama penceramah.
_NAMA_UMUM = {
    "muhammad", "muhammed", "mohammad", "ahmad", "abdullah", "abdul", "abu", "ummu", "bin", "binti",
    "ibnu", "ibn", "al", "ustadz", "ustad", "ustadzah", "syaikh", "syekh", "syeikh", "kh", "dr", "lc",
    "ma", "official", "channel", "tv", "kajian", "media", "dakwah",
    # kata umum nama channel lembaga (mis. "Kajian Sunnah", "Radio Rodja")
    "sunnah", "islam", "islami", "islamic", "muslim", "ilmu", "ilmiah", "radio", "studio", "masjid",
    "yayasan", "pondok", "pesantren", "indonesia", "dzikir", "quran", "alquran", "tafsir",
}
# Kata sebelum token yang membuatnya istilah/bacaan Arab biasa, bukan nama
# (mis. "asbabun nuzul", "wa dzikri maatsirihim", "li dzikri").
_NAMA_KECUALI_SEBELUM = {"asbabun", "asbab", "sabab", "sababun", "wa", "li", "bi", "fi"}


def nama_tokens(nama: list[str] | tuple[str, ...] | str) -> set[str]:
    """Token khas dari nama penceramah (≥4 huruf, bukan kata umum/gelar).
    'Muhammad Nuzul Dzikri' → {'nuzul', 'dzikri'}."""
    if isinstance(nama, str):
        nama = [nama]
    return {w for n in nama for w in _norm(n or "").split() if len(w) >= 4 and w not in _NAMA_UMUM}


def _nama_bocor(text: str, tokens: set[str]) -> bool:
    words = _norm(text).split()
    return any(w in tokens and (i == 0 or words[i - 1] not in _NAMA_KECUALI_SEBELUM)
               for i, w in enumerate(words))


def flag_segments(segments: list[dict], prompt: str = "",
                  nama_pembicara: list[str] | tuple[str, ...] | str = ()) -> list[dict]:
    """Tambahkan field 'flags' (list) ke setiap segmen. Mengubah & mengembalikan list yang sama.
    prompt: contoh gaya + glosarium yang diberikan ke model (untuk tanda MIRIP_PROMPT).
    nama_pembicara: nama penceramah, mis. dari channel YouTube (untuk tanda NAMA_BOCOR)."""
    prompt_words = _norm(prompt or "").split()
    prompt_set = set(prompt_words)
    tokens_nama = nama_tokens(nama_pembicara)
    normed = []   # teks ternormalisasi per segmen (untuk deteksi halusinasi)
    for s in segments:
        flags = []
        teks = s.get("text")
        teks = teks if isinstance(teks, str) else ""   # JSON hasil edit tangan: 'text' bisa hilang / null
        if _angka(s.get("avg_logprob")) < config.QC_LOW_LOGPROB:
            flags.append("RAGU")
        if _angka(s.get("no_speech_prob")) > config.QC_HIGH_NO_SPEECH:
            flags.append("NOISE")
        if _angka(s.get("compression_ratio")) > config.QC_HIGH_COMPRESSION:
            flags.append("BERULANG")
        low = teks.lower()
        if any(f in low for f in FRASA_CURIGA):
            flags.append("FRASA_CURIGA")
        dur = _angka(s.get("end")) - _angka(s.get("start"))
        if (dur >= config.QC_MIN_DUR_TERLEWAT and "NOISE" not in flags
                and len(teks.strip()) / dur < config.QC_MIN_CHARS_PER_SEC):
            flags.append("TERLEWAT")
        if _mirip_prompt(teks, prompt_words, prompt_set):
            flags.append("MIRIP_PROMPT")
        if tokens_nama and _nama_bocor(teks, tokens_nama):
            flags.append("NAMA_BOCOR")
        s["flags"] = flags
        normed.append(_norm(teks))

    # Halusinasi: teks identik berturut-turut ≥ QC_REPEAT_MIN
    i = 0
    while i < len(segments):
        key = normed[i]
        j = i
        while j + 1 < len(segments) and key and normed[j + 1] == key:
            j += 1
        run = j - i + 1
        if key and run >= config.QC_REPEAT_MIN:
            for k in range(i, j + 1):
                if "HALUSINASI" not in segments[k]["flags"]:
                    segments[k]["flags"].append("HALUSINASI")
        i = j + 1
    return segments


def summarize(segments: list[dict], durasi_detik: float = 0) -> dict:
    """Ringkasan kualitas satu video."""
    total = len(segments)
    flagged = [s for s in segments if s.get("flags")]
    per_flag: dict[str, int] = {}
    for s in flagged:
        for f in s["flags"]:
            per_flag[f] = per_flag.get(f, 0) + 1
    pct = round(100 * len(flagged) / total, 1) if total else 0.0

    if total == 0:
        status = "KOSONG"
    elif pct <= 5:
        status = "BAIK"
    elif pct <= 20:
        status = "PERLU_CEK"
    else:
        status = "BURUK"
    if status == "BAIK" and (per_flag.get("TERLEWAT") or per_flag.get("NAMA_BOCOR")):
        status = "PERLU_CEK"   # sedikit segmen, tapi isi/atribusi kutipan bisa salah: wajib didengar

    return {
        "status": status,
        "total_segmen": total,
        "segmen_ditandai": len(flagged),
        "persen_ditandai": pct,
        "per_tanda": per_flag,
        "durasi_detik": durasi_detik,
    }
