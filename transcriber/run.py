"""
run.py — jalankan transcriber.

Contoh:
    python run.py https://youtu.be/AAAA https://youtu.be/BBBB --bab "Thaharah"
    python run.py --file antrian\\bab_thaharah.txt
    python run.py --file antrian\\bab_thaharah.txt --model large-v3-turbo
    python run.py https://youtube.com/playlist?list=XXXX --bab "Shalat" --kitab "Bulughul Maram"

Video yang sudah selesai otomatis dilewati (lihat riwayat.json). Pakai --force untuk mengulang.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import config
from antrian import Antrian, parse_file
from output import load_riwayat, save_result, save_riwayat
from quality import flag_segments, summarize


def build_items(args) -> list[dict]:
    """Gabungkan semua sumber input → list {vid, bab, kitab}, tanpa duplikat."""
    from downloader import expand_urls

    queues: list[Antrian] = []
    if args.urls:
        queues.append(Antrian(bab=args.bab or "Tanpa Bab", kitab=args.kitab or "", urls=args.urls))
    for f in args.file or []:
        q = parse_file(f)
        if args.bab:
            q.bab = args.bab
        if args.kitab:
            q.kitab = args.kitab
        queues.append(q)

    items, seen = [], set()
    for q in queues:
        for vid in expand_urls(q.urls):
            if vid not in seen:
                seen.add(vid)
                items.append({"vid": vid, "bab": q.bab, "kitab": q.kitab})
    return items


def acquire_lock(path: Path):
    """Kunci agar tidak ada dua run.py berjalan bersamaan. Lepas otomatis saat proses selesai/crash.
    Return file handle (simpan selama proses berjalan) atau None jika sedang dipakai."""
    f = open(path, "a+")
    try:
        f.seek(0)
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


class ModelGagalDimuat(RuntimeError):
    pass


def _hint_model_error(e: Exception) -> str:
    msg = str(e).lower()
    if any(k in msg for k in ("cublas", "cudnn", "cuda", "dll", "libcu")):
        return "Masalah GPU/CUDA → jalankan: python check_gpu.py  (atau sementara pakai --cpu)"
    if "dilanjutkan" in msg or "tidak dikenal" in msg:
        return "Lihat pesan di atas; jalankan ulang untuk melanjutkan unduhan model"
    if any(k in msg for k in ("connection", "resolve", "timeout", "huggingface", "proxy", "ssl")):
        return "Gagal mengunduh model → cek internet (model diunduh sekali, ±3 GB untuk large-v3)"
    if any(k in msg for k in ("not found", "invalid", "repository", "404")):
        return "Nama model tidak dikenal → pakai large-v3, large-v3-turbo, atau nama repo HF yang benar"
    return "Jalankan python check_gpu.py untuk diagnosis"


def _cleanup_old_files(old_entry: dict, new_paths: dict) -> None:
    """Hapus file hasil lama (judul/bab berubah saat --force) supaya tidak ada duplikat saat ingest."""
    keep = set(new_paths.values())
    for key in ("file", "file_sebelumnya"):
        for p in (old_entry.get(key) or {}).values():
            if p not in keep:
                Path(p).unlink(missing_ok=True)


def process(items, transcriber_factory, download_fn, riwayat_path: Path, hasil_dir: Path,
            audio_dir: Path, hotwords: str = "", force: bool = False,
            word_timestamps: bool = False, hapus_audio: bool = False) -> list[dict]:
    """Proses daftar video. Satu video gagal tidak menghentikan yang lain."""
    riwayat = load_riwayat(riwayat_path)
    todo = [it for it in items if force or riwayat.get(it["vid"], {}).get("status") != "selesai"]
    skipped = len(items) - len(todo)
    if skipped:
        print(f"⏭️  {skipped} video sudah selesai sebelumnya, dilewati (pakai --force untuk ulang).")
    if not todo:
        print("✅ Tidak ada video baru untuk diproses.")
        return []

    try:
        transcriber = transcriber_factory()   # model dimuat hanya kalau ada pekerjaan
    except Exception as e:  # noqa: BLE001
        raise ModelGagalDimuat(f"{type(e).__name__}: {e}\n   💡 {_hint_model_error(e)}") from e
    report = []
    for n, it in enumerate(todo, 1):
        vid = it["vid"]
        print(f"\n[{n}/{len(todo)}] 🎬 {vid}  (bab: {it['bab']})")
        old_entry = riwayat.get(vid, {})
        entry = {"bab": it["bab"], "kitab": it["kitab"], "diproses_pada": datetime.now().isoformat(timespec="seconds")}
        try:
            audio_path, meta = download_fn(vid, audio_dir)
            meta.update({"bab": it["bab"], "kitab": it["kitab"]})
            print(f"   ⬇️  {meta.get('judul', '')[:70]}")

            result = transcriber.transcribe(audio_path, hotwords=hotwords, word_timestamps=word_timestamps)
            result["prompt"] = hotwords   # tercatat di JSON: transkrip bisa ditelusuri ulang
            segs = flag_segments(result["segments"], hotwords)
            q = summarize(segs, result.get("durasi_audio", 0))
            paths = save_result(hasil_dir, meta, result, q)
            _cleanup_old_files(old_entry, paths)

            print(f"   ✍️  {len(segs)} segmen | {result['durasi_audio']/60:.1f} mnt audio "
                  f"dalam {result['waktu_proses']:.0f}s ({result['kecepatan_x_realtime']}x real-time)")
            print(f"   🔎 Kualitas: {q['status']} ({q['persen_ditandai']}% segmen ditandai)")
            if q["per_tanda"]:
                print("      " + ", ".join(f"{k} {v}" for k, v in sorted(q["per_tanda"].items())))

            entry.update({"status": "selesai", "judul": meta.get("judul", ""), "model": result.get("model"),
                          "kualitas": q["status"], "file": paths})
            if hapus_audio:
                Path(audio_path).unlink(missing_ok=True)
        except Exception as e:  # noqa: BLE001 — catat & lanjut
            print(f"   ❌ Gagal: {type(e).__name__}: {e}")
            entry.update({"status": "gagal", "error": f"{type(e).__name__}: {e}"})
            prev = old_entry.get("file") or old_entry.get("file_sebelumnya")
            if prev:   # hasil lama tetap tercatat supaya bisa dibersihkan saat berhasil nanti
                entry["file_sebelumnya"] = prev

        riwayat[vid] = entry
        save_riwayat(riwayat_path, riwayat)   # simpan tiap video: aman kalau terhenti di tengah
        report.append({"vid": vid, **entry})
    return report


def print_summary(report: list[dict]) -> None:
    if not report:
        return
    ok = [r for r in report if r["status"] == "selesai"]
    fail = [r for r in report if r["status"] == "gagal"]
    print("\n" + "═" * 60)
    print(f"  SELESAI: {len(ok)}   GAGAL: {len(fail)}")
    print("═" * 60)
    for r in ok:
        print(f"  ✅ {r['vid']}  [{r['kualitas']}]  {r.get('judul', '')[:45]}")
    for r in fail:
        print(f"  ❌ {r['vid']}  {r['error'][:60]}")
    if fail:
        print("\n  Jalankan ulang perintah yang sama untuk mencoba video yang gagal.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Transcriber kajian YouTube (faster-whisper, GPU)")
    p.add_argument("urls", nargs="*", help="URL video atau playlist YouTube")
    p.add_argument("--file", action="append", help="File antrian (boleh diulang: --file a.txt --file b.txt)")
    p.add_argument("--bab", help="Nama bab (menimpa '# bab:' di file)")
    p.add_argument("--kitab", help="Nama kitab")
    p.add_argument("--model", default=config.MODEL_NAME, help="large-v3 (default) | large-v3-turbo | repo HF")
    p.add_argument("--batch", type=int, default=config.BATCH_SIZE, help="Ukuran batch GPU (default 8; turunkan jika VRAM habis)")
    p.add_argument("--cpu", action="store_true", help="Paksa CPU (int8), untuk uji tanpa GPU")
    p.add_argument("--words", action="store_true", help="Simpan timestamp per kata")
    p.add_argument("--force", action="store_true", help="Ulang video yang sudah selesai")
    p.add_argument("--hapus-audio", action="store_true", help="Hapus audio setelah ditranskripsi")
    args = p.parse_args(argv)
    config.force_utf8_output()

    if args.batch < 1:
        p.error("--batch minimal 1")
    if not args.urls and not args.file:
        p.print_help()
        return 1

    lock = acquire_lock(config.BASE_DIR / ".run.lock")
    if lock is None:
        print("❌ run.py lain sedang berjalan di folder ini. Tunggu selesai, atau tutup jendela terminal lainnya.")
        return 4

    try:
        items = build_items(args)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    print(f"📋 {len(items)} video dalam antrian.")
    if not items:
        return 1

    device = "cpu" if args.cpu else config.DEVICE
    compute = "int8" if args.cpu else config.COMPUTE_TYPE

    def factory():
        from transcriber import Transcriber
        return Transcriber(args.model, device, compute, args.batch)

    from downloader import download_audio

    t0 = time.time()
    gaya, glos = config.load_prompt_gaya(), config.load_glosarium()
    hotwords = config.build_prompt(gaya, glos)
    if hotwords:
        est = config.estimate_tokens(hotwords)
        n_istilah = len(glos.split(",")) if glos else 0
        print(f"📖 Prompt: contoh gaya {'ada' if gaya else 'tidak ada'}, glosarium {n_istilah} istilah "
              f"(~{est} token, disarankan ≤ {config.PROMPT_RECOMMENDED_TOKENS}).")
        if est >= config.HOTWORDS_MAX_TOKENS:
            print(f"   ⚠️  Terlalu panjang (batas ~{config.HOTWORDS_MAX_TOKENS} token): ujung glosarium akan terpotong, "
                  "dan teks di akhir potongan audio bisa hilang. Ringkas glosarium.txt.")
        elif est > config.PROMPT_RECOMMENDED_TOKENS:
            print("   ⚠️  Agak panjang: prompt memakan ruang tulis model, akhir potongan yang padat ucapan bisa "
                  "terpotong. Sebaiknya ringkas glosarium.txt.")
    try:
        report = process(items, factory, download_audio, config.FILE_RIWAYAT, config.DIR_HASIL,
                         config.DIR_AUDIO, hotwords, args.force, args.words, args.hapus_audio)
    except ModelGagalDimuat as e:
        print(f"\n❌ Model gagal dimuat: {e}")
        return 3
    except KeyboardInterrupt:
        print("\n⏹️  Dihentikan. Video yang sudah selesai tersimpan; jalankan ulang untuk melanjutkan.")
        return 130
    print_summary(report)
    print(f"\n⏱️  Total waktu: {(time.time() - t0)/60:.1f} menit")
    return 0 if all(r["status"] == "selesai" for r in report) else 2


if __name__ == "__main__":
    sys.exit(main())
