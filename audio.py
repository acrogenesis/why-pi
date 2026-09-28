import math

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

from timeline import (
    BAR,
    BEAT,
    CIRCLE_POPS,
    DUR,
    IMPACT,
    NOTES,
    PIECE_FALL,
    PIECE_STARTS,
    POLY_TIMES,
    ROLL_END,
    ROLL_START,
)

SR = 48000
N = int(DUR * SR)
rng = np.random.default_rng(314159)

dry = np.zeros((2, N))
music = np.zeros((2, N))  # ducked by the kick
send = np.zeros((2, N))  # reverb send
kick_env = np.zeros(N)

# A minor pentatonic across two octaves: digit -> note
SCALE = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79]
# Am - F - C - G, one chord per bar
CHORDS = [(45, [57, 60, 64, 71]), (41, [53, 57, 60, 64]), (48, [55, 60, 64, 67]), (43, [55, 59, 62, 67])]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def lowpass(x, cutoff, order=2):
    return sosfilt(butter(order, cutoff, "low", fs=SR, output="sos"), x)


def highpass(x, cutoff, order=2):
    return sosfilt(butter(order, cutoff, "high", fs=SR, output="sos"), x)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def place(bus, sig, t0, gain=1.0, pan=0.0, reverb=0.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    sig = sig[: N - i0] * gain
    left, right = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    bus[0, i0 : i0 + len(sig)] += sig * left
    bus[1, i0 : i0 + len(sig)] += sig * right
    if reverb:
        send[0, i0 : i0 + len(sig)] += sig * left * reverb
        send[1, i0 : i0 + len(sig)] += sig * right * reverb


# ---------- instruments ----------


def pluck(freq, dur=0.9):
    t = tt(dur)
    tone = (
        np.sin(2 * np.pi * freq * t)
        + 0.35 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 9)
        + 0.12 * np.sin(6 * np.pi * freq * t) * np.exp(-t * 16)
    )
    return tone * np.minimum(1, t / 0.004) * np.exp(-t * 5.5)


def saw(freq, t, harmonics=8):
    return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, harmonics + 1))


def pad_chord(notes, dur, attack=0.5, release=0.8):
    t = tt(dur + release)
    sig = np.zeros_like(t)
    for m in notes:
        f = hz(m)
        for cents in (-7, 0, 7):
            sig += saw(f * 2 ** (cents / 1200), t + rng.random(), 6)
    env = np.minimum(1, t / attack) * np.clip((dur + release - t) / release, 0, 1)
    return sig * env / (len(notes) * 3)


def bass_note(freq, dur=0.22):
    t = tt(dur)
    sig = np.tanh(2.2 * (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)))
    return sig * np.minimum(1, t / 0.005) * np.exp(-t * 7)


def kick():
    t = tt(0.45)
    freq = 46 + 115 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.25
    return body + click


def hat(length=0.07):
    t = tt(length)
    return highpass(rng.standard_normal(len(t)), 7000) * np.exp(-t * 70)


def clap():
    t = tt(0.25)
    noise = bandpass(rng.standard_normal(len(t)), 900, 4500)
    bursts = sum(np.exp(-np.maximum(t - d, 0) * 90) * (t >= d) for d in (0, 0.011, 0.022))
    return noise * (bursts * 0.5 + np.exp(-t * 18))


def bell(freq, dur=2.5):
    t = tt(dur)
    partials = ((1, 1.0, 1.6), (2.0, 0.5, 2.6), (2.76, 0.45, 3.2), (5.4, 0.2, 5.5), (8.93, 0.1, 8))
    sig = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * d) for r, a, d in partials)
    return sig * np.minimum(1, t / 0.002)


def whoosh(dur, rising=True):
    t = tt(dur)
    x = t / dur
    shape = x**2.5 if rising else (1 - x) ** 2.5
    env = np.sin(np.pi * x) ** 2 * (0.4 + shape)
    noise = bandpass(rng.standard_normal(len(t)), 250, 5500)
    freq = np.where(rising, 200 + 900 * x**2, 1100 - 900 * x)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.15
    return (noise + tone) * env


def riser(dur):
    t = tt(dur)
    x = t / dur
    freq = 180 * 2 ** (x * 2.2)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(freq) / SR)
    shimmer = highpass(rng.standard_normal(len(t)), 3000) * 0.25
    return (tone * (0.6 + 0.4 * np.sin(2 * np.pi * 8 * t)) + shimmer) * x**2 * np.minimum(1, (1 - x) * 40)


def reverse_swell(dur):
    t = tt(dur)
    x = t / dur
    noise = lowpass(rng.standard_normal(len(t)), 9000)
    return noise * x**3


def thunk():
    t = tt(0.4)
    freq = 70 + 130 * np.exp(-t * 25)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 14)
    click = bandpass(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t * 250) * 0.4
    return body + click


def blip(freq):
    t = tt(0.5)
    return (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)) * np.exp(-t * 11) * np.minimum(1, t / 0.002)


def pop():
    t = tt(0.18)
    freq = 280 + 900 * (1 - np.exp(-t * 35))
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 26)


def impact():
    t = tt(3.5)
    freq = 34 + 40 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 1.6)
    crash = lowpass(rng.standard_normal(len(t)), 7000) * np.exp(-t * 4) * 0.5
    return sub + crash


def tick():
    t = tt(0.05)
    return bandpass(rng.standard_normal(len(t)), 2000, 8000) * np.exp(-t * 120)


# ---------- score ----------


def score():
    # pad: chord per bar through 36 s, then a held tonic chord for the finale
    bar = 0
    while bar * BAR < 36.0:
        _, notes = CHORDS[bar % 4]
        gain = 0.16 * min(1.0, 0.7 + bar * 0.15)
        place(music, pad_chord(notes, BAR), bar * BAR, gain, reverb=0.4)
        bar += 1
    place(music, pad_chord([45, 57, 60, 64, 71, 76], 3.3, attack=0.05, release=1.2), IMPACT, 0.24, reverb=0.6)

    # melody: the digits of pi
    for i, (time, digit) in enumerate(NOTES):
        gain = 0.30 if time < 24 else 0.24
        pan = -0.35 if i % 2 else 0.35
        note = pluck(hz(SCALE[digit]))
        place(dry, note, time, gain, pan, reverb=0.35)
        place(dry, note, time + 0.375, gain * 0.28, -pan, reverb=0.3)  # dotted-eighth echo

    # finale motif: 3 . 1 4
    for time, digit in ((37.0, 3), (37.5, 1), (38.0, 4)):
        place(dry, pluck(hz(SCALE[digit] + 12), 2.5), time, 0.32, reverb=0.7)

    # drums and bass
    t = 8.0
    while t < 34.0 - 1e-9:
        in_breakdown = 18.0 <= t < 24.0
        beat_in_bar = round((t % BAR) / BEAT)
        if not in_breakdown or beat_in_bar in (0, 2):
            place(dry, kick(), t, 0.55)
            i0 = int(t * SR)
            env = np.exp(-np.arange(int(0.3 * SR)) / SR * 12)
            kick_env[i0 : i0 + len(env)] = np.maximum(kick_env[i0 : i0 + len(env)], env[: N - i0])
        place(dry, hat(), t + BEAT / 2, 0.10, 0.4)
        if t >= 24.0:
            place(dry, hat(0.04), t + BEAT / 4, 0.05, -0.4)
            place(dry, hat(0.04), t + 3 * BEAT / 4, 0.05, -0.4)
            if beat_in_bar in (1, 3):
                place(dry, clap(), t, 0.22, reverb=0.25)
        root, _ = CHORDS[int(t // BAR) % 4]
        for eighth in (0, 0.25):
            place(music, bass_note(hz(root)), t + eighth, 0.20)
        t += BEAT

    # sound effects, locked to the picture
    place(dry, impact(), 0.15, 0.35, reverb=0.5)
    place(dry, bell(hz(69), 3.0), 0.15, 0.22, reverb=0.7)
    place(dry, riser(2.6), 0.3, 0.06, reverb=0.5)
    place(dry, bell(hz(81), 2.0), 1.2, 0.14, 0.3, reverb=0.6)
    for k, digit in enumerate((3, 1, 4, 1, 5, 9)):
        place(dry, pluck(hz(SCALE[digit] + 12), 1.2), 1.2 + 0.125 * k, 0.12, -0.4 + 0.16 * k, reverb=0.6)
    place(dry, pop(), 2.0, 0.22, reverb=0.3)
    place(dry, bell(hz(76), 2.0), 2.0, 0.12, -0.3, reverb=0.6)
    for time in (3.55, 23.55, 33.6):
        place(dry, whoosh(0.8), time, 0.22, reverb=0.3)
    place(dry, bell(hz(81), 1.6), 4.3, 0.06, 0.2, reverb=0.6)
    place(dry, pop(), 5.3, 0.25)
    for k in range(5):
        place(dry, tick(), 6.3 + 0.2 * k + 0.05, 0.25, -0.6 + 0.3 * k)
    place(dry, riser(ROLL_END - ROLL_START), ROLL_START, 0.08, reverb=0.3)
    place(dry, bell(hz(81)), ROLL_END, 0.22, reverb=0.6)
    place(dry, bell(hz(88)), ROLL_END, 0.10, reverb=0.6)
    place(dry, whoosh(2.0, rising=False), 15.2, 0.14, reverb=0.4)
    place(dry, bell(hz(76), 2.0), 16.6, 0.14, reverb=0.6)
    place(dry, whoosh(0.9), 18.0, 0.12, reverb=0.3)
    for k, start in enumerate(PIECE_STARTS):
        place(dry, thunk(), start + PIECE_FALL * 0.85, 0.45, -0.4 + 0.4 * k)
    for k, m in enumerate((81, 84, 86, 88)):
        place(dry, bell(hz(m), 1.0), 21.45 + 0.06 * k, 0.07, 0.5, reverb=0.6)
    place(dry, bell(hz(69), 2.0), 22.3, 0.12, reverb=0.6)
    for time, m in zip(POLY_TIMES, (81, 84, 86, 88, 93)):
        place(dry, blip(hz(m)), time, 0.16, reverb=0.4)
    place(dry, bell(hz(76), 2.0), 31.7, 0.14, reverb=0.6)
    place(dry, bell(hz(81), 2.0), 32.3, 0.12, reverb=0.6)
    for k, time in enumerate(CIRCLE_POPS):
        place(dry, pop(), time, 0.28, -0.5 + 0.5 * k, reverb=0.3)
        place(dry, pluck(hz(SCALE[(3, 1, 4)[k]] + 12), 1.2), time, 0.16, -0.5 + 0.5 * k, reverb=0.5)
    place(dry, reverse_swell(IMPACT - 35.2), 35.2, 0.18)
    place(dry, impact(), IMPACT, 0.75, reverb=0.4)


def reverb_ir(length=2.8):
    t = tt(length)
    irs = []
    for _ in range(2):
        ir = lowpass(rng.standard_normal(len(t)), 6000) * np.exp(-t * 2.3)
        irs.append(ir / np.sqrt(np.sum(ir**2)))
    return irs


def main():
    score()
    music_bus = lowpass(music, 1600)
    duck = 1 - 0.6 * np.clip(kick_env, 0, 1)
    ir = reverb_ir()
    wet = np.stack([fftconvolve(send[c], ir[c])[:N] for c in range(2)])
    mix = dry + music_bus * duck + wet * 0.5
    mix = highpass(mix, 25)
    fade = np.clip((DUR - np.arange(N) / SR) / 1.0, 0, 1)
    mix *= fade
    mix /= np.max(np.abs(mix))
    mix = np.tanh(1.6 * mix) / np.tanh(1.6) * 0.9
    wavfile.write("pi.wav", SR, (mix.T * 32767).astype(np.int16))


if __name__ == "__main__":
    main()
