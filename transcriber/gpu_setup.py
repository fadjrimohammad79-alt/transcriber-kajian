"""
gpu_setup.py — di Windows, daftarkan folder DLL CUDA (cuBLAS + cuDNN) yang
terpasang lewat pip (paket nvidia-cublas-cu12 & nvidia-cudnn-cu12),
supaya faster-whisper/CTranslate2 bisa memakai GPU NVIDIA.

Harus di-import SEBELUM faster_whisper.
"""

import os
import sys
from pathlib import Path


def register_cuda_dlls() -> list[str]:
    """Tambahkan folder bin NVIDIA ke pencarian DLL. Return daftar folder yang ditambahkan."""
    if sys.platform != "win32":
        return []

    added = []
    for sp in map(Path, sys.path):
        nvidia_root = sp / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for sub in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
            bin_dir = nvidia_root / sub / "bin"
            if bin_dir.is_dir() and str(bin_dir) not in added:
                os.add_dll_directory(str(bin_dir))
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                added.append(str(bin_dir))
    return added


REGISTERED = register_cuda_dlls()
