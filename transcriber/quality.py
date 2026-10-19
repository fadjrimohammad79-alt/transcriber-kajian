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

Status video minimal PERLU_CEK bila ada TERLEWAT (ada ucapan yang mungkin hilang dari transkrip).
"""

import re
from difflib import SequenceMatcher

import config


# Frasa yang sering muncul sebagai halusinasi Whisper Bahasa Indonesia (dari data subtitle).
FRASA_CURIGA = (
    "terima kasih telah menonton", "terima kasih sudah menonton", "terima kasih telah mendengarkan",
    "sampai jumpa di video", "jangan lupa like", "jangan lupa subscribe", "subtitle oleh",
    "subtitles by", "terjemahan oleh", "amara.org", "diterjemahkan oleh",
)


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


def flag_segments(segments: list[dict], prompt: str = "") -> list[dict]:
    """Tambahkan field 'flags' (list) ke setiap segmen. Mengubah & mengembalikan list yang sama.
    prompt: contoh gaya + glosarium yang diberikan ke model (untuk tanda MIRIP_PROMPT)."""
    prompt_words = _norm(prompt or "").split()
    prompt_set = set(prompt_words)
    for s in segments:
        flags = []
        if s.get("avg_logprob", 0) < config.QC_LOW_LOGPROB:
            flags.append("RAGU")
        if s.get("no_speech_prob", 0) > config.QC_HIGH_NO_SPEECH:
            flags.append("NOISE")
        if s.get("compression_ratio", 0) > config.QC_HIGH_COMPRESSION:
            flags.append("BERULANG")
        low = s.get("text", "").lower()
        if any(f in low for f in FRASA_CURIGA):
            flags.append("FRASA_CURIGA")
        dur = float(s.get("end", 0) or 0) - float(s.get("start", 0) or 0)
        if (dur >= config.QC_MIN_DUR_TERLEWAT and "NOISE" not in flags
                and len(s.get("text", "").strip()) / dur < config.QC_MIN_CHARS_PER_SEC):
            flags.append("TERLEWAT")
        if _mirip_prompt(s.get("text", ""), prompt_words, prompt_set):
            flags.append("MIRIP_PROMPT")
        s["flags"] = flags

    # Halusinasi: teks identik berturut-turut ≥ QC_REPEAT_MIN
    i = 0
    while i < len(segments):
        key = _norm(segments[i]["text"])
        j = i
        while j + 1 < len(segments) and key and _norm(segments[j + 1]["text"]) == key:
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
    if status == "BAIK" and per_flag.get("TERLEWAT"):
        status = "PERLU_CEK"   # sedikit segmen, tapi isinya bisa hilang: wajib didengar

    return {
        "status": status,
        "total_segmen": total,
        "segmen_ditandai": len(flagged),
        "persen_ditandai": pct,
        "per_tanda": per_flag,
        "durasi_detik": durasi_detik,
    }
