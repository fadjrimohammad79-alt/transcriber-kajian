#!/usr/bin/env python3
"""ayat_penuh.py - (UJI, setelah latin_ke_arab.py) tulis AYAT PENUH + ARTINYA untuk setiap penyebutan surah dan ayat Alquran.
Keputusan pemilik 2026-11-06: bila ada surah dan ayat, tulis langsung satu ayat penuh (berharakat) dan artinya (Kemenag),
meski ustaz membacanya separuh-separuh. Ayat diambil dari dalil_inventaris.json (butir quran yang sudah terselesaikan) dan
teks resmi quran_ringkas.json. Cara kerja per segmen:
  1) lewati bila ayat penuh sudah ada di segmen (misalnya hasil perbaikan manual);
  2) buang potongan Arab yang cocok dengan ayat itu (bacaan separuh);
  3) sisipkan "<ayat penuh> Artinya: "<terjemah>"." sesudah kalimat yang memuat penyebutan ayat.
Terjemahan lisan ustaz dan transliterasi Latin TIDAK dihapus (aman, tidak ada isi yang hilang).
Folder masukan DIUBAH di tempat (folder turunan _uji_arab, bisa dibangun ulang dari awal).
Pakai (dari akar repo): python revisi/ayat_penuh.py --masuk hasil/<Bab>_uji_arab [--dalil hasil/<Bab>_revisi/dalil_inventaris.json]"""
import argparse, sys, os, re, json, glob, collections
_ap = argparse.ArgumentParser()
_ap.add_argument('--masuk', required=True)
_ap.add_argument('--dalil', default=None, help='dalil_inventaris.json (default: <masuk dengan _uji_arab diganti _revisi>/dalil_inventaris.json)')
_ap.add_argument('--rujukan', default='revisi/rujukan')
ARGS = _ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revisi_batch as rb
from difflib import SequenceMatcher
Q = json.load(open(os.path.join(ARGS.rujukan, 'quran_ringkas.json'), encoding='utf-8'))
SURAT = json.load(open(os.path.join(ARGS.rujukan, 'surat.json'), encoding='utf-8'))
dalil_path = ARGS.dalil or os.path.join(re.sub(r'_uji_arab/?$', '_revisi', ARGS.masuk.rstrip('/\\')), 'dalil_inventaris.json')
DAL = json.load(open(dalil_path, encoding='utf-8'))
STATUS_OK = {'terselesaikan-dari-penyebutan', 'terverifikasi-arab-cocok', 'terkenali-dari-bacaan-arab', 'diwarisi-dari-surah-sebelumnya'}
POR = collections.defaultdict(list)
for b in DAL['butir']:
    if b.get('jenis') == 'quran' and b.get('status') in STATUS_OK and b.get('terselesaikan'):
        POR[(b['video_id'], b['seg'])].append(b)

def terjemah(t):
    return re.sub(r',?(?<=[A-Za-z,])\d+\)', ')', t).strip()   # buang penanda catatan kaki Kemenag (mis. 'orang382)' / 'kaumnya,424)')

def ayat_penuh(sn, a1, a2):
    ar, tj = [], []
    for a in range(a1, a2 + 1):
        d = Q[str(sn)][a - 1]
        ar.append(d['ar'].strip()); tj.append(terjemah(d['id']))
    return ' '.join(ar), ' '.join(tj)

def sudah_ada(text, ar):
    nt = rb.norm_arab(text); na = rb.norm_arab(ar)
    return bool(na) and na in nt

def potongan_cocok(run, words):
    rn = rb.norm_arab(run); n = len(rn.split())
    if n < 2: return False
    best = 0
    for i in range(len(words)):
        for j in range(i, min(len(words), i + n + 2)):
            best = max(best, SequenceMatcher(None, rn, rb.norm_arab(' '.join(words[i:j + 1])), autojunk=False).ratio())
    return best >= 0.75

def sisip(text, a1, blok):
    pos = None
    for rx in (r'ayat(?:\s+ke)?[-\s]*%d\b' % a1, r'(?<=[A-Za-z\'])[\s:]+%d\b' % a1):
        m = re.search(rx, text)
        if m: pos = m.end(); break
    if pos is None: return (text.rstrip().rstrip(',;:') + ' ' + blok).strip()
    m = re.search(r'[.!?](?=\s|$)', text[pos:])
    k = pos + m.end() if m else len(text.rstrip())
    if not m: text = text[:k].rstrip(',;: ') ; k = len(text)
    return (text[:k].rstrip() + ' ' + blok + (' ' + text[k:].lstrip() if text[k:].strip() else '')).strip()

total = collections.Counter(); laporan = []
for f in sorted(glob.glob(os.path.join(ARGS.masuk, '*.json'))):
    try: V = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not (isinstance(V, dict) and 'segments' in V and 'video' in V): continue
    vid = V['video']['video_id']; ubah = 0; TERAKHIR = {}   # (surah, ayat) -> id segmen terakhir yang memuat ayat penuh
    for s in V['segments']:
        butir = POR.get((vid, s['id']))
        if not butir: continue
        t = s['text']; rec = []; terlihat = set()
        for b in butir:
            r = b['terselesaikan']; sn, a1 = r['surah_no'], r['ayat_awal']; a2 = r.get('ayat_akhir') or a1
            if (sn, a1, a2) in terlihat: continue
            terlihat.add((sn, a1, a2))
            ar, tj = ayat_penuh(sn, a1, a2)
            if sudah_ada(t, ar): TERAKHIR[(sn, a1, a2)] = s['id']; total['sudah-ada'] += 1; continue
            if s['id'] - TERAKHIR.get((sn, a1, a2), -99) <= 3: total['dekat-duplikat'] += 1; continue   # ayat yang sama baru saja ditulis penuh
            TERAKHIR[(sn, a1, a2)] = s['id']
            words = ar.split()
            buang = [m for m in rb.RUN_ARAB.finditer(t) if potongan_cocok(m.group(0).strip(), words)]
            for m in sorted(buang, key=lambda m: -m.start()):
                t = t[:m.start()].rstrip() + ' ' + t[m.end():].lstrip()
            blok = f'{ar} Artinya: "{tj}"'
            blok = blok if blok.endswith('"') else blok
            blok = blok + '.'
            t = sisip(t, a1, blok)
            t = re.sub(r'\s+', ' ', t).replace(' .', '.').strip()
            t = re.sub(r',\s*\.', '.', t); t = re.sub(r'(?<!\.)\.\.(?!\.)', '.', t)   # sisa tanda baca akibat potongan Arab dibuang
            rec.append({'surah': SURAT[sn - 1]['nama'], 'ayat': f'{a1}' + (f'-{a2}' if a2 != a1 else ''), 'potongan_arab_dibuang': len(buang)})
            total['ditulis'] += 1
            laporan.append((V['video']['judul'].split('|')[0].strip(), s['id'], rec[-1]))
        if rec:
            s.setdefault('text_sebelum_ayat_penuh', s['text']); s['text'] = t; s['ayat_penuh'] = rec; ubah += 1
    if ubah:
        V.setdefault('uji_arab', {})['ayat_penuh'] = 'Ayat penuh + artinya (Kemenag) disisipkan untuk semua penyebutan surah dan ayat (keputusan pemilik 2026-11-06).'
        json.dump(V, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        b = f[:-5]
        with open(b + '.txt', 'w', encoding='utf-8') as o:
            o.write(f"Judul  : {V['video']['judul']}\nURL    : {V['video']['url']}\nBab    : {V['video'].get('bab','')} | Kitab: {V['video'].get('kitab','')}\n\n")
            for s in V['segments']: o.write(f"[{rb.mmss(s['start'])}] {s['text']}\n")
        with open(b + '.srt', 'w', encoding='utf-8') as o:
            for n, s in enumerate(V['segments'], 1): o.write(f"{n}\n{rb.srt_waktu(s['start'])} --> {rb.srt_waktu(s['end'])}\n{s['text']}\n\n")
    print(os.path.basename(f)[:40], ubah)
with open(os.path.join(ARGS.masuk, 'LAPORAN_AYAT_PENUH.md'), 'w', encoding='utf-8') as o:
    o.write(f'# Laporan ayat penuh + artinya\n\nTotal: {dict(total)}\n\n| Video | Seg | Surah | Ayat | Potongan Arab dibuang |\n|---|---|---|---|---|\n')
    for v, sid, r in laporan: o.write(f"| {v[:40]} | {sid} | {r['surah']} | {r['ayat']} | {r['potongan_arab_dibuang']} |\n")
print(dict(total))
