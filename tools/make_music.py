"""Generate the game's original chiptune BGM and jingles as WAV files.

Everything here is composed for this project (no third-party material), so the
output is covered by the project's own license. Re-run after editing a song:

    python tools/make_music.py

Songs are written as note strings: "C5:1 E5:.5 r:.5" = note:beats, r = rest.
Each song has up to four channels: lead (pulse 25%), harmony (pulse 50%),
bass (triangle) and drums (k = kick, s = snare, h = hat).
"""
import os
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "bgm", "generated")
RATE = 22050
NOTE_INDEX = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def freq(name):
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + NOTE_INDEX[pitch]
    return 440.0 * 2 ** ((midi - 69) / 12)


def parse(seq):
    out = []
    for tok in seq.split():
        n, b = tok.split(":")
        out.append((None if n == "r" else n, float(b)))
    return out


def osc(kind, f, n, duty=0.5):
    t = np.arange(n) / RATE
    phase = (t * f) % 1.0
    if kind == "pulse":
        return np.where(phase < duty, 1.0, -1.0)
    if kind == "tri":
        return 4 * np.abs(phase - 0.5) - 1
    raise ValueError(kind)


def envelope(n, attack=0.005, release=0.04, sustain=0.75, decay=0.08):
    env = np.full(n, sustain)
    a = min(n, int(attack * RATE))
    d = min(n - a, int(decay * RATE))
    env[:a] = np.linspace(0, 1, a, endpoint=False)
    env[a:a + d] = np.linspace(1, sustain, d, endpoint=False)
    r = min(n, int(release * RATE))
    env[n - r:] *= np.linspace(1, 0, r)
    return env


def render_tone(seq, bpm, kind, duty=0.5, vol=0.2, gate=0.9, vibrato=False):
    spb = 60.0 / bpm
    total = int(round(sum(b for _, b in seq) * spb * RATE))
    buf = np.zeros(total)
    pos = 0.0
    for note, beats in seq:
        n = int(round(beats * spb * RATE))
        start = int(round(pos))
        if note:
            k = max(1, int(n * gate))
            f = freq(note)
            if vibrato and k > RATE * 0.25:
                t = np.arange(k) / RATE
                f = f * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * (t > 0.15))
                phase = np.cumsum(f / RATE) % 1.0
                wave_ = np.where(phase < duty, 1.0, -1.0) if kind == "pulse" else 4 * np.abs(phase - 0.5) - 1
            else:
                wave_ = osc(kind, f, k, duty)
            buf[start:start + k] += wave_ * envelope(k) * vol
        pos += beats * spb * RATE
    return buf


def render_drums(pattern, bpm, steps_per_beat=2, vol=0.18, bars=1):
    """pattern: string like 'k-h-s-h-' one char per step; repeated `bars` times."""
    spb = 60.0 / bpm / steps_per_beat
    step = int(round(spb * RATE))
    rng = np.random.default_rng(1)
    pat = pattern.replace(" ", "") * bars
    buf = np.zeros(step * len(pat))
    for i, c in enumerate(pat):
        s = i * step
        if c == "k":
            n = int(0.12 * RATE)
            t = np.arange(n) / RATE
            f = 120 * np.exp(-t * 30) + 45
            hit = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 25)
            buf[s:s + n] += hit[:len(buf) - s] * vol * 1.6
        elif c == "s":
            n = int(0.10 * RATE)
            hit = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / RATE * 35)
            buf[s:s + n] += hit[:len(buf) - s] * vol
        elif c == "h":
            n = int(0.03 * RATE)
            hit = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / RATE * 120)
            buf[s:s + n] += hit[:len(buf) - s] * vol * 0.5
    return buf


def arp(chords, beats_per_chord, octave=4, step=0.25):
    """Broken-chord pattern. chords like 'C:E:G'."""
    out = []
    for ch in chords.split():
        notes = [f"{p}{octave}" for p in ch.split(":")]
        seq = notes + [notes[1]] if len(notes) == 3 else notes
        for i in range(int(beats_per_chord / step)):
            out.append(f"{seq[i % len(seq)]}:{step}")
    return " ".join(out)


def bassline(roots, beats_per_chord, octave=2, pattern=(1, 1, 1, 1)):
    out = []
    for r in roots.split():
        lo, hi = f"{r}{octave}", f"{r}{octave + 1}"
        for i, b in enumerate(pattern):
            out.append(f"{lo if i % 2 == 0 else hi}:{b}")
        rest = beats_per_chord - sum(pattern)
        if rest > 0:
            out.append(f"r:{rest}")
    return " ".join(out)


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = np.zeros(n)
    for t in tracks:
        out[:len(t)] += t
    peak = np.max(np.abs(out)) or 1
    return out / max(peak, 1.0) * 0.9


def write(name, data):
    os.makedirs(OUT, exist_ok=True)
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    print(f"wrote {name}.wav  {len(data) / RATE:.1f}s")


# ----------------------------------------------------------------------
def song_title():
    bpm = 84
    chords = "A:C:E F:A:C C:E:G G:B:D " * 2
    lead = parse(
        "E5:1.5 D5:.5 C5:1 B4:1  A4:2 C5:1 D5:1  E5:1.5 G5:.5 E5:1 D5:1  D5:3 r:1 "
        "E5:1.5 D5:.5 C5:1 E5:1  F5:2 E5:1 C5:1  D5:1.5 C5:.5 B4:1 G4:1  A4:4")
    harm = parse(arp(chords, 4, octave=4, step=0.5))
    bass = parse(bassline("A F C G A F C G", 4, pattern=(2, 2)))
    return mix(render_tone(lead, bpm, "pulse", 0.25, 0.20, vibrato=True),
               render_tone(harm, bpm, "pulse", 0.5, 0.06, gate=0.6),
               render_tone(bass, bpm, "tri", vol=0.30))


def song_village():
    bpm = 104
    chords = "C:E:G A:C:E F:A:C G:B:D " * 4
    lead = parse(
        "E5:1 G5:1 C6:1.5 B5:.5  A5:1 G5:1 E5:2  F5:1 A5:1 G5:1 F5:1  D5:3 r:1 "
        "E5:1 G5:1 C6:1.5 D6:.5  E6:1 D6:1 C6:2  A5:1 C6:1 B5:1 D6:1  C6:3 r:1 "
        "A5:1.5 G5:.5 F5:1 E5:1  E5:1 D5:1 C5:2  F5:1.5 E5:.5 D5:1 C5:1  B4:2 D5:2 "
        "E5:1 G5:1 C6:1 G5:1  A5:1 F5:1 E5:2  D5:1 F5:1 E5:1 D5:1  C5:3 r:1")
    harm = parse(arp(chords, 4, octave=4, step=0.5))
    bass = parse(bassline("C A F G " * 4, 4, pattern=(1, 1, 1, 1)))
    drums = render_drums("k-h-s-h-", bpm, 2, 0.12, bars=16)
    return mix(render_tone(lead, bpm, "pulse", 0.25, 0.19, vibrato=True),
               render_tone(harm, bpm, "pulse", 0.5, 0.05, gate=0.5),
               render_tone(bass, bpm, "tri", vol=0.30, gate=0.8), drums)


def song_meadow():
    bpm = 132
    chords = "D:F:A C:E:G A#:D:F C:E:G " * 4
    lead = parse(
        "D5:1 F5:1 A5:1 D6:1  C6:2 A5:1 G5:1  F5:1 G5:1 A5:1 F5:1  E5:2 C5:2 "
        "D5:1 F5:1 A5:1 D6:1  E6:2 D6:1 C6:1  A#5:1 A5:1 G5:1 A#5:1  A5:4 "
        "F5:.5 G5:.5 A5:1 A5:1 G5:1  C6:1 A5:1 G5:2  F5:.5 G5:.5 A5:1 D6:1 C6:1  E5:4 "
        "D5:1 E5:1 F5:1 A5:1  G5:1 E5:1 C5:2  A#4:1 D5:1 F5:1 A#5:1  A5:2 E5:2")
    harm = parse(arp(chords, 4, octave=4, step=0.25))
    bass = parse(bassline("D C A# C " * 4, 4, pattern=(.5, .5, .5, .5, .5, .5, .5, .5)))
    drums = render_drums("k-hks-h-k-hks-hh", bpm, 4, 0.13, bars=16)
    return mix(render_tone(lead, bpm, "pulse", 0.25, 0.18),
               render_tone(harm, bpm, "pulse", 0.125, 0.05, gate=0.6),
               render_tone(bass, bpm, "tri", vol=0.32, gate=0.7), drums)


def jingle_victory():
    bpm = 150
    lead = parse("C5:.33 C5:.33 C5:.34 C5:1.5 G#4:1.5 A#4:1.5 C5:.66 A#4:.34 C5:4")
    harm = parse("G4:.33 G4:.33 G4:.34 G4:1.5 D#4:1.5 F4:1.5 G4:.66 F4:.34 G4:4")
    bass = parse("C3:1 r:.5 C3:1.5 G#2:1.5 A#2:1.5 C3:1 C3:4")
    return mix(render_tone(lead, bpm, "pulse", 0.25, 0.22),
               render_tone(harm, bpm, "pulse", 0.5, 0.10),
               render_tone(bass, bpm, "tri", vol=0.30))


def jingle_levelup():
    bpm = 180
    lead = parse("C5:.5 E5:.5 G5:.5 C6:.5 E6:.5 G6:1.5")
    harm = parse("r:.25 C5:.5 E5:.5 G5:.5 C6:.5 E6:1.75")
    return mix(render_tone(lead, bpm, "pulse", 0.25, 0.2), render_tone(harm, bpm, "pulse", 0.5, 0.07))


def jingle_gameover():
    bpm = 72
    lead = parse("A4:1 G#4:1 G4:1 F#4:1 F4:4")
    bass = parse("A2:2 F2:2 D2:4")
    return mix(render_tone(lead, bpm, "pulse", 0.5, 0.18, vibrato=True), render_tone(bass, bpm, "tri", vol=0.3))


if __name__ == "__main__":
    write("title", song_title())
    write("village", song_village())
    write("meadow", song_meadow())
    write("victory", jingle_victory())
    write("levelup", jingle_levelup())
    write("gameover", jingle_gameover())
