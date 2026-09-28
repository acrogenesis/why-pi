"""Shared timing for picture and sound, so every hit lands on the same frame."""

DUR = 40.0
BEAT = 0.5  # 120 bpm
BAR = 2.0


def pi_digits(count):
    """First `count` decimal digits of pi (including the leading 3), via Machin's formula."""
    guard = 10
    scale = 10 ** (count + guard)

    def arctan_inv(x):
        total, term, n, sign = 0, scale // x, 1, 1
        x2 = x * x
        while term:
            total += sign * (term // n)
            term //= x2
            n += 2
            sign = -sign
        return total

    pi = 4 * (4 * arctan_inv(5) - arctan_inv(239))
    return str(pi // 10**guard)[:count]


DIGITS = pi_digits(400)


def melody_notes():
    """(time, digit) pairs: eighth notes 4-24 s, sixteenth notes 24-34 s."""
    notes = []
    t = 4.0
    while t < 24.0 - 1e-9:
        notes.append(t)
        t += 0.25
    while t < 34.0 - 1e-9:
        notes.append(t)
        t += 0.125
    return [(time, int(DIGITS[i])) for i, time in enumerate(notes)]


NOTES = melody_notes()

# Archimedes polygon steps
POLY_TIMES = [25.0, 26.5, 28.0, 29.5, 31.0]
POLY_SIDES = [6, 12, 24, 48, 96]

# Rolling
ROLL_START, ROLL_END = 8.5, 14.5

# Diameter pieces dropping onto the ruler
PIECE_STARTS = [19.2, 19.9, 20.6]
PIECE_FALL = 0.5

# Finale
CIRCLE_POPS = [34.2, 34.55, 34.9]
IMPACT = 36.5
