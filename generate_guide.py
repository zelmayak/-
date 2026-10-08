# -*- coding: utf-8 -*-
"""
PDF guide generator: "Пассивный доход с нуля: 5 стратегий, которые работают в 2026".

Produces passive_income_guide_2026.pdf (A4 portrait).
All illustrations are drawn programmatically with reportlab + matplotlib.
"""

import io
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

# ---------- fonts ----------
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FREE_DIR = "/usr/share/fonts/truetype/freefont"
pdfmetrics.registerFont(TTFont("Body", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("BodyBold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
# DejaVu Sans ships no italic variant; FreeSans has oblique + Cyrillic + ₽.
pdfmetrics.registerFont(TTFont("BodyItalic", os.path.join(FREE_DIR, "FreeSansOblique.ttf")))
pdfmetrics.registerFont(TTFont("BodyBoldItalic", os.path.join(FREE_DIR, "FreeSansBoldOblique.ttf")))

# ---------- palette ----------
C_BG = HexColor("#FFFFFF")
C_ACCENT_BG = HexColor("#F0F4FF")
C_TEXT = HexColor("#1A1A2E")
C_TEXT_MUTED = HexColor("#5B5B7A")
C_PRIMARY = HexColor("#2563EB")
C_PRIMARY_DARK = HexColor("#1E3A8A")
C_GREEN = HexColor("#10B981")
C_RED = HexColor("#EF4444")
C_AMBER = HexColor("#F59E0B")
C_CHART_BG = HexColor("#F8FAFC")
C_PURPLE = HexColor("#7C3AED")
C_LINE = HexColor("#E2E8F0")
C_WHITE = HexColor("#FFFFFF")

# ---------- geometry ----------
PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
MARGIN_TOP = 25 * mm
MARGIN_BOTTOM = 25 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X
CONTENT_TOP = PAGE_H - MARGIN_TOP
CONTENT_BOTTOM = MARGIN_BOTTOM

# matplotlib palette tuned to brand
MPL_PRIMARY = "#2563EB"
MPL_GREEN = "#10B981"
MPL_RED = "#EF4444"
MPL_PURPLE = "#7C3AED"
MPL_AMBER = "#F59E0B"
MPL_TEXT = "#1A1A2E"
MPL_BG = "#F8FAFC"
MPL_GRID = "#E2E8F0"


# ====================================================================
# low-level drawing helpers
# ====================================================================

def set_fill_hex(c, color):
    c.setFillColor(color)


def round_rect(c, x, y, w, h, r, fill_color=None, stroke_color=None, stroke_width=0.6, shadow=False):
    if shadow:
        c.setFillColorRGB(0, 0, 0, alpha=0.06)
        c.setStrokeColorRGB(0, 0, 0, alpha=0)
        c.roundRect(x + 1.2, y - 1.5, w, h, r, fill=1, stroke=0)
    if fill_color is not None:
        c.setFillColor(fill_color)
    if stroke_color is not None:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    c.roundRect(x, y, w, h, r,
                fill=1 if fill_color else 0,
                stroke=1 if stroke_color else 0)


def wrap_text(text, font_name, font_size, max_width):
    """Simple greedy word-wrap returning a list of lines."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip() if cur else w
        if pdfmetrics.stringWidth(trial, font_name, font_size) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_paragraph(c, text, x, y, max_width,
                   font_name="Body", font_size=11, leading=16, color=C_TEXT,
                   align="left"):
    """Draw a wrapped paragraph; returns the y-coordinate just below the last line."""
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    lines = wrap_text(text, font_name, font_size, max_width)
    for ln in lines:
        if align == "center":
            tw = pdfmetrics.stringWidth(ln, font_name, font_size)
            c.drawString(x + (max_width - tw) / 2.0, y, ln)
        else:
            c.drawString(x, y, ln)
        y -= leading
    return y


def draw_heading(c, text, x, y, size=22, color=None, font="BodyBold"):
    c.setFont(font, size)
    c.setFillColor(color or C_TEXT)
    c.drawString(x, y, text)
    return y - size * 1.2


def draw_chapter_banner(c, number, title, subtitle=None):
    """Decorative header strip for chapter openers."""
    top = CONTENT_TOP
    strip_h = 55 * mm
    # background
    c.setFillColor(C_PRIMARY_DARK)
    c.rect(0, PAGE_H - strip_h, PAGE_W, strip_h, fill=1, stroke=0)
    # decorative circles
    c.setFillColor(C_PRIMARY)
    c.setStrokeColor(C_PRIMARY)
    for i, (cx, cy, r) in enumerate([
        (PAGE_W - 20 * mm, PAGE_H - 10 * mm, 25 * mm),
        (PAGE_W - 50 * mm, PAGE_H - 50 * mm, 15 * mm),
        (15 * mm, PAGE_H - 50 * mm, 10 * mm),
    ]):
        c.setFillColor(Color(0.15, 0.4, 0.95, alpha=0.4 - i * 0.1))
        c.circle(cx, cy, r, fill=1, stroke=0)

    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 11)
    c.drawString(MARGIN_X, PAGE_H - 22 * mm, f"ГЛАВА {number}")

    c.setFont("BodyBold", 26)
    c.drawString(MARGIN_X, PAGE_H - 38 * mm, title)

    if subtitle:
        c.setFont("Body", 11)
        c.setFillColor(Color(1, 1, 1, alpha=0.75))
        c.drawString(MARGIN_X, PAGE_H - 48 * mm, subtitle)

    return PAGE_H - strip_h - 10 * mm


def draw_page_number(c, number, total=None):
    c.setFont("Body", 9)
    c.setFillColor(C_TEXT_MUTED)
    label = f"{number}" if total is None else f"{number} / {total}"
    c.drawRightString(PAGE_W - MARGIN_X, 12 * mm, label)
    # footer brand
    c.setFillColor(C_PRIMARY)
    c.drawString(MARGIN_X, 12 * mm, "Пассивный доход с нуля · 2026")


def draw_footer_rule(c):
    c.setStrokeColor(C_LINE)
    c.setLineWidth(0.4)
    c.line(MARGIN_X, 16 * mm, PAGE_W - MARGIN_X, 16 * mm)


# ====================================================================
# icon primitives (programmatic — no emoji glyphs)
# ====================================================================

def icon_check(c, cx, cy, r=5, fg=C_WHITE, bg=C_GREEN):
    c.setFillColor(bg)
    c.setStrokeColor(bg)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setStrokeColor(fg)
    c.setLineWidth(1.6)
    p = c.beginPath()
    p.moveTo(cx - r * 0.5, cy)
    p.lineTo(cx - r * 0.1, cy - r * 0.4)
    p.lineTo(cx + r * 0.5, cy + r * 0.35)
    c.drawPath(p, stroke=1, fill=0)


def icon_cross(c, cx, cy, r=5, fg=C_WHITE, bg=C_RED):
    c.setFillColor(bg)
    c.setStrokeColor(bg)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setStrokeColor(fg)
    c.setLineWidth(1.6)
    c.line(cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45)
    c.line(cx - r * 0.45, cy + r * 0.45, cx + r * 0.45, cy - r * 0.45)


def icon_warning(c, cx, cy, r=6, bg=C_AMBER, fg=C_WHITE):
    # triangle with exclamation
    c.setFillColor(bg)
    c.setStrokeColor(bg)
    p = c.beginPath()
    p.moveTo(cx, cy + r)
    p.lineTo(cx - r * 0.95, cy - r * 0.75)
    p.lineTo(cx + r * 0.95, cy - r * 0.75)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(fg)
    c.setFont("BodyBold", r * 1.1)
    c.drawCentredString(cx, cy - r * 0.4, "!")


def icon_arrow_up(c, cx, cy, r=6, bg=C_PRIMARY, fg=C_WHITE):
    c.setFillColor(bg)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setStrokeColor(fg)
    c.setLineWidth(1.6)
    c.line(cx - r * 0.4, cy - r * 0.1, cx, cy + r * 0.45)
    c.line(cx, cy + r * 0.45, cx + r * 0.4, cy - r * 0.1)
    c.line(cx, cy + r * 0.45, cx, cy - r * 0.5)


def icon_star(c, cx, cy, r, fg=C_AMBER, filled=True):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    c.setFillColor(fg if filled else C_LINE)
    c.setStrokeColor(fg if filled else C_LINE)
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def badge(c, x, y, w, h, text, bg, fg=C_WHITE, font_size=9):
    round_rect(c, x, y, w, h, h / 2, fill_color=bg, stroke_color=None)
    c.setFillColor(fg)
    c.setFont("BodyBold", font_size)
    tw = pdfmetrics.stringWidth(text, "BodyBold", font_size)
    c.drawString(x + (w - tw) / 2, y + h / 2 - font_size * 0.35, text)


def draw_stars(c, x, y, n, total=5, size=4.5):
    for i in range(total):
        icon_star(c, x + i * (size * 2.4), y, size, filled=(i < n))


def draw_risk_bar(c, x, y, w, h, level):
    """level: 1..5. Horizontal green→red gradient with marker."""
    # background rounded container
    round_rect(c, x, y, w, h, h / 2, fill_color=C_CHART_BG, stroke_color=None)
    # gradient segments (approximation)
    seg_colors = [HexColor("#10B981"), HexColor("#84CC16"),
                  HexColor("#F59E0B"), HexColor("#F97316"), HexColor("#EF4444")]
    seg_w = (w - 4) / 5
    for i, col in enumerate(seg_colors):
        c.setFillColor(col)
        c.setStrokeColor(col)
        c.rect(x + 2 + i * seg_w, y + 2, seg_w - 1, h - 4, fill=1, stroke=0)
    # overlay rounded mask via re-draw of ends (keeps feel of pill)
    # marker
    mx = x + 2 + (level - 0.5) * seg_w
    c.setFillColor(C_WHITE)
    c.setStrokeColor(C_TEXT)
    c.setLineWidth(1.2)
    c.circle(mx, y + h / 2, h * 0.6, fill=1, stroke=1)


# ====================================================================
# matplotlib chart helpers → PNG → ImageReader
# ====================================================================

def mpl_style(ax, fig):
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MPL_GRID)
    ax.tick_params(colors=MPL_TEXT, labelsize=9)
    ax.grid(True, linestyle="--", color=MPL_GRID, alpha=0.9, linewidth=0.6)
    ax.set_axisbelow(True)


def chart_compound_interest():
    years = np.arange(0, 21)
    cap = 10000 * (1.15 ** years)
    fig, ax = plt.subplots(figsize=(7.4, 3.8), dpi=180)
    mpl_style(ax, fig)
    ax.plot(years, cap, color=MPL_PRIMARY, linewidth=2.4)
    ax.fill_between(years, 0, cap, color=MPL_PRIMARY, alpha=0.15)
    # markers
    for yr in (1, 5, 10, 15, 20):
        val = 10000 * (1.15 ** yr)
        ax.scatter([yr], [val], s=46, color=MPL_PRIMARY, zorder=5, edgecolors="white", linewidths=1.6)
        ax.annotate(f"{int(val):,} ₽".replace(",", " "),
                    (yr, val), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, color=MPL_TEXT, fontweight="bold")
    ax.set_xlabel("Годы", fontsize=10, color=MPL_TEXT)
    ax.set_ylabel("Капитал, ₽", fontsize=10, color=MPL_TEXT)
    ax.set_title("Рост 10 000 ₽ под 15 % годовых", fontsize=12, color=MPL_TEXT, fontweight="bold", pad=12)
    ax.set_xlim(0, 20.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", " ")))
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=MPL_BG)
    plt.close(fig)
    buf.seek(0)
    return ImageReader(buf)


def chart_strategy_yield(name, low, high, color):
    years = np.arange(0, 11)
    low_curve = 10000 * ((1 + low / 100) ** years)
    high_curve = 10000 * ((1 + high / 100) ** years)
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=180)
    mpl_style(ax, fig)
    ax.fill_between(years, low_curve, high_curve, color=color, alpha=0.18, label="Диапазон")
    ax.plot(years, high_curve, color=color, linewidth=2.2, label=f"{high} % годовых")
    ax.plot(years, low_curve, color=color, linewidth=1.4, linestyle="--", alpha=0.8,
            label=f"{low} % годовых")
    ax.set_xlabel("Годы", fontsize=10, color=MPL_TEXT)
    ax.set_ylabel("Капитал от 10 000 ₽", fontsize=10, color=MPL_TEXT)
    ax.set_title(f"Прогноз доходности · {name}", fontsize=11, color=MPL_TEXT, fontweight="bold", pad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", " ")))
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=MPL_BG)
    plt.close(fig)
    buf.seek(0)
    return ImageReader(buf)


def chart_pie(title, parts):
    labels = [p[0] for p in parts]
    values = [p[1] for p in parts]
    colors = [p[2] for p in parts]
    fig, ax = plt.subplots(figsize=(5.8, 4.6), dpi=180)
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)
    wedges, texts, autotexts = ax.pie(
        values, labels=None, colors=colors,
        autopct=lambda p: f"{p:.0f} %",
        startangle=90, counterclock=False,
        wedgeprops=dict(width=0.42, edgecolor=MPL_BG, linewidth=3),
        pctdistance=0.78,
        textprops=dict(color="white", fontsize=10, fontweight="bold"),
    )
    ax.set_title(title, fontsize=12, color=MPL_TEXT, fontweight="bold", pad=14)
    # legend
    ax.legend(wedges, [f"{l} · {v} %" for l, v in zip(labels, values)],
              loc="center left", bbox_to_anchor=(1.0, 0.5),
              fontsize=9, frameon=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=MPL_BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return ImageReader(buf)


def chart_inflation():
    years = np.arange(0, 11)
    nominal = np.full(len(years), 100000.0)
    real = 100000 * (0.9 ** years)
    fig, ax = plt.subplots(figsize=(7.0, 3.4), dpi=180)
    mpl_style(ax, fig)
    ax.plot(years, nominal, color=MPL_TEXT, linewidth=1.8, linestyle="--",
            label="На счёте (номинально)")
    ax.plot(years, real, color=MPL_RED, linewidth=2.4, label="Покупательная способность")
    ax.fill_between(years, real, nominal, color=MPL_RED, alpha=0.12)
    ax.set_xlabel("Годы", fontsize=10)
    ax.set_ylabel("₽", fontsize=10)
    ax.set_title("Что инфляция делает со 100 000 ₽ за 10 лет", fontsize=12, fontweight="bold", pad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}".replace(",", " ")))
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=MPL_BG)
    plt.close(fig)
    buf.seek(0)
    return ImageReader(buf)


# ====================================================================
# complex block renderers
# ====================================================================

def callout(c, x, y, w, text, title=None, kind="info"):
    """Callout block (left stripe). Returns height used."""
    palette = {
        "info": (C_ACCENT_BG, C_PRIMARY, "ВАЖНО"),
        "do":   (HexColor("#ECFDF5"), C_GREEN, "СДЕЛАЙ СЕЙЧАС"),
        "warn": (HexColor("#FEF2F2"), C_RED, "ОСТОРОЖНО"),
        "tip":  (HexColor("#FFFBEB"), C_AMBER, "СОВЕТ"),
    }
    bg, stripe, default_title = palette[kind]
    inner_x = x + 14
    inner_w = w - 20
    lines_title = []
    if title is None:
        title = default_title
    lines_body = wrap_text(text, "Body", 10.5, inner_w)
    header_h = 16
    body_h = len(lines_body) * 15
    pad_top = 10
    pad_bot = 12
    total_h = pad_top + header_h + body_h + pad_bot
    # background
    round_rect(c, x, y - total_h, w, total_h, 8, fill_color=bg, stroke_color=None)
    # stripe
    c.setFillColor(stripe)
    c.rect(x, y - total_h + 6, 4, total_h - 12, fill=1, stroke=0)
    # title
    c.setFillColor(stripe)
    c.setFont("BodyBold", 9)
    c.drawString(inner_x, y - pad_top - 8, title)
    # body
    c.setFillColor(C_TEXT)
    c.setFont("Body", 10.5)
    ty = y - pad_top - header_h - 6
    for ln in lines_body:
        c.drawString(inner_x, ty, ln)
        ty -= 15
    return total_h


def pros_cons_card(c, x, y, w, pros, cons):
    """Two-column pros/cons card. Returns height used."""
    col_w = (w - 12) / 2
    pad = 12
    line_h = 15
    inner_col_w = col_w - 20
    pros_lines = sum(len(wrap_text(it, "Body", 10, inner_col_w)) for it in pros)
    cons_lines = sum(len(wrap_text(it, "Body", 10, inner_col_w)) for it in cons)
    rows_lines = max(pros_lines, cons_lines)
    header_h = 24
    body_h = rows_lines * line_h + 8
    total_h = pad + header_h + body_h + pad

    round_rect(c, x, y - total_h, w, total_h, 10,
               fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
    # headers
    c.setFillColor(C_GREEN)
    c.setFont("BodyBold", 10)
    icon_check(c, x + pad + 7, y - pad - 10, r=5)
    c.drawString(x + pad + 20, y - pad - 13, "ПЛЮСЫ")

    c.setFillColor(C_RED)
    icon_cross(c, x + pad + col_w + 12 + 7, y - pad - 10, r=5)
    c.drawString(x + pad + col_w + 12 + 20, y - pad - 13, "МИНУСЫ")

    # separator
    c.setStrokeColor(C_LINE)
    c.setLineWidth(0.5)
    c.line(x + col_w + pad + 6, y - pad - 20,
           x + col_w + pad + 6, y - total_h + pad + 4)

    # rows
    ty = y - pad - header_h - 2
    c.setFillColor(C_TEXT)
    c.setFont("Body", 10)
    for item in pros:
        lines = wrap_text(item, "Body", 10, col_w - 20)
        c.setFillColor(C_GREEN)
        c.circle(x + pad + 4, ty - 3, 1.6, fill=1, stroke=0)
        c.setFillColor(C_TEXT)
        c.drawString(x + pad + 11, ty - 5, lines[0])
        for ln in lines[1:]:
            ty -= line_h
            c.drawString(x + pad + 11, ty - 5, ln)
        ty -= line_h
    ty2 = y - pad - header_h - 2
    for item in cons:
        lines = wrap_text(item, "Body", 10, col_w - 20)
        c.setFillColor(C_RED)
        c.circle(x + pad + col_w + 12 + 4, ty2 - 3, 1.6, fill=1, stroke=0)
        c.setFillColor(C_TEXT)
        c.drawString(x + pad + col_w + 12 + 11, ty2 - 5, lines[0])
        for ln in lines[1:]:
            ty2 -= line_h
            c.drawString(x + pad + col_w + 12 + 11, ty2 - 5, ln)
        ty2 -= line_h
    return total_h


def spec_card(c, x, y, w, rows):
    """Characteristics card: list of (label, value, kind) rows.
    kind: 'text' | 'risk:N' | 'stars:N' | 'badge:color'.
    Returns height used."""
    pad = 14
    row_h = 28
    total_h = pad * 2 + row_h * len(rows)
    round_rect(c, x, y - total_h, w, total_h, 10,
               fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
    # title bar
    c.setFillColor(C_PRIMARY)
    c.setFont("BodyBold", 9)
    c.drawString(x + pad, y - pad - 2, "ХАРАКТЕРИСТИКИ")

    for i, (label, value, kind) in enumerate(rows):
        ry = y - pad - 18 - i * row_h
        if i % 2 == 1:
            c.setFillColor(C_CHART_BG)
            c.rect(x + 4, ry - row_h + 6, w - 8, row_h - 2, fill=1, stroke=0)
        c.setFillColor(C_TEXT_MUTED)
        c.setFont("Body", 10)
        c.drawString(x + pad, ry - 6, label)
        # right-aligned value visuals
        rx = x + w - pad
        if kind.startswith("risk:"):
            lvl = int(kind.split(":")[1])
            bw = 80
            draw_risk_bar(c, rx - bw, ry - 14, bw, 10, lvl)
            c.setFillColor(C_TEXT)
            c.setFont("BodyBold", 10)
            c.drawRightString(rx - bw - 6, ry - 6, value)
        elif kind.startswith("stars:"):
            n = int(kind.split(":")[1])
            sw = 5 * 2.4 * 4.5
            draw_stars(c, rx - sw, ry - 7, n, size=4.2)
        else:
            c.setFillColor(C_TEXT)
            c.setFont("BodyBold", 10.5)
            c.drawRightString(rx, ry - 6, value)
    return total_h


def numbered_steps(c, x, y, w, steps, title=None):
    """Vertical numbered-step list. Returns height used."""
    pad = 14
    row_pad = 10
    rows = []
    for i, s in enumerate(steps):
        lines = wrap_text(s, "Body", 10.5, w - 60)
        rows.append(lines)
    header_h = 22 if title else 6
    total_h = pad + header_h + sum((len(r) * 15 + row_pad) for r in rows) + pad - row_pad

    round_rect(c, x, y - total_h, w, total_h, 10,
               fill_color=C_ACCENT_BG, stroke_color=None)
    ty = y - pad
    if title:
        c.setFillColor(C_PRIMARY)
        c.setFont("BodyBold", 11)
        c.drawString(x + pad, ty - 10, title)
        ty -= header_h
    for i, lines in enumerate(rows):
        n = str(i + 1)
        bx = x + pad
        by = ty - 14
        c.setFillColor(C_PRIMARY)
        c.circle(bx + 8, by + 5, 10, fill=1, stroke=0)
        c.setFillColor(C_WHITE)
        c.setFont("BodyBold", 10)
        tw = pdfmetrics.stringWidth(n, "BodyBold", 10)
        c.drawString(bx + 8 - tw / 2, by + 2, n)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10.5)
        tx = bx + 26
        for j, ln in enumerate(lines):
            c.drawString(tx, by + 2 - j * 15, ln)
        ty -= len(lines) * 15 + row_pad
    return total_h


def checklist_block(c, x, y, w, items, title=None):
    pad = 14
    line_h = 18
    header_h = 22 if title else 4
    total_h = pad + header_h + len(items) * line_h + pad
    round_rect(c, x, y - total_h, w, total_h, 10,
               fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
    ty = y - pad
    if title:
        c.setFillColor(C_PRIMARY)
        c.setFont("BodyBold", 11)
        c.drawString(x + pad, ty - 10, title)
        ty -= header_h
    for item in items:
        bx = x + pad
        by = ty - 10
        c.setStrokeColor(C_PRIMARY)
        c.setFillColor(C_WHITE)
        c.setLineWidth(1.2)
        round_rect(c, bx, by - 2, 10, 10, 2, fill_color=C_WHITE, stroke_color=C_PRIMARY)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10.5)
        c.drawString(bx + 18, by, item)
        ty -= line_h
    return total_h


def comparison_table(c, x, y, w, headers, rows):
    """Two-column comparison table."""
    col_w = (w - 4) / 2
    header_h = 32
    row_h = 46
    pad = 10
    total_h = header_h + len(rows) * row_h

    # Header
    round_rect(c, x, y - header_h, col_w, header_h, 8, fill_color=C_PRIMARY, stroke_color=None)
    round_rect(c, x + col_w + 4, y - header_h, col_w, header_h, 8, fill_color=C_PURPLE, stroke_color=None)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 12)
    c.drawCentredString(x + col_w / 2, y - header_h / 2 - 4, headers[0])
    c.drawCentredString(x + col_w + 4 + col_w / 2, y - header_h / 2 - 4, headers[1])

    for i, (a, b) in enumerate(rows):
        ry = y - header_h - i * row_h
        bg = C_CHART_BG if i % 2 == 0 else C_WHITE
        c.setFillColor(bg)
        c.rect(x, ry - row_h, w, row_h, fill=1, stroke=0)
        c.setStrokeColor(C_LINE)
        c.setLineWidth(0.4)
        c.line(x + col_w + 2, ry - row_h + 6, x + col_w + 2, ry - 6)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10)
        for col_i, text in enumerate((a, b)):
            cx = x + col_i * (col_w + 4) + pad
            lines = wrap_text(text, "Body", 10, col_w - pad * 2)
            for j, ln in enumerate(lines[:3]):
                c.drawString(cx, ry - 18 - j * 13, ln)
    return total_h


# ====================================================================
# page composers
# ====================================================================

def page_cover(c):
    # vertical gradient background using many thin bands
    bands = 240
    for i in range(bands):
        t = i / (bands - 1)
        if t < 0.5:
            # #1A1A2E → #2563EB
            u = t / 0.5
            r = (1 - u) * 0.102 + u * 0.145
            g = (1 - u) * 0.102 + u * 0.388
            b = (1 - u) * 0.180 + u * 0.922
        else:
            u = (t - 0.5) / 0.5
            r = (1 - u) * 0.145 + u * 0.486
            g = (1 - u) * 0.388 + u * 0.227
            b = (1 - u) * 0.922 + u * 0.929
        c.setFillColorRGB(r, g, b)
        c.rect(0, PAGE_H - (i + 1) * PAGE_H / bands,
               PAGE_W, PAGE_H / bands + 0.5, fill=1, stroke=0)

    # abstract thin lines + circles
    c.setStrokeColor(Color(1, 1, 1, alpha=0.18))
    c.setLineWidth(0.6)
    for i in range(16):
        y = PAGE_H - 30 * mm - i * 15 * mm
        c.line(0, y, PAGE_W, y + 25)
    # circles / dots
    rng = np.random.default_rng(42)
    for _ in range(90):
        rx = rng.uniform(0, PAGE_W)
        ry = rng.uniform(0, PAGE_H)
        r = rng.uniform(0.4, 2.0)
        c.setFillColor(Color(1, 1, 1, alpha=float(rng.uniform(0.15, 0.6))))
        c.circle(rx, ry, r, fill=1, stroke=0)
    # large accent rings
    c.setStrokeColor(Color(1, 1, 1, alpha=0.14))
    c.setFillColor(Color(0, 0, 0, alpha=0))
    for r in (40, 70, 100):
        c.circle(PAGE_W - 35 * mm, 60 * mm, r, stroke=1, fill=0)

    # Title block
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 11)
    c.drawString(MARGIN_X, PAGE_H - 32 * mm, "ГАЙД · ВЫПУСК 2026")

    c.setFont("BodyBold", 34)
    for i, line in enumerate(["Пассивный доход", "с нуля"]):
        c.drawString(MARGIN_X, PAGE_H - 60 * mm - i * 42, line)

    c.setFont("BodyBold", 20)
    c.setFillColor(Color(1, 1, 1, alpha=0.95))
    c.drawString(MARGIN_X, PAGE_H - 118 * mm, "5 стратегий, которые")
    c.drawString(MARGIN_X, PAGE_H - 118 * mm - 26, "работают в 2026")

    # Decorative divider
    c.setFillColor(C_WHITE)
    c.rect(MARGIN_X, PAGE_H - 158 * mm, 60, 2, fill=1, stroke=0)

    c.setFont("Body", 13)
    c.setFillColor(Color(1, 1, 1, alpha=0.85))
    sub_lines = [
        "Пошаговое руководство для тех, кто хочет,",
        "чтобы деньги работали.",
    ]
    for i, ln in enumerate(sub_lines):
        c.drawString(MARGIN_X, PAGE_H - 168 * mm - i * 18, ln)

    # bottom block
    c.setFillColor(Color(1, 1, 1, alpha=0.12))
    round_rect(c, MARGIN_X, 28 * mm, CONTENT_W, 22 * mm, 10,
               fill_color=Color(1, 1, 1, alpha=0.12), stroke_color=None)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 11)
    c.drawString(MARGIN_X + 14, 42 * mm, "ВНУТРИ")
    c.setFont("Body", 10)
    c.setFillColor(Color(1, 1, 1, alpha=0.85))
    c.drawString(MARGIN_X + 14, 34 * mm,
                 "5 стратегий  ·  3 модельных портфеля  ·  7 ошибок  ·  чек-листы")

    c.setFont("BodyBold", 14)
    c.setFillColor(C_WHITE)
    c.drawRightString(PAGE_W - MARGIN_X, 14 * mm, "2026")


def page_toc(c, toc_items):
    draw_heading(c, "Оглавление", MARGIN_X, CONTENT_TOP - 8, size=28, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 36,
                 "Что внутри. Нажми на главу — попадёшь на нужную страницу.")

    y = CONTENT_TOP - 70
    for i, (label, page_num, anchor) in enumerate(toc_items):
        row_h = 32
        bg = C_CHART_BG if i % 2 == 0 else C_WHITE
        round_rect(c, MARGIN_X, y - row_h, CONTENT_W, row_h, 8,
                   fill_color=bg, stroke_color=C_LINE)
        # number badge
        c.setFillColor(C_PRIMARY)
        c.circle(MARGIN_X + 20, y - row_h / 2, 10, fill=1, stroke=0)
        c.setFillColor(C_WHITE)
        c.setFont("BodyBold", 10)
        label_num = str(i)
        tw = pdfmetrics.stringWidth(label_num, "BodyBold", 10)
        c.drawString(MARGIN_X + 20 - tw / 2, y - row_h / 2 - 4, label_num)

        c.setFillColor(C_TEXT)
        c.setFont("BodyBold", 11)
        c.drawString(MARGIN_X + 40, y - row_h / 2 - 3, label)

        c.setFillColor(C_PRIMARY)
        c.setFont("BodyBold", 11)
        c.drawRightString(PAGE_W - MARGIN_X - 10, y - row_h / 2 - 3, f"стр. {page_num}")

        # link
        c.linkAbsolute("", anchor,
                       (MARGIN_X, y - row_h, MARGIN_X + CONTENT_W, y),
                       thickness=0)
        y -= row_h + 6


def page_intro_1(c):
    draw_heading(c, "Введение", MARGIN_X, CONTENT_TOP - 8, size=28, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 12)
    c.drawString(MARGIN_X, CONTENT_TOP - 34, "Почему это важно именно сейчас")

    y = CONTENT_TOP - 65

    paras = [
        "Представь: ты просыпаешься, завариваешь кофе, идёшь на работу — "
        "а на счёт параллельно капают проценты, дивиденды и купоны. "
        "Это и есть пассивный доход: деньги работают, пока ты занят своей жизнью.",
        "Этот гайд — не очередной мотивационный текст про «финансовую свободу». "
        "Он про конкретные шаги, которые ты можешь сделать с 1 000 ₽ в кармане "
        "и телефоном в руке.",
        "К концу гайда ты будешь знать 5 рабочих стратегий, увидишь три готовых "
        "модельных портфеля (на 5 000, 20 000 и 50 000 ₽) и получишь пошаговые "
        "чек-листы — от открытия брокерского счёта до первой покупки.",
    ]
    for p in paras:
        y = draw_paragraph(c, p, MARGIN_X, y, CONTENT_W,
                           font_size=11.5, leading=18) - 8

    y -= 10
    y -= callout(c, MARGIN_X, y, CONTENT_W,
                 "Важно: гайд носит информационный характер и не является "
                 "индивидуальной инвестиционной рекомендацией. Решения ты принимаешь "
                 "сам и несёшь за них ответственность.",
                 kind="warn", title="ДИСКЛЕЙМЕР")

    y -= 20
    # three facts
    facts = [
        ("8–12 %", "Инфляция ежегодно съедает покупательную способность "
                   "денег на счёте."),
        ("~22 000 ₽", "Средняя пенсия в России — этого недостаточно "
                      "для комфортной жизни."),
        ("x16", "Во столько раз вырастут 10 000 ₽ под 15 % годовых "
                "за 20 лет. Это сложный процент."),
    ]
    card_w = (CONTENT_W - 20) / 3
    for i, (big, small) in enumerate(facts):
        cx = MARGIN_X + i * (card_w + 10)
        round_rect(c, cx, y - 70, card_w, 70, 10,
                   fill_color=C_ACCENT_BG, stroke_color=None)
        c.setFillColor(C_PRIMARY)
        c.setFont("BodyBold", 22)
        c.drawString(cx + 12, y - 36, big)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 9.5)
        for j, ln in enumerate(wrap_text(small, "Body", 9.5, card_w - 24)):
            c.drawString(cx + 12, y - 46 - j * 12, ln)


def page_intro_myths(c):
    draw_heading(c, "5 мифов о пассивном доходе", MARGIN_X, CONTENT_TOP - 8,
                 size=22, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 "Что говорят вокруг — и как есть на самом деле.")

    myths = [
        ("Нужен минимум миллион",
         "Начать можно с 100 ₽ — в индексный БПИФ или с 1 000 ₽ в акции."),
        ("Пассивный доход — это пассивно",
         "Старт требует усилий: разобраться, открыть счёт, собрать портфель."),
        ("Это казино, можно потерять всё",
         "Диверсификация и ОФЗ дают риск близкий к банковскому вкладу."),
        ("Надо следить за рынком каждый день",
         "Индексная стратегия работает лучше 80 % активных управляющих."),
        ("Дивиденды делают богатым за год",
         "Реальный горизонт — 5–10 лет. Магия сложного процента работает долго."),
    ]
    y = CONTENT_TOP - 60
    for i, (myth, truth) in enumerate(myths):
        card_h = 60
        round_rect(c, MARGIN_X, y - card_h, CONTENT_W, card_h, 10,
                   fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
        # left half red
        inner_pad = 14
        half_w = (CONTENT_W - inner_pad * 3) / 2
        c.setFillColor(HexColor("#FEF2F2"))
        round_rect(c, MARGIN_X + inner_pad - 4, y - card_h + 8, half_w + 8, card_h - 16, 6,
                   fill_color=HexColor("#FEF2F2"), stroke_color=None)
        c.setFillColor(HexColor("#ECFDF5"))
        round_rect(c, MARGIN_X + inner_pad * 2 + half_w - 4, y - card_h + 8,
                   half_w + 8, card_h - 16, 6,
                   fill_color=HexColor("#ECFDF5"), stroke_color=None)

        icon_cross(c, MARGIN_X + inner_pad + 8, y - 18, r=6)
        c.setFillColor(C_RED)
        c.setFont("BodyBold", 9)
        c.drawString(MARGIN_X + inner_pad + 22, y - 20, "МИФ")
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10)
        for j, ln in enumerate(wrap_text(myth, "Body", 10, half_w - 20)):
            c.drawString(MARGIN_X + inner_pad + 2, y - 36 - j * 13, ln)

        tx = MARGIN_X + inner_pad * 2 + half_w
        icon_check(c, tx + 8, y - 18, r=6)
        c.setFillColor(C_GREEN)
        c.setFont("BodyBold", 9)
        c.drawString(tx + 22, y - 20, "РЕАЛЬНОСТЬ")
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10)
        for j, ln in enumerate(wrap_text(truth, "Body", 10, half_w - 20)):
            c.drawString(tx + 2, y - 36 - j * 13, ln)

        y -= card_h + 10


def page_intro_inflation(c):
    draw_heading(c, "Почему просто копить — не работает", MARGIN_X, CONTENT_TOP - 8,
                 size=22, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 "Деньги под подушкой или на карте теряют покупательную способность.")

    img = chart_inflation()
    c.drawImage(img, MARGIN_X, CONTENT_TOP - 290, width=CONTENT_W, height=240,
                preserveAspectRatio=True, anchor="n")

    y = CONTENT_TOP - 310
    y = draw_paragraph(
        c,
        "Если положить 100 000 ₽ на карту без процентов и забыть на 10 лет, "
        "сумма на счёте останется той же. Но купить на неё можно будет товаров "
        "примерно на 35 % меньше. Деньги на карте — это не консервация, "
        "а медленное таяние.",
        MARGIN_X, y, CONTENT_W, leading=17) - 10

    y -= callout(
        c, MARGIN_X, y, CONTENT_W,
        "Инвестиции — это не про жадность. Это про то, чтобы инфляция не "
        "съедала твои усилия быстрее, чем ты их прилагаешь.",
        kind="info", title="ГЛАВНАЯ ИДЕЯ")


def page_chapter1_opener(c):
    y = draw_chapter_banner(c, 1, "Фундамент",
                            "Что нужно знать до того, как ты открыл брокерский счёт.")
    y -= 10
    draw_heading(c, "1.1 Что такое пассивный доход", MARGIN_X, y, size=16, color=C_TEXT)
    y -= 28

    y = draw_paragraph(
        c,
        "Пассивный доход — это деньги, которые приходят регулярно и без "
        "твоего ежедневного участия. Ты не меняешь часы жизни на рубли: "
        "работают активы, которые ты купил когда-то раньше.",
        MARGIN_X, y, CONTENT_W, leading=17) - 8

    y = draw_paragraph(
        c,
        "Это не «деньги из воздуха» и не «схема быстрого обогащения». "
        "Это дивиденды с акций, купоны с облигаций, выплаты от фондов "
        "недвижимости, проценты от краудлендинга и рост стоимости "
        "индексного фонда.",
        MARGIN_X, y, CONTENT_W, leading=17) - 8

    y = draw_paragraph(
        c,
        "Начать можно с 1 000 ₽. Нужно другое — время и дисциплина. "
        "Через 10 лет ты поблагодаришь себя за то, что начал сегодня.",
        MARGIN_X, y, CONTENT_W, leading=17) - 16

    callout(c, MARGIN_X, y, CONTENT_W,
            "Мы не обещаем «гарантированной доходности». Любая инвестиция "
            "— это риск. Задача гайда — показать, как этот риск сделать "
            "осознанным и управляемым.",
            kind="warn", title="ЧЕСТНО")


def page_compound(c):
    draw_heading(c, "1.2 Сложный процент — твой главный союзник",
                 MARGIN_X, CONTENT_TOP - 8, size=18, color=C_TEXT)
    y = CONTENT_TOP - 36

    y = draw_paragraph(
        c,
        "Сложный процент — это когда проценты начисляются не только на "
        "начальную сумму, но и на уже накопленные проценты. Каждый год "
        "твой капитал растёт чуть быстрее предыдущего. Это и есть «эффект "
        "снежного кома».",
        MARGIN_X, y, CONTENT_W, leading=17) - 10

    callout(c, MARGIN_X, y, CONTENT_W - 10,
            "Капитал = Начальная сумма × (1 + Ставка)^Число лет\n"
            "Пример: 10 000 × (1 + 0,15)^10 ≈ 40 456 ₽. "
            "За 20 лет — уже 163 665 ₽.",
            kind="tip", title="ФОРМУЛА")

    y -= 90
    img = chart_compound_interest()
    c.drawImage(img, MARGIN_X, y - 230, width=CONTENT_W, height=230,
                preserveAspectRatio=True, anchor="n")

    y -= 240
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 10)
    c.drawString(MARGIN_X, y,
                 "Сравни: за первые 5 лет капитал вырос вдвое. Чтобы вырасти "
                 "ещё вдвое, нужно всего ~5 лет. Такова нелинейность.")


def page_active_vs_passive(c):
    draw_heading(c, "1.3 Активный vs пассивный доход",
                 MARGIN_X, CONTENT_TOP - 8, size=18, color=C_TEXT)
    y = CONTENT_TOP - 36
    y = draw_paragraph(
        c,
        "Чтобы понять, зачем нужен пассивный доход, посмотри на разницу "
        "между двумя источниками денег.",
        MARGIN_X, y, CONTENT_W, leading=17) - 14

    rows = [
        ("Обменял время на деньги. Перестал работать — доход исчез.",
         "Деньги работают сами. Доход капает, пока ты в отпуске или спишь."),
        ("Потолок = количество часов и твоя квалификация.",
         "Потолка нет: капитал растёт, доход с него тоже."),
        ("Примеры: зарплата, фриланс, подработки, разовые проекты.",
         "Примеры: дивиденды, купоны, аренда, доход от фондов."),
        ("Нужно постоянно учиться и двигаться вверх по карьере.",
         "Главный ресурс — время и начальный капитал. Остальное — автоматизм."),
    ]
    comparison_table(c, MARGIN_X, y, CONTENT_W,
                     ["АКТИВНЫЙ ДОХОД", "ПАССИВНЫЙ ДОХОД"], rows)

    y -= 32 + 4 * 46 + 20
    callout(c, MARGIN_X, y, CONTENT_W,
            "Посчитай, какую сумму ты можешь откладывать ежемесячно. "
            "10 % от дохода — хорошее начало. С зарплаты 50 000 ₽ это 5 000 ₽ "
            "в месяц, или 60 000 ₽ в год — уже отличный старт.",
            kind="do", title="СДЕЛАЙ СЕЙЧАС")


# -------- Chapter 2 strategies --------

STRATEGIES = [
    {
        "num": 1, "title": "Дивидендные акции",
        "subtitle": "Долю в компании покупают — часть прибыли получают",
        "color": MPL_PRIMARY, "risk": 3,
        "intro": [
            "Покупая акцию, ты становишься совладельцем компании — на долю, "
            "равную твоей доле акций. Прибыльная компания может делиться "
            "частью заработка с акционерами — это и есть дивиденды.",
            "Выплаты обычно происходят 2–4 раза в год. Акции дивидендных "
            "«аристократов» — компаний, стабильно платящих много лет "
            "(в России это Сбербанк, Лукойл, МТС; за рубежом — Coca-Cola, "
            "Johnson & Johnson, Procter & Gamble) — считаются одной из "
            "самых понятных стратегий.",
            "Акция также может расти в цене. Твой доход — это дивиденды "
            "плюс потенциальный рост котировок.",
        ],
        "specs": [
            ("Минимальный вход", "от 1 000 ₽", "text"),
            ("Ожидаемая доходность", "6–12 % годовых", "text"),
            ("Уровень риска", "Средний", "risk:3"),
            ("Сложность старта", "", "stars:3"),
            ("Время до первого дохода", "3–6 месяцев", "text"),
        ],
        "pros": [
            "Регулярные выплаты 2–4 раза в год.",
            "Рост капитала за счёт удорожания акций.",
            "Высокая ликвидность — можно продать в один клик.",
            "Доступно от 1 000 ₽.",
        ],
        "cons": [
            "Дивиденды не гарантированы — компания может отменить выплаты.",
            "Волатильность: цена акции падает и растёт.",
            "Нужно разбираться в компаниях или брать готовые подборки.",
            "Налог 13 % с дивидендов (кроме ИИС типа Б).",
        ],
        "steps": [
            "Открой брокерский счёт и ИИС в банке с хорошим приложением.",
            "Выбери 3–5 дивидендных «аристократов» для старта.",
            "Купи по чуть-чуть каждой — распредели сумму равномерно.",
        ],
        "do_now": "Открой список дивидендных аристократов МосБиржи и выбери "
                  "3 компании, бизнес которых тебе понятен (банк, нефть, "
                  "ритейл, связь).",
        "yield_range": (6, 12),
    },
    {
        "num": 2, "title": "Облигации и фонды облигаций",
        "subtitle": "Даёшь в долг — получаешь фиксированный процент",
        "color": MPL_GREEN, "risk": 2,
        "intro": [
            "Облигация — это долговая расписка. Ты даёшь компании или "
            "государству деньги на определённый срок, они обещают платить "
            "тебе фиксированный процент (купон) и в конце срока вернуть "
            "номинал.",
            "Главные виды: ОФЗ (облигации федерального займа — выпущены "
            "Минфином, самые надёжные), корпоративные (от компаний: "
            "Сбер, Газпром, РЖД) и муниципальные (от регионов).",
            "Чем выше ключевая ставка ЦБ, тем выше доходность облигаций. "
            "В 2026 году облигации — один из самых интересных инструментов.",
        ],
        "specs": [
            ("Минимальный вход", "от 1 000 ₽", "text"),
            ("Ожидаемая доходность", "10–16 % годовых", "text"),
            ("Уровень риска", "Низкий", "risk:2"),
            ("Сложность старта", "", "stars:2"),
            ("Время до первого дохода", "3–6 месяцев", "text"),
        ],
        "pros": [
            "Предсказуемый доход — купон известен заранее.",
            "ОФЗ — риск на уровне банковского вклада.",
            "Купонные выплаты каждые 3–6 месяцев.",
            "Понятный инструмент — его легко объяснить.",
        ],
        "cons": [
            "Доходность может не покрывать инфляцию.",
            "Цена облигации падает, если ЦБ поднимает ставку.",
            "Корпоративные облигации — риск дефолта эмитента.",
            "Ликвидность отдельных выпусков ниже, чем у акций.",
        ],
        "steps": [
            "Начни с ОФЗ со сроком погашения 1–3 года.",
            "Для диверсификации добавь фонд облигаций (БПИФ).",
            "Собери «лестницу»: разные сроки погашения на 1, 2, 3 года.",
        ],
        "do_now": "Найди в приложении брокера ОФЗ со сроком погашения в 2027 "
                  "или 2028 году и посмотри её текущую доходность к погашению.",
        "yield_range": (10, 16),
    },
    {
        "num": 3, "title": "Индексное инвестирование (ETF)",
        "subtitle": "Один фонд — сотни бумаг внутри",
        "color": MPL_PURPLE, "risk": 3,
        "intro": [
            "Индексный фонд (ETF, в России — БПИФ) — это «коробка» из "
            "десятков или сотен акций и облигаций. Купил пай фонда — "
            "фактически купил маленькую долю всего рынка.",
            "Стратегия называется «ленивой», но данные неумолимы: "
            "индексные фонды переигрывают 80 % активных управляющих "
            "на горизонте 10–20 лет. Причина проста: ты не пытаешься "
            "угадать победителя — ты покупаешь всех.",
            "Это стратегия №1 для новичка: минимум решений, максимум "
            "диверсификации, низкая комиссия.",
        ],
        "specs": [
            ("Минимальный вход", "от 100 ₽", "text"),
            ("Ожидаемая доходность", "10–15 % годовых", "text"),
            ("Уровень риска", "Средний", "risk:3"),
            ("Сложность старта", "", "stars:1"),
            ("Время до первого дохода", "сразу (через рост цены пая)", "text"),
        ],
        "pros": [
            "Диверсификация за 100 ₽ — редкость среди инструментов.",
            "Не нужно выбирать отдельные акции.",
            "Низкие комиссии фонда — 0,5–1 % в год.",
            "Минимум времени: раз в месяц купил — забыл.",
        ],
        "cons": [
            "Дивиденды реинвестируются внутри фонда — на руки не приходят.",
            "Привязка к рынку: падает рынок — падает цена пая.",
            "Нужно платить комиссию управляющей компании.",
            "Нет контроля над отдельными бумагами внутри.",
        ],
        "steps": [
            "Выбери БПИФ на индекс МосБиржи или широкий международный.",
            "Настрой автопополнение: одна и та же сумма каждый месяц.",
            "Не трогай портфель минимум 3–5 лет.",
        ],
        "do_now": "В приложении брокера найди БПИФ с тикером SBMX, EQMX или "
                  "аналогичный — изучи его состав и комиссию.",
        "yield_range": (8, 15),
    },
    {
        "num": 4, "title": "Краудлендинг",
        "subtitle": "Малому бизнесу в долг — высокий процент на риске",
        "color": MPL_AMBER, "risk": 5,
        "intro": [
            "Краудлендинг — это коллективное кредитование. Через платформу-"
            "посредник (JetLend, Поток, Город денег и др.) ты даёшь деньги "
            "в долг малому бизнесу — на закупку товара, расширение, "
            "оборотные средства.",
            "Доходность высокая: 15–25 % годовых, иногда больше. "
            "Но и риск самый большой из нашей пятёрки: бизнес может "
            "обанкротиться, деньги не вернутся, а компенсации от государства "
            "не будет.",
            "Это инструмент не для первого рубля — его стоит пробовать, "
            "когда у тебя уже есть базовый портфель из ОФЗ, акций и фондов.",
        ],
        "specs": [
            ("Минимальный вход", "от 5 000 ₽", "text"),
            ("Ожидаемая доходность", "15–25 % годовых", "text"),
            ("Уровень риска", "Высокий", "risk:5"),
            ("Сложность старта", "", "stars:3"),
            ("Время до первого дохода", "1–2 месяца", "text"),
        ],
        "pros": [
            "Доходность в 2–3 раза выше вклада.",
            "Понятная механика: даёшь в долг — получаешь проценты.",
            "Ежемесячные выплаты процентов и части тела долга.",
            "Можно диверсифицироваться на 50+ малых заёмщиков.",
        ],
        "cons": [
            "Риск невозврата: часть заёмщиков дефолтится.",
            "Нет страхования — АСВ не покрывает краудлендинг.",
            "Платформа тоже может закрыться.",
            "Налог 13 % с процентов и ограниченная ликвидность.",
        ],
        "steps": [
            "Начни с 5 000–10 000 ₽ — только то, что не жалко потерять.",
            "Распредели сумму между 20+ заёмщиками с рейтингом A и B.",
            "Реинвестируй поступления автоматически.",
        ],
        "do_now": "Зарегистрируйся на одной из платформ, пройди верификацию, "
                  "но пока ничего не покупай — изучи рейтинги заёмщиков.",
        "yield_range": (15, 25),
    },
    {
        "num": 5, "title": "Фонды недвижимости (REIT и ЗПИФ)",
        "subtitle": "Арендный доход без покупки квартиры",
        "color": MPL_PRIMARY, "risk": 3,
        "intro": [
            "ЗПИФ недвижимости и БПИФы на недвижимость — это фонды, "
            "которые владеют коммерческими и жилыми объектами и сдают "
            "их в аренду. Купив пай, ты становишься «микро-владельцем» "
            "всей их недвижимости.",
            "Это альтернатива покупке квартиры под сдачу: не нужно "
            "100 000 $, не нужно общаться с жильцами, не нужно платить "
            "за ремонт. Фонд за всё отвечает сам.",
            "Доходность складывается из арендного потока (выплачивается "
            "регулярно) и переоценки объектов. В стабильные периоды — "
            "очень предсказуемый инструмент.",
        ],
        "specs": [
            ("Минимальный вход", "от 1 000 ₽ (БПИФ)", "text"),
            ("Ожидаемая доходность", "8–14 % годовых", "text"),
            ("Уровень риска", "Средний", "risk:3"),
            ("Сложность старта", "", "stars:3"),
            ("Время до первого дохода", "3–6 месяцев", "text"),
        ],
        "pros": [
            "Доход от недвижимости без покупки квартиры.",
            "Диверсификация по десяткам объектов.",
            "Нет головной боли с ремонтом и жильцами.",
            "Низкий порог входа по сравнению с покупкой жилья.",
        ],
        "cons": [
            "Низкая ликвидность у ЗПИФ — не всегда легко продать.",
            "Зависимость от рынка недвижимости.",
            "Комиссия управляющей компании — 1–2 % в год.",
            "Налог 13 % с выплат (кроме ИИС типа Б).",
        ],
        "steps": [
            "Начни с БПИФ на недвижимость — порог ниже, ликвидность выше.",
            "Проверь состав фонда: офисы, склады, жильё, доли.",
            "Держи долгосрочно — минимум 3–5 лет.",
        ],
        "do_now": "В приложении брокера найди БПИФ недвижимости — изучи, "
                  "какие объекты в него входят и какой у фонда уровень выплат.",
        "yield_range": (8, 14),
    },
]


def page_chapter2_opener(c):
    y = draw_chapter_banner(c, 2, "5 стратегий",
                            "Главы о том, где именно деньги могут работать.")
    y -= 20
    draw_heading(c, "Что ты получишь из этой главы", MARGIN_X, y, size=16)
    y -= 28

    cards = [
        ("5", "работающих стратегий", C_PRIMARY),
        ("3", "уровня риска", C_GREEN),
        ("15", "конкретных шагов", C_PURPLE),
        ("500 ₽", "минимальный вход", C_AMBER),
    ]
    cw = (CONTENT_W - 30) / 4
    for i, (big, label, col) in enumerate(cards):
        cx = MARGIN_X + i * (cw + 10)
        round_rect(c, cx, y - 70, cw, 70, 10,
                   fill_color=C_ACCENT_BG, stroke_color=None)
        c.setFillColor(col)
        c.setFont("BodyBold", 24)
        c.drawString(cx + 14, y - 42, big)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 9.5)
        for j, ln in enumerate(wrap_text(label, "Body", 9.5, cw - 24)):
            c.drawString(cx + 14, y - 54 - j * 11, ln)

    y -= 90
    y = draw_paragraph(
        c,
        "Каждая стратегия ниже разобрана по одной схеме: что это, "
        "характеристики (сумма входа, доходность, риск), плюсы и минусы, "
        "три шага старта и одно действие, которое ты можешь сделать "
        "прямо сегодня. Начни читать с той, что ближе по бюджету и риску.",
        MARGIN_X, y, CONTENT_W, leading=17) - 14

    callout(c, MARGIN_X, y, CONTENT_W,
            "Не пытайся запустить сразу все 5. Начни с одной — лучше "
            "ETF или ОФЗ. Через 3 месяца, когда освоишь механику, "
            "добавь вторую. Через полгода — третью.",
            kind="tip", title="СОВЕТ ОТ АВТОРА")


def page_strategy_a(c, s):
    """First page of a strategy: title + intro + spec card."""
    # title band
    bar_h = 60
    c.setFillColor(C_PRIMARY_DARK)
    c.rect(0, PAGE_H - bar_h, PAGE_W, bar_h, fill=1, stroke=0)
    c.setFillColor(C_PRIMARY)
    c.circle(PAGE_W - 10 * mm, PAGE_H - 10 * mm, 25 * mm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 10)
    c.drawString(MARGIN_X, PAGE_H - 20, f"СТРАТЕГИЯ {s['num']} ИЗ 5")
    c.setFont("BodyBold", 22)
    c.drawString(MARGIN_X, PAGE_H - 44, s["title"])
    c.setFont("Body", 10.5)
    c.setFillColor(Color(1, 1, 1, alpha=0.8))
    c.drawString(MARGIN_X, PAGE_H - 56, s["subtitle"])

    y = PAGE_H - bar_h - 20

    # "Что это" label
    c.setFillColor(C_PRIMARY)
    c.setFont("BodyBold", 11)
    c.drawString(MARGIN_X, y, "ЧТО ЭТО")
    y -= 14
    c.setStrokeColor(C_PRIMARY)
    c.setLineWidth(2)
    c.line(MARGIN_X, y + 8, MARGIN_X + 30, y + 8)
    y -= 10

    for para in s["intro"]:
        y = draw_paragraph(c, para, MARGIN_X, y, CONTENT_W,
                           font_size=11, leading=16) - 8

    y -= 10
    spec_card(c, MARGIN_X, y, CONTENT_W, s["specs"])


def page_strategy_b(c, s):
    """Second page of a strategy: pros/cons, chart, steps, do-now."""
    draw_heading(c, f"Стратегия {s['num']}: взвесь за и против",
                 MARGIN_X, CONTENT_TOP - 8, size=18, color=C_TEXT)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 10.5)
    c.drawString(MARGIN_X, CONTENT_TOP - 28, s["title"])
    y = CONTENT_TOP - 46

    pc_h = pros_cons_card(c, MARGIN_X, y, CONTENT_W, s["pros"], s["cons"])
    y -= pc_h + 14

    # yield chart
    low, high = s["yield_range"]
    img = chart_strategy_yield(s["title"], low, high, s["color"])
    img_h = 160
    c.drawImage(img, MARGIN_X, y - img_h, width=CONTENT_W, height=img_h,
                preserveAspectRatio=True, anchor="n")
    y -= img_h + 14

    # steps
    numbered_steps(c, MARGIN_X, y, CONTENT_W, s["steps"], title="КАК НАЧАТЬ ЗА 3 ШАГА")
    y -= 14 + 22 + sum(15 * len(wrap_text(st, "Body", 10.5, CONTENT_W - 60)) + 10
                       for st in s["steps"]) + 14

    callout(c, MARGIN_X, y, CONTENT_W, s["do_now"], kind="do")


# -------- Chapter 3 --------

def page_strategies_summary(c):
    draw_heading(c, "Все 5 стратегий в одной таблице",
                 MARGIN_X, CONTENT_TOP - 8, size=22, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 "Чтобы сравнить всё сразу — распечатай эту страницу.")

    y = CONTENT_TOP - 60

    # table
    col_widths = [CONTENT_W * 0.30, CONTENT_W * 0.14, CONTENT_W * 0.16,
                  CONTENT_W * 0.14, CONTENT_W * 0.26]
    headers = ["Стратегия", "Мин. вход", "Доходность",
               "Риск", "Лучшая для"]
    rows = [
        ("Дивидендные акции", "1 000 ₽", "6–12 %", 3,
         "Регулярный доход 2–4 раза в год"),
        ("Облигации (ОФЗ и др.)", "1 000 ₽", "10–16 %", 2,
         "Низкий риск, предсказуемый доход"),
        ("Индексный ETF (БПИФ)", "100 ₽", "10–15 %", 3,
         "«Ленивая» стратегия для новичка"),
        ("Краудлендинг", "5 000 ₽", "15–25 %", 5,
         "Высокая доходность, высокий риск"),
        ("Фонды недвижимости", "1 000 ₽", "8–14 %", 3,
         "Арендный доход без квартиры"),
    ]

    # header row
    th_h = 32
    round_rect(c, MARGIN_X, y - th_h, CONTENT_W, th_h, 8,
               fill_color=C_PRIMARY, stroke_color=None)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 9.5)
    cx = MARGIN_X + 10
    for i, h in enumerate(headers):
        c.drawString(cx, y - th_h / 2 - 4, h)
        cx += col_widths[i]
    y -= th_h

    row_h = 52
    for ri, (name, inp, yld, risk, best) in enumerate(rows):
        if ri % 2 == 0:
            c.setFillColor(C_CHART_BG)
            c.rect(MARGIN_X, y - row_h, CONTENT_W, row_h, fill=1, stroke=0)
        cx = MARGIN_X + 10
        # Name
        c.setFillColor(C_TEXT)
        c.setFont("BodyBold", 10)
        c.drawString(cx, y - 18, name)
        c.setFillColor(C_TEXT_MUTED)
        c.setFont("Body", 8.5)
        c.drawString(cx, y - 30, f"№ {ri + 1}")
        cx += col_widths[0]
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10)
        c.drawString(cx, y - 24, inp)
        cx += col_widths[1]
        c.setFont("BodyBold", 10)
        c.setFillColor(C_PRIMARY)
        c.drawString(cx, y - 24, yld)
        cx += col_widths[2]
        # risk bar
        draw_risk_bar(c, cx, y - 28, col_widths[3] - 6, 9, risk)
        cx += col_widths[3]
        c.setFillColor(C_TEXT)
        c.setFont("Body", 9)
        for j, ln in enumerate(wrap_text(best, "Body", 9, col_widths[4] - 10)):
            c.drawString(cx, y - 18 - j * 12, ln)
        y -= row_h

    y -= 20
    callout(c, MARGIN_X, y, CONTENT_W,
            "Правило трёх: распредели сумму на 3 стратегии с разным риском. "
            "60 % — консервативная (ОФЗ или БПИФ), 30 % — средний риск "
            "(акции), 10 % — высокий (краудлендинг). Это самый простой "
            "способ не поставить всё на одно поле.",
            kind="tip", title="КАК ВЫБРАТЬ")


def page_chapter3_opener(c):
    y = draw_chapter_banner(c, 3, "Собери свой первый портфель",
                            "От открытия счёта до первой покупки.")
    y -= 10

    draw_heading(c, "3.1 Где открыть счёт", MARGIN_X, y, size=16, color=C_TEXT)
    y -= 28

    y = draw_paragraph(
        c,
        "Чтобы покупать акции, облигации или фонды, нужен брокерский счёт. "
        "Это как банковский счёт, только для ценных бумаг. Открывается "
        "онлайн за 15–20 минут.",
        MARGIN_X, y, CONTENT_W, leading=16) - 6

    y = draw_paragraph(
        c,
        "На что смотреть при выборе брокера:",
        MARGIN_X, y, CONTENT_W, font_name="BodyBold", font_size=11, leading=16) - 4

    bullets = [
        "Комиссия за сделку — должна быть минимальной (0,05–0,3 %).",
        "Удобное мобильное приложение.",
        "Наличие ИИС (индивидуальный инвестиционный счёт).",
        "Надёжность: топ-10 по размеру активов.",
    ]
    for b in bullets:
        c.setFillColor(C_PRIMARY)
        c.circle(MARGIN_X + 4, y + 4, 2, fill=1, stroke=0)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 11)
        c.drawString(MARGIN_X + 14, y, b)
        y -= 16

    y -= 14
    callout(c, MARGIN_X, y, CONTENT_W,
            "ИИС — это особый счёт с налоговыми льготами. По типу А ты "
            "получаешь обратно 13 % от вложенной суммы (до 52 000 ₽ в год). "
            "По типу Б — не платишь налог с прибыли. Для старта чаще "
            "выгоден тип А.",
            kind="info", title="ЧТО ТАКОЕ ИИС")


def page_portfolio(c, name, amount, allocation, caption, kind="start"):
    draw_heading(c, f"Портфель «{name}»",
                 MARGIN_X, CONTENT_TOP - 8, size=24, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 11)
    amount_str = f"{amount:,}".replace(",", " ")
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 f"Для бюджета {amount_str} ₽ · {caption}")

    # amount pill
    pw = 100
    round_rect(c, PAGE_W - MARGIN_X - pw, CONTENT_TOP - 26, pw, 22, 11,
               fill_color=C_PRIMARY, stroke_color=None)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 11)
    c.drawRightString(PAGE_W - MARGIN_X - 10, CONTENT_TOP - 20,
                      f"{amount:,} ₽".replace(",", " "))

    # pie chart
    img = chart_pie(f"Структура портфеля", allocation)
    chart_h = 230
    c.drawImage(img, MARGIN_X, CONTENT_TOP - 56 - chart_h,
                width=CONTENT_W, height=chart_h,
                preserveAspectRatio=True, anchor="n")

    y = CONTENT_TOP - 56 - chart_h - 20

    # instruments table
    row_h = 24
    th_h = 26
    total_h = th_h + len(allocation) * row_h + 6
    round_rect(c, MARGIN_X, y - total_h, CONTENT_W, total_h, 10,
               fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
    c.setFillColor(C_PRIMARY)
    c.rect(MARGIN_X, y - th_h, CONTENT_W, th_h, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 10)
    c.drawString(MARGIN_X + 14, y - th_h / 2 - 3, "ИНСТРУМЕНТ")
    c.drawString(MARGIN_X + CONTENT_W * 0.55, y - th_h / 2 - 3, "ДОЛЯ")
    c.drawRightString(PAGE_W - MARGIN_X - 14, y - th_h / 2 - 3, "СУММА, ₽")

    for i, (label, pct, color_hex) in enumerate(allocation):
        ry = y - th_h - i * row_h
        if i % 2 == 1:
            c.setFillColor(C_CHART_BG)
            c.rect(MARGIN_X + 4, ry - row_h, CONTENT_W - 8, row_h, fill=1, stroke=0)
        # swatch
        c.setFillColor(HexColor(color_hex))
        c.circle(MARGIN_X + 20, ry - row_h / 2, 5, fill=1, stroke=0)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10.5)
        c.drawString(MARGIN_X + 34, ry - row_h / 2 - 3, label)
        c.setFont("BodyBold", 10.5)
        c.drawString(MARGIN_X + CONTENT_W * 0.55, ry - row_h / 2 - 3, f"{pct} %")
        rub = int(amount * pct / 100)
        c.drawRightString(PAGE_W - MARGIN_X - 14, ry - row_h / 2 - 3,
                          f"{rub:,}".replace(",", " "))

    y -= total_h + 14

    # goal callout
    goals = {
        "start": "Привыкнуть к рынку, минимальный риск, понять механику покупки. "
                 "Можно спать спокойно даже в кризис.",
        "grow":  "Баланс роста и дохода. Основа работает, половина портфеля "
                 "активно растёт на дистанции 5+ лет.",
        "agg":   "Максимальный рост при контролируемом риске. Готовность к "
                 "просадкам до 25 %. Горизонт — 10+ лет.",
    }
    callout(c, MARGIN_X, y, CONTENT_W, goals[kind], kind="info", title="ЦЕЛЬ ПОРТФЕЛЯ")


def page_first_purchase(c):
    draw_heading(c, "3.3 Чек-лист первой покупки",
                 MARGIN_X, CONTENT_TOP - 8, size=22, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 "Пошагово: от скачивания приложения до первой бумаги.")

    y = CONTENT_TOP - 60
    steps = [
        "Скачай приложение брокера (Т-Инвестиции, СберИнвестор, "
        "ВТБ Мои Инвестиции, БКС Мир инвестиций).",
        "Пройди регистрацию и верификацию через Госуслуги — обычно "
        "занимает 10–15 минут.",
        "Выбери тип счёта: открой сразу ИИС (тип А) и обычный "
        "брокерский счёт параллельно.",
        "Пополни счёт через привязанную банковскую карту "
        "или по реквизитам.",
        "Выбери один из трёх модельных портфелей — тот, что "
        "соответствует твоему бюджету.",
        "В поиске найди первый инструмент (например, БПИФ EQMX) "
        "и купи его на часть суммы.",
        "Настрой автопополнение счёта на одну и ту же сумму "
        "каждый месяц — так работает усреднение.",
    ]
    numbered_steps(c, MARGIN_X, y, CONTENT_W, steps,
                   title="СЕМЬ ШАГОВ ДЛЯ ПЕРВОЙ ПОКУПКИ")

    # position below the steps
    body_h = sum(15 * len(wrap_text(s, "Body", 10.5, CONTENT_W - 60)) + 10 for s in steps)
    y -= 14 + 22 + body_h + 14
    y -= 10

    callout(c, MARGIN_X, y, CONTENT_W,
            "Выбери один из трёх портфелей и открой брокерский счёт сегодня. "
            "Не завтра. Самый дорогой инструмент в инвестициях — "
            "отложенное решение.",
            kind="do", title="СДЕЛАЙ СЕЙЧАС")


# -------- Chapter 4 errors --------

ERRORS = [
    ("Ждать «идеального момента» для входа",
     "Рынок невозможно предугадать. «Я зайду, когда упадёт» — "
     "это способ не зайти никогда.",
     "Применяй стратегию усреднения: покупай одну и ту же сумму раз "
     "в месяц. Это снижает влияние пиков и просадок."),
    ("Вкладывать всё в один инструмент",
     "Одна акция может рухнуть на 70 % за неделю. "
     "Если это весь твой портфель — ты вылетел из игры.",
     "Распредели капитал: минимум 10–15 бумаг или 3–4 фонда. "
     "Правило — не более 10 % в одну позицию."),
    ("Паниковать при падении рынка",
     "Продажа на дне фиксирует убыток. История показывает: любая "
     "просадка — временная. 2008, 2020, 2022 — рынок всегда восстанавливался.",
     "Готовь нервы заранее. Твоя защита — долгосрочный горизонт, "
     "подушка безопасности и ясное понимание, зачем ты инвестируешь."),
    ("Игнорировать комиссии брокера",
     "Комиссия 1 % в год кажется ерундой. За 20 лет она «съест» "
     "20 % капитала — это сотни тысяч рублей.",
     "Выбирай брокера с комиссией 0,05–0,3 % за сделку. Для фондов "
     "смотри суммарную TER (общий расход фонда)."),
    ("Инвестировать кредитные или последние деньги",
     "Проигрыш не только финансовый, но и психологический: ты не "
     "сможешь спокойно ждать восстановления рынка.",
     "Сначала собери подушку безопасности на 3–6 месяцев расходов. "
     "Инвестируй только то, что реально можешь не трогать 3+ года."),
    ("Слепо следовать советам из Telegram-каналов",
     "«Инвест-гуру» часто продают курсы, а не стратегии. "
     "Их цель — твои деньги, а не твоя доходность.",
     "Проверяй источник. Читай отчёты компаний, аналитику брокеров "
     "и минимум два мнения перед решением."),
    ("Не реинвестировать дивиденды",
     "Если выводить дивиденды, сложный процент не работает. "
     "Из х16 на дистанции получится всего х3–4.",
     "Включи автоматический реинвест. Либо: как только пришли "
     "дивиденды — сразу докупи на них бумаги."),
]


def page_chapter4_opener(c):
    y = draw_chapter_banner(c, 4, "7 ошибок",
                            "Которые убивают доходность — у новичков и опытных.")
    y -= 10

    y = draw_paragraph(
        c,
        "Эти ошибки съедают доходность портфеля сильнее, чем комиссии и "
        "налоги вместе взятые. Хорошая новость — все они предотвращаются "
        "одним решением: прочти главу до конца и приклей её к холодильнику.",
        MARGIN_X, y, CONTENT_W, leading=17) - 14

    draw_heading(c, "Ошибки 1–3", MARGIN_X, y, size=18, color=C_TEXT)
    y -= 28

    for i in range(3):
        y -= draw_error_card(c, MARGIN_X, y, CONTENT_W, i + 1, *ERRORS[i])
        y -= 10


def page_chapter4_rest(c, start, end):
    draw_heading(c, f"Ошибки {start}–{end}",
                 MARGIN_X, CONTENT_TOP - 8, size=22, color=C_PRIMARY)
    y = CONTENT_TOP - 40
    for i in range(start - 1, end):
        y -= draw_error_card(c, MARGIN_X, y, CONTENT_W, i + 1, *ERRORS[i])
        y -= 10


def draw_error_card(c, x, y, w, number, title, why, how):
    pad = 14
    inner_w = w - pad * 2
    title_lines = wrap_text(title, "BodyBold", 12, inner_w - 40)
    why_lines = wrap_text(why, "Body", 10, inner_w)
    how_lines = wrap_text(how, "Body", 10, inner_w - 20)
    total_h = pad + len(title_lines) * 15 + 8 + len(why_lines) * 14 + 10 + \
              12 + len(how_lines) * 14 + pad

    round_rect(c, x, y - total_h, w, total_h, 10,
               fill_color=C_WHITE, stroke_color=C_LINE, shadow=True)
    # number badge
    c.setFillColor(C_RED)
    round_rect(c, x + pad, y - pad - 16, 26, 20, 6, fill_color=C_RED, stroke_color=None)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 11)
    tw = pdfmetrics.stringWidth(f"#{number}", "BodyBold", 11)
    c.drawString(x + pad + 13 - tw / 2, y - pad - 11, f"#{number}")
    # warning icon
    icon_warning(c, x + pad + 44, y - pad - 7, r=7)
    # title
    c.setFillColor(C_TEXT)
    c.setFont("BodyBold", 12)
    tx = x + pad + 60
    ty = y - pad - 10
    for ln in title_lines:
        c.drawString(tx, ty, ln)
        ty -= 15
    cur_y = y - pad - 15 - len(title_lines) * 15 - 2
    # why
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 9.5)
    c.drawString(x + pad, cur_y, "ПОЧЕМУ ОПАСНО")
    cur_y -= 12
    c.setFillColor(C_TEXT)
    c.setFont("Body", 10)
    for ln in why_lines:
        c.drawString(x + pad, cur_y, ln)
        cur_y -= 14
    cur_y -= 2
    # how
    icon_check(c, x + pad + 6, cur_y - 6, r=5)
    c.setFillColor(C_GREEN)
    c.setFont("BodyBold", 9.5)
    c.drawString(x + pad + 18, cur_y - 8, "КАК ИЗБЕЖАТЬ")
    cur_y -= 20
    c.setFillColor(C_TEXT)
    c.setFont("Body", 10)
    for ln in how_lines:
        c.drawString(x + pad + 18, cur_y, ln)
        cur_y -= 14
    return total_h


# -------- Conclusion --------

def page_glossary(c):
    draw_heading(c, "Мини-словарь", MARGIN_X, CONTENT_TOP - 8,
                 size=22, color=C_PRIMARY)
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 11)
    c.drawString(MARGIN_X, CONTENT_TOP - 32,
                 "16 терминов из гайда — объяснение в одну строку.")

    terms = [
        ("Акция", "Доля в компании. Даёт право на часть прибыли и голос."),
        ("Облигация", "Долговая расписка. Платит купон и возвращает номинал."),
        ("ОФЗ", "Облигация федерального займа — долг государства, минимальный риск."),
        ("Купон", "Процент, который облигация платит владельцу (обычно 2 раза в год)."),
        ("Дивиденды", "Часть прибыли компании, выплаченная акционерам."),
        ("БПИФ / ETF", "«Коробка» из многих бумаг, продаётся как одна. Диверсификация в один клик."),
        ("Индекс", "Корзина бумаг, отражающая рынок (напр. МосБиржа, S&P 500)."),
        ("Диверсификация", "Распределение денег между разными активами для снижения риска."),
        ("Волатильность", "Величина колебаний цены актива. Больше — рискованнее."),
        ("Ликвидность", "Способность быстро продать актив без потери в цене."),
        ("ИИС", "Индивидуальный инвестиционный счёт с налоговыми льготами (вычет 13 %)."),
        ("Брокер", "Посредник, через которого ты покупаешь бумаги на бирже."),
        ("Эмитент", "Тот, кто выпустил ценную бумагу (компания, государство)."),
        ("Доходность", "Сколько ты зарабатываешь, в процентах за период (обычно год)."),
        ("Сложный процент", "Проценты, которые начисляются на проценты. Главный двигатель капитала."),
        ("Усреднение (DCA)", "Покупка на одну и ту же сумму регулярно, вне зависимости от цены."),
    ]

    y = CONTENT_TOP - 60
    row_h = 36
    for i, (term, defn) in enumerate(terms):
        if i % 2 == 1:
            c.setFillColor(C_CHART_BG)
            c.rect(MARGIN_X, y - row_h, CONTENT_W, row_h, fill=1, stroke=0)
        c.setFillColor(C_PRIMARY)
        c.setFont("BodyBold", 10.5)
        c.drawString(MARGIN_X + 10, y - 14, term)
        c.setFillColor(C_TEXT)
        c.setFont("Body", 10)
        lines = wrap_text(defn, "Body", 10, CONTENT_W - 150)
        for j, ln in enumerate(lines[:2]):
            c.drawString(MARGIN_X + 140, y - 14 - j * 12, ln)
        y -= row_h


def page_conclusion(c):
    y = draw_chapter_banner(c, "·", "Что дальше",
                            "Ты дочитал. Теперь — три действия.")
    y -= 10

    y = draw_paragraph(
        c,
        "Ты только что получил карту пассивного дохода: 5 стратегий, "
        "3 модельных портфеля и 7 ошибок, которых стоит избежать. "
        "Остался последний шаг — применить.",
        MARGIN_X, y, CONTENT_W, leading=18, font_size=12) - 14

    draw_heading(c, "Три шага на эту неделю", MARGIN_X, y, size=16, color=C_TEXT)
    y -= 26

    numbered_steps(c, MARGIN_X, y, CONTENT_W, [
        "Открой брокерский счёт и ИИС сегодня. Понедельник не считается — "
        "это обман мозга.",
        "Сделай первую покупку из портфеля «Старт»: 60 % ОФЗ, 40 % индексный БПИФ. "
        "Любая сумма, с которой тебе не страшно.",
        "Настрой автопополнение. Инвестирование — не разовое действие, "
        "а привычка. Привычка строится через автоматизацию.",
    ])


def page_cta(c):
    # top accent bar
    c.setFillColor(C_PRIMARY)
    c.rect(0, PAGE_H - 8, PAGE_W, 8, fill=1, stroke=0)

    y = CONTENT_TOP - 10
    draw_heading(c, "Через год ты скажешь себе спасибо",
                 MARGIN_X, y, size=22, color=C_PRIMARY)
    y -= 36

    y = draw_paragraph(
        c,
        "10 000 ₽, вложенные сегодня в индексный фонд, через 10 лет "
        "превратятся примерно в 40 000 ₽. 1 000 ₽ в месяц — это "
        "больше 230 000 ₽ через 10 лет. Главное — начать и не бросить.",
        MARGIN_X, y, CONTENT_W, leading=18, font_size=12) - 20

    # CTA box
    box_h = 170
    round_rect(c, MARGIN_X, y - box_h, CONTENT_W, box_h, 14,
               fill_color=C_PRIMARY_DARK, stroke_color=None)
    # decorative
    c.setFillColor(Color(1, 1, 1, alpha=0.08))
    c.circle(PAGE_W - 60, y - 20, 60, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("BodyBold", 16)
    c.drawString(MARGIN_X + 20, y - 36, "Подпишись на Telegram-канал")
    c.setFont("Body", 11)
    c.setFillColor(Color(1, 1, 1, alpha=0.85))
    for i, ln in enumerate([
        "Каждую неделю: разбор одной стратегии, одной компании и ответы",
        "на вопросы читателей. Без рекламы казино и крипто-пампов.",
    ]):
        c.drawString(MARGIN_X + 20, y - 56 - i * 16, ln)

    # button
    btn_w = CONTENT_W - 60
    btn_h = 40
    btn_y = y - 100
    round_rect(c, MARGIN_X + 20, btn_y - btn_h, btn_w, btn_h, 10,
               fill_color=C_WHITE, stroke_color=None)
    c.setFillColor(C_PRIMARY_DARK)
    c.setFont("BodyBold", 13)
    c.drawString(MARGIN_X + 36, btn_y - btn_h / 2 - 4,
                 "t.me/ [ВСТАВЬ ССЫЛКУ НА КАНАЛ]")
    icon_arrow_up(c, MARGIN_X + btn_w, btn_y - btn_h / 2, r=10, bg=C_PRIMARY)

    c.setFillColor(Color(1, 1, 1, alpha=0.7))
    c.setFont("Body", 9.5)
    c.drawString(MARGIN_X + 20, y - 160,
                 "Подписчики канала получают скидку 50 % на следующие продукты.")

    y -= box_h + 24

    # Next product teaser
    round_rect(c, MARGIN_X, y - 100, CONTENT_W, 100, 10,
               fill_color=C_ACCENT_BG, stroke_color=None)
    c.setFillColor(C_PRIMARY)
    c.setFont("BodyBold", 10)
    c.drawString(MARGIN_X + 16, y - 20, "СКОРО")
    c.setFillColor(C_TEXT)
    c.setFont("BodyBold", 15)
    c.drawString(MARGIN_X + 16, y - 42, "Шаблон автоматического портфеля")
    c.drawString(MARGIN_X + 16, y - 60, "в Google Sheets")
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("Body", 10)
    c.drawString(MARGIN_X + 16, y - 80,
                 "Готовая таблица с автоматическим расчётом долей и доходности.")
    c.drawString(MARGIN_X + 16, y - 92,
                 "Подписчики канала узнают первыми.")

    # footer
    c.setFillColor(C_TEXT_MUTED)
    c.setFont("BodyItalic", 9)
    c.drawCentredString(PAGE_W / 2, 24 * mm,
                        "Спасибо, что дочитал. Удачи с первой покупкой.")
    c.setFont("BodyBold", 10)
    c.setFillColor(C_PRIMARY)
    c.drawCentredString(PAGE_W / 2, 14 * mm,
                        "Пассивный доход с нуля · 2026")


# ====================================================================
# main
# ====================================================================

def main():
    out_path = "passive_income_guide_2026.pdf"
    c = rl_canvas.Canvas(out_path, pagesize=A4)
    c.setTitle("Пассивный доход с нуля: 5 стратегий, которые работают в 2026")
    c.setAuthor("Artem")
    c.setSubject("Руководство для начинающих инвесторов")

    # ---- page 1: Cover (no page number)
    page_cover(c)
    c.showPage()

    # We'll build a list of (label, anchor_name) for TOC and compute page numbers
    toc_entries = []  # filled sequentially as we add pages; (label, pageno, anchor)
    page_counter = 1  # pages after cover (TOC itself is #1 in our footer scheme? we'll start numbering from intro)

    # ---- page 2: TOC placeholder — we need page numbers of chapters.
    # Strategy: generate all content pages first into a list of callables,
    # tracking page numbers, then compose TOC.

    pages = []  # list of (callable, add_number: bool, anchor_name_or_none)

    pages.append((page_intro_1, True, "intro"))
    pages.append((page_intro_myths, True, None))
    pages.append((page_intro_inflation, True, None))

    pages.append((page_chapter1_opener, True, "ch1"))
    pages.append((page_compound, True, None))
    pages.append((page_active_vs_passive, True, None))

    pages.append((page_chapter2_opener, True, "ch2"))
    for s in STRATEGIES:
        pages.append((lambda cv, s=s: page_strategy_a(cv, s), True, f"strategy{s['num']}"))
        pages.append((lambda cv, s=s: page_strategy_b(cv, s), True, None))
    pages.append((page_strategies_summary, True, "ch2summary"))

    pages.append((page_chapter3_opener, True, "ch3"))
    port_start = [
        ("ОФЗ (гособлигации)", 60, "#2563EB"),
        ("Индексный БПИФ", 40, "#10B981"),
    ]
    port_grow = [
        ("Индексный БПИФ", 40, "#2563EB"),
        ("Дивидендные акции", 30, "#10B981"),
        ("Облигации (ОФЗ + корп.)", 20, "#7C3AED"),
        ("ЗПИФ недвижимости", 10, "#F59E0B"),
    ]
    port_agg = [
        ("Акции (рост + дивиденды)", 50, "#2563EB"),
        ("Индексный БПИФ", 20, "#10B981"),
        ("Облигации", 15, "#7C3AED"),
        ("Краудлендинг", 10, "#F59E0B"),
        ("ЗПИФ недвижимости", 5, "#EF4444"),
    ]
    pages.append((lambda cv: page_portfolio(cv, "Старт", 5000, port_start,
                                           "минимальный риск, учебный", "start"),
                  True, None))
    pages.append((lambda cv: page_portfolio(cv, "Рост", 20000, port_grow,
                                           "баланс дохода и роста", "grow"),
                  True, None))
    pages.append((lambda cv: page_portfolio(cv, "Агрессивный", 50000, port_agg,
                                           "максимум роста, горизонт 10+ лет", "agg"),
                  True, None))
    pages.append((page_first_purchase, True, None))

    pages.append((page_chapter4_opener, True, "ch4"))
    pages.append((lambda cv: page_chapter4_rest(cv, 4, 5), True, None))
    pages.append((lambda cv: page_chapter4_rest(cv, 6, 7), True, None))

    pages.append((page_glossary, True, "glossary"))
    pages.append((page_conclusion, True, "end"))
    pages.append((page_cta, False, None))

    # Logical page numbers start at 1 for TOC. Cover = unnumbered; TOC = page 1; intro = page 2.
    # Build TOC entries with anchor-matched page numbers.

    toc_structure = [
        ("Введение: почему это важно сейчас", "intro"),
        ("Глава 1. Фундамент", "ch1"),
        ("Глава 2. 5 стратегий пассивного дохода", "ch2"),
        ("Стратегия 1. Дивидендные акции", "strategy1"),
        ("Стратегия 2. Облигации", "strategy2"),
        ("Стратегия 3. Индексное инвестирование (ETF)", "strategy3"),
        ("Стратегия 4. Краудлендинг", "strategy4"),
        ("Стратегия 5. Фонды недвижимости", "strategy5"),
        ("Сравнение всех 5 стратегий", "ch2summary"),
        ("Глава 3. Собери свой первый портфель", "ch3"),
        ("Глава 4. 7 ошибок, которые убивают доходность", "ch4"),
        ("Мини-словарь терминов", "glossary"),
        ("Заключение + следующий шаг", "end"),
    ]

    # Compute anchor → page number (TOC itself will be page 1; content starts at 2)
    anchor_page = {}
    page_no = 2  # pages after TOC
    for cb, add_number, anchor in pages:
        if anchor:
            anchor_page[anchor] = page_no
        page_no += 1

    toc_items = [(label, anchor_page[anc], anc) for label, anc in toc_structure]

    # ---- page 2 (TOC)
    page_toc(c, toc_items)
    draw_footer_rule(c)
    draw_page_number(c, 1)
    c.showPage()

    # ---- content pages
    current_pageno = 2
    for cb, add_number, anchor in pages:
        if anchor:
            c.bookmarkPage(anchor)
            c.addOutlineEntry(anchor, anchor, level=0)
        cb(c)
        if add_number:
            draw_footer_rule(c)
            draw_page_number(c, current_pageno)
        c.showPage()
        current_pageno += 1

    c.save()
    print(f"Wrote {out_path}: {current_pageno - 1 + 1} logical pages (cover + content).")


if __name__ == "__main__":
    main()
