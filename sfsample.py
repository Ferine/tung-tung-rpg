#!/usr/bin/env python3
"""Condition real instrument recordings into SNES-sized looped samples.

The sources are CC0 orchestral libraries -- Versilian's VSCO-2-CE and VCSL,
both released under CC0-1.0, which is the only licence that actually permits
cutting a recording up and shipping the pieces inside a ROM. See SAMPLES.md.

This is how the 16-bit RPG soundtracks were made in the first place. FF6 and
Chrono Trigger are not synthesised: they are real orchestral recordings cut
down to a few hundred bytes each, looped, and played back through the SPC700's
Gaussian interpolation. Doing the same thing to the same kind of material is
what makes the result sound like 1994 rather than like a chiptune.

What has to happen to a 10-second 44.1kHz stereo WAV before it is a SNES
instrument:

  * mono, because the DSP's stereo is a per-voice pan of a mono sample
  * down to 8-16kHz, because 64KB of ARAM holds the entire soundtrack
  * cut to an attack plus a loop of a few hundred samples
  * loop points on 16-sample boundaries, because BRR is a 16-sample block
    format and the loop can only re-enter at a block start
  * a crossfade across the loop seam, because a loop cut at an arbitrary point
    of a real recording clicks once per cycle otherwise

`C5Speed` then carries the pitch: the DSP is told how fast to read the sample
for note C5, so a recording of a C3 and a recording of a C6 both play in tune
from the same tracker note.
"""
import math
import os
import struct

import itwriter as it

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
    """Mono float in [-1,1], plus the rate. Handles the 16- and 24-bit PCM the
    Versilian libraries ship; anything else is a hard error rather than a
    quietly wrong sample.

    `max_seconds` stops early. These are ten-second recordings and the SNES
    wants a tenth of a second of each, so decoding all of them in full costs
    about thirty seconds of every asset build for material that is thrown
    away."""
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
        elif cid == b'data':
            data = body
        i += 8 + size + (size & 1)

    if fmt is None or data is None:
        raise SystemExit("%s: missing fmt or data chunk" % path)
    tag, chans, rate, _bps, _align, bits = fmt
    if tag != 1:
        raise SystemExit("%s: compressed WAV (tag %d), want PCM" % (path, tag))

    width = bits // 8
    frame = width * chans
    n = len(data) // frame
    if max_seconds:
        n = min(n, int(rate * max_seconds))
    out = [0.0] * n

    if bits == 16:
        scale = 1.0 / 32768.0
        for f in range(n):
            base = f * frame
            acc = 0
            for c in range(chans):
                acc += struct.unpack_from('<h', data, base + c * 2)[0]
            out[f] = acc * scale / chans
    elif bits == 24:
        scale = 1.0 / 8388608.0
        for f in range(n):
            base = f * frame
            acc = 0
            for c in range(chans):
                o = base + c * 3
                v = data[o] | (data[o + 1] << 8) | (data[o + 2] << 16)
                if v & 0x800000:
                    v -= 0x1000000
                acc += v
            out[f] = acc * scale / chans
    else:
        raise SystemExit("%s: %d-bit PCM not handled" % (path, bits))

    return out, rate


# ---- dsp ----------------------------------------------------------------

def resample(buf, src, dst):
    """Linear interpolation with a box pre-filter when decimating.

    Going from 44.1kHz to 10kHz without the pre-filter folds everything above
    5kHz back down into the audible band, which on a bowed string is a lot of
    energy and sounds like a broken radio."""
    if src == dst:
        return list(buf)
    ratio = src / float(dst)
    n = int(len(buf) / ratio)
    out = [0.0] * n

    if ratio > 1.0:
        w = int(ratio)          # average this many input samples per output
        for i in range(n):
            p = i * ratio
            j = int(p)
            acc = 0.0
            cnt = 0
            for k in range(j, min(j + w, len(buf))):
                acc += buf[k]
                cnt += 1
            out[i] = acc / cnt if cnt else 0.0
    else:
        for i in range(n):
            p = i * ratio
            j = int(p)
            f = p - j
            a = buf[j] if j < len(buf) else 0.0
            b = buf[j + 1] if j + 1 < len(buf) else a
            out[i] = a + (b - a) * f
    return out


def normalise(buf, peak=0.92):
    m = max((abs(v) for v in buf), default=0.0)
    if m < 1e-9:
        return list(buf)
    k = peak / m
    return [v * k for v in buf]


def onset(buf, thresh=0.02):
    """First sample above the threshold, backed off a little so the attack
    transient is not clipped off the front."""
    for i, v in enumerate(buf):
        if abs(v) > thresh:
            return max(0, i - 8)
    return 0


def detect_f0(buf, rate, lo=40.0, hi=1400.0):
    """Fundamental, by YIN's cumulative mean normalised difference.

    Plain autocorrelation does not work here and fails in a way that looks
    like success. Normalised correlation is ~1 at small lags for any smooth
    waveform, so "the lowest lag that correlates well" is always a few samples
    -- every sustained instrument comes back an octave or more sharp, and
    consistently enough that it reads as the sample library being mislabelled
    rather than the detector being wrong.

    YIN divides the difference function by its own running mean, which pushes
    d'(tau) towards 1 at small lags and leaves a clear dip at the true period.

    Only a check: the note comes from the filename. But an instrument a
    semitone out is not something anybody notices until the whole soundtrack
    is built around it.
    """
    work = resample(buf, rate, 11025) if rate > 11025 else list(buf)
    wr = 11025 if rate > 11025 else rate

    n = len(work)
    if n < 4096:
        return None
    start = min(n // 3, n - 3072)
    w = work[start:start + 3072]
    mean = sum(w) / len(w)
    w = [v - mean for v in w]

    tau_max = min(len(w) // 2, int(wr / lo))
    tau_min = max(2, int(wr / hi))

    d = [0.0] * (tau_max + 1)
    half = len(w) // 2
    for tau in range(1, tau_max + 1):
        acc = 0.0
        for i in range(half):
            diff = w[i] - w[i + tau]
            acc += diff * diff
        d[tau] = acc

    # cumulative mean normalisation
    dn = [1.0] * (tau_max + 1)
    run = 0.0
    for tau in range(1, tau_max + 1):
        run += d[tau]
        dn[tau] = d[tau] * tau / run if run > 1e-12 else 1.0

    best = None
    for tau in range(tau_min, tau_max):
        if dn[tau] < 0.15 and dn[tau] <= dn[tau + 1] and dn[tau] <= dn[tau - 1]:
            best = tau
            break
    if best is None:
        cand = range(tau_min, tau_max + 1)
        best = min(cand, key=lambda t: dn[t])
        if dn[best] > 0.6:
            return None

    # parabolic interpolation around the dip, for sub-sample accuracy
    if 1 < best < tau_max:
        a, b, c = dn[best - 1], dn[best], dn[best + 1]
        denom = 2 * (2 * b - a - c)
        if abs(denom) > 1e-12:
            best = best + (a - c) / denom
    coarse = wr / best

    # The coarse pass runs at 11kHz, where a 590Hz tone sits at lag 18 and one
    # lag step is 26Hz -- 75 cents. That is not good enough to tune an
    # instrument with: the loop is built to hold a whole number of periods, so
    # an f0 that is 40 cents out puts a fractional period in the loop and the
    # sample plays 40 cents sharp for the rest of the game. So refine at the
    # original rate, where the same tone sits at lag 75 and the steps are four
    # times finer, searching only near the answer we already have.
    return _refine(buf, rate, coarse)


def _refine(buf, rate, coarse, span=0.25):
    tau0 = rate / coarse
    lo = max(2, int(tau0 * (1 - span)))
    hi = int(tau0 * (1 + span)) + 2
    n = min(len(buf), int(rate * 0.12))
    start = max(0, min(len(buf) - n - hi, len(buf) // 3))
    w = buf[start:start + n]
    if len(w) < hi * 4:
        return coarse
    mean = sum(w) / len(w)
    w = [v - mean for v in w]

    half = len(w) - hi
    d = {}
    for tau in range(lo, hi):
        acc = 0.0
        for i in range(0, half, 2):        # every other sample: same minimum
            diff = w[i] - w[i + tau]
            acc += diff * diff
        d[tau] = acc
    best = min(d, key=lambda t: d[t])
    if lo < best < hi - 1:
        a, b, c = d[best - 1], d[best], d[best + 1]
        denom = 2 * (2 * b - a - c)
        if abs(denom) > 1e-12:
            best = best + (a - c) / denom
    return rate / best


# ---- sample construction ------------------------------------------------

BLOCK = 16          # BRR block, in samples


def _align(n):
    return (n // BLOCK) * BLOCK


def resample_frac(buf, at, count, span):
    """`count` output samples covering `span` input samples starting at `at`,
    where span need not be a whole number. Linear, which at these rates is
    indistinguishable from anything cleverer."""
    out = [0.0] * count
    ratio = span / float(count)
    for i in range(count):
        p = at + i * ratio
        j = int(p)
        f = p - j
        a = buf[j] if j < len(buf) else 0.0
        b = buf[j + 1] if j + 1 < len(buf) else a
        out[i] = a + (b - a) * f
    return out


def looped(path, note, rate=10000, attack_ms=60, loop_ms=90, fade=0.35,
           peak=0.92, check=True):
    """A sustained instrument: a short attack followed by a looped body whose
    length is an exact whole number of the instrument's own periods.

    That constraint is the whole job. A loop can only re-enter at a BRR block
    boundary, so its length has to be a multiple of 16 samples -- and 16 has no
    reason to divide the period of a violin. Cut the loop at a round number of
    samples instead and it is 11.5 periods long, so every time it wraps, the
    waveform restarts half a cycle out of phase. A crossfade hides the click
    but not the pitch: what you hear is the loop frequency itself, a 14Hz
    warble under a sustained note, and it is worse the lower the instrument.
    Which is exactly what the contrabass and the harp did.

    So: pick the number of periods k, round k periods to a multiple of 16 to
    get the loop length, and then resample the source so that k periods fit
    that length *exactly*. The rate moves by a fraction of a percent and the
    loop becomes perfectly periodic.

    C5Speed then falls out as 523.25 * (loop_n / k) -- samples per cycle times
    the frequency wanted at note 60, which is the same relation the synthesised
    instruments used when a cycle was 32 samples by construction.
    """
    src, sr = read_wav(path, max_seconds=6.0)
    src = src[onset(src):]

    f0 = detect_f0(src, sr)
    if not f0:
        raise SystemExit("%s: no detectable pitch, cannot build a loop"
                         % os.path.basename(path))
    if check:
        want = note_hz(note)
        cents = 1200 * math.log(f0 / want, 2)
        if abs(cents) > 60:
            raise SystemExit(
                "%s: labelled %s (%.1f Hz) but measures %.1f Hz, %+d cents"
                % (os.path.basename(path), note, want, f0, cents))

    # k whole periods, as close to the requested loop length as the period
    # allows, then rounded out to a BRR block boundary.
    k = max(2, int(round(f0 * loop_ms / 1000.0)))
    p_req = rate / f0
    loop_n = max(BLOCK, int(round(k * p_req / BLOCK)) * BLOCK)
    p = loop_n / float(k)                  # samples per cycle, exactly
    real_rate = f0 * p                     # the rate that makes that true

    attack = _align(int(real_rate * attack_ms / 1000.0))
    span = sr / real_rate                  # input samples per output sample

    need = (attack + 2 * loop_n) * span
    if need > len(src):
        raise SystemExit("%s: %d samples, need %d"
                         % (os.path.basename(path), len(src), int(need)))

    head = resample_frac(src, 0.0, attack, attack * span)
    # The loop is taken a full loop-length past the attack, so there is
    # steady-state material in front of it to fade into.
    at = (attack + loop_n) * span
    body = resample_frac(src, at, loop_n, loop_n * span)
    prev = resample_frac(src, at - loop_n * span, loop_n, loop_n * span)

    m = max(BLOCK, int(loop_n * fade))
    for i in range(m):
        w = (i + 1) / float(m)
        w = w * w * (3 - 2 * w)            # smoothstep: no corner either end
        j = loop_n - m + i
        body[j] = body[j] * (1 - w) + prev[loop_n - m + i] * w

    data = normalise(head + body, peak)
    c5 = int(round(note_hz('C5') * p))
    s = it.Sample(os.path.basename(path)[:24], data, c5,
                  loop=True, loop_start=attack)
    s.cycle = p
    s.periods = k
    return s


def oneshot(path, rate=10000, ms=260, tail_ms=40, peak=0.95, note=None):
    """Percussion: trimmed to the hit, faded out at the end so the sample does
    not stop on a non-zero value and click."""
    src, sr = read_wav(path)
    src = src[onset(src, 0.01):]
    buf = resample(src, sr, rate)

    n = _align(int(rate * ms / 1000.0))
    n = min(n, _align(len(buf)))
    buf = buf[:n]

    tail = min(len(buf), int(rate * tail_ms / 1000.0))
    for i in range(tail):
        w = i / float(tail)
        buf[len(buf) - tail + i] *= (1.0 - w) ** 2

    # A one-shot is triggered at C5, so C5Speed is simply the stored rate --
    # unless the recording has a pitch worth preserving across the keyboard,
    # which for the slit drum it does.
    c5 = rate if note is None else int(round(rate * (note_hz('C5')
                                                     / note_hz(note))))
    return it.Sample(os.path.basename(path)[:24], buf, c5, loop=False)


def brr_bytes(sample):
    """What this sample will cost in ARAM once smconv has packed it: nine
    bytes per sixteen samples, and there are only 64KB of the stuff."""
    return ((len(sample.data) + BLOCK - 1) // BLOCK) * 9
