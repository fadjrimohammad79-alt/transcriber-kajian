#!/usr/bin/env python3
"""cek_sinkron.py - bandingkan koreksi.txt (repo) dengan aturan tertanam skill (revisi/data).
Pakai: python revisi/cek_sinkron.py --koreksi koreksi.txt [--data revisi/data]
Tiap baris 'lama => baru' diuji: aturan skill diterapkan pada 'lama'.
  SAMA     : hasil aturan skill = 'baru' (sinkron)
  BENTROK  : aturan skill mengubah 'lama' menjadi bentuk lain dari 'baru' -> tanyakan pemilik
  BELUM    : aturan skill tidak mengubah 'lama' -> belum ada di skill (tambahkan ke data/keputusan_pemilik.tsv
             bila itu keputusan ejaan; biarkan bila itu koreksi salah-dengar khusus transkripsi)"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revisi_batch as rb

ap = argparse.ArgumentParser()
ap.add_argument('--koreksi', required=True)
ap.add_argument('--data', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
a = ap.parse_args()
R = rb.muat_aturan(a.data, False)
hasil = {'SAMA': [], 'BENTROK': [], 'BELUM': []}
for ln in open(a.koreksi, encoding='utf-8-sig'):
    s = ln.strip()
    if '=>' not in s or s.startswith('#'):
        continue
    lama, baru = [x.strip() for x in s.split('=>', 1)]
    baru = baru.split('#', 1)[0].strip()
    if not lama or not baru:
        continue
    t = rb.terapkan(lama, R['singkatan'], [], 'singkatan')
    t = rb.terapkan(t, R['kamus'], [], 'kamus')
    if t.lower() == baru.lower():
        hasil['SAMA'].append(s)
    elif t.lower() != lama.lower():
        hasil['BENTROK'].append(f'{s}   (skill menghasilkan: {t})')
    else:
        hasil['BELUM'].append(s)
for k in ('BENTROK', 'BELUM', 'SAMA'):
    print(f'== {k}: {len(hasil[k])}')
    if k != 'SAMA':
        for x in hasil[k]:
            print('  ', x)
