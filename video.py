import math

import cairo

from timeline import (
    CIRCLE_POPS,
    DIGITS,
    DUR,
    IMPACT,
    NOTES,
    PIECE_FALL,
    PIECE_STARTS,
    POLY_SIDES,
    POLY_TIMES,
    ROLL_END,
    ROLL_START,
)

W, H, FPS = 1920, 1080, 60
PI = math.pi

BG = (0.035, 0.047, 0.086)
CYAN = (0.30, 0.80, 0.95)
ORANGE = (0.98, 0.70, 0.22)
PINK = (0.98, 0.20, 0.52)
WHITE = (0.94, 0.95, 1.0)
DIM = (0.48, 0.53, 0.66)

SANS = "Noto Sans"
SERIF = "C059"
MONO = "JetBrainsMono Nerd Font"


# ---------- easing ----------


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, x):
    return a + (b - a) * x


def ease(x):
    x = clamp(x)
    return 4 * x**3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def back_out(x):
    x = clamp(x)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def fade_io(t, a, b, fin=0.4, fout=0.35):
    return ease(prog(t, a, a + fin)) * (1 - ease(prog(t, b - fout, b)))


# ---------- drawing primitives ----------


def polyline(ctx, pts, closed=False):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if closed:
        ctx.close_path()


def glow_stroke(ctx, color, width, alpha=1.0):
    path = ctx.copy_path()
    for mul, a in ((7, 0.035), (4, 0.07), (2.2, 0.16)):
        ctx.new_path()
        ctx.append_path(path)
        ctx.set_source_rgba(*color, a * alpha)
        ctx.set_line_width(width * mul)
        ctx.stroke()
    ctx.new_path()
    ctx.append_path(path)
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(width)
    ctx.stroke()


def dot(ctx, x, y, r, color, alpha=1.0):
    for mul, a in ((4, 0.06), (2.4, 0.14)):
        ctx.new_path()
        ctx.arc(x, y, r * mul, 0, 2 * PI)
        ctx.set_source_rgba(*color, a * alpha)
        ctx.fill()
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * PI)
    ctx.set_source_rgba(*color, alpha)
    ctx.fill()


def set_font(ctx, size, font=SANS, bold=False):
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)


def text(ctx, s, x, y, size, color=WHITE, alpha=1.0, align="c", font=SANS, bold=False):
    if alpha <= 0.002:
        return
    set_font(ctx, size, font, bold)
    advance = ctx.text_extents(s).x_advance
    x0 = {"c": x - advance / 2, "r": x - advance, "l": x}[align]
    ctx.move_to(x0, y)
    ctx.set_source_rgba(*color, alpha)
    ctx.show_text(s)


def text_parts(ctx, parts, x, y, size, alpha=1.0, font=SANS, bold=False):
    """Centered run of (string, color) segments."""
    if alpha <= 0.002:
        return
    set_font(ctx, size, font, bold)
    total = sum(ctx.text_extents(s).x_advance for s, _ in parts)
    cx = x - total / 2
    for s, color in parts:
        ctx.move_to(cx, y)
        ctx.set_source_rgba(*color, alpha)
        ctx.show_text(s)
        cx += ctx.text_extents(s).x_advance


def caption(ctx, t, s, a, b, y=140):
    alpha = fade_io(t, a, b)
    lift = (1 - ease_out(prog(t, a, a + 0.5))) * 24
    text(ctx, s, 960, y + lift, 46, WHITE, alpha, bold=True)


def glow_glyph(ctx, s, cx, cy, size, color, alpha, scale=1.0, font=SERIF):
    """Large glyph centred on (cx, cy) with a soft halo."""
    if alpha <= 0.002:
        return
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(scale, scale)
    set_font(ctx, size, font, bold=True)
    e = ctx.text_extents(s)
    ctx.move_to(-e.x_bearing - e.width / 2, -e.y_bearing - e.height / 2)
    ctx.text_path(s)
    path = ctx.copy_path()
    for w, a in ((40, 0.03), (22, 0.06), (10, 0.12)):
        ctx.new_path()
        ctx.append_path(path)
        ctx.set_source_rgba(*color, a * alpha)
        ctx.set_line_width(w)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.new_path()
    ctx.append_path(path)
    ctx.set_source_rgba(*color, alpha)
    ctx.fill()
    ctx.restore()


def background(ctx, t):
    ctx.set_source_rgb(*BG)
    ctx.paint()
    spacing = 64
    drift = (t * 8) % spacing
    ctx.set_source_rgba(*DIM, 0.10)
    y = -spacing + drift * 0.5
    while y < H + spacing:
        x = -spacing + drift
        while x < W + spacing:
            ctx.new_path()
            ctx.arc(x, y, 1.3, 0, 2 * PI)
            ctx.fill()
            x += spacing
        y += spacing
    vignette = cairo.RadialGradient(960, 540, 300, 960, 540, 1250)
    vignette.add_color_stop_rgba(0, 0, 0, 0, 0)
    vignette.add_color_stop_rgba(1, 0, 0, 0, 0.75)
    ctx.set_source(vignette)
    ctx.paint()


# ---------- scene 1: title (0-4 s) ----------


def scene_title(ctx, t):
    exit_ = ease(prog(t, 3.45, 4.05))
    cx, cy = 960, 470

    orbit = ease(prog(t, 0.3, 2.9))
    if orbit > 0:
        radius = 285 * (1 + exit_ * 1.5)
        start = -PI / 2
        ctx.new_path()
        ctx.arc(cx, cy, radius, start, start + orbit * 2 * PI)
        glow_stroke(ctx, CYAN, 4, 0.9 * (1 - exit_))
        tip = start + orbit * 2 * PI
        if orbit < 1:
            dot(ctx, cx + radius * math.cos(tip), cy + radius * math.sin(tip), 7, PINK)

    pop = back_out(prog(t, 0.15, 0.95))
    glow_glyph(ctx, "π", cx, cy, 330, WHITE, clamp(pop) * (1 - exit_), pop * (1 + exit_ * 2.5))

    lift = (1 - ease_out(prog(t, 1.2, 1.7))) * 30
    text(ctx, "= 3.14159…", 960, 870 + lift, 64, WHITE, fade_io(t, 1.2, 3.6), font=MONO, bold=True)
    lift = (1 - ease_out(prog(t, 2.0, 2.5))) * 30
    text(ctx, "but why?", 960, 955 + lift, 44, PINK, fade_io(t, 2.0, 3.6), bold=True)


# ---------- scenes 2-4: roll the circle along a ruler (4-24 s) ----------

R_WORLD = 0.5


def roll_theta(t):
    return 2 * PI * ease(prog(t, ROLL_START, ROLL_END))


def roll_cam(t):
    """(ox, oy, s): screen position of world origin and pixels per unit."""
    z = ease(prog(t, 15.2, 17.2)) * (1 - ease(prog(t, 18.0, 18.9)))
    s = math.exp(lerp(math.log(320), math.log(6000), z))
    pi_x = lerp(320 + PI * 320, 960, z)
    line_y = lerp(720, 620, z)
    return pi_x - PI * s, line_y, s


def to_screen(cam, x, y):
    ox, oy, s = cam
    return ox + x * s, oy - y * s


def number_line(ctx, cam, reveal):
    ox, oy, s = cam
    lo, hi = -0.3, lerp(-0.3, 4.3, reveal)
    vis_lo = max(lo, (-40 - ox) / s)
    vis_hi = min(hi, (W + 40 - ox) / s)
    if vis_hi <= vis_lo:
        return
    polyline(ctx, [to_screen(cam, vis_lo, 0), to_screen(cam, vis_hi, 0)])
    ctx.set_source_rgba(*WHITE, 0.55)
    ctx.set_line_width(3)
    ctx.stroke()

    tenth_a = prog(s, 700, 1800)
    tenth_label_a = prog(s, 1500, 3000)
    hund_a = prog(s, 2500, 5000)
    hund_label_a = prog(s, 4200, 6000)

    first = math.ceil(vis_lo * 100)
    last = math.floor(vis_hi * 100)
    for k in range(first, last + 1):
        x = k / 100
        sx, sy = to_screen(cam, x, 0)
        if k % 100 == 0:
            pop = back_out(prog(reveal * 4.6 - 0.3, x, x + 0.25))
            height, alpha, label, size = 20 * pop, clamp(pop), str(k // 100), 36
            label_a = alpha
        elif k % 10 == 0:
            height, alpha, label, size = 13, tenth_a, f"{x:.1f}", 28
            label_a = tenth_label_a
        else:
            height, alpha, label, size = 8, hund_a, f"{x:.2f}", 22
            label_a = hund_label_a if k == 314 else 0
        if alpha <= 0.01:
            continue
        ctx.new_path()
        ctx.move_to(sx, sy - height)
        ctx.line_to(sx, sy + height)
        ctx.set_source_rgba(*WHITE, 0.6 * alpha)
        ctx.set_line_width(2.5 if k % 100 == 0 else 1.6)
        ctx.stroke()
        text(ctx, label, sx, sy + 34 + size, size, DIM, label_a, font=MONO)


def scene_roll(ctx, t):
    cam = roll_cam(t)
    ox, oy, s = cam
    theta = roll_theta(t)
    r_px = R_WORLD * s

    number_line(ctx, cam, ease(prog(t, 6.3, 7.3)))

    center_x = R_WORLD * theta
    cx, cy = to_screen(cam, center_x, R_WORLD)
    wheel_a = 1 - prog(t, 15.0, 15.6)
    p_angle = -PI / 2 - theta  # math angle (y up) of the marked point

    def wheel_point(angle, radius=r_px):
        return cx + radius * math.cos(angle), cy - radius * math.sin(angle)

    # cycloid traced by the marked point
    trace_a = 0.55 * (1 - prog(t, 15.0, 15.6))
    if theta > 0.01 and trace_a > 0:
        steps = max(2, int(theta * 40))
        pts = []
        for i in range(steps + 1):
            th = theta * i / steps
            pts.append(to_screen(cam, R_WORLD * (th - math.sin(th)), R_WORLD * (1 - math.cos(th))))
        polyline(ctx, pts)
        ctx.set_dash([2, 9])
        ctx.set_source_rgba(*PINK, trace_a)
        ctx.set_line_width(2.5)
        ctx.stroke()
        ctx.set_dash([])

    if wheel_a > 0:
        if t > 5.5:
            ctx.new_path()
            ctx.arc(cx, cy, r_px, 0, 2 * PI)
            ctx.set_source_rgba(*CYAN, 0.16 * wheel_a * prog(t, 5.5, 6.0))
            ctx.set_line_width(2)
            ctx.stroke()
        drawn = min(ease(prog(t, 4.3, 5.5)) * 2 * PI, 2 * PI - theta)
        if drawn > 0.001:
            steps = max(2, int(drawn * 40))
            pts = [wheel_point(-PI / 2 + drawn * i / steps) for i in range(steps + 1)]
            polyline(ctx, pts)
            glow_stroke(ctx, CYAN, 5, wheel_a)

        grow = ease(prog(t, 5.5, 6.2))
        if grow > 0:
            p = wheel_point(p_angle)
            q = wheel_point(p_angle + PI)
            polyline(ctx, [p, (lerp(p[0], q[0], grow), lerp(p[1], q[1], grow))])
            glow_stroke(ctx, ORANGE, 4, wheel_a)
        label_a = fade_io(t, 6.0, 8.8) * wheel_a
        text(ctx, "diameter = 1", cx + r_px + 28, cy + 12, 32, ORANGE, label_a, align="l", bold=True)

    # circumference laid flat on the ruler
    if theta > 0.001:
        polyline(ctx, [to_screen(cam, 0, 0), to_screen(cam, R_WORLD * theta, 0)])
        glow_stroke(ctx, CYAN, 6)

    # the marked point
    pop = back_out(prog(t, 5.3, 5.7))
    if pop > 0:
        if wheel_a > 0 and theta < 2 * PI - 1e-6:
            px, py = wheel_point(p_angle)
        else:
            px, py = to_screen(cam, PI, 0)
        dot(ctx, px, py, 8 * pop, PINK)

    # landing ring
    ring = prog(t, ROLL_END, ROLL_END + 0.7)
    if 0 < ring < 1:
        lx, ly = to_screen(cam, PI, 0)
        ctx.new_path()
        ctx.arc(lx, ly, 12 + ring * 110, 0, 2 * PI)
        ctx.set_source_rgba(*PINK, (1 - ring) * 0.9)
        ctx.set_line_width(4)
        ctx.stroke()

    # distance counter
    counter_a = fade_io(t, 8.5, 18.2)
    text_parts(
        ctx,
        [("distance rolled  ", DIM), (f"{R_WORLD * theta:.5f}", WHITE)],
        960,
        880,
        40,
        counter_a,
        font=MONO,
        bold=True,
    )

    # zoomed-in callout
    call_a = fade_io(t, 16.6, 18.2)
    if call_a > 0:
        lx, ly = to_screen(cam, PI, 0)
        rise = ease_out(prog(t, 16.6, 17.0))
        polyline(ctx, [(lx, ly - 24), (lx, ly - 24 - 110 * rise)])
        glow_stroke(ctx, PINK, 3, call_a)
        text(ctx, "3.14159265…", lx, ly - 160, 72, PINK, call_a, font=MONO, bold=True)

    diameter_pieces(ctx, t, cam)

    caption(ctx, t, "Take a circle exactly 1 unit across", 4.3, 7.9)
    caption(ctx, t, "Roll it one full turn along a ruler…", 8.2, 14.9)
    caption(ctx, t, "…it lands just past 3", 15.0, 17.9)
    caption(ctx, t, "How many diameters fit in that distance?", 18.5, 21.5)
    caption(ctx, t, "Three, plus a sliver that never ends", 21.7, 23.9)


def diameter_pieces(ctx, t, cam):
    lift = 0.17
    for k, start in enumerate(PIECE_STARTS):
        x = prog(t, start, start + PIECE_FALL)
        if x <= 0:
            continue
        fall = ease_out(x)
        mid_x, mid_y = k + 0.5, lerp(1.25, lift, fall)
        angle = lerp(PI / 2, 0, ease(x))
        dx, dy = 0.5 * math.cos(angle), 0.5 * math.sin(angle)
        a = to_screen(cam, mid_x - dx, mid_y - dy)
        b = to_screen(cam, mid_x + dx, mid_y + dy)
        alpha = clamp(x * 4) * (1 - prog(t, 23.5, 24.0))
        polyline(ctx, [(a[0] + 3, a[1]), (b[0] - 3, b[1])])
        glow_stroke(ctx, ORANGE, 6, alpha)
        mx, my = to_screen(cam, mid_x, mid_y)
        text(ctx, str(k + 1), mx, my - 22, 34, ORANGE, alpha * prog(t, start + 0.4, start + 0.6), bold=True)

    grow = ease(prog(t, 21.4, 21.9))
    if grow > 0:
        alpha = 1 - prog(t, 23.5, 24.0)
        a = to_screen(cam, 3, lift)
        b = to_screen(cam, lerp(3, PI, grow), lift)
        polyline(ctx, [(a[0] + 2, a[1]), b])
        glow_stroke(ctx, PINK, 6, alpha)
        text(ctx, "+ 0.14159…", a[0] + 24, a[1] - 26, 34, PINK, alpha * prog(t, 21.7, 22.0), align="l", bold=True)

    text_parts(
        ctx,
        [("circumference ÷ diameter = ", WHITE), ("3.14159…", CYAN), ("  = π", PINK)],
        960,
        960,
        52,
        fade_io(t, 22.3, 24.0),
        bold=True,
    )


# ---------- scene 5: Archimedes squeezes pi (24-34 s) ----------

CIRCLE_C = (600, 585)
CIRCLE_R = 285


def polygon_state(t):
    """(sides, inner radii, outer radii, vertex angles) of the morphing polygons."""
    step = max(i for i, time in enumerate(POLY_TIMES) if time <= t) if t >= POLY_TIMES[0] else -1
    if step <= 0:
        n = POLY_SIDES[0]
        grow = back_out(prog(t, POLY_TIMES[0], POLY_TIMES[0] + 0.5)) if step == 0 else 0
        angles = [-PI / 2 + 2 * PI * k / n for k in range(n)]
        inner = [CIRCLE_R * grow] * n
        outer = [CIRCLE_R / math.cos(PI / n) * grow] * n
        return n, inner, outer, angles
    n = POLY_SIDES[step - 1]
    p = ease(prog(t, POLY_TIMES[step], POLY_TIMES[step] + 0.6))
    angles = [-PI / 2 + PI * k / n for k in range(2 * n)]
    inner, outer = [], []
    for k in range(2 * n):
        if k % 2 == 0:
            inner.append(CIRCLE_R)
            outer.append(lerp(CIRCLE_R / math.cos(PI / n), CIRCLE_R / math.cos(PI / (2 * n)), p))
        else:
            inner.append(lerp(CIRCLE_R * math.cos(PI / n), CIRCLE_R, p))
            outer.append(lerp(CIRCLE_R, CIRCLE_R / math.cos(PI / (2 * n)), p))
    return 2 * n, inner, outer, angles


def polygon_points(radii, angles):
    cx, cy = CIRCLE_C
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for r, a in zip(radii, angles)]


def perimeter_ratio(pts):
    total = sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
    return total / (2 * CIRCLE_R)


def gauge_x(value):
    return lerp(1150, 1780, (value - 3.0) / 0.5)


def scene_archimedes(ctx, t):
    cx, cy = CIRCLE_C
    sweep = ease(prog(t, 24.1, 24.9))
    if sweep > 0:
        ctx.new_path()
        ctx.arc(cx, cy, CIRCLE_R, -PI / 2, -PI / 2 + sweep * 2 * PI)
        ctx.set_source_rgba(*WHITE, 0.9)
        ctx.set_line_width(3)
        ctx.stroke()

    n, inner, outer, angles = polygon_state(t)
    inner_pts = polygon_points(inner, angles)
    outer_pts = polygon_points(outer, angles)
    if t >= POLY_TIMES[0]:
        polyline(ctx, outer_pts, closed=True)
        glow_stroke(ctx, ORANGE, 3)
        polyline(ctx, inner_pts, closed=True)
        glow_stroke(ctx, CYAN, 3)
        dots_a = 1 - prog(n, 24, 48)
        if dots_a > 0:
            for x, y in inner_pts:
                dot(ctx, x, y, 4.5, CYAN, dots_a)

    step_flash = max((1 - prog(t, time, time + 0.5) for time in POLY_TIMES if time <= t), default=0)

    panel_a = fade_io(t, 24.6, 34.0)
    inside = perimeter_ratio(inner_pts) if t >= POLY_TIMES[0] else 0
    outside = perimeter_ratio(outer_pts) if t >= POLY_TIMES[0] else 0
    shown_sides = n if t >= POLY_TIMES[0] else 0

    text(ctx, "SIDES", 1150, 300, 24, DIM, panel_a, align="l", bold=True)
    text(ctx, str(shown_sides), 1150, 385, 80 + step_flash * 14, WHITE, panel_a, align="l", font=MONO, bold=True)
    text(ctx, "inside polygon", 1150, 470, 30, CYAN, panel_a, align="l", bold=True)
    text(ctx, f"{inside:.5f}", 1780, 470, 44, CYAN, panel_a, align="r", font=MONO, bold=True)
    text(ctx, "outside polygon", 1150, 540, 30, ORANGE, panel_a, align="l", bold=True)
    text(ctx, f"{outside:.5f}", 1780, 540, 44, ORANGE, panel_a, align="r", font=MONO, bold=True)

    gy = 650
    if panel_a > 0:
        polyline(ctx, [(gauge_x(3.0), gy), (gauge_x(3.5), gy)])
        ctx.set_source_rgba(*WHITE, 0.4 * panel_a)
        ctx.set_line_width(2)
        ctx.stroke()
        for k in range(6):
            v = 3.0 + k * 0.1
            x = gauge_x(v)
            polyline(ctx, [(x, gy - 8), (x, gy + 8)])
            ctx.stroke()
            text(ctx, f"{v:.1f}", x, gy + 40, 20, DIM, panel_a, font=MONO)
        px = gauge_x(PI)
        polyline(ctx, [(px, gy - 30), (px, gy + 14)])
        ctx.set_source_rgba(*PINK, panel_a)
        ctx.set_line_width(2.5)
        ctx.stroke()
        text(ctx, "π", px, gy - 40, 30, PINK, panel_a, font=SERIF, bold=True)
        if t >= POLY_TIMES[0]:
            a, b = gauge_x(clamp(inside, 3.0, 3.5)), gauge_x(clamp(outside, 3.0, 3.5))
            ctx.rectangle(a, gy - 10, max(b - a, 1), 20)
            ctx.set_source_rgba(*WHITE, 0.18 * panel_a)
            ctx.fill()
            for x, color in ((a, CYAN), (b, ORANGE)):
                polyline(ctx, [(x, gy - 22), (x, gy + 22)])
                glow_stroke(ctx, color, 4, panel_a)

    result_a = fade_io(t, 31.7, 34.0)
    text(ctx, "Archimedes' result", 1465, 770, 24, DIM, result_a, bold=True)
    text_parts(
        ctx,
        [("3.1408", CYAN), (" < ", WHITE), ("π", PINK), (" < ", WHITE), ("3.1429", ORANGE)],
        1465,
        835,
        52,
        result_a,
        font=MONO,
        bold=True,
    )
    lift = (1 - ease_out(prog(t, 32.3, 32.8))) * 20
    text(ctx, "both start with 3.14", 1465, 900 + lift, 36, PINK, fade_io(t, 32.3, 34.0), bold=True)

    caption(ctx, t, "Archimedes, 250 BC: trap the circle between polygons", 24.2, 33.9, y=150)


# ---------- scene 6: finale (34-40 s) ----------


def scene_finale(ctx, t):
    gather = ease(prog(t, 35.9, IMPACT))
    for (x, r), start in zip(((500, 70), (900, 120), (1380, 180)), CIRCLE_POPS):
        sweep = ease(prog(t, start, start + 0.5))
        if sweep <= 0 or gather >= 1:
            continue
        x = lerp(x, 960, gather)
        y = lerp(500, 540, gather)
        r = r * (1 - gather)
        alpha = 1 - gather
        ctx.new_path()
        ctx.arc(x, y, max(r, 0.1), -PI / 2, -PI / 2 + sweep * 2 * PI)
        glow_stroke(ctx, CYAN, 4, alpha)
        grow = ease(prog(t, start + 0.3, start + 0.6))
        if grow > 0:
            polyline(ctx, [(x - r * grow, y), (x + r * grow, y)])
            glow_stroke(ctx, ORANGE, 3.5, alpha)
        label_a = prog(t, start + 0.35, start + 0.6) * alpha
        text(ctx, "C ÷ d = 3.14159…", x, 790 - gather * 200, 30, WHITE, label_a, font=MONO, bold=True)
    caption(ctx, t, "Any circle. Any size. Same number.", 34.1, IMPACT)

    hit = prog(t, IMPACT, IMPACT + 0.6)
    if hit > 0:
        flash = (1 - prog(t, IMPACT, IMPACT + 0.5)) * 0.35
        ctx.set_source_rgba(*WHITE, flash)
        ctx.paint()
        glow_glyph(ctx, "π", 960, 470, 300, WHITE, clamp(hit * 3), back_out(hit))
        lift = (1 - ease_out(prog(t, IMPACT + 0.3, IMPACT + 0.8))) * 24
        text(ctx, "≈ 3.14", 960, 720 + lift, 76, CYAN, ease(prog(t, IMPACT + 0.3, IMPACT + 0.7)), font=MONO, bold=True)
        digit_ring(ctx, t)
        text(
            ctx,
            "the distance around any circle, divided by the distance across",
            960,
            1010,
            32,
            DIM,
            ease(prog(t, 37.5, 38.1)),
            bold=True,
        )


def digit_ring(ctx, t):
    count = 150
    radius = 390
    rotation = -(t - IMPACT) * 0.18
    set_font(ctx, 26, MONO, bold=True)
    for i in range(count):
        appear = prog(t, IMPACT + 0.1 + i * 0.012, IMPACT + 0.3 + i * 0.012)
        if appear <= 0:
            break
        ch = "3."[i] if i < 2 else DIGITS[i - 1]
        color = PINK if i < 4 else CYAN
        alpha = appear * lerp(1.0, 0.25, i / count)
        ctx.save()
        ctx.translate(960, 540)
        ctx.rotate(rotation + i * 2 * PI / (count + 8))
        ctx.translate(0, -radius)
        adv = ctx.text_extents(ch).x_advance
        ctx.move_to(-adv / 2, 0)
        ctx.set_source_rgba(*color, alpha)
        ctx.show_text(ch)
        ctx.restore()


# ---------- the pi-digit ticker that matches the melody ----------


def digit_ticker(ctx, t):
    alpha = fade_io(t, 4.3, 34.0)
    if alpha <= 0 or t < NOTES[0][0]:
        return
    idx = max(i for i, (time, _) in enumerate(NOTES) if time <= t)
    pos = idx - 1 + ease_out(prog(t, NOTES[idx][0], NOTES[idx][0] + 0.1))
    spacing = 30
    y = 1040
    text(ctx, "the melody plays π:", 560, y, 20, DIM, alpha, align="r", bold=True)
    set_font(ctx, 28, MONO, bold=True)
    for j in range(max(0, idx - 12), min(len(NOTES), idx + 12)):
        x = 960 + (j - pos) * spacing
        d = abs(j - pos)
        a = alpha * clamp(1 - d / 12)
        if j == idx:
            pulse = 1 - prog(t, NOTES[idx][0], NOTES[idx][0] + 0.2)
            dot(ctx, x, y - 10, 18 + pulse * 6, PINK, 0.25 * alpha)
            color, a = PINK, alpha
        else:
            color = WHITE if j < idx else DIM
            a *= 0.7 if j < idx else 0.4
        ch = str(NOTES[j][1])
        adv = ctx.text_extents(ch).x_advance
        ctx.move_to(x - adv / 2, y)
        ctx.set_source_rgba(*color, a)
        ctx.show_text(ch)


# ---------- compositing ----------

SCENES = [
    (scene_title, 0.0, 4.1),
    (scene_roll, 3.95, 24.1),
    (scene_archimedes, 23.95, 34.1),
    (scene_finale, 33.95, DUR),
]


def render_frame(index):
    t = index / FPS
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surface)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    background(ctx, t)
    for scene, a, b in SCENES:
        if a <= t <= b:
            ctx.push_group()
            scene(ctx, t)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(prog(t, a, a + 0.3) * (1 - prog(t, b - 0.4, b)))
    digit_ticker(ctx, t)
    fade = prog(t, 39.2, DUR)
    if fade > 0:
        ctx.set_source_rgba(0, 0, 0, ease(fade))
        ctx.paint()
    surface.flush()
    return bytes(surface.get_data())
