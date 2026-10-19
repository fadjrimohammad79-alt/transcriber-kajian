"""
koreksi.py — koreksi otomatis salah eja/salah dengar dari kamus koreksi.txt.

Dipakai otomatis oleh run.py setelah transkripsi. Setiap perubahan dicatat di field segmen
`revisi` (lama, baru, alasan, oleh="koreksi.txt"), format sama dengan revisi QC manual.

Terapkan ke hasil lama (file asli tidak diubah, hasil ke folder <folder>_koreksi):
    python koreksi.py hasil\\Niat
    python koreksi.py hasil\\Niat --out hasil\\Niat_koreksi
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import config

# Batas kata: huruf/angka, tanda hubung, dan apostrof dianggap bagian kata,
# supaya "Zahabi" tidak cocok di dalam "al-Zahabi" dan "Dhahabi" tidak di dalam "adz-Dhahabi".
_APOS = "'’‘`"
_KIRI, _KANAN = rf"(?<![\w{_APOS}\-])", rf"(?![\w{_APOS}\-])"


def _pola_kata(kata: str) -> str:
    """Escape satu kata; semua jenis apostrof (' ’ ‘ `) dianggap sama."""
    return "".join(f"[{_APOS}]" if c in _APOS else re.escape(c) for c in kata)


@dataclass
class Aturan:
    lama: str
    baru: str
    alasan: str
    pola: re.Pattern


def parse_koreksi(teks: str) -> list[Aturan]:
    """Baca isi kamus. Baris: 'salah => benar  # alasan'. Baris # dan kosong diabaikan."""
    aturan, seen = [], set()
    for no, line in enumerate(teks.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        isi, _, alasan = line.partition("#")
        lama, sep, baru = isi.partition("=>")
        lama, baru = lama.strip(), baru.strip()
        if not sep or not lama or not baru:
            print(f"⚠️  koreksi.txt baris {no} diabaikan (format: salah => benar  # alasan): {line[:60]}")
            continue
        pola = re.compile(_KIRI + r"\s+".join(map(_pola_kata, lama.split())) + _KANAN, re.IGNORECASE)
        if pola.search(baru):
            print(f"⚠️  koreksi.txt baris {no} diabaikan: '{lama}' ada di dalam '{baru}' (akan berulang)")
            continue
        if lama.lower() in seen:
            print(f"⚠️  koreksi.txt baris {no} diabaikan: '{lama}' sudah ada di baris sebelumnya")
            continue
        seen.add(lama.lower())
        aturan.append(Aturan(lama, baru, alasan.strip() or "koreksi kamus", pola))
    aturan.sort(key=lambda a: -len(a.lama))   # frasa terpanjang lebih dulu
    return aturan


def load_koreksi(path: Path = config.FILE_KOREKSI) -> list[Aturan]:
    if not Path(path).exists():
        return []
    return parse_koreksi(config.read_text_any(path))


def terapkan(segments: list[dict], aturan: list[Aturan]) -> int:
    """Ganti teks segmen sesuai kamus, catat di s['revisi']. Return jumlah penggantian.
    Satu kali lewat pada teks asli: hasil sebuah aturan tidak diproses lagi oleh aturan lain
    (A => B dan B => C tidak berantai, catatan 'revisi' tidak memuat teks perantara).
    Aturan berhuruf kecil yang cocok dengan teks berawalan kapital menghasilkan pengganti berawalan kapital."""
    if not aturan:
        return 0
    # urutan aturan = prioritas pada posisi yang sama (kamus sudah terurut frasa terpanjang lebih dulu)
    gabung = re.compile("|".join(f"(?P<r{n}>{a.pola.pattern})" for n, a in enumerate(aturan)), re.IGNORECASE)
    total = 0
    for s in segments:
        teks = s.get("text") or ""
        catatan = []

        def ganti(m, catatan=catatan):
            a = aturan[int(m.lastgroup[1:])]
            baru = a.baru
            # aturan ditulis huruf kecil + teks aslinya berawalan kapital (awal kalimat): kapital dipertahankan
            if m.group(0)[:1].isupper() and a.lama[:1].islower() and baru[:1].islower():
                baru = baru[:1].upper() + baru[1:]
            catatan.append({"lama": m.group(0), "baru": baru, "alasan": a.alasan, "oleh": "koreksi.txt"})
            return baru

        baru = gabung.sub(ganti, teks)
        if catatan:
            s.setdefault("revisi", []).extend(catatan)
            total += len(catatan)
        s["text"] = baru
    return total


def koreksi_folder(folder: Path, out: Path, aturan: list[Aturan]) -> list[tuple[str, int]]:
    """Terapkan kamus ke semua .json hasil di folder; tulis JSON+SRT+TXT baru ke out."""
    from output import to_srt, to_txt
    from quality import flag_segments, summarize

    out.mkdir(parents=True, exist_ok=True)
    laporan = []
    for f in sorted(folder.glob("*.json")):
        try:
            doc = config.read_json(f)
        except (ValueError, OSError) as e:
            print(f"⚠️  {f.name} dilewati: {type(e).__name__}: {e}")
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("segments"), list) or "video" not in doc:
            continue
        segs = doc["segments"]
        n = terapkan(segs, aturan)
        tr = doc.setdefault("transkripsi", {})
        tr["koreksi_otomatis"] = tr.get("koreksi_otomatis", 0) + n
        nama = config.QC_NAMA_PEMBICARA or [doc["video"].get("channel") or ""]
        flag_segments(segs, tr.get("prompt", ""), nama)
        doc["kualitas"] = summarize(segs, doc.get("kualitas", {}).get("durasi_detik", 0))
        (out / f.name).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / f.with_suffix(".srt").name).write_text(to_srt(segs), encoding="utf-8")
        (out / f.with_suffix(".txt").name).write_text(to_txt(doc["video"], segs), encoding="utf-8")
        laporan.append((f.name, n))
    return laporan


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Terapkan kamus koreksi.txt ke hasil transkrip yang sudah ada")
    p.add_argument("folder", help="Folder berisi .json hasil, mis. hasil\\Niat")
    p.add_argument("--out", help="Folder keluaran (default: <folder>_koreksi). File asli tidak diubah.")
    p.add_argument("--kamus", default=str(config.FILE_KOREKSI), help="File kamus (default koreksi.txt)")
    args = p.parse_args(argv)
    config.force_utf8_output()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"❌ Folder tidak ada: {folder}")
        return 1
    out = Path(args.out).resolve() if args.out else folder.with_name(folder.name + "_koreksi")
    if out == folder:
        print("❌ --out tidak boleh sama dengan folder asli (file asli tidak diubah).")
        return 1
    aturan = load_koreksi(Path(args.kamus))
    if not aturan:
        print(f"❌ Kamus kosong atau tidak ada: {args.kamus}")
        return 1
    laporan = koreksi_folder(folder, out, aturan)
    for nama, n in laporan:
        print(f"  {'🩹' if n else '  '} {n:3d}  {nama[:70]}")
    print(f"✅ {sum(n for _, n in laporan)} koreksi di {len(laporan)} file → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
