#!/usr/bin/env python3
"""dengar_qwen.py - "dengar ulang" SATU bagian audio kajian dengan ASR open-source Qwen3-ASR 0.6B (sherpa-onnx, int8, CPU).
Pembanding kedua selain Whisper untuk memastikan ucapan ustaz (nama ulama, kata yang meragukan). TIDAK mengubah transkrip apa pun;
hasilnya hanya bukti untuk keputusan koreksi (selalu bertanda [konteks] di aturan_kontekstual.tsv, lihat prinsip 17-18).

Pakai (dari akar repo, audio ada di audio/<video_id>.m4a):
    python revisi/dengar_qwen.py 4F5xW_U3R7w 44:10 44:55 [--chunk 12] [--model-dir /tmp/q/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25]
Saran: jalankan beberapa kali dengan titik awal digeser 3 detik (mis. 44:20, 44:23, 44:26) agar kata di batas potongan terdengar utuh.

Siapkan sekali (butuh python3, pip, ffmpeg tidak wajib):
    pip install sherpa-onnx av numpy
    # model 878 MB dari rilis GitHub (HuggingFace sering terblokir); curl -C - bisa dilanjutkan bila terputus:
    curl -L -C - -O https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25.tar.bz2
    tar xjf sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25.tar.bz2
Keluaran akurat sedang (model kecil): pakai untuk membandingkan dengan Whisper, bukan sebagai sumber tunggal."""
import argparse, os, sys, time
from pathlib import Path
import av, numpy as np, sherpa_onnx

def detik(x):
    r = 0.0
    for v in str(x).split(':'): r = r * 60 + float(v)
    return r

ap = argparse.ArgumentParser()
ap.add_argument('video_id'); ap.add_argument('dari'); ap.add_argument('sampai')
ap.add_argument('--chunk', type=float, default=12.0)
ap.add_argument('--model-dir', default=os.environ.get('QWEN_ASR_DIR', 'sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25'))
ap.add_argument('--threads', type=int, default=2)
A = ap.parse_args()
t0, t1 = detik(A.dari), detik(A.sampai); SR = 16000
audio = Path(__file__).resolve().parent.parent / 'audio' / f'{A.video_id}.m4a'
cont = av.open(str(audio)); st = cont.streams.audio[0]
res = av.AudioResampler(format='fltp', layout='mono', rate=SR)
cont.seek(int(max(0, t0 - 2) * 1_000_000)); buf, ta = [], None
for fr in cont.decode(st):
    ts = float(fr.pts * st.time_base)
    if ts + fr.samples / fr.sample_rate < t0: continue
    if ts > t1: break
    if ta is None: ta = ts
    for o in res.resample(fr): buf.append(o.to_ndarray()[0])
wav = np.concatenate(buf).astype('float32'); off = max(0, t0 - ta); wav = wav[int(off * SR): int((off + t1 - t0) * SR)]
M = A.model_dir
rec = sherpa_onnx.OfflineRecognizer.from_qwen3_asr(conv_frontend=M + '/conv_frontend.onnx', encoder=M + '/encoder.int8.onnx',
        decoder=M + '/decoder.int8.onnx', tokenizer=M + '/tokenizer', num_threads=A.threads, max_new_tokens=256, max_total_len=1024)
n = int(A.chunk * SR)
for k in range(0, len(wav), n):
    s = rec.create_stream(); s.accept_waveform(SR, wav[k:k + n]); rec.decode_stream(s)
    m, sec = divmod(int(t0 + k / SR), 60); print(f'[{m}:{sec:02d}] {s.result.text}', flush=True)
