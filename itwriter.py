#!/usr/bin/env python3
"""A minimal Impulse Tracker writer, for feeding smconv.

smconv (pvsneslib's module converter) reads .it and emits the SPC700 soundbank,
so the way to get music into the ROM is to write .it files. This is the smallest
subset that satisfies it: a header, an order list, one instrument per sample,
sample headers, sample data, and packed patterns.

Field offsets come from the IT format; the structure follows the writer in the
sibling llmodius-snes project, which is what proved this subset is enough for
smconv's itloader.

Note numbers are MIDI note numbers -- note 60 plays the sample at exactly its
C5Speed, which is the only rate at which a percussion sample sounds like what it
was drawn as, so drums are always triggered at 60.
"""
import struct

UNITY = 60

_SEMI = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
         'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def N(spec):
    """'A-4' / 'C#5' -> IT note number (== MIDI note number)."""
    name = spec[:-1].rstrip('-')
    octave = int(spec[-1])
    return (octave + 1) * 12 + _SEMI[name]


NOTE_CUT = 254
NOTE_OFF = 255


class Sample:
    def __init__(self, name, data, rate, loop=False, loop_start=0):
        self.name = name
        self.data = data            # floats in [-1, 1]
        self.rate = rate            # C5Speed
        self.loop = loop
        self.loop_start = loop_start


class Module:
    def __init__(self, name, speed=6, tempo=125, channels=8,
                 global_volume=128, channel_pans=None, channel_volumes=None,
                 message=''):
        self.name = name
        self.speed = speed
        self.tempo = tempo
        self.channels = channels
        self.global_volume = global_volume
        self.channel_pans = list(channel_pans or ([32] * channels))
        self.channel_volumes = list(channel_volumes or ([64] * channels))
        self.message = message
        self.samples = []
        self.patterns = []          # (rows, {row: {chan: cell}})
        self.orders = []

    def add_sample(self, s):
        self.samples.append(s)
        return len(self.samples)    # IT instrument numbers are 1-based

    def add_pattern(self, rows, cells):
        self.patterns.append((rows, cells))
        return len(self.patterns) - 1


def _pcm(s):
    """float -> signed 16-bit PCM. cvt=1 in the sample header means signed."""
    return b''.join(
        struct.pack('<h', max(-32767, min(32767, int(round(v * 32767)))))
        for v in s.data)


def _envelope():
    """A disabled envelope block (82 bytes). Every instrument gets three."""
    b = bytearray(82)
    b[0] = 0
    b[1] = 2
    b[6 + 0] = 64
    struct.pack_into('<H', b, 6 + 1, 0)
    b[6 + 3] = 64
    struct.pack_into('<H', b, 6 + 4, 10)
    return bytes(b)


def _instrument(index, name):
    b = bytearray(554)
    b[0:4] = b'IMPI'
    b[4:16] = (name[:11].encode('latin1') + b'\0' * 12)[:12]
    b[17] = 1           # NNA: continue
    b[24] = 128         # global volume
    b[25] = 32          # default pan, unused
    struct.pack_into('<H', b, 28, 0x0214)
    b[30] = 1           # one sample
    b[32:58] = (name[:25].encode('latin1') + b'\0' * 26)[:26]
    b[58] = 127         # filter cutoff off
    for note in range(120):
        b[64 + note * 2 + 0] = note
        b[64 + note * 2 + 1] = index
    b[304:386] = _envelope()
    b[386:468] = _envelope()
    b[468:550] = _envelope()
    return bytes(b)


def _sample_header(s, data_offset):
    b = bytearray(80)
    b[0:4] = b'IMPS'
    b[4:16] = (s.name[:11].encode('latin1') + b'\0' * 12)[:12]
    b[17] = 64                                   # global volume
    b[18] = 0x01 | 0x02 | (0x10 if s.loop else 0)  # data | 16-bit | loop
    b[19] = 64                                   # default volume
    b[20:46] = (s.name[:25].encode('latin1') + b'\0' * 26)[:26]
    b[46] = 0x01                                 # cvt: signed
    b[47] = 32
    n = len(s.data)
    struct.pack_into('<I', b, 48, n)
    struct.pack_into('<I', b, 52, s.loop_start if s.loop else 0)
    struct.pack_into('<I', b, 56, n if s.loop else 0)
    struct.pack_into('<I', b, 60, s.rate)
    struct.pack_into('<I', b, 72, data_offset)
    return bytes(b)


def _pack_pattern(rows, cells):
    """Packed pattern data with no run-length reuse: every cell carries its own
    mask, which is valid and keeps this trivial."""
    out = bytearray()
    for r in range(rows):
        row = cells.get(r, {})
        for ch in sorted(row):
            note, inst, vol, cmd, param = row[ch]
            mask = 0
            if note is not None:
                mask |= 1
            if inst is not None:
                mask |= 2
            if vol is not None:
                mask |= 4
            if cmd is not None:
                mask |= 8
            out.append(((ch + 1) & 63) | 128)
            out.append(mask)
            if note is not None:
                out.append(note)
            if inst is not None:
                out.append(inst)
            if vol is not None:
                out.append(vol)
            if cmd is not None:
                out.append(cmd)
                out.append(param)
        out.append(0)                            # end of row
    return bytes(out)


def write_it(mod, path):
    ins_n = smp_n = len(mod.samples)
    pat_n = len(mod.patterns)
    orders = bytes(mod.orders) + b'\xff'
    ord_n = len(orders)
    message = mod.message.encode('latin1')

    header = bytearray(192)
    header[0:4] = b'IMPM'
    header[4:30] = (mod.name[:25].encode('latin1') + b'\0' * 26)[:26]
    header[30] = 16
    header[31] = 4
    struct.pack_into('<4H', header, 32, ord_n, ins_n, smp_n, pat_n)
    struct.pack_into('<H', header, 40, 0x0214)
    struct.pack_into('<H', header, 42, 0x0214)
    struct.pack_into('<H', header, 44, 0x000D)   # stereo|instruments|linear
    struct.pack_into('<H', header, 46, 0x0001 if message else 0x0000)
    header[48] = mod.global_volume
    header[49] = 48                              # mix volume
    header[50] = mod.speed
    header[51] = mod.tempo
    header[52] = 128
    for c in range(64):
        header[64 + c] = (mod.channel_pans[c] if c < mod.channels
                          else (32 | 128))
        header[128 + c] = (mod.channel_volumes[c] if c < mod.channels
                           else 64)

    tables = 4 * (ins_n + smp_n + pat_n)
    base = len(header) + ord_n + tables
    if message:
        struct.pack_into('<H', header, 54, len(message))
        struct.pack_into('<I', header, 56, base)

    ins_offsets, blob = [], bytearray(message)
    for i in range(ins_n):
        ins_offsets.append(base + len(blob))
        blob += _instrument(i + 1, mod.samples[i].name)

    smp_offsets = []
    hdr_at = base + len(blob)
    data_at = hdr_at + 80 * smp_n
    pcm = bytearray()
    headers = bytearray()
    for s in mod.samples:
        smp_offsets.append(hdr_at + len(headers))
        headers += _sample_header(s, data_at + len(pcm))
        pcm += _pcm(s)
    blob += headers + pcm

    pat_offsets = []
    for rows, cells in mod.patterns:
        packed = _pack_pattern(rows, cells)
        pat_offsets.append(base + len(blob))
        blob += struct.pack('<HH4x', len(packed), rows) + packed

    with open(path, 'wb') as f:
        f.write(header)
        f.write(orders)
        f.write(struct.pack('<%dI' % ins_n, *ins_offsets))
        f.write(struct.pack('<%dI' % smp_n, *smp_offsets))
        f.write(struct.pack('<%dI' % pat_n, *pat_offsets))
        f.write(blob)
    return len(header) + ord_n + tables + len(blob)
