#!/usr/bin/env python3
"""buang_terjemah_lisan.py - (UJI, setelah ayat_penuh.py) buang terjemahan LISAN ustaz yang menduplikasi 'Artinya: "..."' (Kemenag).
Keputusan pemilik 2026-11-06. Per segmen yang memuat blok 'Artinya: "<terjemah>"': kalimat sesudah blok itu (di segmen yang sama dan
2 segmen berikutnya; kalimat ber-aksara Arab tidak pernah dibuang, berhenti di blok ayat lain) dibuang bila sebagian besar kata isinya (>= --ambang) ada di terjemah Kemenag.
Kalimat lain (penjelasan ustaz) dipertahankan. Teks lama disimpan di text_sebelum_buang_terjemah. Pakai --uji untuk melihat saja.
Pakai: python revisi/buang_terjemah_lisan.py --masuk hasil/<Bab>_uji_arab [--ambang 0.7] [--uji]"""
import argparse, glob, json, os, re, sys, collections
ap = argparse.ArgumentParser()
ap.add_argument('--masuk', required=True); ap.add_argument('--ambang', type=float, default=0.7); ap.add_argument('--uji', action='store_true')
A = ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revisi_batch as rb
STOP = set('yang dengan dan itu ini untuk pada dari kepada adalah akan atau juga karena maka tetapi tapi jadi agar supaya oleh dalam sebagai bahwa mereka kita kami saya anda'.split())
def kata(s):
    s = re.sub(r'[\u0600-\u06FF]+', ' ', s).lower().replace('-', '')
    return [w for w in re.findall(r"[a-z']+", s) if len(w) >= 4 and w not in STOP]
def cocok(w, T): return w in T or any(w[:5] == t[:5] and len(w) >= 5 for t in T)
RX = re.compile(r'Artinya: "(.*?)"(?=\.(?:\s|$))\.', re.S)
def pecah(t): return [x for x in re.split(r'(?<=[.?!])\s+', t.strip()) if x]
total = collections.Counter(); log = []
for f in sorted(glob.glob(os.path.join(A.masuk, '*.json'))):
    try: V = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not (isinstance(V, dict) and 'segments' in V): continue
    S = V['segments']; ubah = False
    for i, s in enumerate(S):
        if 'ayat_penuh' not in s: continue
        blok = list(RX.finditer(s['text']))
        if not blok: continue
        T = set(kata(blok[-1].group(1)))
        for j in range(i, min(len(S), i + 3)):
            if j > i and 'ayat_penuh' in S[j]: break
            t = S[j]['text']
            sisa = t[blok[-1].end():] if j == i else t
            depan = t[:blok[-1].end()] if j == i else ''
            if j > i and 'terjemah_lisan_dibuang' in S[j]: continue
            simpan, buang = [], []
            for k in pecah(sisa):
                w = kata(k)
                skor = (sum(cocok(x, T) for x in w) / len(w)) if (len(w) >= 4 and not re.search(r'[\u0600-\u06FF]', k)) else 0
                (buang if skor >= A.ambang else simpan).append((k, round(skor, 2)))
            if not buang: continue
            baru = (depan + ' ' + ' '.join(k for k, _ in simpan)).strip()
            for k, sc in buang: log.append((V['video']['judul'].split('|')[0].strip()[:20], S[j]['id'], sc, k))
            total['kalimat'] += len(buang)
            if not A.uji:
                S[j].setdefault('text_sebelum_buang_terjemah', t); S[j]['text'] = baru
                S[j]['terjemah_lisan_dibuang'] = [k for k, _ in buang]; ubah = True
    if ubah and not A.uji:
        V.setdefault('uji_arab', {})['buang_terjemah_lisan'] = 'Terjemahan lisan ustaz yang menduplikasi terjemah Kemenag dibuang (keputusan pemilik 2026-11-06).'
        json.dump(V, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        b = f[:-5]
        with open(b + '.txt', 'w', encoding='utf-8') as o:
            o.write(f"Judul  : {V['video']['judul']}\nURL    : {V['video']['url']}\nBab    : {V['video'].get('bab','')} | Kitab: {V['video'].get('kitab','')}\n\n")
            for s in S: o.write(f"[{rb.mmss(s['start'])}] {s['text']}\n")
        with open(b + '.srt', 'w', encoding='utf-8') as o:
            for n, s in enumerate(S, 1): o.write(f"{n}\n{rb.srt_waktu(s['start'])} --> {rb.srt_waktu(s['end'])}\n{s['text']}\n\n")
_lap = os.path.join(A.masuk, 'LAPORAN_BUANG_TERJEMAH_LISAN.md')
if total['kalimat'] or not os.path.exists(_lap):   # jalan ulang tanpa perubahan tidak menimpa laporan lama
  with open(_lap, 'w', encoding='utf-8') as o:
    o.write(f"# Kalimat terjemahan lisan yang dibuang ({'UJI, belum diterapkan' if A.uji else 'diterapkan'}): {total['kalimat']}\n\n| Video | Seg | Skor | Kalimat |\n|---|---|---|---|\n")
    for v, sid, sc, k in log: o.write(f"| {v} | {sid} | {sc} | {k.replace('|','/')} |\n")
print(dict(total))
