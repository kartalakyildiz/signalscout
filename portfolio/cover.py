"""Builds portfolio/graphics/05_signalscout_cover.svg + .png"""
from pathlib import Path

from build_graphics import (
    ACCENT, ACCENT_BG, ACCENT_BORDER, ACCENT_TEXT, ACCENT_GLOW,
    BG, BORDER, BORDER_SOFT, DANGER_BG, DANGER_BORDER, DANGER_TEXT,
    GRAPHICS_DIR, H, SURFACE, SURFACE_2, TEXT_BODY, TEXT_FAINT, TEXT_MUTED, TEXT_PRIMARY, W,
    arrowhead, esc, line, pill, rect, render_png, text, write_svg,
)

parts: list[str] = []

# --- Background --------------------------------------------------------
parts.append(rect(0, 0, W, H, rx=0, fill=BG, stroke="none"))
# Faint ambient glow behind the right-hand preview panel - restrained, not a gradient wash
parts.append(
    f'<defs><radialGradient id="glow" cx="50%" cy="35%" r="65%">'
    f'<stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.10"/>'
    f'<stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>'
    f"</radialGradient></defs>"
)
parts.append(f'<circle cx="1120" cy="360" r="420" fill="url(#glow)"/>')

# --- Left column: branding ---------------------------------------------
LX = 72
badge_label = "EVIDENCE-FIRST RESEARCH PIPELINE"
badge_w = 322
badge_y = 100
parts.append(rect(LX, badge_y, badge_w, 32, rx=5, fill=ACCENT_BG, stroke=ACCENT_BORDER))
parts.append(text(LX + badge_w / 2, badge_y + 21, badge_label, size=12.5, color=ACCENT_TEXT,
                   weight=700, anchor="middle", letter_spacing="0.07em"))

parts.append(text(LX, 224, "SignalScout", size=80, color=TEXT_PRIMARY, weight=750))

parts.append(text(LX, 272, "AI-Powered Web Research & Qualification", size=26, color=TEXT_BODY, weight=500))

parts.append(text(LX, 318, "Web Scraping  •  Structured AI  •  Evidence Validation", size=16.5,
                   color=TEXT_MUTED, weight=500, letter_spacing="0.01em"))
parts.append(text(LX, 344, "SQLite  •  Review Dashboard", size=16.5,
                   color=TEXT_MUTED, weight=500, letter_spacing="0.01em"))

# Value statement, styled like the dashboard's evidence-quote blockquote
VQ_Y = 404
VQ_W = 660
VQ_H = 96
parts.append(rect(LX, VQ_Y, VQ_W, VQ_H, rx=8, fill=SURFACE_2, stroke=BORDER_SOFT))
parts.append(line(LX, VQ_Y, LX, VQ_Y + VQ_H, stroke=ACCENT, width=3))
parts.append(text(LX + 28, VQ_Y + 42, "From public company websites to verified,", size=19.5,
                   color="#E6EDF3", weight=500))
parts.append(text(LX + 28, VQ_Y + 70, "reviewable business signals.", size=19.5,
                   color="#E6EDF3", weight=500))

# Bottom-left implementation tags, echoing the dashboard's own micro-copy
TAGS_Y = 556
tag_items = [
    "Real HTTP + browser-fallback scraping",
    "Structured AI extraction (typed signals)",
    "Evidence verified against scraped source text",
    "Deterministic Python qualification logic",
]
ty = TAGS_Y
for label in tag_items:
    parts.append(f'<circle cx="{LX + 4}" cy="{ty - 5}" r="3" fill="{ACCENT}"/>')
    parts.append(text(LX + 18, ty, label, size=15.5, color=TEXT_BODY, weight=400))
    ty += 36

# "Built with" tech row - small outline chips, low visual weight
BUILT_Y = ty + 34
parts.append(text(LX, BUILT_Y, "BUILT WITH", size=11.5, color=TEXT_FAINT, weight=700,
                   letter_spacing="0.08em"))
chip_labels = ["Python", "OpenAI API", "SQLite", "Streamlit"]
cx = LX
cy = BUILT_Y + 20
for label in chip_labels:
    cw = 16 + len(label) * 7.6
    parts.append(rect(cx, cy, cw, 30, rx=5, fill="none", stroke=BORDER))
    parts.append(text(cx + cw / 2, cy + 20, label, size=13, color=TEXT_MUTED, weight=500, anchor="middle"))
    cx += cw + 12

# --- Right column: pipeline preview + trust-layer card ------------------
RX = 848
RW = 520

# Card 1: research pipeline preview
P_Y = 100
P_H = 472
parts.append(rect(RX, P_Y, RW, P_H, rx=10, fill=SURFACE, stroke=BORDER))
parts.append(text(RX + 28, P_Y + 38, "RESEARCH PIPELINE", size=12.5, color=TEXT_MUTED, weight=700,
                   letter_spacing="0.08em"))
parts.append(line(RX + 28, P_Y + 52, RX + RW - 28, P_Y + 52, stroke=BORDER_SOFT, width=1))

stages = ["Company Websites", "Web Research", "Structured AI", "Evidence Check", "Qualification"]
stage_x = RX + 28
stage_w = RW - 56
stage_h = 54
stage_gap = 26
sy = P_Y + 76
for i, label in enumerate(stages):
    is_last = i == len(stages) - 1
    fill = ACCENT_BG if is_last else SURFACE_2
    stroke = ACCENT_BORDER if is_last else BORDER_SOFT
    color = ACCENT_TEXT if is_last else TEXT_BODY
    parts.append(rect(stage_x, sy, stage_w, stage_h, rx=7, fill=fill, stroke=stroke))
    parts.append(f'<circle cx="{stage_x + 24}" cy="{sy + stage_h / 2}" r="4.5" fill="{ACCENT if is_last else TEXT_FAINT}"/>')
    parts.append(text(stage_x + 44, sy + stage_h / 2 + 5.5, label, size=16, color=color, weight=600))
    if not is_last:
        cx = stage_x + stage_w / 2
        y1 = sy + stage_h
        y2 = y1 + stage_gap
        parts.append(line(cx, y1 + 2, cx, y2 - 7, stroke=BORDER, width=1.5))
        parts.append(arrowhead(cx, y2 - 2, "down", size=5, fill=TEXT_FAINT))
    sy += stage_h + stage_gap

# Card 2: illustrative trust-layer result card (not tied to any real company)
R_Y = P_Y + P_H + 36
R_H = 296
parts.append(rect(RX, R_Y, RW, R_H, rx=10, fill=SURFACE, stroke=BORDER))
parts.append(text(RX + 28, R_Y + 36, "EVIDENCE CHECK — ILLUSTRATIVE", size=12, color=TEXT_MUTED,
                   weight=700, letter_spacing="0.07em"))
parts.append(line(RX + 28, R_Y + 50, RX + RW - 28, R_Y + 50, stroke=BORDER_SOFT, width=1))

sig_rows = [
    ("AI Adoption", "VALIDATED", "accent"),
    ("Technology Change", "VALIDATED", "accent"),
    ("Hiring", "INVALID", "danger"),
]
row_h = 60
row_gap = 16
row_y = R_Y + 66
for label, status, kind in sig_rows:
    accent_color = ACCENT if kind == "accent" else DANGER_TEXT
    box_h = row_h - row_gap
    parts.append(rect(RX + 28, row_y, RW - 56, box_h, rx=6, fill=SURFACE_2, stroke=BORDER_SOFT))
    parts.append(line(RX + 28, row_y, RX + 28, row_y + box_h, stroke=accent_color, width=3))
    parts.append(text(RX + 46, row_y + box_h / 2 + 5.5, label, size=16, color=TEXT_BODY, weight=600))
    p_w = 92
    p_x = RX + RW - 28 - p_w - 14
    p_y = row_y + box_h / 2 - 12
    parts.append(pill(p_x, p_y, status, kind=kind, w=p_w, h=24))
    row_y += row_h

body = "\n".join(parts)
GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)
svg_path = GRAPHICS_DIR / "05_signalscout_cover.svg"
png_path = GRAPHICS_DIR / "05_signalscout_cover.png"
write_svg(svg_path, body)
render_png(svg_path, png_path)
print(f"wrote {svg_path}")
print(f"wrote {png_path}")
