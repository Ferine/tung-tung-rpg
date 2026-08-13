#!/usr/bin/env python3
"""Fail the asset build if a sampled instrument is out of tune.

Every looped instrument is built to hold a whole number of its own periods, so
that C5Speed = 523.25 * (loop length / periods) makes note 60 a C5 exactly.
That arithmetic is only as good as the pitch measured off the original
recording: if the detector reads a violin 40 cents flat, the loop gets a
fractional period in it and the instrument plays 40 cents sharp for the entire
soundtrack, in tune with nothing.

So this measures the finished article -- the stored loop, at the C5Speed the
DSP will read it with -- and complains if it is not a C5.

Measuring it is its own trap. At a 10kHz sample rate a C5 is 19 samples per
cycle, and no period estimator can do better than about a semitone with 19
samples to work with. Measured directly, *mathematically perfect* loops come
back reading -50 to +56 cents, which looks exactly like a broken instrument
builder. The signal is upsampled 8x first, after which the same perfect loops
measure within 5 cents, which is what makes the numbers below mean anything.
"""
import math
import sys

import itwriter as it
import sfsample as sf

TOL = 18.0          # cents; the measurement itself is good to about 5


def measure(body, rate, up=8, seconds=1.6):
    """Repeat the loop out to a fixed *duration*, not a fixed number of
    repeats. A contrabass loop is 464 samples read back at 22kHz to reach C5 --
    a fixed eight repeats of that is a fifth of a second, and after the
    detector's own internal downsampling there is not enough left to run on.
    It reports no detectable pitch, which reads as a broken instrument rather
    than as too short a excerpt."""
    reps = max(2, int(math.ceil(seconds * rate / len(body))))
    return sf.detect_f0(sf.resample(body * reps, rate, rate * up), rate * up)


def main():
    import gen_music as g

    mod = it.Module('checktune')
    g.build_instruments(mod)

    bad = []
    print("looped instruments, measured at the rate the DSP will read them:")
    for s in mod.samples:
        if not s.loop:
            continue
        body = s.data[s.loop_start:]
        if not body:
            continue
        f0 = measure(body, s.rate)
        if not f0:
            bad.append((s.name, None, 'no detectable pitch'))
            print("   %-8s NO PITCH" % s.name)
            continue
        cents = 1200 * math.log(f0 / 523.25, 2)
        ok = abs(cents) <= TOL
        print("   %-8s %6.2f samples/cycle  C5Speed %6d  %7.2f Hz  %+6.2f cents%s"
              % (s.name, getattr(s, 'cycle', 0), s.rate, f0, cents,
                 '' if ok else '   <-- OUT OF TUNE'))
        if not ok:
            bad.append((s.name, cents, 'off by %+.1f cents' % cents))

    if bad:
        print("", file=sys.stderr)
        print("instruments out of tune (tolerance %.0f cents):" % TOL,
              file=sys.stderr)
        for name, _c, why in bad:
            print("   %-8s %s" % (name, why), file=sys.stderr)
        print("The loop must hold a whole number of periods; check what",
              file=sys.stderr)
        print("sfsample.detect_f0 reads for the source recording.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
