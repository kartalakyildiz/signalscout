"""One-off generator for the two SignalScout portfolio graphics (cover +
architecture diagram). Builds hand-authored SVG (using the dashboard's real
design tokens from .streamlit/config.toml and dashboard/app.py) and rasterizes
each to PNG via Playwright/Chromium at exactly 1440x1000.

This script lives under portfolio/ and does not touch application code.
Run with the project's venv:  .venv/Scripts/python.exe portfolio/build_graphics.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

GRAPHICS_DIR = Path(__file__).resolve().parent / "graphics"
FONT = "'Segoe UI', Arial, Helvetica, sans-serif"

# --- Design tokens (from .streamlit/config.toml + dashboard/app.py) --------
BG = "#0D1117"           # app canvas
SIDEBAR_BG = "#0A0D12"   # recessed surface
SURFACE = "#161B22"      # card / elevated surface
SURFACE_2 = "#11161D"    # secondary surface (between canvas and card)
BORDER = "#30363D"       # card borders
BORDER_SOFT = "#21262D"  # subtle dividers / group containers
TEXT_PRIMARY = "#F0F3F6"
TEXT_BODY = "#C9D1D9"
TEXT_MUTED = "#8B949E"
TEXT_FAINT = "#6E7681"
ACCENT = "#58A6FF"
ACCENT_TEXT = "#79B8FF"
ACCENT_BG = "rgba(88, 166, 255, 0.13)"
ACCENT_BORDER = "rgba(88, 166, 255, 0.35)"
ACCENT_GLOW = "rgba(88, 166, 255, 0.10)"
WARN_TEXT = "#E3B341"
WARN_BG = "rgba(210, 153, 34, 0.13)"
WARN_BORDER = "rgba(210, 153, 34, 0.35)"
DANGER_TEXT = "#FF7B72"
DANGER_BG = "rgba(248, 81, 73, 0.13)"
DANGER_BORDER = "rgba(248, 81, 73, 0.35)"

W, H = 1440, 1000


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def rect(x, y, w, h, rx=8, fill=SURFACE, stroke=BORDER, stroke_width=1, opacity=1) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
    )


def line(x1, y1, x2, y2, stroke=BORDER, width=1.5, dash=None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def polyline(points, stroke=BORDER, width=1.5, dash=None) -> str:
    pts = " ".join(f"{x},{y}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'


def arrowhead(x, y, direction="down", size=5, fill=BORDER) -> str:
    """Small filled triangle pointing in `direction`, tip at (x, y)."""
    if direction == "down":
        pts = f"{x - size},{y - size * 1.6} {x + size},{y - size * 1.6} {x},{y}"
    elif direction == "up":
        pts = f"{x - size},{y + size * 1.6} {x + size},{y + size * 1.6} {x},{y}"
    elif direction == "right":
        pts = f"{x - size * 1.6},{y - size} {x - size * 1.6},{y + size} {x},{y}"
    else:  # left
        pts = f"{x + size * 1.6},{y - size} {x + size * 1.6},{y + size} {x},{y}"
    return f'<polygon points="{pts}" fill="{fill}"/>'


def text(x, y, content, size=14, color=TEXT_BODY, weight=400, anchor="start",
          letter_spacing=None, family=FONT, opacity=1) -> str:
    ls = f' letter-spacing="{letter_spacing}"' if letter_spacing else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{ls} opacity="{opacity}">'
        f"{esc(content)}</text>"
    )


def badge(x, y, label, w=None) -> str:
    label = label.upper()
    pad = 14
    approx_w = w or (len(label) * 7.6 + pad * 2)
    parts = [rect(x, y, approx_w, 30, rx=5, fill=ACCENT_BG, stroke=ACCENT_BORDER, stroke_width=1)]
    parts.append(text(x + approx_w / 2, y + 20, label, size=12, color=ACCENT_TEXT, weight=700,
                       anchor="middle", letter_spacing="0.06em"))
    return "\n".join(parts), approx_w


def pill(x, y, label, kind="accent", w=64, h=22) -> str:
    styles = {
        "accent": (ACCENT_BG, ACCENT_TEXT, ACCENT_BORDER),
        "warn": (WARN_BG, WARN_TEXT, WARN_BORDER),
        "danger": (DANGER_BG, DANGER_TEXT, DANGER_BORDER),
        "neutral": (BORDER_SOFT, TEXT_MUTED, BORDER),
    }
    fill, color, stroke = styles[kind]
    parts = [rect(x, y, w, h, rx=4, fill=fill, stroke=stroke, stroke_width=1)]
    parts.append(text(x + w / 2, y + h / 2 + 4, label, size=10.5, color=color, weight=700,
                       anchor="middle", letter_spacing="0.03em"))
    return "\n".join(parts)


def svg_open() -> str:
    return (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">'
    )


SVG_CLOSE = "</svg>"


def write_svg(path: Path, body: str) -> None:
    doc = f'{svg_open()}\n{body}\n{SVG_CLOSE}\n'
    path.write_text(doc, encoding="utf-8")


def render_png(svg_path: Path, png_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(svg_path.resolve().as_uri())
        page.wait_for_timeout(150)
        page.screenshot(path=str(png_path))
        browser.close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"build_graphics.py invoked with mode={mode} (see cover.py / architecture.py)")
