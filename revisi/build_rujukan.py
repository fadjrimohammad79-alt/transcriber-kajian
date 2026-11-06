#!/usr/bin/env python3
"""Bangun rujukan ringkas (mushaf + Riyadhush Shalihin) dari dataset sumber terbuka.
Pakai:  python build_rujukan.py --quran-dir <quran-json/dist> --hadith-json <riyad_assalihin.json> --keluar rujukan/
Sumber & lisensi: lihat rujukan/SUMBER.md"""
import argparse, json, os
ap = argparse.ArgumentParser()
ap.add_argument('--quran-dir', required=True)
ap.add_argument('--hadith-json', required=True)
ap.add_argument('--keluar', default='rujukan')
a = ap.parse_args()
L = lambda p: json.load(open(p, encoding='utf-8'))
ar = L(os.path.join(a.quran_dir, 'quran.json'))
tr = L(os.path.join(a.quran_dir, 'quran_transliteration.json'))
idn = L(os.path.join(a.quran_dir, 'quran_id.json'))
surat, ayat = [], {}
for c_ar, c_tr, c_id in zip(ar, tr, idn):
    n = c_ar['id']
    surat.append({'no': n, 'arab': c_ar['name'], 'nama': c_tr['transliteration'],
                  'arti': c_id['translation'], 'jumlah_ayat': c_ar['total_verses']})
    ayat[str(n)] = [{'n': v['id'], 'ar': v['text'], 'lat': t['transliteration'], 'id': i['translation']}
                    for v, t, i in zip(c_ar['verses'], c_tr['verses'], c_id['verses'])]
h = L(a.hadith_json)
OFFSET_DIVERSE = 1217   # kitab "Miscellany": nomor_lokal = idInBook - 1217 (terverifikasi 9/9 pada Bab Taubat)
had = [{'id_in_book': x['idInBook'], 'arab': x['arabic'], 'rawi_en': x['english'].get('narrator', ''),
        'teks_en': x['english'].get('text', ''),
        'no_lokal': (x['idInBook'] - OFFSET_DIVERSE) if x['idInBook'] > OFFSET_DIVERSE else None}
       for x in h['hadiths']]
os.makedirs(a.keluar, exist_ok=True)
for nm, obj in (('surat.json', surat), ('quran_ringkas.json', ayat), ('riyadhush_shalihin_ringkas.json', had)):
    json.dump(obj, open(os.path.join(a.keluar, nm), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('surat', len(surat), '| ayat', sum(len(v) for v in ayat.values()), '| hadis', len(had))
