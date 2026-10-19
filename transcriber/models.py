"""
models.py — pastikan model Whisper ada di PC, dengan progress bar saat mengunduh.

faster-whisper sengaja mematikan progress bar saat mengunduh model, sehingga unduhan ~3 GB
terlihat seperti macet. Di sini model diunduh lewat huggingface_hub secara langsung (file
yang sama persis), sehingga progres MB/detik terlihat.
"""

import os
from pathlib import Path

# Sama dengan daftar file yang diunduh faster_whisper.utils.download_model
ALLOW_PATTERNS = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]


class ModelDownloadError(RuntimeError):
    pass


def resolve_repo(name: str) -> str:
    """Nama pendek (large-v3, turbo, ...) → repo Hugging Face. Nama 'user/repo' dipakai apa adanya."""
    if "/" in name:
        return name
    from faster_whisper.utils import _MODELS
    repo = _MODELS.get(name)
    if repo is None:
        raise ModelDownloadError(f"Nama model Whisper tidak dikenal: '{name}'. "
                                 f"Pilihan: {', '.join(sorted(_MODELS))}")
    return repo


def is_complete(path: str | Path) -> bool:
    """Folder model dianggap lengkap jika model.bin ada dan tidak kosong (ikuti symlink HF)."""
    p = Path(path) / "model.bin"
    try:
        return p.exists() and os.path.getsize(p) > 1_000_000
    except OSError:
        return False


def ensure_whisper_model(name: str, show_progress: bool = True) -> str:
    """Return folder model siap pakai. Unduh dengan progress bar bila belum ada / belum lengkap."""
    if Path(name).is_dir():
        if not is_complete(name):
            raise ModelDownloadError(f"Folder model '{name}' tidak berisi model.bin yang lengkap.")
        return str(name)

    repo = resolve_repo(name)
    from huggingface_hub import snapshot_download

    try:   # sudah ada di cache? (tanpa internet)
        path = snapshot_download(repo, allow_patterns=ALLOW_PATTERNS, local_files_only=True)
        if is_complete(path):
            return path
        print(f"⚠️  Model '{name}' di cache belum lengkap (unduhan sebelumnya terputus). Melanjutkan unduhan ...")
    except Exception:  # noqa: BLE001 — belum pernah diunduh
        print(f"⬇️  Mengunduh model Whisper '{name}' ({repo}) — sekali saja, ±1,5–3 GB ...")

    kwargs = {"allow_patterns": ALLOW_PATTERNS}
    if not show_progress:
        from huggingface_hub.utils import disable_progress_bars
        disable_progress_bars()
    try:
        path = snapshot_download(repo, **kwargs)
    except Exception as e:  # noqa: BLE001
        raise ModelDownloadError(
            f"Gagal mengunduh model Whisper '{name}': {type(e).__name__}: {e}\n"
            "   Cek internet, lalu jalankan ulang (unduhan dilanjutkan, tidak mulai dari nol)."
        ) from e
    if not is_complete(path):
        raise ModelDownloadError(f"Unduhan model '{name}' selesai tetapi model.bin tidak lengkap. Jalankan ulang.")
    print("   ✅ Model Whisper tersimpan di cache.")
    return path
