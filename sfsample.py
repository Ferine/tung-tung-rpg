#!/usr/bin/env python3
"""Condition real instrument recordings into SNES-sized samples.

The sources are CC0 orchestral libraries -- Versilian's VSCO-2-CE and VCSL,
both released under CC0-1.0, which is the only licence that actually permits
cutting a recording up and shipping the pieces inside a ROM. See SAMPLES.md.

This is how the 16-bit RPG soundtracks were made in the first place. FF6 and
Chrono Trigger are not synthesised: they are real recordings cut down to a few
hundred bytes each, looped, and played back through the SPC700's Gaussian
interpolation. Doing the same thing to the same kind of material is what makes
the result sound like 1994 rather than like a chiptune.

What has to happen to a 10-second 44.1kHz stereo WAV before it is a SNES
instrument, and what went wrong the first time each step was done carelessly:

  * mono, because the DSP's stereo is a per-voice pan of a mono sample
  * a real low-pass before decimation. A box average is not one: everything
    above the new Nyquist folds back into the band, and on a bowed string that
    is a fixed shimmer of inharmonic partials under every note. It is the
    difference between "sampled violin" and "broken radio".
  * an attack followed by a loop that is *contiguous* with it. The loop used to
    be cut a whole loop-length past the attack, so every note ticked once, about
    fifty milliseconds in, where the two did not meet.
  * a loop that is an exact whole number of the instrument's own periods, on
    16-sample BRR block boundaries, crossfaded across the seam
  * a loop seam that agrees with what precedes the loop. smconv's BRR encoder
    predicts each block from the samples before it, and at the wrap those are
    the *end* of the loop, not the attack. If the two differ the first loop
    block is decoded wrong on every pass -- a click at the loop rate.

`C5Speed` then carries the pitch: it is the rate at which the DSP reads the
sample for tracker note 60, so a recording of a C3 and a recording of a C6
both play in tune from the same note number.
"""
import math
import os
import struct

try:
    import numpy as np
except ImportError:                                     # pragma: no cover
    raise SystemExit("the audio pipeline needs numpy: pip install numpy")

import itwriter as it

BLOCK = 16          # BRR block, in samples

# ---- notes --------------------------------------------------------------

_SEMI = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def note_hz(name):
    """"C4" -> 261.63. A4 = 440, and C4 is middle C -- the same convention the
    sample libraries name their files with."""
    letter = name[0].upper()
    i = 1
    semi = _SEMI[letter]
    while i < len(name) and name[i] in '#b':
        semi += 1 if name[i] == '#' else -1
        i += 1
    octave = int(name[i:])
    midi = (octave + 1) * 12 + semi
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


# ---- wav ----------------------------------------------------------------

def read_wav(path, max_seconds=None):
    """Mono float64 in [-1,1], plus the rate. Handles the 16/24/32-bit PCM and
    32-bit float the Versilian libraries ship; anything else is a hard error
    rather than a quietly wrong sample."""
    raw = open(path, 'rb').read()
    if raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise SystemExit("%s: not a RIFF/WAVE file" % path)

    fmt = None
    data = None
    i = 12
    while i + 8 <= len(raw):
        cid = raw[i:i + 4]
        size = struct.unpack_from('<I', raw, i + 4)[0]
        body = raw[i + 8:i + 8 + size]
        if cid == b'fmt ':
            fmt = struct.unpack_from('<HHIIHH', body, 0)
            if fmt[0] == 0xFFFE and len(body) >= 26:      # WAVE_FORMAT_EXTENSIBLE
                fmt = (struct.unpack_from('<H', body, 24)[0],) + fmt[1:]
        elif cid == b'data':
            data = body
        i += 8 + size + (size & 1)

    if fmt is None or data is None:
        raise SystemExit("%s: missing fmt or data chunk" % path)
    tag, chans, rate, _bps, _align, bits = fmt
    width = bits // 8
    frame = width * chans
    n = len(data) // frame
    if max_seconds:
        n = min(n, int(rate * max_seconds))
    data = data[:n * frame]

    if tag == 1 and bits == 16:
        a = np.frombuffer(data, dtype='<i2').astype(np.float64) / 32768.0
    elif tag == 1 and bits == 24:
        b = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        a = v.astype(np.float64) / 8388608.0
    elif tag == 1 and bits == 32:
        a = np.frombuffer(data, dtype='<i4').astype(np.float64) / 2147483648.0
    elif tag == 3 and bits == 32:
        a = np.frombuffer(data, dtype='<f4').astype(np.float64)
    else:
        raise SystemExit("%s: format tag %d, %d-bit not handled"
                         % (path, tag, bits))
    return a.reshape(-1, chans).mean(axis=1), rate


# ---- dsp ----------------------------------------------------------------

def _kaiser_sinc(u, fc, zeros, beta=9.0):
    """Windowed-sinc low-pass kernel, cutoff `fc` in cycles/sample, evaluated
    at offsets `u` (in samples) with `zeros` zero crossings either side."""
    half = zeros / (2.0 * fc)
    x = np.clip(u / half, -1.0, 1.0)
    win = np.i0(beta * np.sqrt(1.0 - x * x)) / np.i0(beta)
    return 2.0 * fc * np.sinc(2.0 * fc * u) * win


def sample_at(x, sr, positions, fc_hz, zeros=12):
    """x evaluated at fractional `positions` (in samples of x), low-passed at
    `fc_hz` on the way. This is the one resampler everything uses: the same
    filter whether the ratio is 1:4.9 or 1:1.003, and correctly band-limited
    in both cases."""
    fc = min(fc_hz / float(sr), 0.5)
    half = int(math.ceil(zeros / (2.0 * fc)))
    positions = np.asarray(positions, dtype=np.float64)
    base = np.floor(positions).astype(np.int64) - half + 1
    taps = np.arange(2 * half)
    out = np.zeros(len(positions))
    pad = np.concatenate([np.zeros(half + 2), x, np.zeros(half + 2)])
    chunk = max(1, 400000 // (2 * half))
    for a in range(0, len(positions), chunk):
        b = min(a + chunk, len(positions))
        idx = base[a:b, None] + taps[None, :]
        u = idx - positions[a:b, None]
        h = _kaiser_sinc(u, fc, zeros)
        out[a:b] = (pad[idx + half + 2] * h).sum(axis=1)
    return out


def resample(buf, src, dst, cutoff=None):
    """Whole-buffer rate change with a proper anti-alias filter."""
    if src == dst and cutoff is None:
        return np.asarray(buf, dtype=np.float64).copy()
    ratio = src / float(dst)
    n = int(len(buf) / ratio)
    fc = min(0.5 * dst * 0.92, cutoff or 1e9, 0.5 * src)
    return sample_at(np.asarray(buf, dtype=np.float64), src,
                     np.arange(n) * ratio, fc)


def normalise(buf, peak=0.95):
    m = float(np.abs(buf).max()) if len(buf) else 0.0
    if m < 1e-9:
        return np.asarray(buf).copy()
    return buf * (peak / m)


def onset(buf, thresh=0.02):
    """First sample above the threshold, backed off a little so the attack
    transient is not clipped off the front."""
    hit = np.nonzero(np.abs(buf) > thresh)[0]
    return max(0, int(hit[0]) - 8) if len(hit) else 0


def shape(buf, sr, hp=25.0, tilt_db=0.0, pivot=1000.0):
    """Zero-phase spectral shaping of a source excerpt: a high-pass to keep DC
    and rumble out of 4-bit samples, and an optional gentle tilt (dB per
    octave above `pivot`) for instruments whose recordings are brighter than
    they are pleasant once every note is pitched around the keyboard."""
    n = len(buf)
    nfft = 1 << int(math.ceil(math.log2(n + 8)))
    spec = np.fft.rfft(buf, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    gain = np.ones_like(f)
    if hp:
        gain *= 1.0 / np.sqrt(1.0 + (hp / np.maximum(f, 1e-3)) ** 4)
    if tilt_db:
        oct_ = np.log2(np.maximum(f, pivot) / pivot)
        gain *= 10.0 ** (tilt_db * oct_ / 20.0)
    return np.fft.irfft(spec * gain, nfft)[:n]


def detect_f0(buf, rate, lo=40.0, hi=1500.0, start=None, seconds=0.30):
    """Fundamental, by YIN's cumulative mean normalised difference, refined by
    measuring the period over several repeats.

    Plain autocorrelation does not work here and fails in a way that looks like
    success: normalised correlation is ~1 at small lags for any smooth
    waveform, so "the lowest lag that correlates well" is always a few samples
    and every sustained instrument comes back an octave or more sharp.

    Only a check on the label, and the loop-length arithmetic: an instrument a
    semitone out is not something anybody notices until the whole soundtrack
    is built around it."""
    n = len(buf)
    win = int(rate * seconds)
    if n < win + int(rate / lo) + 8:
        return None
    s0 = int(n * 0.3) if start is None else start
    s0 = max(0, min(s0, n - win - 1))
    w = buf[s0:s0 + win + int(rate / lo) + 4]
    w = w - w.mean()

    tau_max = min(len(w) // 2, int(rate / lo))
    W = len(w) - tau_max
    if W < 256:
        return None
    a = w[:W]
    cs = np.concatenate([[0.0], np.cumsum(w * w)])
    ea = cs[W]
    nfft = 1 << int(math.ceil(math.log2(len(w) + W)))
    cross = np.fft.irfft(np.fft.rfft(w, nfft) * np.conj(np.fft.rfft(a, nfft)),
                         nfft)[:tau_max + 1]
    taus = np.arange(tau_max + 1)
    eb = cs[taus + W] - cs[taus]
    d = ea + eb - 2.0 * cross
    d[0] = 0.0
    run = np.cumsum(d)
    dn = np.ones_like(d)
    dn[1:] = d[1:] * taus[1:] / np.maximum(run[1:], 1e-12)

    tau_min = max(2, int(rate / hi))
    best = None
    for t in range(tau_min, tau_max - 1):
        if dn[t] < 0.15 and dn[t] <= dn[t + 1] and dn[t] <= dn[t - 1]:
            best = t
            break
    if best is None:
        best = int(tau_min + np.argmin(dn[tau_min:tau_max]))
        if dn[best] > 0.6:
            return None
    if 1 < best < tau_max:
        a_, b_, c_ = dn[best - 1], dn[best], dn[best + 1]
        den = 2 * (2 * b_ - a_ - c_)
        if abs(den) > 1e-12:
            best = best + (a_ - c_) / den
    return _refine(buf, rate, rate / best, s0)


def _refine(buf, rate, coarse, start, repeats=6):
    """Sharpen a period estimate by matching the waveform against itself
    `repeats` periods later: the error in the estimate is divided by the
    number of periods spanned, so a 0.05-sample lag error becomes 0.01."""
    tau0 = rate / coarse
    span = int(rate * 0.25)
    m = max(1, min(repeats, int((len(buf) - start - span) / tau0) - 1))
    n = span - int(m * tau0 * 1.02) - 2
    if n < 64:
        return coarse
    ref = buf[start:start + n]
    best_t, best_d = None, None
    for T in np.arange(m * tau0 * 0.985, m * tau0 * 1.015, 0.02):
        i0 = int(T)
        fr = T - i0
        seg = buf[start + i0:start + i0 + n + 1]
        if len(seg) < n + 1:
            continue
        val = seg[:-1] * (1 - fr) + seg[1:] * fr
        dd = float(((ref - val) ** 2).sum())
        if best_d is None or dd < best_d:
            best_d, best_t = dd, T
    return rate / (best_t / m) if best_t else coarse


# ---- sample construction ------------------------------------------------

def _align(n):
    return (n // BLOCK) * BLOCK


def _smooth(n):
    """Smoothstep 0->1 over n samples, no corner at either end."""
    w = (np.arange(n) + 1.0) / n
    return w * w * (3 - 2 * w)


def looped(path, label=None, p=32, attack_ms=60, loop_ms=100, max_loop=640,
           steady_ms=None, bw_harm=None, tilt_db=0.0, peak=0.95,
           crest=1.6, check=True, max_seconds=6.0):
    """A sustained instrument: a short attack followed by a loop that is an
    exact whole number of the instrument's own periods.

    `p` is samples per cycle in the stored sample, and it is the one number
    that decides how the instrument sounds: p/2 harmonics survive, so p=32 is
    sixteen partials -- a mellow horn -- and p=64 is thirty-two. It also fixes
    the storage cost: bytes scale with p * f0, so a bass at p=32 is nearly free
    and a piccolo at p=32 is not.

    Why a loop has to hold whole periods: a loop can only re-enter at a BRR
    block boundary, so its length is a multiple of 16 -- and 16 has no reason
    to divide the period of a violin. Cut the loop at a round number of samples
    and it is 11.5 periods long, so every wrap restarts the waveform half a
    cycle out of phase; a crossfade hides the click but not the pitch, and
    what you hear is the loop frequency itself, a warble under a sustained
    note. So: pick the number of periods k, round k*p to a multiple of 16 to
    get the loop length L, and resample the source so that k periods fit that
    length exactly.

    C5Speed then falls out as note_hz('C4') * (L / k): samples per cycle times
    the frequency wanted at tracker note 60 (middle C).
    """
    src, sr = read_wav(path, max_seconds=max_seconds)
    src = src[onset(src):]
    src = shape(src, sr, hp=25.0, tilt_db=tilt_db)

    s_ms = steady_ms if steady_ms is not None else max(attack_ms + 250, 450)
    f0 = detect_f0(src, sr, start=int(sr * s_ms / 1000.0))
    if not f0:
        f0 = detect_f0(src, sr)
    if not f0:
        raise SystemExit("%s: no detectable pitch, cannot build a loop"
                         % os.path.basename(path))
    if check and label:
        want = note_hz(label)
        cents = 1200 * math.log(f0 / want, 2)
        if abs(cents) > 60:
            raise SystemExit(
                "%s: labelled %s (%.1f Hz) but measures %.1f Hz, %+d cents"
                % (os.path.basename(path), label, want, f0, cents))

    # k whole periods in a loop of L = 16m samples: p' = L/k is p, nudged.
    k = max(2, int(round(f0 * loop_ms / 1000.0)))
    while int(round(k * p / BLOCK)) * BLOCK > max_loop and k > 2:
        k -= 1
    L = max(BLOCK, int(round(k * p / BLOCK)) * BLOCK)
    pp = L / float(k)                       # samples per cycle, exactly
    real_rate = f0 * pp                     # the rate that makes that true
    step = sr / real_rate                   # source samples per stored sample

    H = max(2 * BLOCK, _align(int(real_rate * attack_ms / 1000.0)))
    c = min(H - BLOCK, max(BLOCK, int(2 * pp)))     # splice window, ~2 cycles
    m = min(L // 2, max(BLOCK, int(3 * pp)))        # loop crossfade, ~3 cycles

    # where the steady tone lives, in stored samples
    J_nom = int(real_rate * s_ms / 1000.0)
    span = int(pp * 3)
    total_src = len(src) / step
    if J_nom + L + span + 8 > total_src:
        J_nom = int(total_src - L - span - 8)
    if J_nom < H + 2 * m:
        raise SystemExit("%s: %d source samples is too short for this loop"
                         % (os.path.basename(path), len(src)))

    lo, hi = max(H + c, m + 1, J_nom - span), J_nom + span
    stored = sample_at(src, sr, np.arange(hi + L + 4) * step,
                       min(0.46 * real_rate, sr * 0.45, real_rate * 0.5))
    if bw_harm:
        # optional further band limit, in harmonics of f0, for bright sources
        stored = _bandlimit(stored, real_rate, bw_harm * f0)

    # pick the loop start J where the source is most periodic over L, and
    # where the splice window agrees best with the tail of the attack.
    best_j, best_s = lo, None
    tailH = stored[H - c:H]
    for j in range(lo, hi):
        a = stored[j + L - m:j + L]
        b = stored[j - m:j]
        d_loop = float(((a - b) ** 2).sum())
        d_join = float(((stored[j - c:j] - tailH) ** 2).sum())
        sc = d_loop + 0.5 * d_join
        if best_s is None or sc < best_s:
            best_j, best_s = j, sc
    J = best_j

    head = stored[:H].copy()
    body = stored[J:J + L].copy()
    pre_c = stored[J - c:J]
    pre_m = stored[J - m:J]

    # attack -> loop: the last c samples of the head are blended to the
    # steady-state samples that precede the loop start, so head and loop meet
    # without a step. The final samples are *exactly* pre_c, which is what the
    # BRR predictor sees at the loop start on the first pass.
    r_head = float(np.sqrt((tailH ** 2).mean())) or 1e-9
    r_pre = float(np.sqrt((pre_c ** 2).mean())) or 1e-9
    g = min(2.0, max(0.5, r_pre / r_head))
    q = max(BLOCK, H // 4)
    head[H - q:] *= 1.0 + (g - 1.0) * _smooth(q)
    w = _smooth(c)
    head[H - c:] = head[H - c:] * (1 - w) + pre_c * w
    head[H - 4:] = pre_c[-4:]

    # loop -> loop: the same for the wrap, so the last samples of the body are
    # what preceded its first sample, i.e. the decoder's state at the wrap
    # equals the state it was encoded with.
    w = _smooth(m)
    body[L - m:] = body[L - m:] * (1 - w) + pre_m * w
    body[L - 4:] = pre_m[-4:]

    data = np.concatenate([head, body])

    # attack transients are much taller than the sustained tone; leave the
    # tone as loud as 4-bit BRR resolution wants and squash only the peaks
    lvl = float(np.abs(body).max()) or 1.0
    ceil = crest * lvl
    over = np.abs(data) > ceil
    if over.any():
        data = np.where(over, np.sign(data) * (ceil + (np.abs(data) - ceil) * 0.35),
                        data)
    data = normalise(data, peak)

    c4 = int(round(note_hz('C4') * pp))
    s = it.Sample(os.path.basename(path)[:24], data.tolist(), c4,
                  loop=True, loop_start=H)
    s.cycle = pp
    s.periods = k
    s.f0 = f0
    s.root = 'C4'           # note 60 sounds middle C
    return s


def _bandlimit(x, rate, cutoff):
    n = len(x)
    nfft = 1 << int(math.ceil(math.log2(n + 8)))
    spec = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1.0 / rate)
    spec *= 1.0 / (1.0 + (f / cutoff) ** 8)
    return np.fft.irfft(spec, nfft)[:n]


def spectral_pitch(buf, sr, hint_hz, t0=0.04, t1=0.6):
    """Strongest partial near `hint_hz`, refined to a fraction of a cent.

    For struck bars, plucked strings and the like the fundamental is the
    strongest partial in the first half second, and unlike a period detector
    this does not care that the waveform is not periodic. It is a measurement,
    not a search: it looks only within an octave of the hint."""
    a, b = int(sr * t0), int(sr * t1)
    seg = buf[a:b]
    if len(seg) < 512:
        return None
    seg = seg * np.hanning(len(seg))
    nfft = 1 << 18
    mag = np.abs(np.fft.rfft(seg, nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    band = (f > hint_hz * 0.7) & (f < hint_hz * 1.42)
    if not band.any():
        return None
    i = int(np.argmax(np.where(band, mag, 0.0)))
    if 0 < i < len(mag) - 1:
        la, lb, lc = (math.log(mag[i - 1] + 1e-12), math.log(mag[i] + 1e-12),
                      math.log(mag[i + 1] + 1e-12))
        den = la - 2 * lb + lc
        if abs(den) > 1e-12:
            return f[i] + 0.5 * (la - lc) / den * (f[1] - f[0])
    return f[i]


def oneshot(path, rate=10000, ms=260, tail_ms=40, peak=0.95, label=None,
            tilt_db=0.0, lp=None, attack_thresh=0.01, measure='spectrum'):
    """Percussion and plucks: trimmed to the hit, low-passed properly, faded
    out at the end so the sample does not stop on a non-zero value and click.

    `label` is the sounding pitch of the recording. A pitched one-shot is then
    tuned so tracker note 60 plays middle C -- the same convention as the
    sustained instruments -- and unpitched percussion (label None) is simply
    triggered at note 60 and plays at the stored rate.

    With `measure` the label is checked and the *measured* pitch is what the
    sample is tuned to ('spectrum' for bars, 'yin' for strings -- the period
    detector, since a plucked string's transient is not a partial): zither strings and marimba bars are
    not on the equal-tempered grid, and a marimba fifty cents flat is not
    something a tuning table can hide. Bells pass measure=False, because the
    pitch a tubular bell is heard at is not its strongest partial."""
    src, sr = read_wav(path)
    src = src[onset(src, attack_thresh):]
    src = shape(src, sr, hp=25.0, tilt_db=tilt_db)
    f_true = note_hz(label) if label else None
    if label and measure:
        if measure == 'yin':
            fm = detect_f0(src, sr, lo=60.0, start=int(sr * 0.06),
                           seconds=0.25)
        else:
            fm = spectral_pitch(src, sr, note_hz(label))
        cents = 1200 * math.log(fm / f_true, 2) if fm else 9999
        if abs(cents) > 60:
            raise SystemExit("%s: labelled %s (%.1f Hz) but measures %s"
                             % (os.path.basename(path), label, f_true,
                                "%.1f Hz, %+d cents" % (fm, cents) if fm
                                else "nothing"))
        f_true = fm
    buf = resample(src, sr, rate, cutoff=lp)

    n = _align(int(rate * ms / 1000.0))
    n = min(n, _align(len(buf)))
    buf = buf[:n]

    tail = min(len(buf), int(rate * tail_ms / 1000.0))
    w = np.arange(tail) / float(tail)
    buf[len(buf) - tail:] *= (1.0 - w) ** 2
    buf = normalise(buf, peak)

    c5 = int(round(rate * (note_hz('C4') / f_true))) if label else rate
    s = it.Sample(os.path.basename(path)[:24], buf.tolist(), c5, loop=False)
    s.root = label
    s.f0 = f_true
    return s


def brr_bytes(sample):
    """What this sample will cost in ARAM once smconv has packed it: nine
    bytes per sixteen samples, and there are only 64KB of the stuff."""
    return ((len(sample.data) + BLOCK - 1) // BLOCK) * 9
