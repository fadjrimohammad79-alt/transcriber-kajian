#!/usr/bin/env python3
"""latin_ke_arab.py - (OPSIONAL, UJI) ganti kutipan Latin-Arab dalam transkrip dengan aksara Arab dari rujukan.
Rujukan utama: Alquran (jika ayat terdeteksi), lalu Riyadhush Shalihin. Arab yang sudah ada dikoreksi ke mushaf/kitab.
File masukan TIDAK diubah. Hasil: .json (+ teks_sebelum_arab, arab_otomatis), .txt, .srt, LAPORAN_UJI_ARAB.md.
Pakai (dari akar repo): python revisi/latin_ke_arab.py --masuk hasil/<Bab>_revisi --keluar hasil/<Bab>_uji_arab [--rujukan revisi/rujukan]
Aturan: ayat Alquran WAJIB berharakat (sumber gundul dilewati dan dilaporkan); hadis dan kutipan syarah kitab boleh gundul.
Catatan: kecocokan teks saja (bukan derajat hadis); periksa baris berskor < 0,9 di laporan. Keputusan korpus baku tetap Arab=Latin."""
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument('--masuk', required=True)
_ap.add_argument('--keluar', required=True)
_ap.add_argument('--rujukan', default='revisi/rujukan')
_ap.add_argument('--dalil', default=None, help='dalil_inventaris.json (default: <masuk>/dalil_inventaris.json)')
_ap.add_argument('--nawawi', default=None, help='nawawi_pembuka_bab.json: pembuka bab dari Imam Nawawi (default: data/nawawi_pembuka_bab.json di sebelah skrip)')
_ap.add_argument('--deskripsi', default=None, help='deskripsi_youtube.json: hadis berharakat dari deskripsi video ustaz (default: data/deskripsi_youtube.json di sebelah skrip)')
ARGS = _ap.parse_args()
import sys, json, re, glob, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revisi_batch as rb
from difflib import SequenceMatcher
Q = json.load(open(os.path.join(ARGS.rujukan, 'quran_ringkas.json'), encoding='utf-8'))
SURAT = json.load(open(os.path.join(ARGS.rujukan, 'surat.json'), encoding='utf-8'))
H = json.load(open(os.path.join(ARGS.rujukan, 'riyadhush_shalihin_ringkas.json'), encoding='utf-8'))
RJ = rb.Rujukan(ARGS.rujukan)
# konstanta aksara dibangun dari kode titik agar aman disalin lewat teks (tanpa karakter tak terlihat)
ORN = chr(0x6DE)
AR_LET = chr(0x621) + '-' + chr(0x64A) + chr(0x671)
AR_MARK = chr(0x64B) + '-' + chr(0x65F) + chr(0x670) + chr(0x6D6) + '-' + chr(0x6ED) + chr(0x640)
AR_HRK = chr(0x64B) + '-' + chr(0x651)
AR_STOP = chr(0x6D6) + '-' + chr(0x6DC) + chr(0x6DE)
MAP = {'ب':'b','ت':'t','ث':'t','ج':'z','ح':'h','خ':'k','د':'d','ذ':'d','ر':'r','ز':'d','س':'s','ش':'s','ص':'s','ض':'d','ط':'t','ظ':'d','غ':'g','ف':'f','ق':'k','ك':'k','ل':'l','م':'m','ن':'n','ه':'h','و':'w','ي':'y'}
SUN = set('تثدذرزسشصضطظلن')
def ar_skel(w):
    w = w.replace('ٱ', 'ا').replace('ى', 'ا').replace('ؤ', 'و').replace('ئ', 'ي')
    for _c in 'أإآ': w = w.replace(_c, 'ا')
    # pecah menjadi (huruf, tanda)
    items = re.findall('([' + AR_LET + '])([' + AR_MARK + ']*)', w)
    if len(items) > 2 and items[0][0] == 'ا' and items[1][0] == 'ل' and items[2][0] in SUN:
        items = items[2:]
    elif len(items) > 3 and items[0][0] == 'و' and items[1][0] == 'ا' and items[2][0] == 'ل' and items[3][0] in SUN:
        items = [items[0]] + items[3:]
    elif len(items) > 2 and items[0][0] == 'ا' and items[1][0] == 'ل' :
        pass
    s = ''
    for k, (c, mk) in enumerate(items):
        if c in 'وي' and k > 0 and not re.search('[' + AR_HRK + ']', mk):
            continue          # huruf mad (u/i panjang)
        s += MAP.get(c, '')
    return re.sub(r'(.)\1+', r'\1', s)
def bersih(t):
    t = t.replace(ORN, '').replace(chr(0x6E9), '')
    t = re.sub('[' + AR_STOP + ']+(?=\\s|$)', '', t)
    return re.sub(r'\s+', ' ', t).strip()
DILEWATI = []   # penggantian yang dibatalkan karena sumber Arab tanpa harakat (gundul)
def berharakat(teks):
    # True bila hampir semua kata Arab memuat harakat (fathah, dammah, kasrah, sukun, syaddah, tanwin)
    ws = [w for w in teks.split() if re.search('[' + AR_LET + ']', w)]
    return bool(ws) and sum(1 for w in ws if re.search('[' + AR_HRK + chr(0x652) + ']', w)) / len(ws) >= 0.8
STOCK = {rb.rangka_latin(x) for x in ('allah', 'subhanahu', 'wa', 'ta', 'ala', 'shallallahu', 'alaihi', 'sallam', 'rahimahullah', 'radhiyallahu', 'anhu', 'anhum', 'anha', 'azza', 'jalla', 'insya', 'masya', 'bismillah', 'alhamdulillah', 'rabb', 'amma', 'baad', 'ya', 'la', 'ilaha', 'illa')}
STOCK |= {rb.rangka_latin(x) for x in ('astaghfirullah', 'atubu', 'ilaih', 'ilaihi', 'allahumma', 'alhamdulillahi', 'rabbal', 'alamin', 'illallah', "ta'ala", 'bin', 'abu', 'ibnu', 'kata', 'binti', 'anhuma', "'anhuma", 'anhu', "'anhu", 'ta')}
# ---- indeks (n-gram karakter pada rangka konsonan)
def unit_quran():
    U = {}
    for sn, lst in Q.items():
        for v in lst:
            ws = [w for w in v['ar'].split() if w.strip(ORN)]
            U[('Q', int(sn), v['n'])] = (None, ws, [ar_skel(w) for w in ws])
    return U
def unit_hadis():
    U = {}
    for h in H:
        ws = h['arab'].split()
        U[('H', h['id_in_book'])] = (None, ws, [ar_skel(w) for w in ws])
    return U
DESK = []
try:
    DESK = json.load(open(ARGS.deskripsi or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'deskripsi_youtube.json'), encoding='utf-8'))['hadis']
except Exception as _e: print('tanpa deskripsi YouTube', _e)
def unit_desk():
    U = {}
    for k, h in enumerate(DESK):
        ws = [x for x in (re.sub('[^' + AR_LET + AR_MARK + ']', '', w) for w in h['ar'].split()) if ar_skel(x)]
        U[('D', k)] = (None, ws, [ar_skel(w) for w in ws])
    return U
NAW = []
try:
    NAW = json.load(open(ARGS.nawawi or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'nawawi_pembuka_bab.json'), encoding='utf-8'))['bab']
except Exception as _e: print('tanpa pembuka bab Nawawi', _e)
def unit_naw():
    U = {}
    for k, h in enumerate(NAW):
        ws = [x for x in (re.sub('[^' + AR_LET + AR_MARK + ']', '', w) for w in h['ar'].split()) if ar_skel(x)]
        U[('N', k)] = (None, ws, [ar_skel(w) for w in ws])
    return U
UQ, UH, UD, UN = unit_quran(), unit_hadis(), unit_desk(), unit_naw()
def bangun(units, n, maxpost):
    ix = collections.defaultdict(set)
    for uid, (_, ws, sk) in units.items():
        s = ''.join(sk)
        for k in range(len(s) - n + 1): ix[s[k:k + n]].add(uid)
    return {g: v for g, v in ix.items() if len(v) <= maxpost}
IXQ, IXH, IXD, IXN = bangun(UQ, 5, 40), bangun(UH, 6, 12), bangun(UD, 6, 20), bangun(UN, 6, 20)
def cari(tokens, units, ix, n, min_share, min_ar, thr, min_ns):
    tsk = [rb.rangka_latin(t[0]) for t in tokens]
    X = ''.join(tsk); xb = []; c = 0
    for s in tsk: xb.append((c, c + len(s))); c += len(s)
    share = collections.Counter()
    for k in set(range(len(X) - n + 1)):
        for uid in ix.get(X[k:k + n], ()): share[uid] += 1
    for _u in HINT:
        if _u in units: share[_u] = max(share[_u], min_share)
    out = []
    for uid, cnt in share.items():
        if cnt < min_share: continue
        _, words, sk = units[uid]
        Y = ''.join(sk); yb = []; c = 0
        for s in sk: yb.append((c, c + len(s))); c += len(s)
        sm = SequenceMatcher(None, X, Y, autojunk=False)
        bl = [b for b in sm.get_matching_blocks() if b.size >= 3]
        if not bl: continue
        # kelompok blok berurutan (celah kecil)
        runs, cur = [], [bl[0]]
        for b in bl[1:]:
            pv = cur[-1]
            if b.a - (pv.a + pv.size) <= 10 and b.b - (pv.b + pv.size) <= 10: cur.append(b)
            else: runs.append(cur); cur = [b]
        runs.append(cur)
        for run in sorted(runs, key=lambda r: -sum(x.size for x in r))[:4]:   # semua kutipan terpisah dalam satu blok (mis. ayat disebut dua kali)
            if sum(x.size for x in run) < 6: continue
            xs, xe = run[0].a, run[-1].a + run[-1].size; ys, ye = run[0].b, run[-1].b + run[-1].size
            a = next((k for k, (s0, e0) in enumerate(xb) if e0 > xs), None); b = max((k for k, (s0, e0) in enumerate(xb) if s0 < xe), default=None)
            i = next((k for k, (s0, e0) in enumerate(yb) if e0 > ys), None); j = max((k for k, (s0, e0) in enumerate(yb) if s0 < ye), default=None)
            if None in (a, b, i, j) or b < a or j < i: continue
            # pangkas token tepi yang jelas bahasa Indonesia
            while a <= b and ind(tokens[a][0]): a += 1
            while b >= a and ind(tokens[b][0]): b -= 1
            if b < a: continue
            inb = [bb for bb in run if bb.a + bb.size > xb[a][0] and bb.a < xb[b][1]]
            if not inb: continue
            ys, ye = inb[0].b, inb[-1].b + inb[-1].size
            i = next((k for k, (s0, e0) in enumerate(yb) if e0 > ys), None); j = max((k for k, (s0, e0) in enumerate(yb) if s0 < ye), default=None)
            if None in (i, j) or j < i: continue
            nl = j - i + 1; nt = b - a + 1
            r = SequenceMatcher(None, ''.join(tsk[a:b + 1]), ''.join(sk[i:j + 1]), autojunk=False).ratio()
            nonstock = sum(1 for x in range(a, b + 1) if tsk[x] not in STOCK)
            n_ind = sum(1 for x in range(a, b + 1) if ind(tokens[x][0]))
            hint = uid in HINT
            trait_ok = hint or arabness([tokens[x][0] for x in range(a, b + 1)]) >= 0.6
            ok = trait_ok and nt >= (2 if hint else (4 if r < 0.95 else 3)) and nonstock >= (2 if hint else min_ns) and n_ind <= max(1 if min_ar >= 5 else 0, int(0.2 * nt)) and (nl >= min_ar or (nl >= 2 and r >= 0.9 and len(''.join(sk[i:j + 1])) >= 7 and n_ind == 0))
            if not hint and r < 0.9 and nl <= 3: continue   # kutipan pendek tanpa petunjuk ayat harus sangat mirip
            if r >= (0.8 if hint else thr) and ok and nt <= nl + 3 and nl <= nt + 3:
                out.append((r, a, b, uid, i, j))
    return out
FREQ = collections.Counter()
for _f in glob.glob(os.path.join(ARGS.masuk, '*.json')):
    try:
        _v = json.load(open(_f, encoding='utf-8'))
        for _s in _v['segments']:
            FREQ.update(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'’`\-]*", _s['text']))
    except Exception: pass
ARABPART = {'wa','la','min','fi','ila','an','ma','ya','qul','inna','innal','innallaha','allah','allahu','billah','lillah','ala','fa','bi','li','man','lam','lan','qad','kana','kun','huwa','hum','hu','ana','anna','illa','al','ash','ad','ar','as','at','wal','fal','alladhina','alladhi','iza','idha','hatta','thumma','aw','am','ayyuha','ayyuhal'}
def ind(tok): return FREQ[tok.lower()] >= 50 and tok.lower() not in ARABPART
TRAIT = re.compile(r"(dh|th|kh|sh|gh|zh|aa|ii|uu|ay|aw|'|’|-)|(ah|ih|uh|un|in|an|ina|una|ihi|uhu|ahu|ka|kum|hum|hu|na|iya|iyyah|ullah)$")
def arabness(toks):
    cek = [x for x in toks if x.lower() not in ARABPART]
    return (sum(1 for x in cek if TRAIT.search(x.lower())) / len(cek)) if cek else 0
HINT = set()
DAL = {}
try:
    for _b in json.load(open(ARGS.dalil or os.path.join(ARGS.masuk, 'dalil_inventaris.json'), encoding='utf-8'))['butir']:
        if _b['jenis'] == 'quran' and _b['terselesaikan'].get('surah_no') and _b['terselesaikan'].get('ayat_awal'):
            DAL.setdefault((_b['video_id'], _b['seg']), set()).add((_b['terselesaikan']['surah_no'], _b['terselesaikan']['ayat_awal'], _b['terselesaikan'].get('ayat_akhir') or _b['terselesaikan']['ayat_awal']))
except Exception as _e: print('tanpa petunjuk dalil', _e)
TOK = re.compile(r"[A-Za-z][A-Za-z'’`\-]*")
def proses_teks(text, vid=None, sid=0, seed=None):
    global HINT
    HINT = set()
    for k in range(sid - 8, sid + 2):
        for (sn, a1, a2) in DAL.get((vid, k), ()):
            for ay in range(a1, a2 + 1): HINT.add(('Q', sn, ay))

    reps = list(seed or [])   # (start,end,new,info); seed = kalimat Nawawi manual (diproses lebih dulu)
    # 1) Arab yang sudah ada -> koreksi ke rujukan
    for m in rb.RUN_ARAB.finditer(text):
        run = m.group(0).strip(); rn = rb.norm_arab(run)
        if len(rn.split()) < 3: continue
        q = RJ.cocok_quran(rn); h = RJ.cocok_hadis(rn)
        if q and (not h or q['cakupan'] >= h['cakupan']):
            words = []
            for ay in range(q['ayat_awal'], q['ayat_akhir'] + 1):
                words += [w for w in Q[str(q['surah'])][ay - 1]['ar'].split() if w.strip(ORN)]
            ref = f"Alquran {SURAT[q['surah']-1]['nama']}:{q['ayat_awal']}" + (f"-{q['ayat_akhir']}" if q['ayat_akhir'] != q['ayat_awal'] else '')
        elif h:
            words = next(x for x in H if x['id_in_book'] == h['id_in_book'])['arab'].split()
            ref = f"Riyadhush Shalihin idInBook {h['id_in_book']}"
        else: continue
        n = len(rn.split()); best = (0, 0, 0)
        for i in range(len(words)):
            for j in range(i, min(len(words), i + n + 2)):
                r = SequenceMatcher(None, rn, rb.norm_arab(' '.join(words[i:j + 1])), autojunk=False).ratio()
                if r > best[0]: best = (r, i, j)
        if best[0] >= 0.7:
            new = bersih(' '.join(words[best[1]:best[2] + 1]))
            if new != run and ref.startswith('Alquran') and not berharakat(new): DILEWATI.append(('koreksi-arab', run, new, ref))
            elif new != run: reps.append((m.start(), m.end(), new, {'jenis': 'koreksi-arab', 'lama': run, 'rujukan': ref, 'skor': round(best[0], 2)}))
    # 2) Latin -> Arab
    toks = [(m.group(0), m.start(), m.end(), None) for m in TOK.finditer(text)]
    # pecah di aksara Arab
    segs, cur = [], []
    for t in toks:
        if cur and rb.RUN_ARAB.search(text[cur[-1][2]:t[1]]): segs.append(cur); cur = []
        cur.append(t)
    if cur: segs.append(cur)
    used = []
    for blok in segs:
        if len(blok) < 3: continue
        for (units, ix, ng, share, minar, thr, minns) in ((UQ, IXQ, 5, 4, 3, 0.82, 3), (UD, IXD, 6, 5, 4, 0.85, 4), (UN, IXN, 6, 4, 4, 0.85, 3), (UH, IXH, 6, 6, 5, 0.85, 4)):
            cand = cari(blok, units, ix, ng, share, minar, thr, minns)
            for r, a, b, uid, i, j in sorted(cand, key=lambda x: (-round(x[0], 2), -(x[2] - x[1]), 0 if x[3] in HINT else 1, x[3])):
                s, e = blok[a][1], blok[b][2]
                if any(not (e <= u0 or s >= u1) for u0, u1 in used) or any(not (e <= x[0] or s >= x[1]) for x in reps): continue
                words = units[uid][1][i:j + 1]
                if uid[0] == 'Q' and not berharakat(' '.join(words)):
                    DILEWATI.append(('latin-ke-arab', text[s:e], ' '.join(words), f"{uid[0]} {uid[1]}")); continue
                if uid[0] == 'D': _d = DESK[uid[1]]; ref = f"Deskripsi YouTube kajian nomor {'/'.join(map(str, _d['video']))}" + (f" ({_d['rujukan']})" if _d.get('rujukan') else '') + f" kata {i+1}-{j+1}"
                elif uid[0] == 'N': _n = NAW[uid[1]]; ref = f"Imam Nawawi, {_n['kitab']}, pembuka Bab {_n['bab']} (Shamela buku {_n['shamela_buku']} hlm. {_n['shamela_halaman']}) kata {i+1}-{j+1}"
                elif uid[0] == 'Q': ref = f"Alquran {SURAT[uid[1]-1]['nama']}:{uid[2]} kata {i+1}-{j+1}"
                else:
                    hd = next(x for x in H if x['id_in_book'] == uid[1]); ref = f"Riyadhush Shalihin idInBook {uid[1]} (no. lokal {hd['no_lokal']}) kata {i+1}-{j+1}"
                used.append((s, e))
                alt = [c for c in cand if (c[1], c[2]) == (a, b) and c[3] != uid and abs(c[0] - r) < 0.01 and ' '.join(units[c[3]][1][c[4]:c[5] + 1]) == ' '.join(words)]
                reps.append((s, e, bersih(' '.join(words)), {'jenis': 'latin-ke-arab', 'lama': text[s:e], 'rujukan': ref, 'skor': round(r, 2), 'serupa': [(f"{SURAT[c[3][1]-1]['nama']}:{c[3][2]}" if c[3][0]=='Q' else f"{c[3][0]} {c[3][1]}") for c in alt[:5]]}))
    return reps
NAWAWI = [(r"Fa intaba min ba'diha.*?wa bakiya alaihil baki", "فَإِنْ تَابَ مِنْ بَعْضِهَا صَحَّتْ تَوْبَتُهُ عِنْدَ أَهْلِ الْحَقِّ مِنْ ذَلِكَ الذَّنْبِ وَبَقِيَ عَلَيْهِ الْبَاقِي"),
          (r"Inda ahlil haq min dhalika dhan wa baqya alaihil baqi", "عِنْدَ أَهْلِ الْحَقِّ مِنْ ذَلِكَ الذَّنْبِ وَبَقِيَ عَلَيْهِ الْبَاقِي"),
          (r"waqad tazharat dala'ilul kitab wa sunah wa ijma'il ummah ala wujubi tobat", "وَقَدْ تَظَاهَرَتْ دَلَائِلُ الْكِتَابِ وَالسُّنَّةِ، وَإِجْمَاعِ الْأُمَّةِ عَلَى وُجُوبِ التَّوْبَةِ"),
          (r"Fa.in ka.natil ma.siatu bayna la.abdi wa bayna Allahi ta.ala.*?falaha thalathatu shuruta", "فَإِنْ كَانَتِ الْمَعْصِيَةُ بَيْنَ الْعَبْدِ وَبَيْنَ اللهِ تَعَالَى لَا تَتَعَلَّقُ بِحَقِّ آدَمِيٍّ فَلَهَا ثَلَاثَةُ شُرُوطٍ"),
          (r"An yuqli.a anil ma.siyah", "أَنْ يُقْلِعَ عَنِ الْمَعْصِيَةِ"),
          (r"An ya.zim alla ya.uda ilaiha abadah", "أَنْ يَعْزِمَ أَنْ لَا يَعُودَ إِلَيْهَا أَبَدًا"),
          (r"Qawla al-ulama al-tawbatu wajibatun min kulli dhanba", "قَالَ الْعُلَمَاءُ: التَّوْبَةُ وَاجِبَةٌ مِنْ كُلِّ ذَنْبٍ")]
out = ARGS.keluar; os.makedirs(out, exist_ok=True)
laporan = []; total = collections.Counter()
FILES = sorted(glob.glob(os.path.join(ARGS.masuk, '*.json')))
for f in FILES:
    try: V = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not (isinstance(V, dict) and 'segments' in V and 'video' in V): continue
    nm = os.path.splitext(os.path.basename(f))[0]; n_v = collections.Counter()
    for s in V['segments']:
        t = s['text']; seed = []
        for rx, ar in NAWAWI:
            m = re.search(rx, t, re.I | re.S)
            if m and not any(not (m.end() <= x[0] or m.start() >= x[1]) for x in seed):
                seed.append((m.start(), m.end(), ar, {'jenis': 'nawawi-manual', 'lama': m.group(0), 'rujukan': 'Riyadhush Shalihin, pembuka Bab Taubat (kalemtayeb.com/ahadeeth/sub/384; dicocokkan ke Shamela buku 2348 hlm. 24)', 'skor': 1.0}))
        reps = proses_teks(t, V['video']['video_id'], s['id'], seed)
        if not reps: continue
        for a, b, new, info in sorted(reps, reverse=True): t = t[:a] + new + t[b:]
        s['text_sebelum_arab'] = s['text']; s['text'] = t
        s['arab_otomatis'] = [dict(info, baru=new) for a, b, new, info in sorted(reps)]
        for a, b, new, info in sorted(reps):
            n_v[info['jenis']] += 1; laporan.append((V['video']['judul'].split('|')[0].strip(), s['id'], info, new))
    V['uji_arab'] = {'catatan': 'UJI: Latin-Arab diganti aksara Arab dari Alquran (quran-json 3.1.2) / Riyadhush Shalihin (hadith-json). Keputusan korpus tetap Arab=Latin.'}
    json.dump(V, open(f'{out}/{nm}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(f'{out}/{nm}.txt', 'w', encoding='utf-8') as o:
        o.write(f"Judul  : {V['video']['judul']}\nURL    : {V['video']['url']}\nBab    : {V['video'].get('bab','')} | Kitab: {V['video'].get('kitab','')}\n\n")
        for s in V['segments']: o.write(f"[{rb.mmss(s['start'])}] {s['text']}\n")
    with open(f'{out}/{nm}.srt', 'w', encoding='utf-8') as o:
        for n, s in enumerate(V['segments'], 1): o.write(f"{n}\n{rb.srt_waktu(s['start'])} --> {rb.srt_waktu(s['end'])}\n{s['text']}\n\n")
    total.update(n_v); print(nm[:40], dict(n_v))
with open(f'{out}/LAPORAN_UJI_ARAB.md', 'w', encoding='utf-8') as o:
    o.write(f'# Laporan uji Latin-ke-Arab\n\nTotal: {dict(total)}\n\n| Video | Seg | Jenis | Lama | Baru | Rujukan | Skor |\n|---|---|---|---|---|---|---|\n')
    for v, sid, info, new in laporan:
        o.write(f"| {v[:30]} | {sid} | {info['jenis']} | {info['lama'][:60].replace('|','/')} | {new[:60]} | {info['rujukan']} | {info['skor']} |\n")
with open(f'{out}/LAPORAN_UJI_ARAB.md', 'a', encoding='utf-8') as o:
    o.write(f'\n## Dilewati karena ayat Alquran tanpa harakat (gundul): {len(DILEWATI)}\n\nTetap Latin/Arab asli. Butuh sumber bertasykil agar bisa diganti.\n\n| Jenis | Teks asli | Rujukan |\n|---|---|---|\n')
    for j, lama, baru, rf in DILEWATI: o.write(f"| {j} | {lama[:70].replace('|','/')} | {rf} |\n")
print(dict(total), 'dilewati-gundul', len(DILEWATI))
