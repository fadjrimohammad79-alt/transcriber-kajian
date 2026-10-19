"""
check_gpu.py — pastikan GPU NVIDIA siap dipakai sebelum memproses banyak video.

    python check_gpu.py            # cek GPU + muat model kecil
    python check_gpu.py --full     # juga muat model large-v3 (download ~3 GB pertama kali)
"""

import gpu_setup  # harus sebelum ctranslate2/faster_whisper (daftarkan DLL CUDA di Windows)

# isort: split

import shutil
import subprocess
import sys

import config


def main() -> int:
    config.force_utf8_output()   # stdout & stderr: emoji tidak crash di konsol cp1252
    ok = True
    print("═" * 55)
    print("  CEK KESIAPAN GPU")
    print("═" * 55)

    # 1. Driver NVIDIA
    if shutil.which("nvidia-smi"):
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                              "--format=csv,noheader"], capture_output=True, text=True)
        print(f"✅ Driver NVIDIA : {out.stdout.strip()}")
    else:
        print("❌ nvidia-smi tidak ditemukan → install/update driver NVIDIA terbaru.")
        ok = False

    # 2. DLL CUDA dari pip
    if sys.platform == "win32":
        if gpu_setup.REGISTERED:
            print(f"✅ DLL CUDA      : {len(gpu_setup.REGISTERED)} folder terdaftar")
        else:
            print("❌ DLL CUDA tidak ditemukan → jalankan: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*")
            ok = False

    # 3. CTranslate2 melihat GPU
    try:
        import ctranslate2
        n = ctranslate2.get_cuda_device_count()
        if n > 0:
            print(f"✅ CTranslate2   : v{ctranslate2.__version__}, {n} GPU CUDA terdeteksi")
        else:
            print("❌ CTranslate2 tidak melihat GPU CUDA.")
            ok = False
    except Exception as e:  # noqa: BLE001 — alat diagnosis: semua error dilaporkan, bukan crash
        print(f"❌ CTranslate2 error: {e}")
        ok = False

    # 4. Uji muat model di GPU
    if ok:
        model = "large-v3" if "--full" in sys.argv else "tiny"
        try:
            from faster_whisper import WhisperModel
            print(f"⏳ Memuat model '{model}' di GPU ...")
            WhisperModel(model, device="cuda", compute_type="float16")
            print(f"✅ Model '{model}' berhasil dimuat di GPU")
        except Exception as e:  # noqa: BLE001 — alat diagnosis: semua error dilaporkan, bukan crash
            print(f"❌ Gagal memuat model di GPU: {type(e).__name__}: {e}")
            if "cudnn" in str(e).lower() or "cublas" in str(e).lower():
                print("   → pip install --force-reinstall nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*")
            ok = False

    # 5. Alat pendukung
    print(f"{'✅' if shutil.which('ffmpeg') else 'ℹ️ '} ffmpeg        : "
          f"{'ada' if shutil.which('ffmpeg') else 'tidak ada (opsional, tidak wajib)'}")

    print("═" * 55)
    print("🎉 GPU siap!" if ok else "⚠️  Perbaiki item ❌ di atas, lalu jalankan ulang.")
    if not ok:
        print("   Tanpa GPU NVIDIA: isi GROQ_API_KEY di .env lalu pakai --backend groq (lihat README).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
