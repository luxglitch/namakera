#!/usr/bin/env python3
"""Generate an SVG terminal preview of the namakera TUI."""

# Cyberpunk palette (matches namakera.py exactly)
BG      = "#08000f"
BG2     = "#140028"
CYAN    = "#00e5ff"
PINK    = "#ff2d78"
YELLOW  = "#f5ff00"
GREEN   = "#39ff14"
DIM     = "#4a3060"
WHITE   = "#e8e0ff"

FONT    = "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace"
CW      = 9.6    # char width  (px) at font-size 15
LH      = 22     # line height (px)
PAD     = 24     # window padding

# ── Layout ────────────────────────────────────────────────────────────────────
# Each row: (text, color, bg_color_or_None, bold)
TITLE_BAR = ("▓▓ NAMAKERA ▓▓", CYAN, BG2, True)

ROWS = [
    # (text, fg, bg, bold)
    ("",                                              WHITE,  None,  False),
    ("  ▓ NAMAKERA ▓",                               PINK,   None,  True ),
    ("  llama.cpp build manager",                     DIM,    None,  False),
    ("",                                              WHITE,  None,  False),
    ("  INSTALL    clone → build → install  ",        CYAN,   BG2,   True ),
    ("  UPDATE     pull  → rebuild          ",        CYAN,   BG2,   True ),
    ("  STATUS                              ",        CYAN,   BG2,   True ),
    ("  SETTINGS   paths / backend          ",        CYAN,   BG2,   True ),
    ("  UNINSTALL                           ",        CYAN,   BG2,   True ),
    ("",                                              WHITE,  None,  False),
    ("  QUIT                                ",        PINK,   BG2,   True ),
    ("",                                              WHITE,  None,  False),
]

# Measure window size
MAX_CHARS = max(len(r[0]) for r in ROWS) + 4   # +4 for border chars
WIN_W  = int(MAX_CHARS * CW) + PAD * 2
WIN_H  = (len(ROWS) + 3) * LH + PAD * 2        # +3 for title bar + gaps
IMG_W  = WIN_W + 80
IMG_H  = WIN_H + 60


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rect(x, y, w, h, fill, rx=3) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="{rx}"/>'


def text(x, y, content, fill, bold=False, size=15, anchor="start") -> str:
    weight = "bold" if bold else "normal"
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family={FONT!r} '
            f'font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f'{esc(content)}</text>')


def border_rect(x, y, w, h, color, focused=False) -> list[str]:
    """Draw a double-line box border."""
    out = []
    lw = 1.5
    # outer
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
               f'fill="none" stroke="{color}" stroke-width="{lw}" rx="2"/>')
    # inner (double border effect)
    m = 3
    out.append(f'<rect x="{x+m}" y="{y+m}" width="{w-m*2}" height="{h-m*2}" '
               f'fill="none" stroke="{color}" stroke-width="{lw*0.6}" rx="1" '
               f'stroke-dasharray="none" opacity="0.5"/>')
    return out


lines = []

# ── SVG header ────────────────────────────────────────────────────────────────
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
             f'width="{IMG_W}" height="{IMG_H}" '
             f'viewBox="0 0 {IMG_W} {IMG_H}">')

# Scanline / glow filter
lines.append('''
<defs>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="2.5" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softglow">
    <feGaussianBlur stdDeviation="4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="bggrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%"   stop-color="#0d001a"/>
    <stop offset="100%" stop-color="#000008"/>
  </linearGradient>
</defs>
''')

# Background
lines.append(rect(0, 0, IMG_W, IMG_H, "url(#bggrad)", rx=8))

# Subtle grid lines (cyberpunk effect)
for gy in range(0, IMG_H, LH):
    lines.append(f'<line x1="0" y1="{gy}" x2="{IMG_W}" y2="{gy}" '
                 f'stroke="#1a0030" stroke-width="0.5" opacity="0.4"/>')

# Window position
WX = (IMG_W - WIN_W) // 2
WY = (IMG_H - WIN_H) // 2

# Window background
lines.append(rect(WX, WY, WIN_W, WIN_H, BG, rx=4))

# Glow behind window
lines.append(f'<rect x="{WX-6}" y="{WY-6}" width="{WIN_W+12}" height="{WIN_H+12}" '
             f'fill="none" stroke="{CYAN}" stroke-width="6" rx="6" '
             f'opacity="0.08" filter="url(#softglow)"/>')

# Double border
lines.extend(border_rect(WX, WY, WIN_W, WIN_H, CYAN))

# Title bar background
lines.append(rect(WX+4, WY+4, WIN_W-8, LH+6, BG2, rx=2))

# Title bar text
tx = WX + WIN_W // 2
ty = WY + 4 + (LH + 6) // 2
lines.append(text(tx, ty, TITLE_BAR[0], CYAN, bold=True, anchor="middle"))

# Separator line under title
sep_y = WY + LH + 10
lines.append(f'<line x1="{WX+4}" y1="{sep_y}" x2="{WX+WIN_W-4}" y2="{sep_y}" '
             f'stroke="{CYAN}" stroke-width="0.8" opacity="0.6"/>')

# Content rows
row_x  = WX + PAD // 2
row_y0 = sep_y + LH

for i, (content, fg, bg, bold) in enumerate(ROWS):
    ry = row_y0 + i * LH

    if bg and content.strip():
        # Button row — draw background pill
        btn_x = WX + 8
        btn_w = WIN_W - 16
        lines.append(rect(btn_x, ry - LH // 2 + 2, btn_w, LH - 2, bg, rx=2))

        # Left accent bar on buttons
        lines.append(f'<rect x="{btn_x}" y="{ry - LH//2 + 2}" '
                     f'width="3" height="{LH-2}" fill="{CYAN}" rx="1" opacity="0.7"/>')

    if content.strip():
        lines.append(text(row_x + 4, ry, content, fg, bold=bold))

# Corner decorations
corner_size = 12
corners = [
    (WX,           WY,           1,  1 ),
    (WX+WIN_W,     WY,          -1,  1 ),
    (WX,           WY+WIN_H,     1, -1 ),
    (WX+WIN_W,     WY+WIN_H,    -1, -1 ),
]
for cx, cy, dx, dy in corners:
    lines.append(f'<polyline points="{cx+dx*corner_size},{cy} {cx},{cy} {cx},{cy+dy*corner_size}" '
                 f'fill="none" stroke="{PINK}" stroke-width="2.5" filter="url(#glow)"/>')

# Bottom status bar
bar_y = WY + WIN_H + 12
lines.append(text(WX, bar_y, f"// jacked in //  source: {BG}  backend: cpu  ", DIM, size=12))
lines.append(text(WX + WIN_W, bar_y, "namakera v1.0", DIM, size=12, anchor="end"))

lines.append("</svg>")

svg = "\n".join(lines)
out = "preview.svg"
with open(out, "w") as f:
    f.write(svg)
print(f"Written {out}  ({len(svg):,} bytes)")
