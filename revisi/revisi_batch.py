#!/usr/bin/env python3
"""revisi_batch.py - revisi + inventaris dalil batch transkrip kajian (korpus RAG "secondbrain ustadz").

Prinsip:
  1. File asli TIDAK pernah diubah; hasil ditulis ke folder keluaran terpisah.
  2. Yang dikoreksi hanya salah-dengar/ejaan, bukan isi ucapan ustaz.
  3. Tiga tingkat tindakan:
       A = otomatis aman (kamus KBBI terverifikasi + singkatan ditulis lengkap)
       B = otomatis kontekstual (selalu dicatat di `revisi`, dapat dibalik)
       C = tidak diubah; masuk titik_dengar.md (perlu didengar ulang / diputuskan manusia)
  4. Dalil diverifikasi terhadap rujukan otoritatif sebagai LAPISAN TERPISAH (dalil_inventaris.json),
     bukan menimpa ucapan ustaz. Derajat hadis dan hukum bukan wewenang skrip ini.
  5. Aksara Arab dan kutipan Latin Arab tidak diubah.

Pakai:
  python revisi_batch.py --masuk hasil/Taubat --keluar hasil/Taubat_revisi
        [--data revisi/data] [--rujukan revisi/rujukan] [--termasuk-belum-verifikasi]
"""
import argparse, csv, glob, json, os, re, sys, collections, datetime
from difflib import SequenceMatcher

VERSI = '1.0'
ARAB = r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'
RUN_ARAB = re.compile(ARAB + r'(?:[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s\u200c\u200f]*' + ARAB + r')?')


# ------------------------------------------------------------------ util teks
def jaga_huruf(src, dst):
    if len(src) > 1 and src.isupper():
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def awal_kalimat(teks, pos):
    pre = teks[:pos].rstrip()
    return pre == '' or pre[-1] in '.?!\u2026'


def norm_arab(s):
    s = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u0640\u200c\u200f]', '', s)
    s = re.sub('[\u0623\u0625\u0622\u0671]', '\u0627', s)
    s = s.replace('\u0649', '\u064A').replace('\u0629', '\u0647').replace('\u0624', '\u0648').replace('\u0626', '\u064A')
    s = re.sub(r'[^\u0621-\u064A\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def kunci_latin(s):
    return re.sub(r'[^a-z]', '', s.lower())


ARTIKEL = ('adh', 'ath', 'ash', 'asy', 'al', 'an', 'ar', 'as', 'at', 'ad', 'az')


def varian_kunci(nama):
    k = kunci_latin(nama)
    v = {k}
    for a in ARTIKEL:
        if k.startswith(a) and len(k) - len(a) >= 2:
            v.add(k[len(a):])
    if k.startswith('ali') and len(k) > 5:
        v.add(k[3:])
    return v


def rangka_latin(s):
    s = s.lower()
    for a, b in (('dh', 'd'), ('th', 't'), ('kh', 'k'), ('sh', 's'), ('gh', 'g'), ('ts', 's'), ('dz', 'd'),
                 ('sy', 's'), ('aa', 'a'), ('ii', 'i'), ('uu', 'u'), ('q', 'k'), ('z', 'd'), ('j', 'z')):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z]", '', s)
    s = re.sub(r'[aeiou]', '', s)
    return re.sub(r'(.)\1+', r'\1', s)


def kapital_surat(nama):
    """Nama surah: huruf awal tiap bagian (dipisah tanda hubung/spasi) kapital, mis. 'al-anfal' -> 'Al-Anfal', 'Ash-shura' -> 'Ash-Shura'."""
    return re.sub(r"(^|[-\s])([a-z])", lambda m: m.group(1) + m.group(2).upper(), nama)


def mmss(t):
    t = int(t)
    return f'{t // 3600:d}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600 else f'{t // 60:d}:{t % 60:02d}'


def srt_waktu(t):
    ms = int(round((t - int(t)) * 1000))
    t = int(t)
    return f'{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d},{ms:03d}'


# ------------------------------------------------------------------ muat aturan
def baca_tsv(path):
    baris = []
    if not os.path.exists(path):
        return baris
    for ln in open(path, encoding='utf-8'):
        ln = ln.rstrip('\n').replace('<TAB>', '\t')   # '<TAB>' = penanda tab agar aman disalin lewat teks
        if not ln.strip() or ln.startswith('#'):
            continue
        baris.append(ln.split('\t'))
    return baris


def muat_aturan(dir_data, termasuk_belum):
    R = {'kamus': [], 'singkatan': [], 'kontekstual': []}
    files = [('keputusan_pemilik.tsv', 'keputusan-pemilik'), ('kamus_ejaan_kbbi.tsv', 'terverifikasi')]
    if termasuk_belum:
        files.append(('kamus_belum_diverifikasi.tsv', 'belum-diverifikasi'))
    for fn, _ in files:
        for r in baca_tsv(os.path.join(dir_data, fn)):
            r += [''] * (6 - len(r))
            R['kamus'].append({'id': r[0], 'rx': re.compile(r[1], re.I), 'ganti': r[2], 'status': r[3],
                               'sumber': r[4], 'tingkat': 'A'})
    for r in baca_tsv(os.path.join(dir_data, 'singkatan.tsv')):
        r += [''] * (5 - len(r))
        R['singkatan'].append({'id': r[0], 'rx': re.compile(r[1]), 'ganti': r[2],
                               'syarat': re.compile(r[3], re.I) if r[3] else None, 'tingkat': 'A'})
    for r in baca_tsv(os.path.join(dir_data, 'aturan_kontekstual.tsv')):
        R['kontekstual'].append({'id': r[0], 'rx': re.compile(r[1]), 'ganti': r[2], 'tingkat': r[3], 'alasan': r[4]})
    return R


# ------------------------------------------------------------------ penerapan aturan
def terapkan(teks, rules, edits, mode):
    """Satu putaran aturan; mencatat setiap perubahan ke `edits`."""
    for ru in rules:
        def ganti(m, ru=ru):
            lama = m.group(0)
            if mode == 'kamus':
                if ru['id'] == 'jemaah' and re.search(r'(?:\bwal|\bwa al|\bal)[- ]?$', m.string[max(0, m.start() - 8):m.start()], re.I):
                    return lama
                if ru['id'] == 'saleh' and (
                        re.search(r'\b(?:bin|ibn|ibnu|binti|abu|syaikh|syekh|syeikh|sheikh)\s+$', m.string[max(0, m.start() - 14):m.start()], re.I)
                        or re.match(r'\s+(?:al-|ut|us)', m.string[m.end():m.end() + 6], re.I)):
                    return lama          # bagian nama orang (mis. Muhammad bin Shalih al-Utsaimin): jangan disentuh
                baru = m.expand(ru['ganti'])
                baru = baru if ru['ganti'][:1].isupper() else jaga_huruf(lama, baru)
                alasan = ('keputusan pemilik korpus (bukan KBBI)' if ru['status'].startswith('keputusan') else f"ejaan baku KBBI ({ru['status']})")
            elif mode == 'singkatan':
                if ru['syarat']:
                    ctx = m.string[max(0, m.start() - 60):m.end() + 60]
                    if not ru['syarat'].search(ctx):
                        return lama
                baru = ru['ganti']
                dot = m.group(1) if m.lastindex else ''
                sisa = m.string[m.end():]
                if dot:
                    # titik milik singkatan dibuang bila kalimat berlanjut (huruf kecil); selain itu titik akhir kalimat
                    baru += '' if re.match(r'\s+[a-z]', sisa) else '.'
                if awal_kalimat(m.string, m.start()):
                    baru = baru[:1].upper() + baru[1:]
                alasan = 'singkatan ditulis lengkap'
            else:
                baru = m.expand(ru['ganti'])
                alasan = ru['alasan']
            if baru == lama:
                return lama
            edits.append({'lama': lama, 'baru': baru, 'alasan': alasan, 'oleh': f"revisi_batch:{ru['id']}",
                          'tingkat': ru['tingkat']})
            return baru
        teks = ru['rx'].sub(ganti, teks)
    return teks


# ------------------------------------------------------------------ rujukan
class Rujukan:
    def __init__(self, d):
        L = lambda f: json.load(open(os.path.join(d, f), encoding='utf-8'))
        self.surat = L('surat.json')
        self.ayat = L('quran_ringkas.json')
        self.hadis = L('riyadhush_shalihin_ringkas.json')
        self.kunci_surat = [(s, varian_kunci(s['nama'])) for s in self.surat]
        self.pilihan_nama = {}   # ejaan ucapan -> nomor surah (diputuskan lewat isi), dipakai ulang antar-video
        # indeks trigram kata -> {(surah, ayat)}
        self.idx_q = collections.defaultdict(set)
        self.norm_q = {}
        for sn, lst in self.ayat.items():
            for v in lst:
                w = norm_arab(v['ar']).split()
                self.norm_q[(int(sn), v['n'])] = ' '.join(w)
                for i in range(len(w) - 2):
                    self.idx_q[tuple(w[i:i + 3])].add((int(sn), v['n']))
        self.idx_h = collections.defaultdict(set)
        self.norm_h = {}
        for h in self.hadis:
            w = norm_arab(h['arab']).split()
            self.norm_h[h['id_in_book']] = ' '.join(w)
            for i in range(len(w) - 2):
                self.idx_h[tuple(w[i:i + 3])].add(h['id_in_book'])

    def cari_surat(self, token):
        kt = varian_kunci(token)
        terbaik = (0.0, None)
        for s, ks in self.kunci_surat:
            r = max(SequenceMatcher(None, a, b).ratio() for a in kt for b in ks if len(a) >= 2 and len(b) >= 2) \
                if any(len(a) >= 2 for a in kt) else 0
            if r > terbaik[0]:
                terbaik = (r, s)
        return terbaik

    def cari_surat_semua(self, token):
        kt = [a for a in varian_kunci(token) if len(a) >= 2]
        hasil = []
        for sr, ks in self.kunci_surat:
            r = max((SequenceMatcher(None, a, b).ratio() for a in kt for b in ks if len(b) >= 2), default=0.0)
            hasil.append((r, sr))
        hasil.sort(key=lambda x: -x[0])
        return hasil

    @staticmethod
    def _cover(run, tgt):
        sm = SequenceMatcher(None, run, tgt, autojunk=False)
        return sum(b.size for b in sm.get_matching_blocks()) / max(1, len(run))

    def cocok_quran(self, run_norm):
        w = run_norm.split()
        if len(w) < 3 or len(run_norm) < 12:
            return None
        cand = set()
        for i in range(len(w) - 2):
            cand |= self.idx_q.get(tuple(w[i:i + 3]), set())
        if not cand:
            return None
        terbaik = None
        for (s, a) in cand:
            maks = len(self.ayat[str(s)])
            for st in (a - 1, a):
                for pj in (1, 2, 3):
                    aw = [x for x in range(st, st + pj) if 1 <= x <= maks]
                    if not aw or aw[0] != st:
                        continue
                    teks = ' '.join(self.norm_q[(s, x)] for x in aw)
                    c = self._cover(run_norm, teks)
                    # utamakan cakupan tinggi, lalu jendela terpendek
                    key = (round(c, 3), -len(aw))
                    if terbaik is None or key > terbaik[0]:
                        terbaik = (key, s, aw[0], aw[-1], c)
        if terbaik and terbaik[4] >= 0.6:
            return {'surah': terbaik[1], 'ayat_awal': terbaik[2], 'ayat_akhir': terbaik[3], 'cakupan': round(terbaik[4], 3)}
        return None

    def cocok_hadis(self, run_norm):
        w = run_norm.split()
        if len(w) < 4:
            return None
        cand = set()
        for i in range(len(w) - 2):
            cand |= self.idx_h.get(tuple(w[i:i + 3]), set())
        terbaik = None
        for hid in cand:
            c = self._cover(run_norm, self.norm_h[hid])
            if terbaik is None or c > terbaik[1]:
                terbaik = (hid, c)
        if terbaik and terbaik[1] >= 0.6:
            return {'id_in_book': terbaik[0], 'cakupan': round(terbaik[1], 3)}
        return None


# ------------------------------------------------------------------ pemindai dalil
RX_SURAT = re.compile(r'\b([Ss]ur(?:at|ah))\s+', re.U)
RX_ANGKA = re.compile(r'^\s*[,.]?\s*(?:ayat\s*)?(?:ke-?\s*)?(\d{1,3})(?:\s*(?:-|sampai|hingga|dan)\s*(\d{1,3}))?(?![\d])', re.I)
RX_AYAT_SAJA = re.compile(r'\bayat\s+(?:ke-?\s*)?(\d{1,3})(?![\d])', re.I)
RX_PENYEBUT = re.compile(
    r"\b(Allah(?:\s+subhanahu wa ta'ala)?\s+(?:berfirman|mengatakan|menyatakan)|firman\s+Allah|"
    r"(?:Nabi|Rasulullah|Rasul)(?:\s+shallallahu 'alaihi wa sallam)?\s+(?:bersabda|bersabda,|mengatakan|bersabda)|"
    r"sabda\s+(?:Nabi|Rasul)|dalam\s+(?:sebuah\s+)?hadi(?:s|th|ts)|hadi(?:s|th|ts)\s+riwayat)", re.I)
RX_RAWI = re.compile(r"\b(?:riwayat|diriwayatkan\s+oleh|HR\.?)\s+(?:Imam\s+)?(Bukhari|Muslim|Ahmad|Tirmidzi|Turmudzi|Abu\s+Daud|Abu\s+Dawud|Nasa'?i|An-Nasa'?i|Ibnu\s+Majah|Malik|Darimi|Baihaqi|Thabrani)", re.I)
RX_ULAMA = re.compile(r"\b(?:kata|ucapan|ungkapan|menurut|dikatakan\s+oleh)\s+(?:para\s+ulama\s+seperti\s+)?((?:Al-)?(?:Imam|Syaikh|Syekh|Ibnu|Ibn)\s+[A-Z][\w'\u2019-]+(?:\s+[A-Z][\w'\u2019-]+)?)")
RX_HADIS_NO = re.compile(r"\b(?:hadis|hadits|hadith)\w*\s+(?:nomor|nomer|no\.?|ke-?|yang\s+ke-?)\s*(\d{1,3})\b", re.I)


def pindai_surat(teks, rj, edits, terapkan_koreksi=True):
    """Kembalikan (teks_baru, daftar_mention). Mengganti 'surat'->'surah' hanya bila nama surah terselesaikan."""
    hasil, mention, out, pos = [], [], [], 0
    for m in RX_SURAT.finditer(teks):
        if m.start() < pos:
            continue
        sisa = teks[m.end():m.end() + 60]
        # token kandidat nama: hingga 3 token, berhenti di 'ayat'/angka
        toks = []
        for t in re.finditer(r"[A-Za-z'\u2019`\-]+", sisa):
            if t.group(0).lower() in ('ayat', 'ke', 'nomor'):
                break
            if re.search(r'\d', sisa[max(0, t.start() - 2):t.start()]):
                break
            toks.append(t)
            if len(toks) == 3:
                break
        terbaik = (0.0, None, 0, 0)
        ties = []
        for st in range(0, min(2, len(toks))):          # boleh melewati <=1 kata sela (mis. 'surat apa? An-Nisa')
            for n in range(st + 1, len(toks) + 1):
                if n - st > 2 and st > 0:
                    continue
                frasa = sisa[toks[st].start():toks[n - 1].end()]
                if frasa.lower().strip('-') in ('ayat', 'apa', 'yang', 'ini', 'itu', 'dan', 'di', 'ke'):
                    continue
                semua = rj.cari_surat_semua(frasa)
                r, s = semua[0]
                if r > terbaik[0] + 1e-9:
                    terbaik = (r, s, n, st)
                    ties = [x[1] for x in semua if r - x[0] <= 0.04]
        if not terbaik[1] or terbaik[0] < 0.78:
            continue
        r, s, n, st = terbaik
        awal_nama = m.end() + toks[st].start()
        akhir_nama = m.end() + toks[n - 1].end()
        asli_nama = teks[awal_nama:akhir_nama]
        mt = RX_ANGKA.match(teks[akhir_nama:akhir_nama + 25])
        a1 = int(mt.group(1)) if mt else None
        a2 = int(mt.group(2)) if mt and mt.group(2) else None
        sama = kunci_latin(asli_nama) in varian_kunci(s['nama']) or kunci_latin(asli_nama) == kunci_latin(s['nama'])
        # ejaan lazim dipertahankan; ganti hanya salah-dengar jelas (kemiripan < 0,9) dan nama tidak kembar
        baru_nama = kapital_surat(asli_nama if (sama or r >= 0.9 or len(ties) > 1) else s['nama'])
        baru_kata = 'surah' if m.group(1)[0].islower() else 'Surah'
        out.append(teks[pos:m.start()])
        if terapkan_koreksi:
            if m.group(1) != baru_kata:
                edits.append({'lama': m.group(1), 'baru': baru_kata, 'alasan': 'surah (bab Al-Quran) menurut KBBI; surat = tulisan/ surah',
                              'oleh': 'revisi_batch:surah', 'tingkat': 'A'})
            if baru_nama != asli_nama and baru_nama.lower() == asli_nama.lower():
                edits.append({'lama': asli_nama, 'baru': baru_nama,
                              'alasan': 'kapitalisasi nama surah (huruf awal tiap bagian kapital, mis. Al-Anfal)',
                              'oleh': 'revisi_batch:kapital_surat', 'tingkat': 'A'})
            elif baru_nama != asli_nama:
                edits.append({'lama': asli_nama, 'baru': baru_nama,
                              'alasan': f"nama surah dinormalkan ke '{s['nama']}' (rujukan mushaf; kemiripan {round(r, 2)})",
                              'oleh': 'revisi_batch:nama_surah', 'tingkat': 'B'})
        out.append(baru_kata + teks[m.end() - (m.end() - m.start() - len(m.group(1))):awal_nama] + baru_nama)
        pos = akhir_nama
        mention.append({'surah': s['no'], 'nama': s['nama'], 'ayat_awal': a1, 'ayat_akhir': a2,
                        'ejaan_ucapan': asli_nama, 'kemiripan_nama': round(r, 3), 'kandidat': [x['no'] for x in ties],
                        'ayat_valid': (a1 is None) or (a1 <= s['jumlah_ayat'] and (a2 is None or a2 <= s['jumlah_ayat'])),
                        'jumlah_ayat_surah': s['jumlah_ayat']})
    out.append(teks[pos:])
    return ''.join(out), mention


# ------------------------------------------------------------------ proses satu video
def proses_video(path, R, rj, keluar, opsi):
    asli = json.load(open(path, encoding='utf-8-sig'))
    d = json.loads(json.dumps(asli))
    vid = d['video']['video_id']
    segs = d['segments']
    ringkas = collections.Counter()
    n_baru = 0
    contoh = collections.defaultdict(list)
    dalil, titik = [], []
    per_seg_mention = {}
    arab_per_seg = {}

    def tambah_titik(seg, kategori, alasan, saran='', tingkat='C'):
        titik.append({'video_id': vid, 'judul': d['video']['judul'], 'seg': seg['id'], 'mulai': seg['start'],
                      'link': seg.get('link', ''), 'kategori': kategori, 'alasan': alasan, 'saran': saran,
                      'cuplikan': seg['text'][:220]})

    # --- fase teks (A/B)
    for seg in segs:
        t0 = seg['text']
        edits = []
        t = t0
        t = terapkan(t, R['kontekstual'], edits, 'kontekstual')
        t, mention = pindai_surat(t, rj, edits)
        t = terapkan(t, R['singkatan'], edits, 'singkatan')
        t = terapkan(t, R['kamus'], edits, 'kamus')
        t = re.sub(r'[ \t]{2,}', ' ', t).strip()
        per_seg_mention[seg['id']] = mention
        if t != t0:
            seg['text_sebelum_batch'] = seg.get('text_sebelum_batch', t0)   # = teks input (sudah melewati koreksi.txt pipeline), BUKAN keluaran mentah Whisper
            seg['text'] = t
            seg['revisi'] = (seg.get('revisi') or []) + edits
            for e in edits:
                n_baru += 1
                ringkas[(e['tingkat'], e['oleh'])] += 1
                if len(contoh[e['oleh']]) < 4:
                    contoh[e['oleh']].append((e['lama'], e['baru'], vid, seg['id']))

    # --- sisa singkatan (butuh keputusan)
    RX_SISA = re.compile(r"\b(?:[A-Z]{2,6}(?:-nya)?|(?:[A-Za-z]\.){2,}[A-Za-z]?|wb)\b\.?")
    for seg in segs:
        for m in RX_SISA.finditer(seg['text']):
            tok = m.group(0)
            if tok.strip('.') in ('II', 'III', 'IV', 'OK'):
                continue
            tambah_titik(seg, 'singkatan-belum-terselesaikan',
                         f"Singkatan/akronim '{tok}' belum ditulis lengkap (konteks tidak cukup pasti).",
                         'Dengarkan audio / putuskan kepanjangan, lalu tambahkan ke data/singkatan.tsv')

    # --- ejaan nama orang yang tidak diubah otomatis
    for seg in segs:
        for m in re.finditer(r"\b(?:bin|ibnu?|binti)\s+(?:Soleh|Soley|Saleh|Salih|Shalih|Sholeh)\b", seg['text'], re.I):
            tambah_titik(seg, 'ejaan-nama-ulama', f"Ejaan nama '{m.group(0)}' (bagian nama, tidak diubah KBBI).",
                         "Samakan dengan ejaan nama di koreksi.txt/glosarium (mis. 'Muhammad bin Shalih al-Utsaimin') setelah dicek audio.")

    # --- aksara Arab -> pencocokan mushaf/hadis
    for seg in segs:
        runs = [m.group(0).strip() for m in RUN_ARAB.finditer(seg['text'])]
        hasil_seg = []
        for run in runs:
            rn = norm_arab(run)
            if len(rn.split()) < 3:
                continue
            q = rj.cocok_quran(rn)
            h = rj.cocok_hadis(rn)
            hasil_seg.append({'teks_ucapan': run, 'quran': q, 'hadis': h})
        if hasil_seg:
            arab_per_seg[seg['id']] = hasil_seg

    # --- mention surah/ayat -> butir dalil
    urut = [s['id'] for s in segs]
    idx = {s['id']: i for i, s in enumerate(segs)}
    sudah_arab = set()
    terakhir_surah = None

    def jendela(i, belakang=0, depan=3):
        return segs[max(0, i - belakang): i + depan + 1]

    for i, seg in enumerate(segs):
        mentions = per_seg_mention.get(seg['id'], [])
        for k, mt in enumerate(mentions):
            if len(mt.get('kandidat', [])) > 1:      # nama kembar -> putuskan lewat isi (Latin/Arab) di jendela
                lat = RUN_ARAB.sub(' ', ' '.join(x['text'] for x in jendela(i, 2, 3)))
                skor = []
                for no in mt['kandidat']:
                    sr = rj.surat[no - 1]
                    sc = 0.0
                    if mt['ayat_awal'] and mt['ayat_awal'] <= sr['jumlah_ayat']:
                        a1 = mt['ayat_awal']; a2 = mt['ayat_akhir'] or a1
                        skv = rangka_latin(' '.join(rj.ayat[str(no)][x - 1]['lat'] for x in range(a1, min(a2, a1 + 2) + 1)))
                        if skv:
                            sm = SequenceMatcher(None, rangka_latin(lat), skv, autojunk=False)
                            sc += sum(b.size for b in sm.get_matching_blocks()) / len(skv)
                    else:
                        sc -= 1
                    for sj in jendela(i, 1, 4):
                        for ar in arab_per_seg.get(sj['id'], []):
                            if ar['quran'] and ar['quran']['surah'] == no:
                                sc += 1
                    skor.append((sc, no))
                skor.sort(reverse=True)
                if len(skor) > 1 and skor[0][0] - skor[1][0] >= 0.15 and skor[0][0] >= 0.6:
                    sr = rj.surat[skor[0][1] - 1]
                    mt.update({'surah': sr['no'], 'nama': sr['nama'], 'jumlah_ayat_surah': sr['jumlah_ayat'],
                               'ayat_valid': (mt['ayat_awal'] is None) or mt['ayat_awal'] <= sr['jumlah_ayat']})
                    mt['dipilih_lewat_isi'] = [round(x[0], 2) for x in skor[:2]]
                    rj.pilihan_nama[kunci_latin(mt['ejaan_ucapan'])] = sr['no']
                else:
                    pil = rj.pilihan_nama.get(kunci_latin(mt['ejaan_ucapan']))
                    if pil and mt['ayat_awal'] and mt['ayat_awal'] <= rj.surat[pil - 1]['jumlah_ayat']:
                        sr = rj.surat[pil - 1]
                        mt.update({'surah': sr['no'], 'nama': sr['nama'], 'jumlah_ayat_surah': sr['jumlah_ayat'], 'ayat_valid': True})
                        mt['dipilih_lewat_konsistensi'] = True
                    else:
                        mt['ambigu'] = [rj.surat[n - 1]['nama'] for n in mt['kandidat']]
            terakhir_surah = (i, mt)
            butir = {
                'id': f"{vid}:{seg['id']}:q{k}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''),
                'jenis': 'quran', 'disebut_ustaz': {'surah': mt['ejaan_ucapan'], 'ayat': mt['ayat_awal'] if mt['ayat_akhir'] is None else f"{mt['ayat_awal']}-{mt['ayat_akhir']}"},
                'terselesaikan': {'surah_no': mt['surah'], 'surah': mt['nama'], 'ayat_awal': mt['ayat_awal'], 'ayat_akhir': mt['ayat_akhir']},
                'bukti': {'kemiripan_nama_surah': mt['kemiripan_nama']}, 'status': None, 'catatan': []}
            if mt.get('ambigu'):
                butir['status'] = 'surah-ambigu'
                butir['terselesaikan'] = {'kandidat': mt['ambigu']}
                butir['catatan'].append('Nama surah yang terdengar cocok dengan beberapa surah dan isi ayat tidak cukup untuk memutuskan.')
                tambah_titik(seg, 'dalil-surah-ambigu', f"Nama surah '{mt['ejaan_ucapan']}' cocok dengan {', '.join(mt['ambigu'])}.", 'Dengar audio.')
            elif mt['ayat_awal'] is None:
                butir['status'] = 'surah-tanpa-nomor-ayat'
                butir['catatan'].append('Ustaz menyebut surah tetapi nomor ayat tidak terdengar/ tidak disebut.')
                tambah_titik(seg, 'dalil-tidak-lengkap', f"Surah {mt['nama']} disebut tanpa nomor ayat.",
                             'Dengar audio untuk nomor ayat; atau biarkan sebagai rujukan tingkat surah.')
            elif not mt['ayat_valid']:
                butir['status'] = 'nomor-ayat-tidak-valid'
                butir['catatan'].append(f"Surah {mt['nama']} hanya {mt['jumlah_ayat_surah']} ayat.")
                tambah_titik(seg, 'dalil-nomor-tidak-valid', f"Nomor ayat melebihi jumlah ayat surah {mt['nama']} ({mt['jumlah_ayat_surah']}).",
                             'Dengarkan audio; kemungkinan salah dengar angka atau nama surah.')
            else:
                a1, a2 = mt['ayat_awal'], mt['ayat_akhir'] or mt['ayat_awal']
                lst = rj.ayat[str(mt['surah'])]
                if a2 < a1:
                    a1, a2 = a2, a1
                butir['teks_resmi'] = [{'n': v['n'], 'ar': v['ar'], 'terjemah_id': v['id']} for v in lst[a1 - 1:a2]]
                butir['status'] = 'terselesaikan-dari-penyebutan'
                # silang dengan aksara Arab di jendela segmen
                for sj in jendela(i, 1, 4):
                    for ar in arab_per_seg.get(sj['id'], []):
                        q = ar['quran']
                        if q and q['surah'] == mt['surah']:
                            ok = not (q['ayat_akhir'] < a1 or q['ayat_awal'] > a2)
                            butir['bukti']['arab_ucapan'] = {'seg': sj['id'], 'cakupan': q['cakupan'], 'ayat_cocok': f"{q['ayat_awal']}-{q['ayat_akhir']}", 'tumpang_tindih_dengan_penyebutan': ok}
                            sudah_arab.add((sj['id'], id(ar)))
                            ar['dipakai'] = True
                            if ok:
                                butir['status'] = 'terverifikasi-arab-cocok'
                            else:
                                butir['status'] = 'konflik-penyebutan-vs-arab'
                                butir['catatan'].append('Ayat yang dibacakan (Arab) tidak sama dengan nomor yang disebut.')
                                tambah_titik(seg, 'dalil-konflik', f"Disebut {mt['nama']}:{a1}, tetapi bacaan Arab cocok dengan {q['surah']}:{q['ayat_awal']}-{q['ayat_akhir']}.",
                                             'Dengarkan audio; tentukan mana yang benar.')
                # kemiripan kutipan Latin (bukti pendukung saja)
                lat = ' '.join(x['text'] for x in jendela(i, 0, 3))
                lat = RUN_ARAB.sub(' ', lat)
                tr = ' '.join(rj.ayat[str(mt['surah'])][x - 1]['lat'] for x in range(a1, min(a2, a1 + 2) + 1))
                sk_v, sk_t = rangka_latin(tr), rangka_latin(lat)
                if sk_v:
                    sm = SequenceMatcher(None, sk_t, sk_v, autojunk=False)
                    sim = sum(b.size for b in sm.get_matching_blocks()) / len(sk_v)
                    butir['bukti']['kemiripan_kutipan_latin'] = round(sim, 3)
                    if sim < 0.35 and butir['status'] == 'terselesaikan-dari-penyebutan':
                        butir['catatan'].append('Kutipan Latin ustaz tidak mirip transliterasi ayat (atau ayat tidak dibacakan).')
                if butir['status'] == 'terselesaikan-dari-penyebutan' and 'arab_ucapan' not in butir['bukti']:
                    butir['catatan'].append('Ayat ditentukan dari penyebutan nomor (surah:ayat valid); bacaan Arab tidak tersedia untuk silang.')
            if mt.get('dipilih_lewat_konsistensi'):
                butir['catatan'].append(f"Nama kembar; dipilih {mt['nama']} karena ejaan yang sama telah terselesaikan lewat isi ayat di tempat lain pada korpus (kepastian lebih rendah).")
            if mt.get('dipilih_lewat_isi'):
                butir['catatan'].append(f"Nama kembar ({', '.join(rj.surat[n-1]['nama'] for n in mt['kandidat'])}); dipilih {mt['nama']} berdasarkan kecocokan isi ayat (skor {mt['dipilih_lewat_isi']}).")
            if mt['kemiripan_nama'] < 0.9:
                butir['catatan'].append(f"Nama surah dikoreksi dari '{mt['ejaan_ucapan']}' (kemiripan {mt['kemiripan_nama']}).")
            dalil.append(butir)

        # ayat tanpa surah di segmen yang sama (mewarisi surah terakhir <=6 segmen)
        if not mentions:
            for m in RX_AYAT_SAJA.finditer(seg['text']):
                if terakhir_surah and i - terakhir_surah[0] <= 6:
                    mt = terakhir_surah[1]
                    a = int(m.group(1))
                    dalil.append({'id': f"{vid}:{seg['id']}:w{m.start()}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''),
                                  'jenis': 'quran', 'disebut_ustaz': {'surah': None, 'ayat': a},
                                  'terselesaikan': {'surah_no': mt['surah'], 'surah': mt['nama'], 'ayat_awal': a, 'ayat_akhir': None},
                                  'status': 'diwarisi-dari-surah-sebelumnya' if a <= mt['jumlah_ayat_surah'] else 'nomor-ayat-tidak-valid',
                                  'bukti': {}, 'catatan': ['Surah diwarisi dari penyebutan sebelumnya (<=6 segmen); verifikasi dengan audio bila dipakai sebagai dalil.']})
                    if a <= mt['jumlah_ayat_surah']:
                        lst = rj.ayat[str(mt['surah'])]
                        dalil[-1]['teks_resmi'] = [{'n': lst[a - 1]['n'], 'ar': lst[a - 1]['ar'], 'terjemah_id': lst[a - 1]['id']}]
                else:
                    tambah_titik(seg, 'dalil-tanpa-surah', f"'ayat {m.group(1)}' disebut tanpa surah yang terbaca di sekitarnya.", 'Dengar audio untuk surah.')

        # nama surah tanpa kata 'surat' + 'ayat N' (mis. 'At-tawlaq ayat 2 dan 3')
        for m in re.finditer(r"\b([A-Z][A-Za-z'\u2019]*(?:[- ][A-Za-z'\u2019]+)?)\s+ayat\s+(?:ke-?)?(\d{1,3})", seg['text']):
            if RX_SURAT.search(seg['text'][max(0, m.start() - 8):m.start()]):
                continue
            r, s = rj.cari_surat(m.group(1))
            if r >= 0.85 and not any(b['seg'] == seg['id'] and b['terselesaikan']['surah_no'] == s['no'] for b in dalil):
                dalil.append({'id': f"{vid}:{seg['id']}:n{m.start()}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''),
                              'jenis': 'quran', 'disebut_ustaz': {'surah': m.group(1), 'ayat': int(m.group(2))},
                              'terselesaikan': {'surah_no': s['no'], 'surah': s['nama'], 'ayat_awal': int(m.group(2)), 'ayat_akhir': None},
                              'status': 'terselesaikan-dari-penyebutan' if int(m.group(2)) <= s['jumlah_ayat'] else 'nomor-ayat-tidak-valid',
                              'bukti': {'kemiripan_nama_surah': round(r, 3)}, 'catatan': ['Disebut tanpa kata "surah".']})
                if int(m.group(2)) <= s['jumlah_ayat']:
                    v = rj.ayat[str(s['no'])][int(m.group(2)) - 1]
                    dalil[-1]['teks_resmi'] = [{'n': v['n'], 'ar': v['ar'], 'terjemah_id': v['id']}]

    # --- bacaan Arab yang belum terpakai silang: tetap dicatat
    for sid, lst in arab_per_seg.items():
        seg = segs[idx[sid]]
        for k, ar in enumerate(lst):
            if ar.get('dipakai'):
                continue
            q, h = ar['quran'], ar['hadis']
            if q and (not h or q['cakupan'] >= h['cakupan']):
                v = rj.ayat[str(q['surah'])]
                nm = rj.surat[q['surah'] - 1]['nama']
                dalil.append({'id': f"{vid}:{sid}:a{k}", 'video_id': vid, 'seg': sid, 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'quran',
                              'disebut_ustaz': {'surah': None, 'ayat': None}, 'terselesaikan': {'surah_no': q['surah'], 'surah': nm, 'ayat_awal': q['ayat_awal'], 'ayat_akhir': q['ayat_akhir']},
                              'status': 'terkenali-dari-bacaan-arab', 'bukti': {'arab_ucapan': {'seg': sid, 'cakupan': q['cakupan']}},
                              'teks_resmi': [{'n': x['n'], 'ar': x['ar'], 'terjemah_id': x['id']} for x in v[q['ayat_awal'] - 1:q['ayat_akhir']]],
                              'catatan': ['Surah/ayat ditemukan dari pencocokan teks Arab (ustaz tidak menyebut/ tidak terbaca).']})
            elif h:
                hd = next(x for x in rj.hadis if x['id_in_book'] == h['id_in_book'])
                dalil.append({'id': f"{vid}:{sid}:h{k}", 'video_id': vid, 'seg': sid, 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'hadis',
                              'disebut_ustaz': {}, 'terselesaikan': {'kitab': 'Riyadhush Shalihin', 'id_in_book': hd['id_in_book'], 'nomor_lokal_kitab_bunga_rampai': hd['no_lokal']},
                              'status': 'terkenali-dari-bacaan-arab', 'bukti': {'arab_ucapan': {'seg': sid, 'cakupan': h['cakupan']}},
                              'teks_resmi': {'ar': hd['arab'], 'rawi_en': hd['rawi_en'], 'teks_en': hd['teks_en']},
                              'catatan': ['Derajat hadis TIDAK ditetapkan skrip; rujuk takhrij pensyarah/ahli.']})
            else:
                tambah_titik(seg, 'arab-tak-dikenali', 'Teks Arab tidak cocok dengan mushaf maupun Riyadhush Shalihin (>=60% cakupan).',
                             'Dengarkan audio; Whisper sering salah mengeja Arab. Jangan dijadikan dalil sebelum dicek.')
                dalil.append({'id': f"{vid}:{sid}:x{k}", 'video_id': vid, 'seg': sid, 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'arab-tak-dikenali',
                              'disebut_ustaz': {}, 'terselesaikan': {}, 'status': 'tidak-terverifikasi', 'bukti': {}, 'teks_ucapan': ar['teks_ucapan'], 'catatan': []})
        # usulan koreksi aksara Arab (tidak menimpa)
        for ar in lst:
            q = ar['quran']
            if q and q['cakupan'] < 0.97:
                for b in dalil:
                    if b['seg'] == sid and b['jenis'] == 'quran' and b['terselesaikan'].get('surah_no') == q['surah']:
                        b.setdefault('usulan_ganti_arab', []).append({'dari_ucapan': ar['teks_ucapan'], 'ke_mushaf': ' '.join(x['ar'] for x in rj.ayat[str(q['surah'])][q['ayat_awal'] - 1:q['ayat_akhir']]), 'cakupan': q['cakupan']})
                        break

    # --- hadis: nomor, rawi, 'hadis surat' ; penyebut tanpa rujukan ; ulama
    for i, seg in enumerate(segs):
        t = seg['text']
        for m in RX_HADIS_NO.finditer(t):
            n = int(m.group(1))
            pra = t[max(0, m.start() - 70):m.start()] + t[m.start():m.start() + 12]
            alt = bool(re.search(r'megang|memegang|melihat|buku|cetakan|terbitan|edisi|versi', pra, re.I))
            hd = None if alt else next((x for x in rj.hadis if x['no_lokal'] == n), None)
            dalil.append({'id': f"{vid}:{seg['id']}:hn{m.start()}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'hadis',
                          'disebut_ustaz': {'nomor': n}, 'terselesaikan': ({'kitab': 'Riyadhush Shalihin', 'id_in_book': hd['id_in_book'], 'nomor_lokal_kitab_bunga_rampai': n} if hd else {}),
                          'status': ('terselesaikan-dari-penyebutan' if hd else ('nomor-edisi-lain' if alt else 'nomor-tidak-dikenal')), 'bukti': {},
                          'teks_resmi': ({'ar': hd['arab'], 'rawi_en': hd['rawi_en'], 'teks_en': hd['teks_en']} if hd else None),
                          'catatan': ['Penomoran kitab Riyadhush Shalihin: edisi dataset Sunnah.com (nomor lokal = idInBook-1217 untuk bagian Bunga Rampai).'] if not alt else ['Ustaz menyebut nomor menurut cetakan lain; penomoran Riyadhush Shalihin berbeda antar cetakan. Cocokkan lewat isi hadis, bukan nomor.']})
            if alt:
                tambah_titik(seg, 'hadis-nomor-edisi-lain', f"Nomor hadis {n} disebut menurut cetakan lain.", 'Gunakan nomor edisi utama (yang disebut ustaz sebagai pokok) untuk kutipan.')
        for m in RX_RAWI.finditer(t):
            dalil.append({'id': f"{vid}:{seg['id']}:r{m.start()}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'rawi-disebut',
                          'disebut_ustaz': {'mukharrij': m.group(1)}, 'terselesaikan': {}, 'status': 'hanya-disebut', 'bukti': {}, 'catatan': ['Hanya penyebutan perawi/mukharrij; teks hadis belum dicocokkan.']})
        for m in RX_ULAMA.finditer(t):
            dalil.append({'id': f"{vid}:{seg['id']}:u{m.start()}", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'qaul-ulama',
                          'disebut_ustaz': {'ulama': m.group(1)}, 'terselesaikan': {}, 'status': 'hanya-disebut', 'bukti': {}, 'catatan': ['Pendapat/ucapan ulama sebagaimana disampaikan ustaz; sumber kitab tidak disebut.']})
        # penyebut dalil tanpa rujukan eksplisit di sekitar
        if RX_PENYEBUT.search(t):
            ada = any(b['video_id'] == vid and abs(idx[b['seg']] - i) <= 4 and b['jenis'] in ('quran', 'hadis', 'rawi-disebut') and b['status'] not in ('arab-tak-dikenali',) for b in dalil)
            if not ada:
                dalil.append({'id': f"{vid}:{seg['id']}:p", 'video_id': vid, 'seg': seg['id'], 'mulai': seg['start'], 'link': seg.get('link', ''), 'jenis': 'penyebut-dalil',
                              'disebut_ustaz': {'kalimat': RX_PENYEBUT.search(t).group(0)}, 'terselesaikan': {}, 'status': 'tanpa-rujukan-eksplisit', 'bukti': {},
                              'catatan': ['Ustaz menisbatkan ucapan pada Allah/Nabi tanpa menyebut surah/ayat/perawi di sekitarnya. RAG: jangan menambahkan sumber yang tidak disebut.']})

    # --- titik dengar dari flag QC dan salah-dengar yang tidak diubah
    for seg in segs:
        for fl in seg.get('flags', []):
            if fl in ('FRASA_CURIGA', 'HALUSINASI', 'NOISE', 'MIRIP_PROMPT', 'NAMA_BOCOR', 'TERLEWAT', 'BERULANG', 'CELAH'):
                tambah_titik(seg, f'flag-{fl}', f'Flag QC pipeline: {fl}.', 'Bandingkan dengan audio.')
        if re.search(r'\bhadi(?:s|th|ts)\s+surat\b', seg['text'], re.I):
            tambah_titik(seg, 'salah-dengar-mungkin', "'hadis surat' (kemungkinan 'hadis riwayat').", 'Dengar audio.')
        if seg.get('avg_logprob', 0) <= opsi.ambang_logprob or seg.get('compression_ratio', 0) >= opsi.ambang_kompresi:
            tambah_titik(seg, 'keyakinan-rendah', f"avg_logprob={seg.get('avg_logprob')}, compression_ratio={seg.get('compression_ratio')}", 'Cek bila memuat dalil.')

    # --- header & tulis
    jumlah = n_baru
    sebelumnya = sum(1 for s in segs for e in s.get('revisi', []) if not str(e.get('oleh', '')).startswith('revisi_batch:')) 
    d['revisi_batch'] = {'tanggal': datetime.date.today().isoformat(), 'skrip': 'revisi/revisi_batch.py', 'versi': VERSI,
                         'jumlah_perubahan': jumlah, 'revisi_sebelumnya_dipertahankan': sebelumnya, 'ejaan': 'KBBI (hanya aturan berstatus terverifikasi)' + (' + kandidat belum terverifikasi' if opsi.termasuk_belum_verifikasi else ''),
                         'catatan': 'File asli tidak diubah; teks sebelum batch ada di segments[].text_sebelum_batch (riwayat koreksi.txt tetap di segments[].revisi). Aksara Arab dan Latin-Arab dibiarkan.'}
    for s in segs:
        refs = [b['id'] for b in dalil if b['seg'] == s['id']]
        if refs:
            s['dalil_ref'] = refs
    nama = os.path.splitext(os.path.basename(path))[0]
    json.dump(d, open(os.path.join(keluar, nama + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(os.path.join(keluar, nama + '.txt'), 'w', encoding='utf-8') as f:
        f.write(f"Judul  : {d['video']['judul']}\nURL    : {d['video']['url']}\nBab    : {d['video'].get('bab', '')} | Kitab: {d['video'].get('kitab', '')}\n\n")
        for s in segs:
            f.write(f"[{mmss(s['start'])}] {s['text']}\n")
    with open(os.path.join(keluar, nama + '.srt'), 'w', encoding='utf-8') as f:
        for n, s in enumerate(segs, 1):
            f.write(f"{n}\n{srt_waktu(s['start'])} --> {srt_waktu(s['end'])}\n{s['text']}\n\n")
    return {'video_id': vid, 'judul': d['video']['judul'], 'berkas': nama, 'segmen': len(segs), 'perubahan': jumlah,
            'ringkas': {f'{a}|{b}': c for (a, b), c in ringkas.items()}, 'contoh': contoh,
            'dalil': len(dalil), 'titik_dengar': len(titik), 'video_id': vid, 'flags': [s_.get('flags', []) for s_ in segs]}, dalil, titik


# ------------------------------------------------------------------ laporan
def tulis_titik_dengar(titik, path):
    kat = collections.Counter(t['kategori'] for t in titik)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('# Titik dengar - perlu didengar ulang / diputuskan manusia\n\n')
        f.write(f'Total {len(titik)} butir. Urut per video lalu waktu. Klik tautan untuk loncat ke detik tersebut di YouTube.\n\n')
        f.write('| Kategori | Jumlah |\n|---|---|\n')
        for k, v in kat.most_common():
            f.write(f'| {k} | {v} |\n')
        by = collections.defaultdict(list)
        for t in titik:
            by[t['judul']].append(t)
        for judul in sorted(by, key=lambda x: int(re.match(r'\d+', x).group(0)) if re.match(r'\d+', x) else 0):
            f.write(f'\n## {judul}\n\n')
            for t in sorted(by[judul], key=lambda x: x['mulai']):
                f.write(f"- [{mmss(t['mulai'])}]({t['link']}) **{t['kategori']}** - {t['alasan']}"
                        + (f" _Saran: {t['saran']}_" if t['saran'] else '') + f"\n  > {t['cuplikan']}\n")



FLAG_DIBUANG = {'HALUSINASI', 'FRASA_CURIGA', 'NOISE'}   # selaras dengan notebook RAG6


def gerbang_video(ringkas_v, segs_flags, titik_v, dalil_v):
    alasan = []
    if any(f in FLAG_DIBUANG for fl in segs_flags for f in fl):
        return 'TAHAN', ['ada segmen berflag ' + '/'.join(sorted(FLAG_DIBUANG)) + ' yang belum ditinjau']
    if any(b['status'] in ('nomor-ayat-tidak-valid', 'konflik-penyebutan-vs-arab', 'surah-ambigu') for b in dalil_v):
        alasan.append('ada dalil dengan nomor tidak valid/konflik/ambigu')
    if any(b['jenis'] == 'arab-tak-dikenali' for b in dalil_v):
        alasan.append('ada teks Arab yang tidak cocok dengan rujukan (jangan dijadikan dalil)')
    if titik_v:
        alasan.append(f'{titik_v} titik dengar terbuka')
    return ('LULUS_BERSYARAT' if alasan else 'LULUS'), alasan


def tulis_laporan(a, R, rj, ringkasan, semua_dalil, semua_titik, contoh_total, per_aturan, flags_per_video, jumlah_belum, bentrok):
    jum = sum(r['perubahan'] for r in ringkasan)
    L = [f"# Laporan revisi batch - {os.path.basename(os.path.normpath(a.keluar))}", '',
         f"Dibuat {datetime.datetime.now().isoformat(timespec='seconds')} oleh `revisi_batch.py` v{VERSI}. File asli di `{a.masuk}` tidak diubah.", '',
         '## Ringkasan', '',
         f"- Video: {len(ringkasan)}; segmen: {sum(r['segmen'] for r in ringkasan)}; perubahan teks baru: **{jum}** (tingkat A otomatis aman, B otomatis kontekstual - semua tercatat di `segments[].revisi`).",
         f"- Butir dalil: {len(semua_dalil)}; titik dengar terbuka: **{len(semua_titik)}** (lihat `titik_dengar.md`).",
         '- Aksara Arab dan Latin-Arab tidak diubah. Derajat hadis dan hukum tidak ditetapkan skrip.', '',
         '## Perubahan per aturan', '', '| Tingkat | Aturan | Jumlah | Contoh (lama -> baru) |', '|---|---|---|---|']
    for (tg, rid), n in sorted(per_aturan.items(), key=lambda x: -x[1]):
        ex = '; '.join(f"`{l}` -> `{b}`" for l, b, *_ in contoh_total.get(rid, [])[:3])
        L.append(f"| {tg} | {rid.split(':')[1]} | {n} | {ex} |")
    L += ['', '## Status dalil', '', '| Jenis | Status | Jumlah |', '|---|---|---|']
    for (jn, st), n in sorted(collections.Counter((b['jenis'], b['status']) for b in semua_dalil).items(), key=lambda x: (x[0][0], -x[1])):
        L.append(f'| {jn} | {st} | {n} |')
    L += ['', '## Gerbang RAG per video', '', '| Video | Gerbang | Catatan |', '|---|---|---|']
    for r in ringkasan:
        L.append(f"| {r['judul'].split('|')[0].strip()} | {r['gerbang']} | {'; '.join(r['gerbang_alasan']) or '-'} |")
    L += ['', '- TAHAN: jangan di-ingest sebelum flag ditinjau. LULUS_BERSYARAT: boleh di-ingest, tetapi dalil berstatus tidak terverifikasi tidak boleh dikutip sebagai rujukan. LULUS: tidak ada butir terbuka.', '']
    L += ['## Kandidat ejaan belum terverifikasi (TIDAK diterapkan)', '',
          'Aktifkan dengan `--termasuk-belum-verifikasi` HANYA setelah dicek di KBBI Daring. Jumlah kemunculan di korpus:', '', '| Aturan | Kemunculan |', '|---|---|']
    for k, v in sorted(jumlah_belum.items(), key=lambda x: -x[1]):
        L.append(f'| {k} | {v} |')
    if bentrok:
        L += ['', '## Bentrok `koreksi.txt` vs KBBI', '',
              'Aturan di `koreksi.txt` yang keluarannya bertentangan dengan kamus KBBI (aturan KBBI menang di batch ini, karena KBBI adalah rujukan tunggal ejaan):', '']
        for b in bentrok:
            L.append(f'- `{b}`')
    L += ['', '## Keterbatasan', '',
          '- Verifikasi dalil = kecocokan teks dengan rujukan; bukan penilaian shahih/dhaif atau fatwa.',
          '- Teks Arab hasil Whisper sering salah eja: gunakan `usulan_ganti_arab` di inventaris sebagai bahan koreksi, bukan sebagai pengganti otomatis.',
          '- Nomor hadis: penomoran antar cetakan berbeda; cocokkan lewat isi (bacaan Arab) bila ada.',
          '- Nama surah kembar diputuskan lewat isi ayat; bila tidak cukup bukti ditandai ambigu.']
    open(os.path.join(a.keluar, 'LAPORAN_REVISI.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--masuk', required=True)
    ap.add_argument('--keluar', required=True)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--data', default=os.path.join(here, 'data'))
    ap.add_argument('--rujukan', default=os.path.join(here, 'rujukan'))
    ap.add_argument('--ambang-logprob', type=float, default=-0.45, dest='ambang_logprob', help='segmen dengan avg_logprob <= nilai ini masuk titik dengar (ambang QC repo -1.0 tidak pernah tercapai di data nyata)')
    ap.add_argument('--ambang-kompresi', type=float, default=2.4, dest='ambang_kompresi')
    ap.add_argument('--koreksi', default=None, help='koreksi.txt repo (opsional) untuk mendeteksi bentrok dengan KBBI')
    ap.add_argument('--termasuk-belum-verifikasi', action='store_true', dest='termasuk_belum_verifikasi')
    a = ap.parse_args()
    os.makedirs(a.keluar, exist_ok=True)
    R = muat_aturan(a.data, a.termasuk_belum_verifikasi)
    rj = Rujukan(a.rujukan)
    files = []
    for p in sorted(glob.glob(os.path.join(a.masuk, '*.json'))):
        try:
            j = json.load(open(p, encoding='utf-8-sig'))
        except Exception:
            continue
        if isinstance(j, dict) and 'video' in j and 'segments' in j:
            files.append(p)
        else:
            print('lewati (bukan transkrip):', os.path.basename(p))
    ringkasan, semua_dalil, semua_titik = [], [], []
    for p in files:
        r, d, t = proses_video(p, R, rj, a.keluar, a)
        ringkasan.append(r); semua_dalil += d; semua_titik += t
        print(f"{r['berkas'][:48]:50s} segmen={r['segmen']:3d} perubahan={r['perubahan']:3d} dalil={r['dalil']:3d} titik={r['titik_dengar']:3d}")
    json.dump({'skema': 'dalil_inventaris/1', 'dihasilkan': datetime.datetime.now().isoformat(timespec='seconds'),
               'rujukan': {'quran': 'quran-json 3.1.2 (teks Arab Tanzil, terjemah Kemenag, transliterasi Tanzil)',
                           'hadis': 'hadith-json: Riyadhush Shalihin (data Sunnah.com), nomor lokal = idInBook-1217'},
               'peringatan': 'Skrip menetapkan KECOCOKAN TEKS, bukan derajat hadis atau hukum. Arab hasil Whisper tidak boleh dijadikan dalil tanpa verifikasi.',
               'butir': semua_dalil}, open(os.path.join(a.keluar, 'dalil_inventaris.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(a.keluar, 'dalil_inventaris.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['id', 'video_id', 'seg', 'mulai', 'link', 'jenis', 'status', 'disebut_ustaz', 'terselesaikan', 'bukti', 'catatan'])
        for b in semua_dalil:
            w.writerow([b['id'], b['video_id'], b['seg'], b['mulai'], b['link'], b['jenis'], b['status'],
                        json.dumps(b['disebut_ustaz'], ensure_ascii=False), json.dumps(b['terselesaikan'], ensure_ascii=False),
                        json.dumps(b['bukti'], ensure_ascii=False), ' | '.join(b['catatan'])])
    tulis_titik_dengar(semua_titik, os.path.join(a.keluar, 'titik_dengar.md'))
    per_aturan = collections.Counter(); contoh_total = collections.defaultdict(list)
    for r in ringkasan:
        for k, n in r['ringkas'].items():
            tg, rid = k.split('|'); per_aturan[(tg, rid)] += n
        for rid, lst in r['contoh'].items():
            contoh_total[rid] += lst
    for r in ringkasan:
        dv = [b for b in semua_dalil if b['video_id'] == r['video_id']]
        tv = sum(1 for t in semua_titik if t['video_id'] == r['video_id'])
        r['gerbang'], r['gerbang_alasan'] = gerbang_video(r, r.pop('flags'), tv, dv)
    # kandidat belum diverifikasi: hitung kemunculan, tidak diterapkan
    belum = collections.Counter()
    if not a.termasuk_belum_verifikasi:
        semua_teks = ' '.join(sg['text'] for r_ in ringkasan for sg in json.load(open(os.path.join(a.keluar, r_['berkas'] + '.json'), encoding='utf-8'))['segments'])
        for r in baca_tsv(os.path.join(a.data, 'kamus_belum_diverifikasi.tsv')):
            belum[f"{r[0]} ({r[1]} -> {r[2]})"] = len(re.findall(r[1], semua_teks, re.I))
    bentrok = []
    if a.koreksi and os.path.exists(a.koreksi):
        pola = [(ru['rx'], ru['id']) for ru in R['kamus']] + [(re.compile(r[1], re.I), r[0]) for r in baca_tsv(os.path.join(a.data, 'kamus_belum_diverifikasi.tsv'))]
        for ln in open(a.koreksi, encoding='utf-8'):
            ln = ln.strip()
            if '=>' in ln and not ln.startswith('#'):
                lama, baru = [x.strip() for x in ln.split('=>', 1)]
                baru = baru.split('#', 1)[0].strip()
                for rx, rid in pola:
                    if rid == 'saleh' and re.search(r'\b(?:bin|ibnu?|syaikh|sheikh|al-)', baru, re.I):
                        continue      # nama orang
                    if rx.search(baru):
                        bentrok.append(f"{ln}   (KBBI: {rid})"); break
    tulis_laporan(a, R, rj, ringkasan, semua_dalil, semua_titik, contoh_total, per_aturan, None, belum, bentrok)
    json.dump({'versi': VERSI, 'video': ringkasan,
               'dalil_per_status': dict(collections.Counter((b['jenis'], b['status']) .__str__() for b in semua_dalil)),
               'titik_dengar_per_kategori': dict(collections.Counter(t['kategori'] for t in semua_titik))},
              open(os.path.join(a.keluar, 'ringkasan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('selesai ->', a.keluar)


if __name__ == '__main__':
    main()
