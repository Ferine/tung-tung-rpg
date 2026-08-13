#!/usr/bin/env python3
"""Run the ROM headless in the Mesen-S libretro core and capture real frames.

preview.py only shows what the *generators* produced. This shows what the
console actually put on screen, which is the only way to observe a mistake made
between the .pic file and the PPU -- a wrong tilemap base, a palette loaded to
the wrong CGRAM index, an OBJ whose size bit disagrees with its art.

    python3 capture.py                       # the default shot list
    python3 capture.py --script "60:;10:start;300:down" --out shots

A script step is `frames:buttons`, buttons comma-separated and held for the
whole step. Names are the libretro joypad ids: a b x y l r start select and the
four directions.
"""
import ctypes
import argparse
import os
import sys

CORE_ENV = 'MESEN_S_CORE'
ROM_ENV = 'TUNGTUNG_ROM'
DEFAULT_ROM = 'tungtung.sfc'

# libretro.h
ENV_SET_PIXEL_FORMAT = 10
ENV_GET_SYSTEM_DIRECTORY = 9
ENV_GET_SAVE_DIRECTORY = 31
ENV_GET_VARIABLE = 15
ENV_SET_VARIABLES = 16
ENV_GET_VARIABLE_UPDATE = 17
ENV_GET_LOG_INTERFACE = 27
ENV_SET_SUPPORT_NO_GAME = 18

DEVICE_JOYPAD = 1
BUTTONS = {'b': 0, 'y': 1, 'select': 2, 'start': 3, 'up': 4, 'down': 5,
           'left': 6, 'right': 7, 'a': 8, 'x': 9, 'l': 10, 'r': 11}

PIX_0RGB1555, PIX_XRGB8888, PIX_RGB565 = 0, 1, 2


class GameInfo(ctypes.Structure):
    _fields_ = [('path', ctypes.c_char_p),
                ('data', ctypes.c_void_p),
                ('size', ctypes.c_size_t),
                ('meta', ctypes.c_char_p)]


class Geometry(ctypes.Structure):
    _fields_ = [('base_width', ctypes.c_uint), ('base_height', ctypes.c_uint),
                ('max_width', ctypes.c_uint), ('max_height', ctypes.c_uint),
                ('aspect_ratio', ctypes.c_float)]


class Timing(ctypes.Structure):
    _fields_ = [('fps', ctypes.c_double), ('sample_rate', ctypes.c_double)]


class AVInfo(ctypes.Structure):
    _fields_ = [('geometry', Geometry), ('timing', Timing)]


ENV_CB = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)
VIDEO_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint,
                            ctypes.c_uint, ctypes.c_size_t)
AUDIO_CB = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)
AUDIO_BATCH_CB = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p,
                                  ctypes.c_size_t)
POLL_CB = ctypes.CFUNCTYPE(None)
INPUT_CB = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_uint, ctypes.c_uint)


class Core:
    def __init__(self, path=None, sysdir='.'):
        path = path or os.environ.get(CORE_ENV)
        if not path:
            raise SystemExit(
                'Mesen-S core not configured: set %s to the libretro core path'
                % CORE_ENV)
        if not os.path.isfile(path):
            raise SystemExit('Mesen-S core not found: %s' % path)
        self.lib = ctypes.CDLL(path)
        self.pixfmt = PIX_0RGB1555
        self.frame = None
        self.held = set()
        self.sysdir = ctypes.c_char_p(os.path.abspath(sysdir).encode())

        # The callbacks must stay referenced for as long as the core runs;
        # ctypes will otherwise collect the trampolines and the first call
        # into one segfaults.
        self._env = ENV_CB(self._environment)
        self._video = VIDEO_CB(self._video_refresh)
        self._audio = AUDIO_CB(lambda l, r: None)
        # A sink the tests can turn on: the core hands us the SPC700's output,
        # and silence is how a soundbank that links perfectly tells you it
        # never actually loaded.
        self.audio = None
        self._audio_batch = AUDIO_BATCH_CB(self._on_audio)
        self._poll = POLL_CB(lambda: None)
        self._input = INPUT_CB(self._input_state)

        self.lib.retro_load_game.restype = ctypes.c_bool
        self.lib.retro_load_game.argtypes = [ctypes.POINTER(GameInfo)]
        self.lib.retro_get_system_av_info.argtypes = [ctypes.POINTER(AVInfo)]
        self.lib.retro_api_version.restype = ctypes.c_uint

        # Order matters, and not the order libretro.h implies. This core's
        # setters are three instructions -- load a pointer from a global,
        # store the callback into it -- and that global is null until
        # retro_init constructs the object. Calling retro_set_video_refresh
        # first, as a normal frontend does, writes through null and segfaults.
        # Environment is the exception: it stores into a plain global, and the
        # core reads it during retro_init.
        self.lib.retro_set_environment(self._env)
        self.lib.retro_init()
        self.lib.retro_set_video_refresh(self._video)
        self.lib.retro_set_audio_sample(self._audio)
        self.lib.retro_set_audio_sample_batch(self._audio_batch)
        self.lib.retro_set_input_poll(self._poll)
        self.lib.retro_set_input_state(self._input)

    def _environment(self, cmd, data):
        if cmd == ENV_SET_PIXEL_FORMAT:
            self.pixfmt = ctypes.cast(data,
                                      ctypes.POINTER(ctypes.c_int))[0]
            return True
        if cmd in (ENV_GET_SYSTEM_DIRECTORY, ENV_GET_SAVE_DIRECTORY):
            ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))[0] = self.sysdir
            return True
        if cmd == ENV_GET_VARIABLE_UPDATE:
            ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = False
            return True
        return False

    def _video_refresh(self, data, width, height, pitch):
        if not data:
            return              # duped frame: keep the previous one
        self.frame = (bytes(ctypes.string_at(data, pitch * height)),
                      width, height, pitch)

    def _input_state(self, port, device, index, ident):
        if port != 0 or device != DEVICE_JOYPAD:
            return 0
        return 1 if ident in self.held else 0

    def load(self, rom):
        blob = open(rom, 'rb').read()
        # The buffer has to outlive the call: the core keeps the pointer, and a
        # temporary here is collected the moment load() returns -- which
        # presents as a segfault somewhere inside the first retro_run.
        self._buf = ctypes.create_string_buffer(blob, len(blob))
        self._path = ctypes.c_char_p(os.path.abspath(rom).encode())
        info = GameInfo()
        info.path = self._path
        info.data = ctypes.cast(self._buf, ctypes.c_void_p)
        info.size = len(blob)
        info.meta = None
        self._info = info
        if not self.lib.retro_load_game(ctypes.byref(self._info)):
            raise SystemExit('core refused the ROM')
        av = AVInfo()
        self.lib.retro_get_system_av_info(ctypes.byref(av))
        return av

    def press(self, names):
        self.held = set(BUTTONS[n] for n in names if n)

    def run(self, frames):
        for _ in range(frames):
            self.lib.retro_run()

    def _on_audio(self, data, frames):
        if self.audio is not None and frames:
            self.audio.append(ctypes.string_at(data, frames * 4))
        return frames

    def audio_rms(self):
        """RMS of everything captured since record() -- one number that says
        whether the sound chip is doing anything at all."""
        import struct
        total = 0.0
        n = 0
        for b in self.audio or []:
            for i in range(0, len(b) - 1, 2):
                v = struct.unpack_from('<h', b, i)[0]
                total += v * v
                n += 1
        return (total / n) ** 0.5 if n else 0.0

    def record(self):
        self.audio = []

    def shot(self, path):
        """The current frame, on disk. Every script wants this and every
        script was writing it out longhand."""
        img = self.image()
        img.save(path)
        return img

    def image(self):
        from PIL import Image

        if not self.frame:
            raise SystemExit('core produced no frame')
        buf, w, h, pitch = self.frame
        img = Image.new('RGB', (w, h))
        px = img.load()
        if self.pixfmt == PIX_XRGB8888:
            for y in range(h):
                row = y * pitch
                for x in range(w):
                    o = row + x * 4
                    px[x, y] = (buf[o + 2], buf[o + 1], buf[o])
        elif self.pixfmt == PIX_RGB565:
            for y in range(h):
                row = y * pitch
                for x in range(w):
                    o = row + x * 2
                    v = buf[o] | (buf[o + 1] << 8)
                    px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2,
                                (v & 31) << 3)
        else:
            for y in range(h):
                row = y * pitch
                for x in range(w):
                    o = row + x * 2
                    v = buf[o] | (buf[o + 1] << 8)
                    px[x, y] = (((v >> 10) & 31) << 3, ((v >> 5) & 31) << 3,
                                (v & 31) << 3)
        # The core always renders 239 lines; the game runs the 224-line mode
        # ($2133 D2 clear), so the last 15 are outside the display area.
        if h > 224:
            img = img.crop((0, 0, w, 224))
        return img


def parse_script(text):
    steps = []
    for part in text.split(';'):
        part = part.strip()
        if not part:
            continue
        frames, _, buttons = part.partition(':')
        steps.append((int(frames),
                      [b.strip() for b in buttons.split(',') if b.strip()]))
    return steps


DEFAULT = [
    ('title', 90, []),
    ('field', 40, ['start']),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--core', default=os.environ.get(CORE_ENV),
        help='Mesen-S libretro core (or set %s)' % CORE_ENV)
    parser.add_argument(
        '--rom', default=os.environ.get(ROM_ENV, DEFAULT_ROM),
        help='ROM to load (default: %%(default)s; or set %s)' % ROM_ENV)
    parser.add_argument('--out', default='shots', help='screenshot directory')
    parser.add_argument('--script', type=parse_script,
                        help='semicolon-separated frames:buttons steps')
    args = parser.parse_args()

    if not args.core:
        parser.error('pass --core or set %s' % CORE_ENV)
    if not os.path.isfile(args.rom):
        parser.error('ROM not found: %s (run make first)' % args.rom)

    os.makedirs(args.out, exist_ok=True)
    core = Core(args.core)
    av = core.load(args.rom)
    print('geometry %dx%d, fps %.2f, pixfmt %d'
          % (av.geometry.base_width, av.geometry.base_height,
             av.timing.fps, core.pixfmt))

    if args.script is None:
        n = 0
        for name, frames, buttons in DEFAULT:
            core.press(buttons)
            core.run(frames)
            core.press([])
            core.run(2)
            core.image().save('%s/%02d-%s.png' % (args.out, n, name))
            print('%s/%02d-%s.png' % (args.out, n, name))
            n += 1
    else:
        for n, (frames, buttons) in enumerate(args.script):
            core.press(buttons)
            core.run(frames)
            core.image().save('%s/%02d.png' % (args.out, n))
            print('%s/%02d.png' % (args.out, n))

    core.lib.retro_unload_game()
    core.lib.retro_deinit()


if __name__ == '__main__':
    main()
