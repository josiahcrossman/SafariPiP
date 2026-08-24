#!/usr/bin/env python3
"""Generate SafariPiP icons with the standard library only (no Pillow).

Draws a Picture-in-Picture glyph: a rounded outer frame with a small filled
inset rectangle in the lower-right, on a blue rounded-square background.
Renders at high resolution with 3x3 supersampling for smooth edges; sips
downsizes to the remaining icon sizes.
"""
import struct
import zlib

S = 512          # output logical size
SS = 3           # supersample factor per axis
N = S * SS

# Colors (RGBA, 0-255)
BG_TOP = (10, 132, 255)      # iOS-ish blue
BG_BOT = (0, 96, 224)
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)


def rounded_rect_coverage(x, y, rx0, ry0, rx1, ry1, radius):
    """Signed-ish inside test for a rounded rect; returns True if (x,y) inside."""
    # Clamp point to the inner rectangle (shrunk by radius) then measure dist.
    cx = min(max(x, rx0 + radius), rx1 - radius)
    cy = min(max(y, ry0 + radius), ry1 - radius)
    dx = x - cx
    dy = y - cy
    return (dx * dx + dy * dy) <= radius * radius


def blend(dst, src):
    sr, sg, sb, sa = src
    if sa == 0:
        return dst
    if sa == 255:
        return src
    a = sa / 255.0
    dr, dg, db, da = dst
    return (
        int(sr * a + dr * (1 - a)),
        int(sg * a + dg * (1 - a)),
        int(sb * a + db * (1 - a)),
        255,
    )


def sample(px, py):
    """Return RGBA for a supersample point in logical (0..S) coordinates."""
    # Background rounded square
    margin = S * 0.06
    if not rounded_rect_coverage(px, py, margin, margin, S - margin, S - margin, S * 0.22):
        return TRANSPARENT
    t = py / S
    bg = (
        int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t),
        int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t),
        int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t),
        255,
    )
    color = bg

    # Outer frame (white rounded outline)
    fx0, fy0, fx1, fy1 = S * 0.20, S * 0.24, S * 0.80, S * 0.72
    outer = rounded_rect_coverage(px, py, fx0, fy0, fx1, fy1, S * 0.05)
    stroke = S * 0.055
    inner = rounded_rect_coverage(
        px, py, fx0 + stroke, fy0 + stroke, fx1 - stroke, fy1 - stroke, S * 0.03
    )
    if outer and not inner:
        color = blend(color, WHITE)

    # Inset PiP rectangle (lower-right, filled white)
    ix0, iy0, ix1, iy1 = S * 0.50, S * 0.46, S * 0.74, S * 0.66
    if rounded_rect_coverage(px, py, ix0, iy0, ix1, iy1, S * 0.02):
        color = blend(color, WHITE)

    return color


def build():
    raw = bytearray()
    for gy in range(S):
        raw.append(0)  # PNG filter type 0 for this scanline
        for gx in range(S):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    px = gx + (sx + 0.5) / SS
                    py = gy + (sy + 0.5) / SS
                    cr, cg, cb, ca = sample(px, py)
                    r += cr * ca
                    g += cg * ca
                    b += cb * ca
                    a += ca
            n = SS * SS
            if a > 0:
                # premultiplied average -> straight alpha
                raw.append(int(r / a))
                raw.append(int(g / a))
                raw.append(int(b / a))
                raw.append(int(a / n))
            else:
                raw.extend((0, 0, 0, 0))
    return bytes(raw)


def png_chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, width, height, raw):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(raw, 9)
    with open(path, "wb") as f:
        f.write(sig)
        f.write(png_chunk(b"IHDR", ihdr))
        f.write(png_chunk(b"IDAT", idat))
        f.write(png_chunk(b"IEND", b""))


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "extension", "images", "icon-512.png")
    write_png(out, S, S, build())
    print("wrote", out)
