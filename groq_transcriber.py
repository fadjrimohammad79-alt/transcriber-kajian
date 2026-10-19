"""
groq_transcriber.py — transkripsi lewat Groq API (whisper-large-v3 di server Groq),
untuk PC/VPS tanpa GPU NVIDIA. Perlu GROQ_API_KEY di .env (https://console.groq.com/keys).

Antarmuka sama dengan transcriber.Transcriber: transcribe() mengembalikan dict segmen
dengan avg_logprob / no_speech_prob / compression_ratio, jadi cek kualitas tetap jalan.

Alur: audio → Opus mono 16 kHz (PyAV, ±11 MB/jam) → dipotong bila > batas ukuran
→ upload per potongan → segmen digabung dengan timestamp digeser sesuai posisi potongan.
"""

import json
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import config

API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# Nama model lokal → nama model di Groq
MODEL_MAP = {"large-v3": "whisper-large-v3", "large-v3-turbo": "whisper-large-v3-turbo",
             "whisper-large-v3": "whisper-large-v3", "whisper-large-v3-turbo": "whisper-large-v3-turbo"}
MAX_UPLOAD_BYTES = 24 * 1024 * 1024    # batas tier gratis 25 MB, sisakan ruang untuk header multipart
OPUS_BITRATE = 24_000                  # cukup untuk ucapan; 1 jam ≈ 11 MB
MAX_RETRY = 3


class GroqError(RuntimeError):
    pass


def resolve_model(name: str) -> str:
    """Nama model lokal → model Groq. Nama lain (repo HF, tiny, distil, ...) → whisper-large-v3
    (atau turbo bila namanya mengandung 'turbo'), supaya backend auto tidak gagal total."""
    if name in MODEL_MAP:
        return MODEL_MAP[name]
    pengganti = "whisper-large-v3-turbo" if "turbo" in (name or "").lower() else "whisper-large-v3"
    print(f"   ℹ️  Model '{name}' tidak ada di Groq → memakai {pengganti}.")
    return pengganti


def encode_chunks(audio_path: Path, out_dir: Path, chunk_sec: float) -> list[tuple[Path, float]]:
    """Ubah audio ke Opus mono 16 kHz, dipotong tiap chunk_sec detik.
    Return [(path_potongan, detik_mulai), ...]."""
    import av

    chunks: list[tuple[Path, float]] = []
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    out = stream = None
    written = 0          # sampel yang sudah ditulis ke potongan aktif
    total = 0            # sampel total (16 kHz)

    def open_chunk():
        nonlocal out, stream, written
        p = out_dir / f"potongan_{len(chunks):03d}.ogg"
        out = av.open(str(p), "w", format="ogg")
        stream = out.add_stream("libopus", rate=16000, layout="mono")
        stream.bit_rate = OPUS_BITRATE
        chunks.append((p, total / 16000))
        written = 0

    def close_chunk():
        if out is not None:
            for pkt in stream.encode(None):
                out.mux(pkt)
            out.close()

    with av.open(str(audio_path)) as src:
        for frame in src.decode(audio=0):
            for f in resampler.resample(frame):
                if out is None or written >= chunk_sec * 16000:
                    close_chunk()
                    open_chunk()
                f.pts = None
                for pkt in stream.encode(f):
                    out.mux(pkt)
                written += f.samples
                total += f.samples
        for f in resampler.resample(None):
            if out is None:
                open_chunk()
            f.pts = None
            for pkt in stream.encode(f):
                out.mux(pkt)
            total += f.samples
    close_chunk()
    return chunks


def _multipart(fields: dict[str, str | list[str]], file_path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, val in fields.items():
        for v in (val if isinstance(val, list) else [val]):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
                 f"Content-Type: audio/ogg\r\n\r\n".encode())
    parts.append(file_path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _error_message(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read().decode("utf-8", "replace"))["error"]["message"]
    except Exception:  # noqa: BLE001
        return e.reason or ""


class GroqTranscriber:
    def __init__(self, model_name: str = config.MODEL_NAME, api_key: str = config.GROQ_API_KEY,
                 max_upload_bytes: int = MAX_UPLOAD_BYTES, sleep=time.sleep):
        if not api_key:
            raise GroqError("GROQ_API_KEY kosong → isi di .env (buat key di https://console.groq.com/keys)")
        self.model_name = resolve_model(model_name)
        self.api_key = api_key
        self.max_upload_bytes = max_upload_bytes
        self._sleep = sleep
        self.device, self.compute_type = "groq", "api"
        print(f"☁️  Transkripsi lewat Groq API ({self.model_name}).")

    def _post(self, chunk: Path, prompt: str, word_timestamps: bool) -> dict:
        fields = {"model": self.model_name, "language": config.LANGUAGE, "temperature": "0",
                  "response_format": "verbose_json",
                  "timestamp_granularities[]": ["segment", "word"] if word_timestamps else ["segment"]}
        if prompt:
            fields["prompt"] = prompt
        body, ctype = _multipart(fields, chunk)
        for attempt in range(1, MAX_RETRY + 1):
            req = urllib.request.Request(API_URL, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": ctype,
                "User-Agent": "transcriber-kajian"})
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                msg = _error_message(e)
                if (e.code == 429 or e.code >= 500) and attempt < MAX_RETRY:
                    try:
                        wait = float(e.headers.get("retry-after") or 0)
                    except ValueError:
                        wait = 0
                    wait = min(max(wait, 5 * attempt), 300)
                    print(f"   ⏳ Groq {e.code} ({msg[:80]}), coba lagi dalam {wait:.0f} dtk ...")
                    self._sleep(wait)
                    continue
                hint = {401: " → cek GROQ_API_KEY", 413: " → file terlalu besar",
                        429: " → batas pemakaian Groq tercapai, coba lagi nanti"}.get(e.code, "")
                raise GroqError(f"Groq HTTP {e.code}: {msg}{hint}") from None
            except (urllib.error.URLError, OSError) as e:   # OSError: timeout / koneksi putus saat membaca
                if attempt < MAX_RETRY:
                    print(f"   ⏳ Koneksi ke Groq gagal ({type(e).__name__}), coba lagi ...")
                    self._sleep(5 * attempt)
                    continue
                raise GroqError(f"Tidak bisa menghubungi Groq: {getattr(e, 'reason', None) or e}") from None
        raise GroqError("Groq gagal setelah beberapa percobaan")  # tidak tercapai

    def transcribe(self, audio_path: Path, hotwords: str = "", word_timestamps: bool = False,
                   show_progress: bool = True) -> dict:
        """Transkripsi satu file audio. Return dict berisi segmen + info (format sama dengan Transcriber)."""
        t0 = time.time()
        # Potongan per jam audio (±11 MB); diperkecil bila hasil encode masih melebihi batas upload.
        chunk_sec = 3600.0
        with tempfile.TemporaryDirectory(prefix="groq_") as tmp:
            while True:
                for old in Path(tmp).glob("*.ogg"):
                    old.unlink()
                chunks = encode_chunks(Path(audio_path), Path(tmp), chunk_sec)
                if all(p.stat().st_size <= self.max_upload_bytes for p, _ in chunks) or chunk_sec <= 60:
                    break
                chunk_sec /= 2

            segments, durasi = [], 0.0
            for n, (p, offset) in enumerate(chunks, 1):
                if show_progress and len(chunks) > 1:
                    print(f"   ☁️  Potongan {n}/{len(chunks)} ({p.stat().st_size / 1e6:.1f} MB) ...")
                data = self._post(p, hotwords, word_timestamps)
                words = data.get("words") or []
                for s in data.get("segments") or []:
                    start, end = float(s.get("start", 0)), float(s.get("end", 0))
                    item = {
                        "id": len(segments),
                        "start": round(start + offset, 2),
                        "end": round(end + offset, 2),
                        "text": (s.get("text") or "").strip(),
                        "avg_logprob": round(float(s.get("avg_logprob", 0)), 3),
                        "no_speech_prob": round(float(s.get("no_speech_prob", 0)), 3),
                        "compression_ratio": round(float(s.get("compression_ratio", 0)), 3),
                    }
                    if word_timestamps:
                        ws = [{"start": round(float(w["start"]) + offset, 2), "end": round(float(w["end"]) + offset, 2),
                               "word": w.get("word", ""), "prob": None}
                              for w in words if start <= float(w.get("start", -1)) < end]
                        if ws:
                            item["words"] = ws
                    segments.append(item)
                akhir = segments[-1]["end"] if segments else offset
                durasi = max(durasi, offset + float(data.get("duration") or 0), akhir)

        elapsed = time.time() - t0
        return {
            "segments": segments,
            "durasi_audio": round(durasi, 1),
            "waktu_proses": round(elapsed, 1),
            "kecepatan_x_realtime": round(durasi / elapsed, 1) if elapsed > 0 else 0,
            "model": f"groq/{self.model_name}",
            "device": self.device,
            "compute_type": self.compute_type,
        }
