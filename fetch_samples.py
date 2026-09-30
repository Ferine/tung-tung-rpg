#!/usr/bin/env python3
"""Fetch the CC0 instrument recordings the soundtrack is cut from.

Not committed: they are about 25MB of source material for about 15KB of ROM. Run
this once and `samples/` is populated; gen_music.py needs it and says so if it
is missing.

    python3 fetch_samples.py

Provenance and licence are in SAMPLES.md. Short version: everything here is
from Versilian Studios' VSCO-2-CE and VCSL, both CC0-1.0, which is a public
domain dedication and therefore the only kind of licence under which you can
cut a recording into pieces and ship the pieces inside a cartridge image.

A note on octaves. VSCO-2-CE names middle C as "C3"; VCSL names it "C4", which
is scientific pitch. The `note` column below is always **scientific**, so half
of these do not match the filename they came from -- deliberately. This was not
guessed: sfsample.detect_f0 measures every one of them at build time and stops
the build if a recording disagrees with the note claimed for it by more than 60
cents. Five separate VSCO instruments each measured exactly one octave above
their filename, which is what a naming convention looks like from the outside.
"""
import argparse
import hashlib
import os
import sys
import urllib.parse
import urllib.request

DEST = 'samples'

# Pin the repositories rather than following their mutable default branches.
# SHA256 below then protects against a corrupt download or a changed object at
# the source. Both repositories dedicate these recordings under CC0-1.0; see
# SAMPLES.md for provenance.
REVISIONS = {
    'VSCO-2-CE': '440300901dfe9275fd84e0b7763af1f8443ae62e',
    'VCSL': 'c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e',
}

# name, repo, path within the repo, scientific note (None = unpitched one-shot)
PICKS = [
    # --- sustained, looped -------------------------------------------------
    ('strings', 'VSCO-2-CE',
     'Strings/Violin Section/susVib/VlnEns_susVib_C4_v1.wav', 'C5'),
    ('cello', 'VSCO-2-CE',
     'Strings/Cello Section/susvib/susvib_C3_v1_1.wav', 'C4'),
    ('contra', 'VSCO-2-CE',
     'Strings/Solo Contrabass/SusNV/BKCtbss_SusNV_E2_v1_rr1.wav', 'E3'),
    ('oboe', 'VSCO-2-CE',
     'Woodwinds/Oboe/Sus/Oboe_Sus_D4_v1_Main.wav', 'D5'),
    ('flute', 'VSCO-2-CE',
     'Woodwinds/Flute/susNV/LDFlute_susNV_C4_v1_1.wav', 'C5'),
    ('horn', 'VSCO-2-CE',
     'Brass/F Horn/sus/MOHorn_sus_C3_v2_1.wav', 'C4'),
    ('trumpet', 'VSCO-2-CE',
     'Brass/Trumpet/sus/Sum_SHTrumpet_sus_C3_v3_rr1.wav', 'C4'),
    ('trombone', 'VSCO-2-CE',
     'Brass/Tenor Trombone/sus/tenortbn_sus_D2_v2_1.wav', 'D3'),
    # Numbered rather than named; 37 measures 263.4 Hz, which is a C4.
    ('organ', 'VSCO-2-CE',
     'Keys/Organ/Loud/Rode_Man3Open_37.wav', 'C4'),
    ('harp', 'VCSL',
     'Chordophones/Composite Chordophones/Concert Harp/KSHarp_C3_mf3.wav',
     'C3'),
    # Glockenspiel bars are strongly inharmonic -- the C5 and C6 recordings
    # measure the *same* frequency, because the detector locks a shared
    # partial rather than either fundamental. The label is trusted here and
    # the check is skipped; see gen_music.
    ('glock', 'VCSL',
     'Idiophones/Struck Idiophones/Glockenspiel/glock_medium_C6_01.wav', 'C6'),
    ('viola_spic', 'VSCO-2-CE',
     'Strings/Viola Section/spic/Violas_spic_C4_v2_rr1.wav', 'C5'),

    # --- one-shots ---------------------------------------------------------
    # The slit drum is the point of the whole game: a kentongan is a slit
    # drum, and Tung Tung Tung Sahur is the sound of one being beaten before
    # dawn. Two pitches, high and low, so the title theme can play a rhythm on
    # the instrument the character is named after.
    ('slitdrum', 'VCSL',
     'Idiophones/Struck Idiophones/Slit Drum/LogDrumHi_MedM_v2_rr1_Sum.wav',
     None),
    ('slitlow', 'VCSL',
     'Idiophones/Struck Idiophones/Slit Drum/LogDrumLo_MedM_v2_rr1_Sum.wav',
     None),
    ('timpani', 'VSCO-2-CE',
     'Percussion/Timpani/Timpani1_Hit_v3_rr1_Sum.wav', None),
    ('snare', 'VCSL',
     'Membranophones/Struck Membranophones/Snare Drum, Rope Tension/Hi/'
     'RopeSnare_hi_sn_Main_vl2_rr1.wav', None),
    ('bassdrum', 'VCSL',
     'Membranophones/Struck Membranophones/Bass Drum 2/bassdrum_hit_f.wav',
     None),
    ('hihat', 'VCSL',
     'Idiophones/Struck Idiophones/Hi-Hat Cymbal/HiHat_Close_rr1_Mid.wav',
     None),

    # --- added for the full score: more voices, plucks, mallets --------------
    ('violin', 'VSCO-2-CE',
     'Strings/Solo Violin/Arco Vib/LLVln_ArcoVib_A4_p.wav',
     'A4'),
    ('strings_lo', 'VSCO-2-CE',
     'Strings/Violin Section/susVib/VlnEns_susVib_G2_v1.wav',
     'G3'),
    ('viola', 'VSCO-2-CE',
     'Strings/Viola Section/susvib/ViolaEns_susvib_D3_v2_1.wav',
     'D4'),
    ('cello_lo', 'VSCO-2-CE',
     'Strings/Cello Section/susvib/susvib_C1_v1_1.wav',
     'C2'),
    ('bass_lo', 'VSCO-2-CE',
     'Strings/Solo Contrabass/SusNV/BKCtbss_SusNV_A#0_v1_rr1.wav',
     'A#1'),
    ('clarinet', 'VSCO-2-CE',
     'Woodwinds/Clarinet/susLong/DCClar_susLong_F3_v2_rr1_sum.wav',
     'F4'),
    ('bassoon', 'VSCO-2-CE',
     'Woodwinds/Bassoon/sus/PSBassoon_G2_v2_1.wav',
     'G3'),
    ('tuba', 'VSCO-2-CE',
     'Brass/Tuba/sus/Tuba3_sus_D2_v2_rr1_Mid.wav',
     'D3'),

    # --- struck and plucked, pitched: the gamelan side of the palette --------
    # Their labels are the *sounding* pitch, measured from the spectrum -- VCSL
    # names these files an octave below where they sound.
    ('pizz_vln', 'VSCO-2-CE',
     'Strings/Violin Section/Pizz/VlnEns_Pizz_A3_v1_rr1.wav',
     'A4'),
    ('pizz_vlc', 'VSCO-2-CE',
     'Strings/Cello Section/pizzT/pizzT_A2_v1_RR1.wav',
     'A3'),
    ('pizz_cb', 'VSCO-2-CE',
     'Strings/Solo Contrabass/Pizz/BKCtbss_Pizz_A1_v1_rr1.wav',
     'A2'),
    ('dantranh', 'VCSL',
     'Chordophones/Zithers/Dan Tranh/Normal/B3_mf_1.wav',
     'B4'),
    ('marimba', 'VCSL',
     'Idiophones/Struck Idiophones/Marimba/Marimba_hit_Outrigger_C4_med_01.wav',
     'C5'),
    ('balafon', 'VCSL',
     'Idiophones/Struck Idiophones/Balafon/Soft Mallet/EthnicXylo_softM_C4_vl2_rr1_Mid.wav',
     'C5'),
    ('tubebell', 'VCSL',
     'Idiophones/Struck Idiophones/Tubular Bells 2/TB_hit_C5_v2_1.wav',
     'C5'),

    # --- more unpitched percussion -----------------------------------------
    ('cymbal', 'VSCO-2-CE',
     'Percussion/susCymb1-hit_f_rr1.wav',
     None),
    ('triangle', 'VSCO-2-CE',
     'Percussion/Triangle3-Hit_v1_rr1_Sum.wav',
     None),
    ('claves', 'VSCO-2-CE',
     'Percussion/Claves1_Hit_v2_rr1_Sum.wav',
     None),
    ('anvil', 'VSCO-2-CE',
     'Percussion/Anvil_Hit1_v2_Sum.wav',
     None),
    ('gong', 'VCSL',
     'Idiophones/Struck Idiophones/Gong 1/gong_mf.wav',
     None),
    ('tambourine', 'VCSL',
     'Idiophones/Struck Idiophones/Tambourine 1/Tamb1_Hit_v2_rr1_Mid.wav',
     None),
]

NOTES = {name: note for name, _repo, _path, note in PICKS}

SHA256 = {
    'strings': 'c07edd5b2119fa1da2207aba996961b50dd616f69bbcf2300ab271bc6c16239f',
    'cello': 'a614ee7ca821b44660236e47b89620cf914ec6ad27a99bc0d9764f47dbe512e1',
    'contra': '1b9d36042135c2eda513881612fb550a1b2669caddf70a7a514caeb4725fbbf2',
    'oboe': 'cbc9cdf1b6ca5765ec67918cd4a19669f792f9c6f755837ab807d3b8e0f3dfa9',
    'flute': '105a6dbced98de7ae04a317bdd3ba1a5c6b90dc94034439b68cce6635e2781df',
    'horn': 'c0c0b157dcde094c4417b7c165d645897cde9ea6d74247bbab0c0e75355e78c3',
    'trumpet': '4a55ab4d867cfa3499fbcf1c5d8d530f757621a9979aee5b46d3fd69a2931c99',
    'trombone': 'f71a6d3914ac0daa656553cbd2b50af560897fd31920fb578ac85313d2787b36',
    'organ': '9f3b80ef47d908b8acae4d6e7898a28e8179c3e090d6ee1ff4c326d35ea1d945',
    'harp': '18e6222e8fc11a8106e8d7a875d208835eb5b45598f010b21c786b1482e09869',
    'glock': 'e942cbf502cf6731df2925945fe3234c876cb63f047d91007b6929887f9e4904',
    'viola_spic': '3b4c0644c38ec7d13e03e3de88bce2dad899eb3c94a6251ec2acc8e6531687a5',
    'slitdrum': '8c4f61b36a13a8559f1777845ee9795bec52e07d2e86f05d50097bee6abd08b0',
    'slitlow': '609a9ae5441a007371e0dc3120d7e6d4ad5d23073f5f4fb3f16d0dc08823dfc4',
    'timpani': '8b39a785901d08dee14dd89914bdf2201e16ee418965e4d903fdb8e280a14d24',
    'snare': '08c3f8ceeef6b85f0c5c719e16d4500851367afc1ddfef7479a429b10e63fe8a',
    'bassdrum': 'e2f909d4986e2502b0653858c47bd10b0914c5893da770eae3034a9431e31439',
    'hihat': '4e4dbb4ddbeea653f95c2c229685fd5966ed9492fb8489d89d19dbd864f1a6b4',
    'violin': '0d05607b46b78690893006d5aa7923ac304c7fb497df1e96536dc88ac5ac487f',
    'strings_lo': 'feb96c5064fbef43087c495d61a9cab9f70ff1be5b22905147c1f86d5f89547c',
    'viola': 'f941028c5d5e854b4391669056f0f639799f80ac7c8da3939c7788b1a394d16c',
    'cello_lo': 'abdcea431f384e135c469b0f3e4ac2a437f282f521dc5bcbe22abc221536e8de',
    'bass_lo': 'b3800588b7aeff8f0c81998bdc4bfe47b3fc3e621f166de3df68f614a9f53afd',
    'clarinet': '3c9a237651cd049cacdf4052ef85ff406da1d9e5d4f59439c20f45a7578ff431',
    'bassoon': '74f59f6ad00584ed709b16c58769f099b64e4886c3af1bb74f2626719611f35c',
    'tuba': '005cd575e2d12b54a5a8f305b859cb6ae89cdbc010027b32fa0091aad39fffab',
    'pizz_vln': '6807c9f8a2b8851e866e1f9bb92e9809982693e3593882673d0fe6dedf9b7a96',
    'pizz_vlc': '3ef328e9c07e58797bb65831edef89b1fc946013a736826b6e380776c91b1f83',
    'pizz_cb': 'c88e632ac4f716d4e85112d6ea5bbe2d27d67019296787c25d27178a9e5f18ac',
    'cymbal': '42a8ece91eccec9b7063793e6644d037a9005c01d5b76f6bec358e8d53fb92a5',
    'triangle': 'ec2eb51ef2d090b8b3e33622bf39db7520867d52ddf56ced088d7994807a3763',
    'claves': 'ae0493fa57d0d1dd57693e8639dfe5fd9675b520a1c0c0eb45cf992f2a23ca9c',
    'anvil': 'dfef593c86cb8ce18ee38b249dffc07f7c5ebb176ec827530bb3f80ce5aaec7d',
    'dantranh': 'df91841b4552f2367334ceafaf5a4d839bd5aa57721f0e360ccebd94d7b70c53',
    'marimba': '3e88c006eef05e8f7891f8f6027042006199a4ec3b53a0ad7308f9782a52d4df',
    'balafon': 'c46eaef41eed9c720227ec5c9e52d93bab53703c3bfd90e2e6a111cef01604c9',
    'tubebell': '816b398d78d7bb0881c88e64ba781aaec4a1816495401f9ff4674854f4b70bec',
    'gong': '7e520ad14acda55db7906984f7efc2430961419435d951f55c8cdd9cd7a71108',
    'tambourine': '885ebf1d70f8e888f576682e4e4112b92b69649162f392c83b3379c91a09cf41',
}


def url_for(repo, path):
    return ("https://raw.githubusercontent.com/sgossner/%s/%s/%s"
            % (repo, REVISIONS[repo], urllib.parse.quote(path)))


def digest(body):
    return hashlib.sha256(body).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', default=DEST,
                        help='download directory (default: %(default)s)')
    args = parser.parse_args(argv)

    os.makedirs(args.dest, exist_ok=True)
    total = 0
    for name, repo, path, _note in PICKS:
        out = os.path.join(args.dest, name + '.wav')
        if os.path.exists(out) and os.path.getsize(out) > 1024:
            with open(out, 'rb') as src:
                body = src.read()
            if digest(body) == SHA256[name]:
                total += len(body)
                print("  have %-9s %8d bytes" % (name, len(body)))
                continue
            print("  stale %-9s checksum mismatch; downloading again" % name)
        url = url_for(repo, path)
        print("  get  %-9s %s" % (name, path))
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                body = r.read()
        except Exception as exc:                        # noqa: BLE001
            print("       FAILED: %s" % exc, file=sys.stderr)
            return 1
        # A 404 comes back as a short HTML/text body, not an exception.
        if len(body) < 1024 or body[:4] != b'RIFF':
            print("       FAILED: not a WAV (%d bytes)" % len(body),
                  file=sys.stderr)
            return 1
        actual = digest(body)
        if actual != SHA256[name]:
            print("       FAILED: SHA256 mismatch\n"
                  "       expected %s\n"
                  "       actual   %s" % (SHA256[name], actual),
                  file=sys.stderr)
            return 1
        with open(out, 'wb') as dst:
            dst.write(body)
        total += len(body)
    print("%s/: %d files, %.1f MB"
          % (args.dest, len(PICKS), total / 1048576.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
