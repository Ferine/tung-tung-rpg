#!/usr/bin/env python3
"""Play a theme through an emulated SPC700 and measure what comes out.

The score is the composer's; this is the check on what the console does with
it. It builds a tiny ROM (audition/) that loads the same soundbank the game
does and plays whatever order it is told to, runs it in the Mesen-S libretro
core headless, and records the DSP's output at 32kHz. Then it says whether the
result is loud, clipped, or harsh -- the three things that turn a good score
into something you turn off:

    python3 audition.py                       every theme in res/
    python3 audition.py FIELD TITLE           just these (built from the score)
    python3 audition.py FIELD --seconds 90 --spectrogram

Needs PVSNESLIB_HOME (to build the ROM) and MESEN_S_CORE (the emulator core),
the same two the rest of the tooling uses. WAVs and the ROM land in
build/audition/.

What the numbers mean. LUFS is ITU BS.1770 loudness (K-weighted, gated):
-19 to -15 is a comfortable game soundtrack. Peak is the largest sample; it
must stay under 0dB or the DSP is clipping, which sounds like a crackle laid
over the top of everything. "presence" is the share of A-weighted energy in
2-6kHz, where the ear is most sensitive and a shrill trumpet lives; the score
was tuned to keep it under -11dB (-9.5 for combat), where the version this
replaced sat near -7.7. "centroid" is the A-weighted spectral centre of mass.
"""
import argparse
import ctypes
import math
import os
import re
import shutil
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, 'build', 'audition')

# thresholds that make the summary line say something
LUFS_RANGE = (-21.0, -13.0)
# quiet themes are allowed to be quiet: a held breath at -18 LUFS is not one
LUFS_BY_THEME = {'HUSH': (-27.0, -17.0), 'SALT': (-25.0, -15.0),
                 'FOREST': (-24.0, -14.0), 'FANFARE': (-22.0, -8.0)}
PEAK_MAX_DB = -1.0
PRESENCE_MAX = {'default': -11.0, 'combat': -9.5}
COMBAT = ('BATTLE', 'BOSS', 'FINAL', 'FINAL2', 'FORTRESS')


# ---- build ------------------------------------------------------------------

def _run(cmd, cwd, env):
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def build_rom(mod_dir, work=WORK):
    """Copy audition/ to `work`, drop the modules in, build aud.sfc. Returns
    (rom path, smconv's report as a dict)."""
    home = os.environ.get('PVSNESLIB_HOME')
    if not home:
        raise SystemExit("set PVSNESLIB_HOME to your pvsneslib install")
    env = dict(os.environ)
    if os.path.isdir(work):
        shutil.rmtree(work)
    shutil.copytree(os.path.join(HERE, 'audition'), work)
    os.makedirs(os.path.join(work, 'res'), exist_ok=True)
    for f in ('ttsfx.it', 'ttbgm.it', 'music.h'):
        shutil.copy(os.path.join(mod_dir, f), os.path.join(work, 'res', f))
    _, out = _run(['make', 'musics'], work, env)
    asm = os.path.join(work, 'res', 'soundbank.asm')
    if not os.path.exists(asm):
        raise SystemExit("smconv failed:\n" + out[-2500:])
    two = bool(re.search(r'^SOUNDBANK__0:', open(asm).read(), re.M))
    with open(os.path.join(work, 'bankdefs.h'), 'w') as f:
        f.write('#define TWO_BANKS 1\nextern char SOUNDBANK__0, SOUNDBANK__1;\n'
                if two else 'extern char SOUNDBANK__;\n')
    code, out2 = _run(['make'], work, env)
    rom = os.path.join(work, 'aud.sfc')
    if code or not os.path.exists(rom):
        raise SystemExit("audition ROM did not build:\n" + out2[-2500:])
    info = {'total': None, 'free': None}
    m = re.search(r'Total Modules Size: \[ *(\d+) bytes\]', out)
    if m:
        info['total'] = int(m.group(1))
    free = re.findall(r'\*(\d+) bytes free\*', out)
    if free:
        info['free'] = int(free[-1])
    return rom, info


# ---- the emulator -----------------------------------------------------------

class Rig:
    def __init__(self, rom):
        sys.path.insert(0, HERE)
        import capture
        core = os.environ.get('MESEN_S_CORE')
        if not core:
            raise SystemExit("set MESEN_S_CORE to the Mesen-S libretro core")
        self.core = capture.Core(core)
        self.core.lib.retro_get_memory_data.restype = ctypes.c_void_p
        self.core.lib.retro_get_memory_data.argtypes = [ctypes.c_uint]
        av = self.core.load(rom)
        self.rate = int(round(av.timing.sample_rate))
        self.fps = av.timing.fps
        self.ptr = self.core.lib.retro_get_memory_data(2)
        self.sym = {}
        for line in open(os.path.splitext(rom)[0] + '.sym'):
            p = line.split()
            if len(p) == 2:
                try:
                    self.sym[p[1]] = int(p[0], 16)
                except ValueError:
                    pass
        self.seq = 0
        self.core.run(900)      # spcLoad of ~50KB is a multi-frame transfer

    def _poke(self, name, v):
        ctypes.memset(self.ptr + self.sym[name] - 0x7e0000, v, 1)

    def send(self, kind, arg=0, vol=0):
        self._poke('cmdKind', kind)
        self._poke('cmdArg', arg)
        self._poke('cmdVol', vol)
        self.seq = (self.seq + 1) & 255
        self._poke('cmdSeq', self.seq)

    def play(self, order, seconds, lead=0.08):
        """The DSP's output for `seconds`, from order `order`. `lead` is the
        SPC's start-up latency (a few frames, plus the echo buffer being
        cleared); recording starts after it, so a theme's first note is heard."""
        self.send(2)
        self.core.run(90)                   # let the last theme's echo die
        self.send(1, order)
        self.core.run(int(lead * self.fps))
        self.core.record()
        self.core.run(int(seconds * self.fps))
        raw = b''.join(self.core.audio)
        self.core.audio = None
        return np.frombuffer(raw, dtype='<i2').reshape(-1, 2)


def write_wav(path, pcm, rate):
    w = wave.open(path, 'wb')
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(np.asarray(pcm).astype('<i2').tobytes())
    w.close()


# ---- measurement ------------------------------------------------------------

def _kweight_power_gain(f, rate):
    """|H|^2 of the two BS.1770 K-weighting biquads at frequencies `f`."""
    def mag2(b, a):
        w = 2 * np.pi * f / rate
        z = np.exp(-1j * w)
        num = b[0] + b[1] * z + b[2] * z * z
        den = a[0] + a[1] * z + a[2] * z * z
        return np.abs(num / den) ** 2
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = math.tan(math.pi * f0 / rate)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    s1 = mag2([(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0,
               (Vh - Vb * K / Q + K * K) / a0],
              [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0])
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / rate)
    a0 = 1 + K / Q + K * K
    s2 = mag2([1, -2, 1], [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0])
    return s1 * s2


def _kweight(x, rate):
    """K-weighted signal, by weighting the whole spectrum. Zero-phase, which
    is fine: loudness is a power measurement."""
    n = len(x)
    nfft = 1 << int(math.ceil(math.log2(n + 8)))
    spec = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / rate)
    return np.fft.irfft(spec * np.sqrt(_kweight_power_gain(f, rate)), nfft)[:n]


def _a_weight_power(f):
    f2 = f * f
    ra = (12194 ** 2 * f2 ** 2) / ((f2 + 20.6 ** 2) * np.sqrt(
        (f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    return ra ** 2


def measure(pcm, rate, skip=1.0):
    """Everything worth knowing about a render."""
    x = pcm.astype(np.float64) / 32768.0
    peak = float(np.abs(x).max())
    clip = int(((pcm == 32767) | (pcm == -32768)).any(axis=1).sum())

    kl, kr = _kweight(x[:, 0], rate), _kweight(x[:, 1], rate)
    blk, hop = int(0.4 * rate), int(0.1 * rate)
    ms = np.array([(kl[i:i + blk] ** 2).mean() + (kr[i:i + blk] ** 2).mean()
                   for i in range(0, len(kl) - blk, hop)] or [1e-12])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    g = lk[lk > -70]
    if len(g):
        rel = -0.691 + 10 * np.log10(np.mean(10 ** ((g + 0.691) / 10))) - 10
        g = g[g > rel]
    lufs = (-0.691 + 10 * np.log10(np.mean(10 ** ((g + 0.691) / 10)))
            if len(g) else -99.0)

    m = x.mean(axis=1)[int(rate * skip):]
    win = np.hanning(4096)
    acc = np.zeros(2049)
    cnt = 0
    for i in range(0, len(m) - 4096, 2048):
        acc += np.abs(np.fft.rfft(m[i:i + 4096] * win)) ** 2
        cnt += 1
    acc /= max(cnt, 1)
    f = np.fft.rfftfreq(4096, 1.0 / rate)
    band = (f > 50) & (f < 12000)
    a = acc * _a_weight_power(np.maximum(f, 1.0))
    tot = a[band].sum() + 1e-20
    pres = a[(f > 2000) & (f < 6000)].sum() / tot
    top = a[(f > 4000) & (f < 12000)].sum() / tot
    # Dropouts: places where everything goes quiet at once for a moment
    # (below a twelfth of the median level, 60ms or more). A voice that ends
    # one row early, or a note cut instead of released, leaves one at every
    # bar line, and it does not show in a loudness figure.
    blk5 = int(0.005 * rate)
    mono = x.mean(axis=1)
    nb = len(mono) // blk5
    lvl = np.sqrt((mono[:nb * blk5].reshape(nb, blk5) ** 2).mean(axis=1))
    med = float(np.median(lvl)) or 1e-9
    quiet = np.nonzero(lvl < 0.08 * med)[0]
    quiet = quiet[quiet > int(skip / 0.005)]
    gaps, run = [], []
    for i in quiet:
        if run and i - run[-1] > 2:
            gaps.append(run)
            run = []
        run.append(i)
    if run:
        gaps.append(run)
    # a dip *inside* sustained music, not composed silence. Plucks and drum
    # strokes decay to nothing between hits and a sparse intro is mostly
    # rests, and neither is a hole. A hole has continuous material either
    # side: the quiet quarter of the surrounding two seconds is still an
    # ordinary level, i.e. something was holding the sound up until it wasn't.
    def loud_around(g):
        a0, b0 = g[0], g[-1] + 1
        near = np.concatenate([lvl[max(0, a0 - 200):a0], lvl[b0:b0 + 200]])
        if len(near) < 100:
            return False
        return float(np.percentile(near, 25)) > 0.35 * med
    gaps = [g for g in gaps if len(g) * 5 >= 60 and loud_around(g)]
    return dict(
        gaps=len(gaps), gap_at=[round(g[0] * 0.005, 1) for g in gaps[:6]],
        peak_db=20 * math.log10(peak + 1e-12), clip=clip, lufs=float(lufs),
        presence=10 * math.log10(pres + 1e-12),
        top=10 * math.log10(top + 1e-12),
        centroid=float((a * f)[band].sum() / tot),
        seconds=len(x) / float(rate))


def verdict(name, m):
    bad = []
    if m['clip']:
        bad.append("CLIPS x%d" % m['clip'])
    if m['peak_db'] > PEAK_MAX_DB:
        bad.append("peak %.1fdB" % m['peak_db'])
    lo, hi = LUFS_BY_THEME.get(name, LUFS_RANGE)
    if not lo <= m['lufs'] <= hi:
        bad.append("loudness %.1f LUFS" % m['lufs'])
    if m['gaps']:
        bad.append("%d dropouts (first at %s s)" % (m['gaps'], m['gap_at']))
    lim = PRESENCE_MAX['combat' if name in COMBAT else 'default']
    if m['presence'] > lim:
        bad.append("harsh %.1fdB (limit %.1f)" % (m['presence'], lim))
    return bad


def themes_from_header(path):
    d = {}
    for m in re.finditer(r'#define MUS_(\w+)_(FIRST|LAST)\s+(\d+)',
                         open(path).read()):
        d.setdefault(m.group(1), {})[m.group(2)] = int(m.group(3))
    return {k: (v['FIRST'], v['LAST']) for k, v in d.items()}


def spectrogram(wavs, out):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("(no matplotlib: skipping the spectrogram)")
        return
    fig, ax = plt.subplots(len(wavs), 1, figsize=(13, 3.2 * len(wavs)))
    ax = [ax] if len(wavs) == 1 else ax
    for a, (name, path) in zip(ax, wavs):
        w = wave.open(path)
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2)
        a.specgram(x.mean(axis=1) / 32768.0, NFFT=2048, Fs=w.getframerate(),
                   noverlap=1536, cmap='magma', vmin=-130, vmax=-30)
        a.set_ylim(0, 8000)
        a.set_title(name)
        a.set_ylabel('Hz')
    plt.tight_layout()
    plt.savefig(out, dpi=70)
    print("spectrogram: " + out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('themes', nargs='*', help='themes to play (default: all)')
    ap.add_argument('--seconds', type=float, default=70.0)
    ap.add_argument('--work', default=WORK, help='build directory')
    ap.add_argument('--spectrogram', action='store_true')
    ap.add_argument('--modules', help='directory holding ttsfx.it, ttbgm.it, '
                    'music.h (default: res/, or a fresh build if THEMES given)')
    args = ap.parse_args(argv)

    want = [t.upper() for t in args.themes]
    mods = args.modules
    if not mods:
        if want:
            import gen_music
            # beside the work directory, not inside it: build_rom clears that
            mods = args.work.rstrip('/') + '-modules'
            os.makedirs(mods, exist_ok=True)
            gen_music.main(['--only'] + want + ['--out', mods])
        else:
            mods = os.path.join(HERE, 'res')
    rom, info = build_rom(mods, args.work)
    if info['total']:
        print("soundbank: %d bytes; %s free in the SPC's 64KB"
              % (info['total'], info['free']))
    themes = themes_from_header(os.path.join(mods, 'music.h'))
    order = want or list(themes)
    for t in order:
        if t not in themes:
            raise SystemExit("no theme %s in %s (have %s)"
                             % (t, mods, ', '.join(themes)))

    rig = Rig(rom)
    wavdir = os.path.join(args.work, 'wavs')
    os.makedirs(wavdir, exist_ok=True)
    print("%-9s %7s %6s %7s %9s %8s %6s %5s" % (
        'theme', 'peak', 'LUFS', 'clip', 'presence', 'centroid', 'sec',
        'gaps'))
    made = []
    failed = 0
    for t in order:
        first, last = themes[t]
        pcm = rig.play(first, args.seconds)
        path = os.path.join(wavdir, t.lower() + '.wav')
        write_wav(path, pcm, rig.rate)
        made.append((t, path))
        m = measure(pcm, rig.rate)
        bad = verdict(t, m)
        failed += bool(bad)
        print("%-9s %5.1fdB %6.1f %7d %7.1fdB %6.0fHz %6.1f %5d  %s" % (
            t, m['peak_db'], m['lufs'], m['clip'], m['presence'],
            m['centroid'], m['seconds'], m['gaps'], '; '.join(bad) or 'ok'))
    if args.spectrogram and made:
        spectrogram(made, os.path.join(args.work, 'spectrogram.png'))
    print("wavs: " + wavdir)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
