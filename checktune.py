#!/usr/bin/env python3
"""Fail the asset build if a sampled instrument is out of tune or has a seam.

Two things go wrong with a looped sample and both are invisible in the source
recording:

  TUNE. Every looped instrument is built to hold a whole number of its own
  periods, so that C5Speed = 261.63 * (loop length / periods) makes tracker
  note 60 middle C exactly. That arithmetic is only as good as the pitch
  measured off the original recording: if the detector reads a violin 40 cents
  flat, the loop gets a fractional period in it and the instrument plays 40
  cents sharp for the entire soundtrack, in tune with nothing.

  SEAMS. A step where the attack meets the loop, or where the loop wraps, is a
  click on every single note. The first version of this pipeline had one at
  the attack-to-loop join of four of nine instruments (5-7x the median
  sample-to-sample step), and it is exactly the kind of fault that sounds like "harsh"
  rather than like "a bug".

So this measures the finished article -- the stored loop, at the C5Speed the
DSP will read it with -- and complains if it is not a middle C, or if either
seam steps by more than the loop's own steepest ordinary step.

Measuring pitch is its own trap. At a 10kHz sample rate a C4 is 38 samples per
cycle and no period estimator does better than a few tens of cents with that
little to work with. Measured directly, mathematically perfect loops come back
reading tens of cents off, which looks exactly like a broken instrument
builder. The signal is upsampled 8x first, after which the same loops measure
within a few cents.
"""
import math
import sys

import numpy as np

import itwriter as it
import orchestra as orc
import sfsample as sf

TOL = 18.0          # cents; the measurement itself is good to about 5
SEAM = 1.25         # a seam may step by this many times the
                    # loop's own steepest ordinary step (98th percentile)


def measure(body, rate, up=8, seconds=1.6):
    """Repeat the loop out to a fixed *duration*, not a fixed number of
    repeats, so a short loop of a low instrument still has enough to run on."""
    body = np.asarray(body, dtype=np.float64)
    reps = max(2, int(math.ceil(seconds * rate / len(body))))
    x = sf.resample(np.tile(body, reps), rate, rate * up)
    return sf.detect_f0(x, rate * up, lo=60.0, hi=1500.0)


def main():
    bad = []
    print("looped instruments, measured at the rate the DSP will read them:")
    for name, spec in orc.INSTRUMENTS.items():
        if spec['kind'] != 'loop':
            continue
        s = orc.build(name)
        d = np.asarray(s.data)
        body = d[s.loop_start:]
        f0 = measure(body, s.rate)
        if not f0:
            bad.append((name, 'no detectable pitch'))
            print("   %-10s NO PITCH" % name)
            continue
        cents = 1200 * math.log(f0 / sf.note_hz('C4'), 2)
        # the yardstick is the loop's own steepest ordinary step, not its
        # median one: a peaky waveform (a trumpet) is *all* steep edges
        step = float(np.percentile(np.abs(np.diff(body)), 98)) or 1e-9
        join = abs(d[s.loop_start] - d[s.loop_start - 1]) / step
        wrap = abs(d[s.loop_start] - d[-1]) / step
        flags = []
        if abs(cents) > TOL:
            flags.append("OUT OF TUNE")
            bad.append((name, 'off by %+.1f cents' % cents))
        if join > SEAM or wrap > SEAM:
            flags.append("SEAM")
            bad.append((name, 'seam steps %.1fx / %.1fx the loop\'s '
                        'steepest ordinary step' % (join, wrap)))
        print("   %-10s %5.1f samples/cycle  C5Speed %6d  %+6.2f cents  "
              "join %.1fx wrap %.1fx%s"
              % (name, s.cycle, s.rate, cents, join, wrap,
                 '   <-- ' + ', '.join(flags) if flags else ''))

    if bad:
        print("", file=sys.stderr)
        print("instruments failed:", file=sys.stderr)
        for name, why in bad:
            print("   %-10s %s" % (name, why), file=sys.stderr)
        print("A loop must hold a whole number of periods and meet its own "
              "attack; check what sfsample.detect_f0 reads for the source "
              "recording.", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
