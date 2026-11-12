import numpy as np, wave, subprocess, os
import json, sys
CU=open(sys.argv[2] if len(sys.argv)>2 else 'cues.js').read(); CUES=json.loads(CU.split('window.CUES=')[1].split(';')[0]); OUTRO=float(CU.split('window.OUTRO=')[1].split(';')[0])
SR = 44100; DUR = OUTRO + 4.0; N = int(SR * DUR)
rng = np.random.default_rng(7)
tt = np.arange(N) / SR

def load(path):
    out = path + '.44k.raw'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', path, '-af', 'highpass=f=70,equalizer=f=200:t=q:w=1:g=1.5,equalizer=f=3500:t=q:w=1:g=2,acompressor=threshold=-18dB:ratio=3:attack=5:release=80', '-ac', '1', '-ar', str(SR), '-f', 's16le', out], check=True)
    return np.frombuffer(open(out, 'rb').read(), dtype=np.int16).astype(np.float32) / 32768

# ---------------- voice ----------------
voice = np.zeros(N, np.float32)
if len(sys.argv) > 1:   # one full voice-over file (the user's recording), placed at 0
    a = load(sys.argv[1]); a = a / max(1e-6, np.abs(a).max()) * 0.9
    off = int(0.3 * SR); voice[off:min(N, off + len(a))] = a[:N - off]
else:
    for i, cu in enumerate(CUES):
        a = load(f'tts/out3/{i:02d}.wav'); st = int(cu['s'] * SR); e = min(N, st + len(a)); voice[st:e] += a[:e - st]
voice *= 0.95

# voice activity envelope for ducking
env = np.convolve(np.abs(voice), np.ones(2205) / 2205, mode='same')
act = (env > 0.02).astype(np.float32)
k = np.ones(int(0.35 * SR)) / int(0.35 * SR)
act = np.clip(np.convolve(act, k, mode='same') * 1.6, 0, 1)

# ---------------- music ----------------
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
BPM = 96; beat = 60 / BPM; bar = beat * 4
# F major: Fmaj7, Dm7, Bbmaj7, C(add9)
CH = [[53, 57, 60, 64], [50, 57, 60, 65], [46, 53, 57, 62], [48, 55, 62, 64]]
music = np.zeros(N, np.float32)
# pad
for b in range(int(DUR / bar) + 2):
    t0 = b * bar; ch = CH[b % 4]
    s = int(t0 * SR); L = int((bar + 0.6) * SR); e = min(N, s + L)
    if s >= N: break
    x = np.arange(e - s) / SR
    envp = np.minimum(1, x / 0.5) * np.minimum(1, (bar + 0.6 - x) / 0.6)
    sig = np.zeros(e - s)
    for m in ch:
        f = mtof(m + 12)
        sig += np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.003 * x) + 0.12 * np.sin(2 * np.pi * f * 3 * x)
    music[s:e] += 0.035 * sig * envp
    # bass
    fb = mtof(ch[0] - 12)
    music[s:e] += 0.09 * np.sin(2 * np.pi * fb * x) * envp
# pluck arpeggio (eighths) starts after hook
step = beat / 2
for n in range(int(DUR / step)):
    t0 = n * step
    if t0 < 0.3 or t0 > OUTRO + 1.5: continue
    ch = CH[int(t0 // bar) % 4]
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    m = ch[pat[n % 8]] + 24
    s = int(t0 * SR); L = int(0.6 * SR); e = min(N, s + L); x = np.arange(e - s) / SR
    f = mtof(m)
    sig = (np.sin(2 * np.pi * f * x) + 0.25 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x * 7)
    music[s:e] += 0.05 * sig * (0.8 if n % 2 else 1.0)
# soft kick + shaker from 5.9s to 24.8s
for n in range(int(DUR / beat)):
    t0 = n * beat
    if CUES[2]['s'] <= t0 < OUTRO - 0.1:
        s = int(t0 * SR); L = int(0.25 * SR); e = min(N, s + L); x = np.arange(e - s) / SR
        if n % 2 == 0:
            ph = 2 * np.pi * np.cumsum(50 + 90 * np.exp(-x * 30)) / SR
            music[s:e] += 0.22 * np.sin(ph) * np.exp(-x * 14)
        sh = rng.standard_normal(e - s) * np.exp(-x * 60)
        sh = np.diff(np.concatenate([[0], sh]))  # crude highpass
        music[s:e] += 0.012 * sh
# music fades
mfade = np.minimum(1, tt / 0.8) * np.clip((DUR - tt) / 2.2, 0, 1)
music *= mfade
duck = (1 - 0.72 * act) * 0.85
music *= duck

# ---------------- sfx ----------------
sfx = np.zeros(N, np.float32)
def add(t0, sig, g=1.0):
    s = int(t0 * SR); e = min(N, s + len(sig)); sfx[s:e] += g * sig[:e - s]
def pop(f0=900, f1=500, d=0.09):
    x = np.arange(int(d * SR)) / SR; fr = f1 + (f0 - f1) * np.exp(-x * 40)
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-x * 35)
def tick(f=1800, d=0.05):
    x = np.arange(int(d * SR)) / SR; return np.sin(2 * np.pi * f * x) * np.exp(-x * 90)
def whoosh(d=0.5, up=True):
    x = np.arange(int(d * SR)) / SR; n = rng.standard_normal(len(x))
    # simple resonant-ish filter by moving average of varying length (approx): use two lowpasses
    lp = np.convolve(n, np.ones(12) / 12, mode='same'); hp = n - np.convolve(n, np.ones(60) / 60, mode='same')
    mix = (lp * (x / d) + hp * (1 - x / d)) if up else (hp * (x / d) + lp * (1 - x / d))
    e = np.sin(np.pi * x / d) ** 2
    return mix * e
def chime(notes=(76, 80, 83), d=1.2):
    x = np.arange(int(d * SR)) / SR; s = np.zeros(len(x))
    for i, m in enumerate(notes):
        f = mtof(m); o = int(i * 0.07 * SR)
        xx = x[:len(x) - o]
        s[o:] += (np.sin(2 * np.pi * f * xx) + 0.3 * np.sin(2 * np.pi * f * 2.76 * xx) * np.exp(-xx * 8)) * np.exp(-xx * 4)
    return s / 3
def buzz(d=0.28):
    x = np.arange(int(d * SR)) / SR
    s = np.sign(np.sin(2 * np.pi * 150 * x)) * 0.3 + np.sin(2 * np.pi * 155 * x)
    s = np.convolve(s, np.ones(8) / 8, mode='same')
    e = np.minimum(1, x / 0.01) * np.exp(-x * 8)
    return s * e

at = lambda i, f: CUES[i]['s'] + (CUES[i]['e'] - CUES[i]['s']) * f
S = lambda i: CUES[i]['s']
E = lambda i: CUES[i]['e']
sl = lambda i, f: CUES[i]['s'] + (CUES[i]['e'] - CUES[i]['s']) * f
def thud(d=0.35):
    x = np.arange(int(d * SR)) / SR; ph = 2 * np.pi * np.cumsum(45 + 120 * np.exp(-x * 25)) / SR
    return np.sin(ph) * np.exp(-x * 10)
add(S(0), whoosh(0.4), 0.08); add(at(0, .4), buzz(0.25), 0.12)
add(at(1, .2), tick(), 0.25)
add(S(2), whoosh(0.6), 0.12); add(at(3, .2), thud(), 0.22); add(at(3, .6), tick(), 0.3); add(at(3, .6) + .15, tick(1500), 0.25)
add(S(5), whoosh(0.6), 0.12); add(at(5, .5), pop(900, 500, 0.1), 0.25); add(at(6, .05), thud(), 0.2)
add(S(7), whoosh(0.6), 0.12); add(at(8, .3), pop(1000, 600), 0.25); add(at(8, .6), chime((79, 83), 0.8), 0.2)
add(S(9), whoosh(0.6), 0.12); add(at(10, .2), pop(1100, 650), 0.22); add(S(11), thud(), 0.18); add(at(11, .2), chime((76, 80, 83), 1.0), 0.2)
add(S(12), whoosh(0.5), 0.1); add(S(12) + .1, pop(), 0.3); add(S(13), pop(1300, 800, 0.07), 0.3)
add(OUTRO, whoosh(0.8), 0.1); add(OUTRO + .6, chime((72, 76, 79, 84), 1.6), 0.22)
mix = voice + music + sfx
st = np.stack([mix, mix], 1)
st = np.clip(st, -1, 1)
with wave.open(sys.argv[3] if len(sys.argv)>3 else 'mix_raw.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
# stem for voice-only processing check
print('peak', np.abs(mix).max())
