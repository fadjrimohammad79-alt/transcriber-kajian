"""
transcriber.py — inti transkripsi dengan faster-whisper di GPU.

Model dimuat sekali lalu dipakai untuk banyak video.
"""

import gpu_setup  # noqa: F401  (harus sebelum faster_whisper — daftarkan DLL CUDA di Windows)

import functools
import time
from pathlib import Path

import config


def patch_av_compat() -> bool:
    """PyAV >= 19 tidak lagi menerima argumen 'metadata_errors' yang dipakai faster-whisper
    saat membuka audio. Jika versi itu terpasang, buang argumen tersebut secara otomatis.
    Return True jika patch dipasang."""
    import av
    if getattr(av.open, "_compat_patched", False):
        return True
    try:
        major = int(str(av.__version__).split(".")[0])
    except ValueError:
        return False
    if major < 19:
        return False

    original = av.open

    @functools.wraps(original)
    def open_compat(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return original(*args, **kwargs)

    open_compat._compat_patched = True
    av.open = open_compat
    return True


class Transcriber:
    def __init__(
        self,
        model_name: str = config.MODEL_NAME,
        device: str = config.DEVICE,
        compute_type: str = config.COMPUTE_TYPE,
        batch_size: int = config.BATCH_SIZE,
    ):
        from faster_whisper import WhisperModel, BatchedInferencePipeline
        from models import ensure_whisper_model

        patch_av_compat()
        path = ensure_whisper_model(model_name)     # progress bar bila model perlu diunduh

        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.batch_size = batch_size

        print(f"🧠 Memuat model '{model_name}' ke {device} ({compute_type}) ...")
        t0 = time.time()
        self.model = WhisperModel(path, device=device, compute_type=compute_type)
        self.pipeline = BatchedInferencePipeline(model=self.model) if batch_size > 1 else None
        print(f"   ✅ Model siap ({time.time() - t0:.1f}s)")

    def transcribe(self, audio_path: Path, hotwords: str = "", word_timestamps: bool = False,
                   show_progress: bool = True) -> dict:
        """Transkripsi satu file audio. Return dict berisi segmen + info."""
        kwargs = dict(
            language=config.LANGUAGE,          # dikunci: cegah salah deteksi saat bacaan Arab
            beam_size=config.BEAM_SIZE,
            vad_filter=True,                   # lewati hening → kurangi halusinasi
            vad_parameters={"min_silence_duration_ms": 700},
            condition_on_previous_text=False,  # cegah "macet" mengulang kalimat
            hotwords=hotwords or None,         # glosarium istilah Arab/fiqih, berlaku tiap potongan
            word_timestamps=word_timestamps,
        )

        t0 = time.time()
        if self.pipeline is not None:
            seg_iter, info = self.pipeline.transcribe(str(audio_path), batch_size=self.batch_size, **kwargs)
        else:
            seg_iter, info = self.model.transcribe(str(audio_path), **kwargs)

        from tqdm import tqdm
        total = float(getattr(info, "duration", 0) or 0)
        # disable=None: progress bar otomatis mati bila output bukan terminal (log/n8n)
        bar = tqdm(total=round(total), unit="s", desc="   🎧 Transkripsi",
                   disable=None if show_progress else True,
                   bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} dtk [{elapsed}<{remaining}]")
        segments = []
        for s in seg_iter:  # generator: transkripsi berjalan di sini
            item = {
                "id": len(segments),
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
                "avg_logprob": round(s.avg_logprob, 3),
                "no_speech_prob": round(s.no_speech_prob, 3),
                "compression_ratio": round(s.compression_ratio, 3),
            }
            if word_timestamps and s.words:
                item["words"] = [
                    {"start": round(w.start, 2), "end": round(w.end, 2),
                     "word": w.word, "prob": round(w.probability, 3)}
                    for w in s.words
                ]
            segments.append(item)
            bar.update(max(0, min(round(s.end), bar.total or 0) - bar.n))
        bar.update(max(0, (bar.total or 0) - bar.n))
        bar.close()

        elapsed = time.time() - t0
        durasi = float(getattr(info, "duration", 0) or 0)
        return {
            "segments": segments,
            "durasi_audio": round(durasi, 1),
            "waktu_proses": round(elapsed, 1),
            "kecepatan_x_realtime": round(durasi / elapsed, 1) if elapsed > 0 else 0,
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
        }
