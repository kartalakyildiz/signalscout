"""Builds portfolio/graphics/06_signalscout_architecture.svg + .png"""
from build_graphics import (
    ACCENT, ACCENT_BG, ACCENT_BORDER, ACCENT_TEXT,
    BG, BORDER, BORDER_SOFT, GRAPHICS_DIR, H, SURFACE, SURFACE_2,
    TEXT_BODY, TEXT_FAINT, TEXT_MUTED, TEXT_PRIMARY, W,
    arrowhead, line, rect, render_png, text, write_svg,
)

parts: list[str] = []

# --- Background ----------------------------------------------------------
parts.append(rect(0, 0, W, H, rx=0, fill=BG, stroke="none"))

# --- Header ----------------------------------------------------------------
parts.append(text(W / 2, 92, "SignalScout Architecture", size=38, color=TEXT_PRIMARY,
                   weight=750, anchor="middle"))
parts.append(text(W / 2, 126, "Evidence-first research automation from public web data to reviewable output",
                   size=16, color=TEXT_MUTED, weight=400, anchor="middle"))


def box(x, y, w, h, title, subtitle=None, fill=SURFACE, stroke=BORDER, title_color=TEXT_PRIMARY):
    out = [rect(x, y, w, h, rx=8, fill=fill, stroke=stroke)]
    ty = y + (h / 2 - 6 if subtitle else h / 2 + 5)
    out.append(text(x + w / 2, ty, title, size=14, color=title_color, weight=650, anchor="middle"))
    if subtitle:
        out.append(text(x + w / 2, ty + 20, subtitle, size=11, color=TEXT_MUTED, weight=400, anchor="middle"))
    return "\n".join(out)


def group_container(x, y, w, h, label, label_y=None):
    # label_y defaults to just above the container, but can be pinned to a
    # shared header row even when shorter columns are vertically re-centered.
    out = [rect(x, y, w, h, rx=12, fill=SURFACE_2, stroke=BORDER_SOFT, stroke_width=1)]
    ly = label_y if label_y is not None else y - 14
    out.append(text(x + w / 2, ly, label, size=12.5, color=ACCENT_TEXT, weight=700,
                     anchor="middle", letter_spacing="0.09em"))
    return "\n".join(out)


def varrow(cx, y1, y2):
    out = [line(cx, y1 + 2, cx, y2 - 7, stroke=BORDER, width=1.5)]
    out.append(arrowhead(cx, y2 - 2, "down", size=4.5, fill=TEXT_FAINT))
    return "\n".join(out)


def harrow(x1, x2, y1, y2=None):
    """Straight horizontal arrow when y1 == y2, otherwise a clean elbow
    connector (jogs at the horizontal midpoint) between differing heights."""
    if y2 is None or y1 == y2:
        out = [line(x1 + 2, y1, x2 - 8, y1, stroke=BORDER, width=1.5)]
        out.append(arrowhead(x2 - 2, y1, "right", size=5, fill=TEXT_FAINT))
        return "\n".join(out)
    mid_x = x1 + (x2 - x1) / 2
    out = [f'<polyline points="{x1 + 2},{y1} {mid_x},{y1} {mid_x},{y2} {x2 - 8},{y2}" '
           f'fill="none" stroke="{BORDER}" stroke-width="1.5"/>']
    out.append(arrowhead(x2 - 2, y2, "right", size=5, fill=TEXT_FAINT))
    return "\n".join(out)


# --- Column geometry --------------------------------------------------------
GROUP_TOP = 232
TALL_GROUP_H = 456
SHORT_GROUP_H = 236
# Short columns (Input/Storage/Output) are vertically centered within the
# same band the tall columns (Research/AI+Trust) occupy, instead of being
# top-aligned and leaving a large empty gap beneath them.
SHORT_TOP = GROUP_TOP + (TALL_GROUP_H - SHORT_GROUP_H) / 2
COL_GAP = 26
cols = {
    "input":   {"x": 73,  "w": 220},
    "research":{"x": 73 + 220 + COL_GAP, "w": 300},
    "trust":   {"x": 73 + 220 + COL_GAP + 300 + COL_GAP, "w": 230},
    "storage": {"x": 73 + 220 + COL_GAP + 300 + COL_GAP + 230 + COL_GAP, "w": 210},
    "output":  {"x": 73 + 220 + COL_GAP + 300 + COL_GAP + 230 + COL_GAP + 210 + COL_GAP, "w": 230},
}
PAD = 18

# --- INPUT column ------------------------------------------------------------
c = cols["input"]
cx0, cw = c["x"], c["w"]
group_h = SHORT_GROUP_H
parts.append(group_container(cx0, SHORT_TOP, cw, group_h, "INPUT", label_y=GROUP_TOP - 14))
bx, bw = cx0 + PAD, cw - PAD * 2
b1_y = SHORT_TOP + 26
b1_h = 60
parts.append(box(bx, b1_y, bw, b1_h, "CSV Companies", "Company • Website • Industry"))
b2_y = b1_y + b1_h + 30
b2_h = 60
parts.append(varrow(cx0 + cw / 2, b1_y + b1_h, b2_y))
parts.append(box(bx, b2_y, bw, b2_h, "Validation & Dedup", "Normalize URLs, remove duplicates"))
input_bottom = b2_y + b2_h
input_mid_y = b1_y + b1_h / 2

# --- RESEARCH column -----------------------------------------------------
c = cols["research"]
cx0, cw = c["x"], c["w"]
group_h = 456
parts.append(group_container(cx0, GROUP_TOP, cw, group_h, "RESEARCH"))
bx, bw = cx0 + PAD, cw - PAD * 2

r1_y = GROUP_TOP + 26
r1_h = 56
parts.append(box(bx, r1_y, bw, r1_h, "Page Discovery", "About • Product • Careers • News"))

r2_y = r1_y + r1_h + 26
r2_h = 56
parts.append(varrow(cx0 + cw / 2, r1_y + r1_h, r2_y))
parts.append(box(bx, r2_y, bw, r2_h, "HTTPX Scraper", "Primary fetch (fast, static HTML)"))

# Fork: "sufficient content" -> straight to Cleaning ; "thin / JS content" -> Playwright -> Cleaning
fork_top = r2_y + r2_h
center_x = cx0 + cw / 2
left_x = bx + bw * 0.22
right_x = bx + bw * 0.68

pw_y = fork_top + 46
pw_h = 42
pw_w = 118
pw_x = right_x - pw_w / 2
parts.append(box(pw_x, pw_y, pw_w, pw_h, "Playwright", "JS fallback", fill=SURFACE_2))

clean_y = pw_y + pw_h + 46
clean_h = 56
clean_top = clean_y

# left path: straight down, label "sufficient content"
parts.append(line(left_x, fork_top + 2, left_x, clean_top - 7, stroke=BORDER, width=1.5))
parts.append(arrowhead(left_x, clean_top - 2, "down", size=4.5, fill=TEXT_FAINT))
parts.append(text(left_x, fork_top + 20, "sufficient", size=10, color=TEXT_MUTED, weight=600, anchor="middle"))
parts.append(text(left_x, fork_top + 32, "content", size=10, color=TEXT_MUTED, weight=600, anchor="middle"))

# right path: down, over, into Playwright, then down+left into Cleaning
parts.append(line(right_x, fork_top + 2, right_x, pw_y - 5, stroke=BORDER, width=1.5))
parts.append(arrowhead(right_x, pw_y - 2, "down", size=4.5, fill=TEXT_FAINT))
parts.append(text(right_x, fork_top + 20, "thin / JS", size=10, color=TEXT_MUTED, weight=600, anchor="middle"))
parts.append(text(right_x, fork_top + 32, "content", size=10, color=TEXT_MUTED, weight=600, anchor="middle"))

parts.append(line(right_x, pw_y + pw_h, right_x, clean_top - 7, stroke=BORDER, width=1.5))
parts.append(arrowhead(right_x, clean_top - 2, "down", size=4.5, fill=TEXT_FAINT))

parts.append(box(bx, clean_y, bw, clean_h, "HTML Cleaning", "Strip noise, extract text"))
research_bottom = clean_y + clean_h
research_mid_y = r1_y + r1_h / 2

# --- AI + TRUST column -----------------------------------------------------
c = cols["trust"]
cx0, cw = c["x"], c["w"]
group_h = 456
parts.append(group_container(cx0, GROUP_TOP, cw, group_h, "AI + TRUST"))
bx, bw = cx0 + PAD, cw - PAD * 2

t1_y = GROUP_TOP + 26
t1_h = 60
parts.append(box(bx, t1_y, bw, t1_h, "Structured AI Extraction", "Typed signal extraction"))

t2_y = t1_y + t1_h + 30
t2_h = 60
parts.append(varrow(cx0 + cw / 2, t1_y + t1_h, t2_y))
parts.append(box(bx, t2_y, bw, t2_h, "Evidence Validation", "Source ID + quote verification",
                  fill=ACCENT_BG, stroke=ACCENT_BORDER, title_color=ACCENT_TEXT))

t3_y = t2_y + t2_h + 30
t3_h = 60
parts.append(varrow(cx0 + cw / 2, t2_y + t2_h, t3_y))
parts.append(box(bx, t3_y, bw, t3_h, "Deterministic Qualification", "Deterministic Python rules"))
trust_bottom = t3_y + t3_h
trust_mid_y = t1_y + t1_h / 2

# --- STORAGE column ----------------------------------------------------------
c = cols["storage"]
cx0, cw = c["x"], c["w"]
group_h = SHORT_GROUP_H
parts.append(group_container(cx0, SHORT_TOP, cw, group_h, "STORAGE", label_y=GROUP_TOP - 14))
bx, bw = cx0 + PAD, cw - PAD * 2

s1_y = SHORT_TOP + 26
s1_h = 60
parts.append(box(bx, s1_y, bw, s1_h, "SQLAlchemy", "ORM data-access layer"))
s2_y = s1_y + s1_h + 30
s2_h = 60
parts.append(varrow(cx0 + cw / 2, s1_y + s1_h, s2_y))
parts.append(box(bx, s2_y, bw, s2_h, "SQLite", "Companies • Scans • Pages • Evidence"))
storage_bottom = s2_y + s2_h
storage_mid_y = s1_y + s1_h / 2

# --- OUTPUT column ------------------------------------------------------------
c = cols["output"]
cx0, cw = c["x"], c["w"]
group_h = SHORT_GROUP_H
parts.append(group_container(cx0, SHORT_TOP, cw, group_h, "OUTPUT", label_y=GROUP_TOP - 14))
bx, bw = cx0 + PAD, cw - PAD * 2

o1_y = SHORT_TOP + 26
o1_h = 60
parts.append(box(bx, o1_y, bw, o1_h, "Streamlit Dashboard", "Review, filters, manual review"))
o2_y = o1_y + o1_h + 30
o2_h = 60
parts.append(box(bx, o2_y, bw, o2_h, "CSV / Excel Export", "Company summary + evidence log"))
output_bottom = o2_y + o2_h

# --- Inter-column connectors --------------------------------------------
in_x1 = cols["input"]["x"] + cols["input"]["w"]
in_x2 = cols["research"]["x"]
parts.append(harrow(in_x1, in_x2, input_mid_y, research_mid_y))

res_x1 = cols["research"]["x"] + cols["research"]["w"]
res_x2 = cols["trust"]["x"]
parts.append(harrow(res_x1, res_x2, research_mid_y, trust_mid_y))

trust_x1 = cols["trust"]["x"] + cols["trust"]["w"]
trust_x2 = cols["storage"]["x"]
parts.append(harrow(trust_x1, trust_x2, trust_mid_y, storage_mid_y))

# storage -> output: two arrows (dashboard + export), same origin area, fanning out
stor_x1 = cols["storage"]["x"] + cols["storage"]["w"]
out_x2 = cols["output"]["x"]
storage_mid = (s1_y + s1_h / 2, s2_y + s2_h / 2)
out_targets = (o1_y + o1_h / 2, o2_y + o2_h / 2)
origin_y = storage_mid_y
for target_y in out_targets:
    mid_x = stor_x1 + (out_x2 - stor_x1) / 2
    parts.append(f'<polyline points="{stor_x1 + 2},{origin_y} {mid_x},{origin_y} {mid_x},{target_y} {out_x2 - 8},{target_y}" '
                 f'fill="none" stroke="{BORDER}" stroke-width="1.5"/>')
    parts.append(arrowhead(out_x2 - 2, target_y, "right", size=5, fill=TEXT_FAINT))

# --- Footer emphasis note --------------------------------------------------
FOOT_Y = 800
foot_text = "Unsupported evidence is rejected before it can affect qualification."
foot_w = 620
foot_x = (W - foot_w) / 2
parts.append(rect(foot_x, FOOT_Y - 26, foot_w, 40, rx=8, fill=ACCENT_BG, stroke=ACCENT_BORDER))
parts.append(text(W / 2, FOOT_Y, foot_text, size=14.5, color=ACCENT_TEXT, weight=650, anchor="middle"))

body = "\n".join(parts)
GRAPHICS_DIR.mkdir(parents=True, exist_ok=True)
svg_path = GRAPHICS_DIR / "06_signalscout_architecture.svg"
png_path = GRAPHICS_DIR / "06_signalscout_architecture.png"
write_svg(svg_path, body)
render_png(svg_path, png_path)
print(f"wrote {svg_path}")
print(f"wrote {png_path}")
