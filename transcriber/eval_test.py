"""
eval_test.py — test suite transcriber. Jalankan: python eval_test.py [--verbose]

Grup 1-8 tidak butuh GPU/internet (transkripsi & download di-mock).
Grup 9 (opsional) menjalankan model Whisper sungguhan jika model bisa diunduh.
"""

import ast
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import types
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(Path(__file__).resolve().parent)

PASS, FAIL, WARN = "✅ PASS", "❌ FAIL", "⚠️  WARN"
results = []
TMP = Path(tempfile.mkdtemp(prefix="eval_transcriber_"))


def test(name, fn):
    t0 = time.time()
    try:
        msg = fn()
        if isinstance(msg, str) and msg.startswith("SKIP"):
            results.append((WARN, name, msg))
        else:
            results.append((PASS, name, f"{msg or 'OK'} ({time.time()-t0:.2f}s)"))
    except Exception as e:
        results.append((FAIL, name, f"{type(e).__name__}: {e}"))
        if "--verbose" in sys.argv:
            traceback.print_exc()


def group(title):
    print(f"\n{'═'*60}\n  {title}\n{'═'*60}")


# ═════════════════════════════════════════════════════════════════════
group("1. STATIC: syntax & file pendukung")

PY_FILES = ["config.py", "gpu_setup.py", "models.py", "antrian.py", "downloader.py", "quality.py",
            "transcriber.py", "output.py", "run.py", "check_gpu.py"]

def t_syntax():
    for f in PY_FILES:
        ast.parse(Path(f).read_text(encoding="utf-8"), filename=f)
    return f"{len(PY_FILES)} file OK"

def t_bat_crlf():
    n = 0
    for f in ("setup_windows.bat", "run.bat"):
        lines = Path(f).read_bytes().split(b"\n")[:-1]
        assert all(l.endswith(b"\r") for l in lines), f"{f}: ada baris tanpa CRLF"
        n += len(lines)
    assert b"%~dp0.venv" in Path("run.bat").read_bytes(), "run.bat harus pakai python di .venv"
    assert b"run.bat" in Path("setup_windows.bat").read_bytes()
    return f"setup_windows.bat + run.bat, {n} baris CRLF"

def t_requirements():
    req = Path("requirements.txt").read_text()
    for pkg in ["faster-whisper", "yt-dlp", "nvidia-cublas-cu12", "nvidia-cudnn-cu12"]:
        assert pkg in req, pkg
    return "dependency lengkap"

test("Syntax semua file Python", t_syntax)
test("setup_windows.bat pakai CRLF (Windows)", t_bat_crlf)
test("requirements.txt lengkap", t_requirements)


# ═════════════════════════════════════════════════════════════════════
group("2. ANTRIAN: parsing URL & file")
from antrian import parse_file, video_id, is_playlist, youtube_link

def t_video_id_variants():
    V = "dQw4w9WgXcQ"
    cases = {
        f"https://www.youtube.com/watch?v={V}": V,
        f"https://youtube.com/watch?v={V}&t=120s": V,
        f"https://www.youtube.com/watch?v={V}&list=PLabc&index=3": V,
        f"https://m.youtube.com/watch?v={V}": V,
        f"https://youtu.be/{V}": V,
        f"https://youtu.be/{V}?si=xyz&t=30": V,
        f"https://www.youtube.com/shorts/{V}": V,
        f"https://www.youtube.com/live/{V}?feature=share": V,
        f"https://www.youtube.com/embed/{V}": V,
        V: V,
        "https://www.youtube.com/playlist?list=PLabc": None,
        "https://vimeo.com/123": None,
        "bukan url": None,
        "https://youtu.be/pendek": None,
        "": None,
    }
    for url, exp in cases.items():
        got = video_id(url)
        assert got == exp, f"{url!r} → {got!r}, harusnya {exp!r}"
    return f"{len(cases)} variasi URL benar"

def t_is_playlist():
    assert is_playlist("https://www.youtube.com/playlist?list=PLabc")
    assert is_playlist("https://youtube.com/playlist?list=PLabc&si=x")
    assert not is_playlist("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc")
    assert not is_playlist("https://youtu.be/dQw4w9WgXcQ")
    return "playlist vs video-dalam-playlist dibedakan"

def t_parse_file():
    f = TMP / "bab_thaharah.txt"
    f.write_text("﻿# bab: Thaharah Lengkap\n# KITAB : Bulughul Maram\n\n"
                 "https://youtu.be/AAAAAAAAAAA   # video 1\n"
                 "# komentar\nhttps://youtu.be/BBBBBBBBBBB\nhttps://youtu.be/AAAAAAAAAAA\n",
                 encoding="utf-8")
    q = parse_file(f)
    assert q.bab == "Thaharah Lengkap", q.bab
    assert q.kitab == "Bulughul Maram", q.kitab
    assert q.urls == ["https://youtu.be/AAAAAAAAAAA", "https://youtu.be/BBBBBBBBBBB"], q.urls
    return "metadata, BOM, komentar & duplikat ditangani"

def t_parse_file_default_bab():
    f = TMP / "bab_shalat_jamaah.txt"
    f.write_text("https://youtu.be/AAAAAAAAAAA\n", encoding="utf-8")
    q = parse_file(f)
    assert q.bab == "Shalat Jamaah", q.bab
    return f"bab dari nama file: '{q.bab}'"

def t_parse_missing():
    try:
        parse_file(TMP / "tidak_ada.txt")
    except FileNotFoundError:
        return "FileNotFoundError dilempar"
    raise AssertionError("harusnya error")

def t_youtube_link():
    assert youtube_link("dQw4w9WgXcQ", 0) == "https://youtu.be/dQw4w9WgXcQ"
    assert youtube_link("dQw4w9WgXcQ", 125.9) == "https://youtu.be/dQw4w9WgXcQ?t=125"
    assert youtube_link("dQw4w9WgXcQ", -3) == "https://youtu.be/dQw4w9WgXcQ"
    return "link timestamp benar"

test("video_id: 15 variasi URL", t_video_id_variants)
test("is_playlist", t_is_playlist)
test("parse_file: metadata, BOM, komentar, duplikat", t_parse_file)
test("parse_file: bab default dari nama file", t_parse_file_default_bab)
test("parse_file: file tidak ada → error", t_parse_missing)
test("youtube_link: sitasi per detik", t_youtube_link)


# ═════════════════════════════════════════════════════════════════════
group("3. DOWNLOADER (yt-dlp di-mock)")
import downloader

class FakeYDL:
    def __init__(self, playlist=None, download_dir=None):
        self.playlist, self.download_dir, self.calls = playlist or {}, download_dir, []
    def __call__(self, opts):
        self.opts = opts
        return self
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def extract_info(self, url, download=False):
        self.calls.append((url, download))
        if "playlist" in url:
            return {"entries": [{"id": v} for v in self.playlist[url]] + [None]}
        vid = url.split("v=")[1]
        if download:
            (self.download_dir / f"{vid}.m4a").write_bytes(b"audio")
        return {"title": f"Kajian {vid}", "channel": "Kanal Ustadz",
                "upload_date": "20260101", "duration": 3600}

def t_expand_urls():
    pl = "https://www.youtube.com/playlist?list=PL1"
    fake = FakeYDL(playlist={pl: ["AAAAAAAAAAA", "BBBBBBBBBBB"]})
    with mock.patch.object(downloader, "_ydl", lambda opts: fake(opts)):
        ids = downloader.expand_urls(["https://youtu.be/BBBBBBBBBBB", pl,
                                      "https://vimeo.com/1", "https://youtu.be/CCCCCCCCCCC"])
    assert ids == ["BBBBBBBBBBB", "AAAAAAAAAAA", "CCCCCCCCCCC"], ids
    return f"playlist dibuka, urutan & dedup benar: {ids}"

def t_download_and_cache():
    d = TMP / "audio_dl"
    fake = FakeYDL(download_dir=d)
    with mock.patch.object(downloader, "_ydl", lambda opts: fake(opts)):
        p1, meta = downloader.download_audio("AAAAAAAAAAA", d)
        p2, meta2 = downloader.download_audio("AAAAAAAAAAA", d)
    assert p1 == p2 and p1.exists()
    assert [c[1] for c in fake.calls] == [False, True], f"panggilan kedua harus dari cache: {fake.calls}"
    assert meta == meta2 and meta["judul"] == "Kajian AAAAAAAAAAA" and meta["durasi_detik"] == 3600
    return "cek info → unduh; panggilan kedua 100% dari cache"

def t_cache_ignores_partial():
    d = TMP / "audio_part"; d.mkdir()
    (d / "XXXXXXXXXXX.m4a.part").write_bytes(b"x")
    assert downloader.find_cached_audio("XXXXXXXXXXX", d) is None
    return "file .part tidak dianggap selesai"

test("expand_urls: playlist + video + URL asing", t_expand_urls)
test("download_audio: unduh lalu pakai cache", t_download_and_cache)
test("cache mengabaikan download setengah jadi", t_cache_ignores_partial)


# ═════════════════════════════════════════════════════════════════════
group("4. TRANSCRIBER (faster-whisper di-mock)")

def _seg(i, start, end, text, words=None, lp=-0.3, ns=0.05, cr=1.4):
    return types.SimpleNamespace(id=i, start=start, end=end, text=f" {text}", avg_logprob=lp,
                                 no_speech_prob=ns, compression_ratio=cr, words=words)

class FakeModel:
    last_kwargs = None
    def __init__(self, name, device, compute_type):
        self.args = (name, device, compute_type)
    def transcribe(self, audio, **kw):
        FakeModel.last_kwargs = kw
        W = types.SimpleNamespace
        segs = [_seg(0, 0.0, 4.2, "Bab thaharah.", [W(start=0.0, end=0.5, word=" Bab", probability=0.99)]),
                _seg(1, 4.2, 9.87654, "Hadats kecil dan besar.")]
        return iter(segs), types.SimpleNamespace(duration=600.0)

class FakeBatched:
    def __init__(self, model): self.model = model
    def transcribe(self, audio, batch_size, **kw):
        FakeBatched.batch_size = batch_size
        return self.model.transcribe(audio, **kw)

fake_fw = types.ModuleType("faster_whisper")
fake_fw.WhisperModel, fake_fw.BatchedInferencePipeline = FakeModel, FakeBatched

def _make(batch):
    import models
    with mock.patch.dict(sys.modules, {"faster_whisper": fake_fw}), \
         mock.patch.object(models, "ensure_whisper_model", lambda name: f"/cache/{name}"):
        import transcriber
        t = transcriber.Transcriber("large-v3", "cuda", "float16", batch)
    assert t.model.args[0] == "/cache/large-v3", "WhisperModel harus memuat folder hasil unduhan"
    return t

def t_transcriber_kwargs():
    t = _make(8)
    r = t.transcribe(Path("x.m4a"), hotwords="thaharah, hadats")
    kw = FakeModel.last_kwargs
    assert kw["language"] == "id"
    assert kw["vad_filter"] is True
    assert kw["condition_on_previous_text"] is False
    assert kw["hotwords"] == "thaharah, hadats"
    assert FakeBatched.batch_size == 8
    assert r["segments"][1]["end"] == 9.88 and r["segments"][0]["text"] == "Bab thaharah."
    assert r["durasi_audio"] == 600.0 and r["model"] == "large-v3"
    return "bahasa id, VAD, anti-loop, glosarium, batch 8"

def t_transcriber_no_batch_no_hotwords():
    t = _make(1)
    assert t.pipeline is None
    t.transcribe(Path("x.m4a"), hotwords="")
    assert FakeModel.last_kwargs["hotwords"] is None, "hotwords kosong harus None"
    return "batch=1 pakai model langsung, hotwords kosong → None"

def t_word_timestamps():
    t = _make(4)
    r = t.transcribe(Path("x.m4a"), word_timestamps=True)
    assert r["segments"][0]["words"][0] == {"start": 0.0, "end": 0.5, "word": " Bab", "prob": 0.99}
    assert "words" not in r["segments"][1]
    r2 = t.transcribe(Path("x.m4a"))
    assert "words" not in r2["segments"][0]
    return "timestamp per kata hanya bila diminta"

def t_gpu_setup_windows():
    import gpu_setup
    sp = TMP / "site-packages"
    for sub in ("cublas", "cudnn"):
        (sp / "nvidia" / sub / "bin").mkdir(parents=True)
    added_calls = []
    with mock.patch.object(gpu_setup.sys, "platform", "win32"), \
         mock.patch.object(gpu_setup.sys, "path", [str(sp), str(TMP / "kosong")]), \
         mock.patch.object(gpu_setup.os, "add_dll_directory", added_calls.append, create=True), \
         mock.patch.dict(os.environ, {"PATH": ""}):
        added = gpu_setup.register_cuda_dlls()
    assert len(added) == 2 and len(added_calls) == 2, added
    assert gpu_setup.register_cuda_dlls() == []   # di Linux: no-op
    return "DLL cublas+cudnn didaftarkan di Windows, no-op di Linux"

def t_progress_hook():
    import io as _io
    hook = downloader.DownloadProgress(show=True)
    class TTY(_io.StringIO):
        def isatty(self): return True
    err = TTY()
    with mock.patch("sys.stderr", err):
        hook({"status": "downloading", "downloaded_bytes": 0, "total_bytes_estimate": 1000})
        hook({"status": "downloading", "downloaded_bytes": 400, "total_bytes": 50_000_000})
        hook({"status": "downloading", "downloaded_bytes": 300})            # mundur: diabaikan
        assert hook.bar.n == 400 and hook.bar.total == 50_000_000
        hook({"status": "finished", "downloaded_bytes": 50_000_000})
        assert hook.bar is None
        hook({"status": "error"})
        hook.close()
    assert "100%" in err.getvalue() and "50.0M" in err.getvalue(), "bar harus tampil di terminal & ditutup 100%"
    return "ukuran berubah, byte mundur & error ditangani; bar ditutup saat selesai"

def t_download_has_hook():
    d = TMP / "audio_hook"
    fake = FakeYDL(download_dir=d)
    with mock.patch.object(downloader, "_ydl", lambda opts: fake(opts)):
        downloader.download_audio("HHHHHHHHHHH", d)
    hooks = fake.opts.get("progress_hooks") or []
    assert len(hooks) == 1 and isinstance(hooks[0], downloader.DownloadProgress)
    return "unduhan audio memasang progress hook"

def t_transcribe_no_spam():
    import io as _io
    t = _make(4)
    err = _io.StringIO()
    with mock.patch("sys.stderr", err):
        t.transcribe(Path("x.m4a"))
    assert "%|" not in err.getvalue(), "progress bar harus mati bila output bukan terminal"
    return "output dialihkan (log/n8n) → tanpa progress bar"

def t_model_download():
    import models, huggingface_hub, io as _io
    good = TMP / "m_ok"; good.mkdir(); (good / "model.bin").write_bytes(b"0" * 2_000_000)
    bad = TMP / "m_bad"; bad.mkdir(); (bad / "model.bin").write_bytes(b"")
    state = {"local": "complete", "fail": False}; calls = []
    def snap(repo, allow_patterns=None, local_files_only=False, **kw):
        calls.append("local" if local_files_only else "download")
        if local_files_only:
            if state["local"] == "missing": raise FileNotFoundError
            return str(good if state["local"] == "complete" else bad)
        if state["fail"]: raise ConnectionError("down")
        return str(good)
    with mock.patch.object(huggingface_hub, "snapshot_download", snap), mock.patch("sys.stdout", _io.StringIO()):
        assert models.ensure_whisper_model("large-v3") == str(good) and calls == ["local"]
        state["local"] = "partial"; calls.clear(); models.ensure_whisper_model("large-v3-turbo")
        assert calls == ["local", "download"], "unduhan setengah jadi harus dilanjutkan"
        state.update(local="missing", fail=True)
        try:
            models.ensure_whisper_model("large-v3"); raise AssertionError("harus error")
        except models.ModelDownloadError as e:
            assert "dilanjutkan" in str(e)
    try:
        models.ensure_whisper_model("large-v9"); raise AssertionError("harus error")
    except models.ModelDownloadError as e:
        assert "tidak dikenal" in str(e)
    import run
    assert "jalankan ulang" in run._hint_model_error(models.ModelDownloadError("x, unduhan dilanjutkan"))
    return "cache lengkap tanpa unduh; setengah jadi dilanjutkan; gagal/nama salah dilaporkan"

test("Progress: hook unduhan audio", t_progress_hook)
test("Progress: hook terpasang saat unduh", t_download_has_hook)
test("Progress: mati saat output dialihkan", t_transcribe_no_spam)
test("Unduh model Whisper (progress)", t_model_download)
test("Transcriber: parameter anti-halusinasi & glosarium", t_transcriber_kwargs)
test("Transcriber: tanpa batch, hotwords kosong", t_transcriber_no_batch_no_hotwords)
test("Transcriber: timestamp per kata opsional", t_word_timestamps)
test("gpu_setup: daftar DLL CUDA di Windows", t_gpu_setup_windows)


# ═════════════════════════════════════════════════════════════════════
group("5. CEK KUALITAS")
import config
from quality import flag_segments, summarize

def _s(text, lp=-0.3, ns=0.05, cr=1.4):
    return {"text": text, "avg_logprob": lp, "no_speech_prob": ns, "compression_ratio": cr}

def t_flags_basic():
    segs = flag_segments([_s("normal"), _s("ragu", lp=-1.5), _s("noise", ns=0.9), _s("ulang", cr=3.0)])
    assert [s["flags"] for s in segs] == [[], ["RAGU"], ["NOISE"], ["BERULANG"]]
    return "RAGU, NOISE, BERULANG terdeteksi"

def t_flags_hallucination():
    segs = flag_segments([_s("awal"), _s("Terima kasih."), _s("terima kasih"),
                          _s("Terima Kasih!"), _s("akhir")])
    assert segs[0]["flags"] == [] and segs[4]["flags"] == []
    assert all("HALUSINASI" in segs[i]["flags"] for i in (1, 2, 3))
    return "3x berturut (beda kapital/tanda baca) → HALUSINASI"

def t_flags_no_false_positive():
    segs = flag_segments([_s("Allahu a'lam"), _s("Allahu a'lam"), _s("lain"), _s("Allahu a'lam"),
                          _s(""), _s(""), _s("")])
    assert all(s["flags"] == [] for s in segs), [s["flags"] for s in segs]
    return "2x berulang & teks kosong tidak ditandai"

def t_summarize():
    base = [_s(f"kalimat {i}") for i in range(100)]
    assert summarize(flag_segments(base))["status"] == "BAIK"
    mix = [_s(f"kalimat {i}") for i in range(85)] + [_s(f"x{i}", lp=-2) for i in range(15)]
    s = summarize(flag_segments(mix))
    assert s["status"] == "PERLU_CEK" and s["persen_ditandai"] == 15.0 and s["per_tanda"] == {"RAGU": 15}
    bad = [dict(_s(f"x{i}", lp=-2)) for i in range(10)]
    assert summarize(flag_segments(bad))["status"] == "BURUK"
    assert summarize([])["status"] == "KOSONG"
    return "BAIK / PERLU_CEK / BURUK / KOSONG"

def t_flag_terlewat():
    real = {"text": "Assalamualaikum warahmatullahi wabarakatuh", "start": 4.0, "end": 34.0,
            "avg_logprob": -0.2, "no_speech_prob": 0.05, "compression_ratio": 1.3}
    normal = {"text": "x" * 400, "start": 34.0, "end": 64.0, "avg_logprob": -0.2,
              "no_speech_prob": 0.05, "compression_ratio": 1.3}
    short = {"text": "Amin", "start": 64.0, "end": 66.0, "avg_logprob": -0.2,
             "no_speech_prob": 0.05, "compression_ratio": 1.3}
    noisy = {"text": "", "start": 70.0, "end": 95.0, "avg_logprob": -0.2,
             "no_speech_prob": 0.9, "compression_ratio": 1.3}
    segs = flag_segments([real, normal, short, noisy])
    assert segs[0]["flags"] == ["TERLEWAT"], segs[0]["flags"]
    assert segs[1]["flags"] == [] and segs[2]["flags"] == []
    assert segs[3]["flags"] == ["NOISE"], "bagian non-ucapan tidak dianggap terlewat"
    return "kasus nyata [0:04] (30 dtk, 42 huruf) ditandai; ucapan normal/pendek/noise tidak"

def t_flag_mirip_prompt():
    P = config.build_prompt(config.load_prompt_gaya(), config.load_glosarium())
    teks = {
        "Alhamdulillah, hamdan katsiran thayyiban mubarakan fih. Ash-shalatu wassalamu ala Rasulillah.": True,
        "thaharah, hadats, istiqamah, jumhur ulama": True,
        "hamdan katsiran thayyiban mubarakan fih kama yuhibbu rabbuna wa yardha": False,  # pembukaan asli
        "Maka thaharah itu syarat sah shalat, dan hadats harus diangkat dulu sebelum shalat.": False,
        "Niat itu tempatnya di hati, dan para ulama sepakat bahwa niat adalah syarat sah ibadah.": False,
        "Alhamdulillah": False, "": False,
    }
    for t, harus in teks.items():
        got = "MIRIP_PROMPT" in flag_segments([_s(t)], P)[0]["flags"]
        assert got == harus, (t, got)
    assert flag_segments([_s(list(teks)[0])])[0]["flags"] == [], "tanpa prompt: tidak ditandai"
    return "bocoran gaya/glosarium ditandai; pembukaan asli & kalimat ber-istilah tidak"

def t_summarize_terlewat_floor():
    segs = [_s(f"kalimat {i}") for i in range(99)] + [dict(_s("a"), start=0.0, end=30.0)]
    q = summarize(flag_segments(segs))
    assert q["persen_ditandai"] == 1.0 and q["status"] == "PERLU_CEK", q
    return "1% saja tapi ada TERLEWAT → PERLU_CEK (bukan BAIK)"

def t_flag_nama_bocor():
    from quality import nama_tokens
    assert nama_tokens("Muhammad Nuzul Dzikri") == {"nuzul", "dzikri"}
    assert nama_tokens(["", "Ustadz Abu Muhammad"]) == set(), "hanya gelar/kata umum: tidak ada token"
    assert nama_tokens(["Kajian Sunnah Official", "Radio Rodja"]) == {"rodja"}, "channel lembaga"
    assert nama_tokens([None]) == set(), "channel kosong/None dari info.json lama"
    nama = ["Muhammad Nuzul Dzikri"]
    teks = {   # kasus nyata dari LAPORAN_REVISI.md (revisi 2026-10-17)
        "Al-imam Muhammad Nuzul Uthaymeen rahimahullah mengatakan": True,
        "Imam Muhammad Nuzul Dzikri menjelaskan,": True,
        "berlomba-lomba untuk Muhammad Nuzul Dzikri.": True,
        "udah main Nuzul,": True,
        "Syaikh Muhammad bin Shalih al-Utsaimin menjelaskan": False,
        "Para ulama menyebutkan asbabun nuzul ayat ini": False,
        "Perbanyak dzikir pagi dan petang": False,
        "wa birrihim wa dzikri maathirihim wa thanai": False,   # video 05 seg 23: bacaan Arab
        "aqimish shalata li dzikri": False,
        "": False,
    }
    for t, harus in teks.items():
        got = "NAMA_BOCOR" in flag_segments([_s(t)], "", nama)[0]["flags"]
        assert got == harus, (t, got)
    assert flag_segments([_s(list(teks)[0])])[0]["flags"] == [], "tanpa nama: tidak ditandai"
    segs = [_s(f"kalimat {i}") for i in range(99)] + [_s("udah main Nuzul,")]
    q = summarize(flag_segments(segs, "", nama))
    assert q["persen_ditandai"] == 1.0 and q["status"] == "PERLU_CEK", q
    return "4 bocoran nyata ditandai; al-Utsaimin, asbabun nuzul, dzikir tidak; 1% → PERLU_CEK"

test("Tanda NAMA_BOCOR (nama penceramah bocor ke kutipan)", t_flag_nama_bocor)
test("Tanda TERLEWAT (bacaan Arab dilewati)", t_flag_terlewat)
test("Tanda MIRIP_PROMPT (prompt bocor ke transkrip)", t_flag_mirip_prompt)
test("Status minimal PERLU_CEK bila ada TERLEWAT", t_summarize_terlewat_floor)
test("Tanda RAGU, NOISE, BERULANG", t_flags_basic)
test("Deteksi halusinasi berulang", t_flags_hallucination)
test("Tidak ada false positive", t_flags_no_false_positive)
test("Ringkasan status kualitas", t_summarize)


# ═════════════════════════════════════════════════════════════════════
group("6. OUTPUT: JSON / SRT / TXT / riwayat")
import output

def t_srt_time():
    assert output.fmt_srt_time(0) == "00:00:00,000"
    assert output.fmt_srt_time(3725.5) == "01:02:05,500"
    assert output.fmt_srt_time(59.9996) == "00:01:00,000"
    assert output.fmt_srt_time(-1) == "00:00:00,000"
    return "format SRT benar termasuk pembulatan"

def t_safe_name():
    assert output.safe_name('Kajian: Bab "Wudhu" / Part 1?') == "Kajian Bab Wudhu Part 1"
    assert output.safe_name("...") == "tanpa_nama"
    assert output.safe_name("") == "tanpa_nama"
    assert len(output.safe_name("x" * 200)) == 60
    return "karakter terlarang Windows dibuang"

def t_save_result():
    meta = {"video_id": "AAAAAAAAAAA", "judul": "Kajian: Wudhu?", "tanggal_upload": "20260105",
            "bab": "Thaharah", "kitab": "Bulughul Maram", "url": "https://youtu.be/AAAAAAAAAAA"}
    segs = flag_segments([dict(_s("Pembukaan"), start=0.0, end=3.0),
                          dict(_s("Wudhu", lp=-2), start=65.4, end=70.0)])
    result = {"segments": segs, "durasi_audio": 70.0, "waktu_proses": 7.0, "model": "large-v3"}
    paths = output.save_result(TMP / "hasil", meta, result, summarize(segs))
    for k in ("json", "srt", "txt"):
        assert Path(paths[k]).exists(), k
    assert "Thaharah" in paths["json"] and "20260105_AAAAAAAAAAA_Kajian Wudhu" in paths["json"]
    doc = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert doc["segments"][1]["link"] == "https://youtu.be/AAAAAAAAAAA?t=65"
    assert doc["video"]["kitab"] == "Bulughul Maram" and doc["kualitas"]["segmen_ditandai"] == 1
    txt = Path(paths["txt"]).read_text(encoding="utf-8")
    assert "[1:05] Wudhu  ⚠ RAGU" in txt
    srt = Path(paths["srt"]).read_text(encoding="utf-8")
    assert "00:01:05,400 --> 00:01:10,000" in srt
    return "3 file, link per detik, tanda QC di TXT"

def t_riwayat_atomic_and_corrupt():
    p = TMP / "riwayat.json"
    output.save_riwayat(p, {"A": {"status": "selesai"}})
    assert output.load_riwayat(p) == {"A": {"status": "selesai"}}
    assert not p.with_suffix(".tmp").exists()
    p.write_text("{rusak", encoding="utf-8")
    assert output.load_riwayat(p) == {}
    assert p.with_suffix(".rusak.json").exists()
    return "simpan atomic, file rusak di-backup"

test("Format waktu SRT", t_srt_time)
test("Nama file aman Windows", t_safe_name)
test("save_result: JSON + SRT + TXT", t_save_result)
test("Riwayat: atomic & pemulihan file rusak", t_riwayat_atomic_and_corrupt)


# ═════════════════════════════════════════════════════════════════════
group("7. ALUR PROSES (run.process)")
import run

class StubTranscriber:
    def __init__(self, fail_on=()):
        self.fail_on, self.calls = set(fail_on), []
    def transcribe(self, audio_path, hotwords="", word_timestamps=False):
        vid = Path(audio_path).stem
        self.calls.append(vid)
        if vid in self.fail_on:
            raise RuntimeError("CUDA out of memory")
        return {"segments": [{"text": "isi", "start": 0.0, "end": 2.0, "avg_logprob": -0.2,
                              "no_speech_prob": 0.0, "compression_ratio": 1.2}],
                "durasi_audio": 2.0, "waktu_proses": 0.5, "kecepatan_x_realtime": 4.0, "model": "stub"}

def stub_download(vid, audio_dir):
    audio_dir.mkdir(parents=True, exist_ok=True)
    p = audio_dir / f"{vid}.m4a"; p.write_bytes(b"a")
    return p, {"video_id": vid, "judul": f"Kajian {vid}", "url": f"https://youtu.be/{vid}"}

def _run(items, fail_on=(), **kw):
    d = kw.pop("dir")
    factory_calls = []
    stub = StubTranscriber(fail_on)
    def factory():
        factory_calls.append(1)
        return stub
    rep = run.process(items, factory, stub_download, d / "riwayat.json", d / "hasil", d / "audio", **kw)
    return rep, stub, factory_calls

ITEMS = [{"vid": v, "bab": "Thaharah", "kitab": ""} for v in ("AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC")]

def t_prompt_recorded():
    d = TMP / "pr"
    _run(ITEMS[:1], dir=d, hotwords="Amma ba'du. thaharah")
    doc = json.loads(next((d / "hasil").rglob("*.json")).read_text(encoding="utf-8"))
    assert doc["transkripsi"]["prompt"] == "Amma ba'du. thaharah"
    return "prompt yang dipakai tersimpan di JSON hasil"

def t_process_nama_dari_channel():
    d = TMP / "nb"
    class Bocor(StubTranscriber):
        def transcribe(self, audio_path, hotwords="", word_timestamps=False):
            r = super().transcribe(audio_path, hotwords, word_timestamps)
            r["segments"][0]["text"] = "Imam Muhammad Nuzul Dzikri menjelaskan,"
            return r
    def dl(vid, audio_dir):
        p, meta = stub_download(vid, audio_dir)
        return p, {**meta, "channel": "Muhammad Nuzul Dzikri"}
    run.process(ITEMS[:1], Bocor, dl, d / "riwayat.json", d / "hasil", d / "audio")
    doc = json.loads(next((d / "hasil").rglob("*.json")).read_text(encoding="utf-8"))
    assert doc["segments"][0]["flags"] == ["NAMA_BOCOR"], doc["segments"][0]
    assert doc["kualitas"]["per_tanda"] == {"NAMA_BOCOR": 1}, doc["kualitas"]
    old = config.QC_NAMA_PEMBICARA
    try:   # .env menimpa channel: nama lain → bocoran "Nuzul" tidak lagi ditandai
        config.QC_NAMA_PEMBICARA = ["Firanda Andirja"]
        d2 = TMP / "nb2"
        run.process(ITEMS[:1], Bocor, dl, d2 / "riwayat.json", d2 / "hasil", d2 / "audio")
        doc = json.loads(next((d2 / "hasil").rglob("*.json")).read_text(encoding="utf-8"))
        assert doc["segments"][0]["flags"] == [], doc["segments"][0]
    finally:
        config.QC_NAMA_PEMBICARA = old
    return "nama channel YouTube dipakai untuk NAMA_BOCOR; QC_NAMA_PEMBICARA menimpanya"

def t_process_failure_continues():
    d = TMP / "p1"
    rep, stub, _ = _run(ITEMS, fail_on={"BBBBBBBBBBB"}, dir=d)
    assert [r["status"] for r in rep] == ["selesai", "gagal", "selesai"]
    rw = json.loads((d / "riwayat.json").read_text(encoding="utf-8"))
    assert rw["BBBBBBBBBBB"]["status"] == "gagal" and "out of memory" in rw["BBBBBBBBBBB"]["error"]
    return "1 gagal tidak menghentikan 2 lainnya"

def t_process_resume():
    d = TMP / "p1"   # lanjut dari test sebelumnya
    rep, stub, _ = _run(ITEMS, dir=d)
    assert stub.calls == ["BBBBBBBBBBB"], stub.calls
    return "jalan ulang: hanya video gagal yang diproses"

def t_process_nothing_no_model():
    d = TMP / "p1"
    rep, stub, factory_calls = _run(ITEMS, dir=d)
    assert rep == [] and factory_calls == [], "model tidak boleh dimuat jika tak ada kerja"
    return "semua selesai → model tidak dimuat"

def t_process_force():
    d = TMP / "p1"
    rep, stub, _ = _run(ITEMS[:1], dir=d, force=True)
    assert stub.calls == ["AAAAAAAAAAA"]
    return "--force mengulang video selesai"

def t_process_hapus_audio():
    d = TMP / "p2"
    _run(ITEMS[:1], dir=d, hapus_audio=True)
    assert not (d / "audio" / "AAAAAAAAAAA.m4a").exists()
    _run(ITEMS[1:2], dir=d)
    assert (d / "audio" / "BBBBBBBBBBB.m4a").exists()
    return "--hapus-audio bekerja, default menyimpan cache"

def t_main_no_args():
    with mock.patch("sys.stdout"):
        assert run.main([]) == 1
    return "tanpa argumen → tampil bantuan, exit 1"

def t_build_items_merge():
    f = TMP / "bab_wudhu.txt"
    f.write_text("# bab: Wudhu\nhttps://youtu.be/AAAAAAAAAAA\nhttps://youtu.be/BBBBBBBBBBB\n", encoding="utf-8")
    args = types.SimpleNamespace(urls=["https://youtu.be/AAAAAAAAAAA"], file=[str(f)], bab=None, kitab=None)
    with mock.patch.object(downloader, "_ydl", lambda o: FakeYDL()(o)):
        items = run.build_items(args)
    assert [i["vid"] for i in items] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert items[0]["bab"] == "Tanpa Bab" and items[1]["bab"] == "Wudhu"
    return "URL langsung + file digabung tanpa duplikat"

test("Prompt tercatat di JSON hasil", t_prompt_recorded)
test("Nama channel → tanda NAMA_BOCOR", t_process_nama_dari_channel)
test("Proses: satu gagal, lainnya lanjut", t_process_failure_continues)
test("Proses: resume hanya yang gagal", t_process_resume)
test("Proses: tidak ada kerja → model tak dimuat", t_process_nothing_no_model)
test("Proses: --force", t_process_force)
test("Proses: --hapus-audio", t_process_hapus_audio)
test("run.main tanpa argumen", t_main_no_args)
test("build_items: gabung URL & file", t_build_items_merge)


# ═════════════════════════════════════════════════════════════════════
group("8. CONFIG & GLOSARIUM")
import config

def t_glosarium():
    g = config.load_glosarium()
    assert "thaharah" in g and "#" not in g
    assert config.load_glosarium(TMP / "tidak_ada.txt") == ""
    n = len(g.split(", "))
    return f"{n} istilah dimuat, komentar diabaikan"

def t_glosarium_length():
    est = config.estimate_tokens(config.load_glosarium())
    assert est < config.HOTWORDS_MAX_TOKENS, f"glosarium ~{est} token, batas {config.HOTWORDS_MAX_TOKENS}"
    assert config.estimate_tokens("x" * 1000) > config.HOTWORDS_MAX_TOKENS
    return f"~{est} token dari batas {config.HOTWORDS_MAX_TOKENS}"

def t_prompt_gaya():
    gaya = config.load_prompt_gaya()
    assert "hamdan katsiran" in gaya and "#" not in gaya
    f = TMP / "gaya.txt"; f.write_bytes("\ufeff# komentar\r\nAlhamdulillah.\r\n\r\nAmma ba'du.\r\n".encode("utf-8"))
    assert config.load_prompt_gaya(f) == "Alhamdulillah. Amma ba'du."
    assert config.load_prompt_gaya(TMP / "tidak_ada.txt") == ""
    p = config.build_prompt("GAYA.", "a, b")
    assert p == "GAYA. a, b", "contoh gaya harus di depan (yang terpotong bila kepanjangan adalah glosarium)"
    assert config.build_prompt("", "a") == "a" and config.build_prompt("", "") == ""
    est = config.estimate_tokens(config.build_prompt(gaya, config.load_glosarium()))
    assert est <= config.PROMPT_RECOMMENDED_TOKENS, f"bawaan ~{est} token melebihi anjuran"
    return f"gaya dimuat; gaya di depan glosarium; bawaan ~{est} token ≤ {config.PROMPT_RECOMMENDED_TOKENS}"

def t_prompt_passed_to_model():
    t = _make(4)
    t.transcribe(Path("x.m4a"), hotwords=config.build_prompt(config.load_prompt_gaya(), "thaharah"))
    hw = FakeModel.last_kwargs["hotwords"]
    assert hw.startswith("Alhamdulillah, hamdan katsiran") and hw.endswith("thaharah")
    return "contoh gaya + glosarium sampai ke model di setiap potongan"

test("Glosarium dimuat", t_glosarium)
test("Contoh gaya (prompt_gaya.txt)", t_prompt_gaya)
test("Contoh gaya dikirim ke model", t_prompt_passed_to_model)
test("Glosarium tidak melebihi batas", t_glosarium_length)



# ═════════════════════════════════════════════════════════════════════
group("10. EDGE CASES")
import io

def t_edge_clean_url():
    from antrian import clean_url
    V = "dQw4w9WgXcQ"
    for raw in (f"<https://youtu.be/{V}>", f'"https://youtu.be/{V}",', f"(https://youtu.be/{V})",
                f"  https://youtu.be/{V};  ", f"'https://www.youtube.com/watch?v={V}'"):
        assert video_id(raw) == V, raw
    assert clean_url('"",') == ""
    return "URL dalam kutip/kurung/koma tetap terbaca"

def t_edge_file_encodings():
    f1 = TMP / "ansi.txt"
    f1.write_bytes("# bab: Café Fiqih\r\nhttps://youtu.be/AAAAAAAAAAA\r\n".encode("cp1252"))
    q = parse_file(f1)
    assert q.bab == "Café Fiqih" and q.urls == ["https://youtu.be/AAAAAAAAAAA"], (q.bab, q.urls)
    g = TMP / "glos.txt"
    g.write_bytes("﻿thaharah\r\nالطهارة\r\n".encode("utf-8"))
    out = config.load_glosarium(g)
    assert out == "thaharah, الطهارة", repr(out)
    empty = TMP / "kosong.txt"; empty.write_bytes(b"")
    assert parse_file(empty).urls == []
    return "ANSI (Notepad lama), UTF-8 BOM, CRLF, huruf Arab, file kosong"

def t_edge_playlist_error_continues():
    class Boom(FakeYDL):
        def extract_info(self, url, download=False):
            if "PLbad" in url: raise RuntimeError("This playlist does not exist")
            if "PLempty" in url: return {"entries": []}
            return super().extract_info(url, download)
    fake = Boom(playlist={"https://www.youtube.com/playlist?list=PLok": ["AAAAAAAAAAA"]})
    with mock.patch.object(downloader, "_ydl", lambda o: fake(o)), mock.patch("sys.stdout", io.StringIO()):
        ids = downloader.expand_urls(["https://www.youtube.com/playlist?list=PLbad",
                                      "https://www.youtube.com/playlist?list=PLempty",
                                      "https://www.youtube.com/playlist?list=PLok",
                                      "https://youtu.be/BBBBBBBBBBB"])
    assert ids == ["AAAAAAAAAAA", "BBBBBBBBBBB"], ids
    return "playlist rusak/kosong dilewati, sisanya lanjut"

def t_edge_live_video():
    for status in ("is_live", "is_upcoming", "post_live"):
        d = TMP / f"live_{status}"
        class Live(FakeYDL):
            def extract_info(self, url, download=False):
                self.calls.append((url, download))
                return {"title": "Live", "live_status": status}
        fake = Live(download_dir=d)
        with mock.patch.object(downloader, "_ydl", lambda o: fake(o)):
            try:
                downloader.download_audio("LLLLLLLLLLL", d)
                raise AssertionError(f"{status} harusnya ditolak")
            except downloader.VideoTidakSiap:
                pass
        assert all(dl is False for _, dl in fake.calls), "tidak boleh mengunduh siaran live"
    return "live / premiere / baru selesai live ditolak tanpa diunduh"

def t_edge_offline_rerun():
    d = TMP / "offline"
    fake = FakeYDL(download_dir=d)
    with mock.patch.object(downloader, "_ydl", lambda o: fake(o)):
        downloader.download_audio("AAAAAAAAAAA", d)
    def no_net(o): raise ConnectionError("no internet")
    with mock.patch.object(downloader, "_ydl", no_net):
        p, meta = downloader.download_audio("AAAAAAAAAAA", d)
    assert p.exists() and meta["judul"] == "Kajian AAAAAAAAAAA"
    return "ulang transkripsi (mis. ganti model) tanpa internet"

def t_edge_zero_byte_cache():
    d = TMP / "zero"; d.mkdir()
    (d / "ZZZZZZZZZZZ.m4a").write_bytes(b"")
    assert downloader.find_cached_audio("ZZZZZZZZZZZ", d) is None
    return "file audio 0 byte tidak dipakai sebagai cache"

def t_edge_reserved_names():
    for raw, exp in [("CON", "_CON"), ("nul", "_nul"), ("Com1.txt", "_Com1.txt"),
                     ("Bab Shalat...", "Bab Shalat"), ("Bab   Wudhu  ", "Bab Wudhu"), (None, "tanpa_nama"),
                     ("Console", "Console")]:
        assert output.safe_name(raw) == exp, (raw, output.safe_name(raw))
    return "CON/NUL/COM1, titik & spasi di akhir, None"

def t_edge_long_path():
    meta = {"video_id": "AAAAAAAAAAA", "judul": "J" * 300, "tanggal_upload": "20260105", "bab": "B" * 300}
    segs = [dict(_s("x"), start=0.0, end=1.0)]
    paths = output.save_result(TMP / "hp", meta, {"segments": segs}, summarize(flag_segments(segs)))
    rel = Path(paths["json"]).relative_to(TMP / "hp")
    assert len(str(rel)) <= 130, len(str(rel))
    return f"path relatif {len(str(rel))} karakter (aman dari batas 260 Windows)"

def t_edge_frasa_curiga():
    segs = flag_segments([_s("Terima kasih telah menonton!"), _s("Subtitle oleh komunitas"),
                          _s("terima kasih atas perhatiannya"), _s("Wallahu a'lam")])
    assert segs[0]["flags"] == ["FRASA_CURIGA"] and segs[1]["flags"] == ["FRASA_CURIGA"]
    assert segs[2]["flags"] == [] and segs[3]["flags"] == []
    return "frasa halusinasi khas Whisper ditandai, ucapan wajar tidak"

def t_edge_empty_transcript():
    meta = {"video_id": "EEEEEEEEEEE", "judul": "Hening", "bab": "Uji"}
    q = summarize(flag_segments([]))
    paths = output.save_result(TMP / "empty", meta, {"segments": []}, q)
    assert q["status"] == "KOSONG" and Path(paths["srt"]).read_text() == ""
    return "video tanpa ucapan → status KOSONG, tidak crash"

def t_edge_force_cleans_old_files():
    d = TMP / "force_clean"
    titles = iter(["Judul Lama", "Judul Baru"])
    def dl(vid, audio_dir):
        p, meta = stub_download(vid, audio_dir)
        meta["judul"] = next(titles)
        return p, meta
    stub = StubTranscriber()
    with mock.patch("sys.stdout", io.StringIO()):
        run.process(ITEMS[:1], lambda: stub, dl, d / "r.json", d / "hasil", d / "audio")
        run.process(ITEMS[:1], lambda: stub, dl, d / "r.json", d / "hasil", d / "audio", force=True)
    files = sorted(x.name for x in (d / "hasil" / "Thaharah").iterdir())
    assert len(files) == 3 and all("Judul Baru" in f for f in files), files
    return "judul berubah + --force → file lama dihapus, tidak ada duplikat"

def t_edge_force_fail_then_success():
    d = TMP / "force_fail"
    with mock.patch("sys.stdout", io.StringIO()):
        run.process(ITEMS[:1], lambda: StubTranscriber(), stub_download, d / "r.json", d / "hasil", d / "audio")
        run.process(ITEMS[:1], lambda: StubTranscriber(fail_on={"AAAAAAAAAAA"}), stub_download,
                    d / "r.json", d / "hasil", d / "audio", force=True)
    rw = json.loads((d / "r.json").read_text(encoding="utf-8"))["AAAAAAAAAAA"]
    assert rw["status"] == "gagal" and "file_sebelumnya" in rw
    old_json = Path(rw["file_sebelumnya"]["json"]); assert old_json.exists()
    def dl2(vid, ad):
        p, m = stub_download(vid, ad); m["judul"] = "Versi Baru"; return p, m
    with mock.patch("sys.stdout", io.StringIO()):
        run.process(ITEMS[:1], lambda: StubTranscriber(), dl2, d / "r.json", d / "hasil", d / "audio")
    assert not old_json.exists(), "file lama harus dibersihkan setelah berhasil"
    return "gagal saat --force menyimpan jejak file lama, dibersihkan saat berhasil"

def t_edge_model_load_failure():
    d = TMP / "modelfail"
    def bad(): raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
    try:
        with mock.patch("sys.stdout", io.StringIO()):
            run.process(ITEMS[:1], bad, stub_download, d / "r.json", d / "hasil", d / "audio")
        raise AssertionError("harusnya ModelGagalDimuat")
    except run.ModelGagalDimuat as e:
        assert "check_gpu" in str(e)
    assert not (d / "r.json").exists(), "riwayat tidak boleh ditulis jika model gagal"
    for msg, key in [("Connection error to huggingface.co", "internet"),
                     ("Repository Not Found for url", "Nama model"), ("weird", "check_gpu")]:
        assert key in run._hint_model_error(RuntimeError(msg)), msg
    return "error DLL/internet/nama model diberi petunjuk, riwayat aman"

def t_edge_ctrl_c():
    d = TMP / "ctrlc"
    class Interrupt(StubTranscriber):
        def transcribe(self, audio_path, **kw):
            if Path(audio_path).stem == "BBBBBBBBBBB": raise KeyboardInterrupt
            return super().transcribe(audio_path, **kw)
    try:
        with mock.patch("sys.stdout", io.StringIO()):
            run.process(ITEMS, lambda: Interrupt(), stub_download, d / "r.json", d / "hasil", d / "audio")
        raise AssertionError("Ctrl+C harus menghentikan proses")
    except KeyboardInterrupt:
        pass
    rw = json.loads((d / "r.json").read_text(encoding="utf-8"))
    assert list(rw) == ["AAAAAAAAAAA"] and rw["AAAAAAAAAAA"]["status"] == "selesai"
    return "Ctrl+C: video yang sudah selesai tetap tercatat"

def t_edge_cli_validation():
    with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
        try:
            run.main(["https://youtu.be/AAAAAAAAAAA", "--batch", "0"]); raise AssertionError("harusnya error")
        except SystemExit as e:
            assert e.code == 2
        assert run.main(["--file", str(TMP / "tidak_ada.txt")]) == 1
    return "--batch 0 ditolak, file antrian salah → pesan jelas"

def t_edge_utf8_redirect():
    raw = io.BytesIO()
    fake_out = io.TextIOWrapper(raw, encoding="cp1252")
    with mock.patch("sys.stdout", fake_out), mock.patch("sys.stderr", io.StringIO()):
        config.force_utf8_output()
        print("✅ 🎬 ⚠ selesai")
        sys.stdout.flush()
    assert "✅" in raw.getvalue().decode("utf-8")
    return "output dialihkan ke file (cp1252) tidak crash karena emoji"

def t_edge_lock():
    lp = TMP / ".run.lock"
    a = run.acquire_lock(lp); assert a is not None
    b = run.acquire_lock(lp); assert b is None, "run kedua harus ditolak"
    a.close()
    c = run.acquire_lock(lp); assert c is not None, "kunci harus lepas setelah run pertama selesai"
    c.close()
    return "run ganda ditolak, kunci lepas otomatis"

def t_edge_av19_compat():
    import av
    from faster_whisper.audio import decode_audio
    wav = TMP / "av.wav"
    import wave, numpy as np
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
    real_open = av.open
    while getattr(real_open, "_compat_patched", False):   # ambil fungsi asli bila sudah dipasangi patch
        real_open = real_open.__wrapped__
    av.open = real_open
    def strict_open(*a, **k):          # tiru PyAV 19: tolak metadata_errors
        if "metadata_errors" in k:
            raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
        return real_open(*a, **k)
    import transcriber
    try:
        with mock.patch.object(av, "open", strict_open), mock.patch.object(av, "__version__", "19.0.1"):
            try:
                decode_audio(str(wav)); raise AssertionError("simulasi PyAV 19 harus gagal tanpa patch")
            except TypeError:
                pass
            assert transcriber.patch_av_compat() is True
            assert decode_audio(str(wav)).shape == (16000,)
        with mock.patch.object(av, "__version__", "18.1.0"):
            assert transcriber.patch_av_compat() is False
    finally:
        av.open = real_open
    req = Path("requirements.txt").read_text()
    assert "av>=11,<19" in req
    return "error metadata_errors (PyAV 19) direproduksi lalu diatasi; versi dikunci <19"

for name, fn in [("URL dengan kutip/kurung/koma", t_edge_clean_url),
                 ("Encoding file: ANSI, BOM, CRLF, Arab, kosong", t_edge_file_encodings),
                 ("Playlist rusak/kosong tidak menghentikan antrian", t_edge_playlist_error_continues),
                 ("Video live/premiere tidak diunduh", t_edge_live_video),
                 ("Jalan ulang tanpa internet dari cache", t_edge_offline_rerun),
                 ("Audio 0 byte diabaikan", t_edge_zero_byte_cache),
                 ("Nama terlarang Windows", t_edge_reserved_names),
                 ("Path panjang Windows", t_edge_long_path),
                 ("Frasa halusinasi khas Whisper", t_edge_frasa_curiga),
                 ("Transkrip kosong", t_edge_empty_transcript),
                 ("--force membersihkan file lama", t_edge_force_cleans_old_files),
                 ("--force gagal lalu berhasil", t_edge_force_fail_then_success),
                 ("Model gagal dimuat", t_edge_model_load_failure),
                 ("Ctrl+C di tengah antrian", t_edge_ctrl_c),
                 ("Validasi argumen CLI", t_edge_cli_validation),
                 ("Output UTF-8 saat dialihkan", t_edge_utf8_redirect),
                 ("Kunci run ganda", t_edge_lock),
                 ("Kompatibilitas PyAV 19 (metadata_errors)", t_edge_av19_compat)]:
    test(f"Edge: {name}", fn)

# ═════════════════════════════════════════════════════════════════════
group("9. MODEL SUNGGUHAN (opsional — butuh unduh model)")

def t_real_model():
    try:
        from faster_whisper import WhisperModel
        import numpy as np
        m = WhisperModel("tiny", device="cpu", compute_type="int8")
    except Exception as e:
        return f"SKIP: model tidak bisa diunduh di lingkungan ini ({type(e).__name__})"
    import transcriber
    t = transcriber.Transcriber.__new__(transcriber.Transcriber)
    t.model, t.pipeline, t.model_name, t.device, t.compute_type, t.batch_size = m, None, "tiny", "cpu", "int8", 1
    wav = TMP / "silence.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(np.zeros(16000 * 5, dtype=np.int16).tobytes())
    r = t.transcribe(wav, hotwords="thaharah")
    assert r["durasi_audio"] == 5.0
    return f"model tiny jalan end-to-end, {len(r['segments'])} segmen pada audio hening (VAD)"

test("faster-whisper sungguhan (tiny, CPU)", t_real_model)


# ═════════════════════════════════════════════════════════════════════
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'═'*60}\n  LAPORAN HASIL EVAL\n{'═'*60}")
for status, name, detail in results:
    print(f"{status}  {name}\n        {detail}")
p = sum(r[0] == PASS for r in results); f = sum(r[0] == FAIL for r in results); w = sum(r[0] == WARN for r in results)
print(f"\n{'─'*60}\n  Total: {len(results)}   PASS: {p}   FAIL: {f}   WARN: {w}\n{'─'*60}")
sys.exit(1 if f else 0)
