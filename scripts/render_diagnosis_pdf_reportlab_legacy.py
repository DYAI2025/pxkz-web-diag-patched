#!/usr/bin/env python3
"""Render a validated Pixelkiez client report model as a branded A4-landscape PDF."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

SKILL_DIR = Path(__file__).resolve().parent.parent
BRAND_PATH = SKILL_DIR / "assets" / "brand.json"
PAGE_W, PAGE_H = landscape(A4)
MARGIN = 14 * mm


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def register_fonts() -> tuple[str, str, str]:
    candidates = [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
        ),
    ]
    for regular, bold, mono in candidates:
        if regular.exists() and bold.exists() and mono.exists():
            pdfmetrics.registerFont(TTFont("PKSans", str(regular)))
            pdfmetrics.registerFont(TTFont("PKSansBold", str(bold)))
            pdfmetrics.registerFont(TTFont("PKMono", str(mono)))
            return "PKSans", "PKSansBold", "PKMono"
    return "Helvetica", "Helvetica-Bold", "Courier"


FONT, FONT_BOLD, FONT_MONO = register_fonts()


def hx(value: str) -> colors.Color:
    return colors.HexColor(value)


def sanitize(text: object) -> str:
    return " ".join(str(text or "").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-").split())


def paragraph(canvas: Canvas, text: object, x: float, y_top: float, w: float, h: float,
              *, size: float = 12, leading: float | None = None, color: colors.Color = colors.black,
              bold: bool = False, mono: bool = False, align: int = TA_LEFT) -> float:
    font = FONT_MONO if mono else (FONT_BOLD if bold else FONT)
    style = ParagraphStyle(
        "pk",
        fontName=font,
        fontSize=size,
        leading=leading or size * 1.35,
        textColor=color,
        alignment=align,
        spaceAfter=0,
        spaceBefore=0,
    )
    p = Paragraph(sanitize(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)
    need_w, need_h = p.wrap(w, h)
    if need_h > h + 0.1:
        raise ValueError(f"text overflow ({need_h:.1f}>{h:.1f}) for: {sanitize(text)[:100]}")
    p.drawOn(canvas, x, y_top - need_h)
    return need_h


def round_rect(c: Canvas, x: float, y: float, w: float, h: float, fill: colors.Color,
               stroke: colors.Color | None = None, radius: float = 5 * mm, line: float = 0.7) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.setLineWidth(line)
    c.roundRect(x, y, w, h, radius, stroke=1 if stroke else 0, fill=1)


def draw_wordmark(c: Canvas, ink: colors.Color, muted: colors.Color) -> None:
    c.setFillColor(ink)
    c.setFont(FONT_BOLD, 18)
    c.drawString(MARGIN, PAGE_H - MARGIN - 3 * mm, "Pixelkiez")
    c.setFillColor(muted)
    c.setFont(FONT_MONO, 6.8)
    c.drawString(MARGIN + 38 * mm, PAGE_H - MARGIN - 2.5 * mm, "WEB DESIGN BERLIN")


def draw_eyebrow(c: Canvas, label: str, x: float, y: float, w: float, ink: colors.Color, on_dark: bool = False) -> None:
    rule = hx("#2B3634") if on_dark else ink
    c.setStrokeColor(rule)
    c.setLineWidth(0.7)
    c.line(x, y, x + w, y)
    c.setFillColor(rule)
    c.setFont(FONT_MONO, 7.5)
    c.drawString(x, y - 7 * mm, sanitize(label).upper())


def draw_pixel_meter(c: Canvas, x: float, y: float, score: int | None, fg: colors.Color, bg: colors.Color,
                     cell: float = 4.2 * mm, gap: float = 1.2 * mm) -> None:
    total = 18
    filled = 0 if score is None else max(0, min(total, int(round(score / 100 * total))))
    for r in range(3):
        for col in range(6):
            idx = r * 6 + col
            c.setFillColor(fg if idx < filled else bg)
            c.roundRect(x + col * (cell + gap), y - r * (cell + gap), cell, cell, 0.7 * mm, stroke=0, fill=1)


def draw_footer(c: Canvas, meta: dict[str, Any], ink: colors.Color, line: colors.Color, page: int, on_dark: bool = False) -> None:
    fg = hx("#C6D4D1") if on_dark else ink
    c.setStrokeColor(line)
    c.setLineWidth(0.4)
    c.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)
    c.setFillColor(fg)
    c.setFont(FONT_MONO, 6.5)
    c.drawString(MARGIN, 5.6 * mm, f"Pixelkiez · Website-Analyse · {sanitize(meta.get('customer'))}")
    c.drawRightString(PAGE_W - MARGIN, 5.6 * mm, f"{sanitize(meta.get('date'))} · {page}")


def new_page(c: Canvas, bg: colors.Color, meta: dict[str, Any], page_no: int, *, header: bool = True) -> None:
    c.setFillColor(bg)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    if header:
        dark = bg == hx("#0E1414")
        draw_wordmark(c, hx("#C6D4D1") if dark else hx("#0E1414"), hx("#93A29E") if dark else hx("#475350"))
        draw_footer(c, meta, hx("#0E1414"), hx("#566360") if not dark else hx("#2B3634"), page_no, on_dark=dark)


def score_status_color(score: int | None, brand: dict[str, Any]) -> colors.Color:
    # The overall Pixelkiez score is a proprietary orientation score, not Lighthouse.
    # Use the brand accent consistently rather than importing Lighthouse red/amber/green semantics.
    palette = brand["colors"]
    return hx(palette["ink"] if score is None else palette["orange"])


def draw_cover(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    palette = brand["colors"]
    sage = hx(palette["sage_raised"])
    ink = hx(palette["ink"])
    orange = hx(palette["orange"])
    white = hx(palette["white"])
    muted = hx("#475350")
    new_page(c, sage, model["meta"], page_no, header=False)

    draw_wordmark(c, ink, muted)
    draw_eyebrow(c, model["cover"]["eyebrow"], MARGIN, PAGE_H - 42 * mm, 105 * mm, ink)
    paragraph(c, model["cover"]["title"], MARGIN, PAGE_H - 58 * mm, 150 * mm, 40 * mm, size=28, leading=32, color=ink, bold=True)
    paragraph(c, model["cover"]["customer"], MARGIN, PAGE_H - 105 * mm, 145 * mm, 12 * mm, size=14, color=ink, bold=True)
    paragraph(c, model["cover"]["url"], MARGIN, PAGE_H - 120 * mm, 145 * mm, 10 * mm, size=9.5, color=muted, mono=True)

    # Score field
    x = PAGE_W - MARGIN - 105 * mm
    y = 33 * mm
    round_rect(c, x, y, 105 * mm, 118 * mm, white, stroke=hx(palette["sage_line"]), radius=5 * mm)
    paragraph(c, model["cover"]["score_label"], x + 9 * mm, y + 105 * mm, 87 * mm, 10 * mm, size=8.5, color=ink, mono=True, bold=False)
    score = model["cover"]["score"]
    score_text = "-" if score is None else str(score)
    c.setFillColor(score_status_color(score, brand))
    c.setFont(FONT_BOLD, 43)
    c.drawString(x + 9 * mm, y + 60 * mm, score_text)
    c.setFillColor(muted)
    c.setFont(FONT_MONO, 10)
    c.drawString(x + 42 * mm, y + 63 * mm, "/100" if score is not None else "NO SCORE")
    draw_pixel_meter(c, x + 9 * mm, y + 48 * mm, score, ink, hx(palette["sage_raised"]))
    paragraph(c, model["cover"]["verdict"], x + 9 * mm, y + 34 * mm, 87 * mm, 18 * mm, size=11, color=ink, bold=True)
    paragraph(c, f"Messabdeckung {model['cover']['coverage']}% · Sicherheit {model['cover'].get('confidence_label', model['cover']['confidence'])}", x + 9 * mm, y + 14 * mm, 87 * mm, 8 * mm, size=7.5, color=muted, mono=True)

    if model["cover"].get("blocker_note"):
        round_rect(c, MARGIN, 26 * mm, 150 * mm, 22 * mm, orange, radius=4 * mm)
        paragraph(c, model["cover"]["blocker_note"], MARGIN + 7 * mm, 42 * mm, 136 * mm, 12 * mm, size=10.5, color=ink, bold=True)

    draw_footer(c, model["meta"], ink, hx(palette["sage_line"]), page_no)
    c.showPage()


def draw_exec(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    orange, ink, white = hx(p["orange"]), hx(p["ink"]), hx(p["white"])
    new_page(c, orange, model["meta"], page_no)
    draw_eyebrow(c, "02 · ENTSCHEIDUNG AUF EINEN BLICK", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
    paragraph(c, model["executive"]["takeaway"], MARGIN, PAGE_H - 58 * mm, PAGE_W - 2 * MARGIN, 32 * mm, size=18.5, leading=22, color=ink, bold=True)

    gap = 8 * mm
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    y = 38 * mm
    h = 76 * mm
    round_rect(c, MARGIN, y, card_w, h, white, radius=5 * mm)
    round_rect(c, MARGIN + card_w + gap, y, card_w, h, hx(p["sage_raised"]), radius=5 * mm)
    paragraph(c, "DAS FUNKTIONIERT", MARGIN + 8 * mm, y + h - 10 * mm, card_w - 16 * mm, 8 * mm, size=8.2, mono=True, color=ink)
    paragraph(c, "DAS BREMST", MARGIN + card_w + gap + 8 * mm, y + h - 10 * mm, card_w - 16 * mm, 8 * mm, size=8.2, mono=True, color=ink)

    top = y + h - 23 * mm
    for i, text in enumerate(model["executive"]["strengths"][:3], 1):
        paragraph(c, f"{i:02d}  {text}", MARGIN + 8 * mm, top - (i - 1) * 18 * mm, card_w - 16 * mm, 15 * mm, size=11, color=ink, bold=(i == 1))
    for i, text in enumerate(model["executive"]["priorities"][:3], 1):
        paragraph(c, f"{i:02d}  {text}", MARGIN + card_w + gap + 8 * mm, top - (i - 1) * 18 * mm, card_w - 16 * mm, 15 * mm, size=11, color=ink, bold=(i == 1))

    paragraph(c, f"Empfohlener Weg: {model['executive']['recommended_route']}", MARGIN, 27 * mm, PAGE_W - 2 * MARGIN, 10 * mm, size=11.5, color=ink, bold=True)
    c.showPage()


def draw_categories(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    sage, ink, white, orange = hx(p["sage"]), hx(p["ink"]), hx(p["white"]), hx(p["orange"])
    new_page(c, sage, model["meta"], page_no)
    draw_eyebrow(c, "03 · KATEGORIE-SCORES", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
    paragraph(c, "Sechs Bereiche. Qualit\u00e4t und Messabdeckung bleiben getrennt.", MARGIN, PAGE_H - 56 * mm, 210 * mm, 22 * mm, size=18, leading=21.5, color=ink, bold=True)

    cols, rows = 3, 2
    gap_x, gap_y = 7 * mm, 7 * mm
    card_w = (PAGE_W - 2 * MARGIN - gap_x * (cols - 1)) / cols
    card_h = 62 * mm
    start_y = 29 * mm + card_h + gap_y
    fills = [white, sage, orange, ink, white, sage]
    for idx, item in enumerate(model["categories"][:6]):
        row, col = divmod(idx, cols)
        x = MARGIN + col * (card_w + gap_x)
        y = start_y - row * (card_h + gap_y)
        fill = fills[idx]
        on_dark = fill == ink
        textc = hx(p["sage_raised"]) if on_dark else ink
        stroke = hx(p["sage_line"]) if fill in {sage, white} else None
        round_rect(c, x, y, card_w, card_h, fill, stroke=stroke, radius=4 * mm)
        paragraph(c, item["label"], x + 6 * mm, y + card_h - 8 * mm, card_w - 12 * mm, 11 * mm, size=10.5, color=textc, bold=True)
        score = item.get("score")
        c.setFillColor(textc)
        c.setFont(FONT_BOLD, 27)
        c.drawString(x + 6 * mm, y + 28 * mm, "-" if score is None else str(score))
        c.setFont(FONT_MONO, 7)
        c.drawString(x + 25 * mm, y + 31 * mm, "/100" if score is not None else "nicht ausreichend gemessen")
        paragraph(c, f"Messabdeckung {item['coverage']}% · Sicherheit {item.get('confidence_label', item['confidence'])}", x + 6 * mm, y + 20 * mm, card_w - 12 * mm, 7 * mm, size=6.8, color=textc, mono=True)
        paragraph(c, item["summary"], x + 6 * mm, y + 11.5 * mm, card_w - 12 * mm, 11.5 * mm, size=8.5, leading=10.2, color=textc)
    c.showPage()


def draw_coverage(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    ink, sage, orange = hx(p["ink"]), hx(p["sage_raised"]), hx(p["orange"])
    new_page(c, ink, model["meta"], page_no)
    draw_eyebrow(c, "04 · WAS WURDE GEPRÜFT?", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, sage, on_dark=True)
    paragraph(c, "Der Score zeigt nur, was tatsächlich gemessen oder direkt beobachtet wurde.", MARGIN, PAGE_H - 56 * mm, 220 * mm, 20 * mm, size=20, color=sage, bold=True)

    gap = 8 * mm
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    y, h = 38 * mm, 88 * mm
    round_rect(c, MARGIN, y, card_w, h, sage, radius=5 * mm)
    round_rect(c, MARGIN + card_w + gap, y, card_w, h, orange, radius=5 * mm)
    paragraph(c, "GEPRÜFTE OBERFLÄCHEN", MARGIN + 7 * mm, y + h - 8 * mm, card_w - 14 * mm, 8 * mm, size=8, mono=True, color=ink)
    yy = y + h - 22 * mm
    for i, item in enumerate(model["coverage"]["tested"][:6]):
        paragraph(c, f"{i+1:02d}  {item['type']}", MARGIN + 7 * mm, yy - i * 10 * mm, card_w - 14 * mm, 9 * mm, size=9.5, color=ink, bold=(i == 0))
    paragraph(c, "NICHT ODER NUR TEILWEISE GEPRÜFT", MARGIN + card_w + gap + 7 * mm, y + h - 8 * mm, card_w - 14 * mm, 8 * mm, size=8, mono=True, color=ink)
    yy2 = y + h - 22 * mm
    for i, item in enumerate(model["coverage"]["not_tested"][:6]):
        paragraph(c, f"{i+1:02d}  {item}", MARGIN + card_w + gap + 7 * mm, yy2 - i * 10 * mm, card_w - 14 * mm, 9 * mm, size=9.5, color=ink)
    c.showPage()


def severity_style(severity: str, brand: dict[str, Any]) -> tuple[colors.Color, colors.Color, str]:
    p = brand["colors"]
    if severity == "critical":
        return hx(p["bad_surface"]), hx(p["bad"]), "KRITISCH"
    if severity == "high":
        return hx(p["warn_surface"]), hx("#8A5A08"), "HOCH"
    if severity == "medium":
        return hx(p["sage_raised"]), hx(p["ink"]), "MITTEL"
    if severity == "low":
        return hx(p["sage_raised"]), hx(p["ink_soft"]), "NIEDRIG"
    return hx(p["good_surface"]), hx(p["good"]), "STÄRKE"


def draw_finding_card(c: Canvas, finding: dict[str, Any], x: float, y: float, w: float, h: float, brand: dict[str, Any]) -> None:
    p = brand["colors"]
    ink, white = hx(p["ink"]), hx(p["white"])
    round_rect(c, x, y, w, h, white, stroke=hx(p["sage_line"]), radius=4 * mm)
    badge_fill, badge_text, badge_label = severity_style(finding.get("severity", "medium"), brand)
    round_rect(c, x + 7 * mm, y + h - 17 * mm, 24 * mm, 8.5 * mm, badge_fill, radius=3 * mm)
    paragraph(c, badge_label, x + 9 * mm, y + h - 11.4 * mm, 20 * mm, 5 * mm, size=6.8, mono=True, color=badge_text, bold=True)
    paragraph(c, finding["headline"], x + 36 * mm, y + h - 8 * mm, w - 43 * mm, 18 * mm, size=11.4, leading=14, color=ink, bold=True)

    label_w = 30 * mm
    blocks = [
        ("BEOBACHTUNG", finding["observation"]),
        ("WARUM DAS ZÄHLT", finding["impact"]),
        ("NÄCHSTER SCHRITT", finding["action"]),
    ]
    yy = y + h - 31 * mm
    for label, text in blocks:
        paragraph(c, label, x + 7 * mm, yy, label_w, 7 * mm, size=6.8, mono=True, color=hx("#475350"))
        paragraph(c, text, x + 37 * mm, yy + 1 * mm, w - 44 * mm, 20 * mm, size=10.3, leading=13, color=ink, bold=(label == "NÄCHSTER SCHRITT"))
        yy -= 23 * mm
    paragraph(c, f"Sicherheit {finding['confidence']}/5", x + 7 * mm, y + 10 * mm, w - 14 * mm, 6 * mm, size=6.5, mono=True, color=hx("#475350"))



def fmt_num(value: object) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return sanitize(value)
    if isinstance(value, float) and not value.is_integer():
        s = f"{value:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{int(value):,}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _chart_area() -> tuple[float, float, float, float]:
    return MARGIN + 5 * mm, 35 * mm, 180 * mm, 99 * mm


def _scale(values: list[float], lo: float | None = None, hi: float | None = None) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    mn = min(values) if lo is None else lo
    mx = max(values) if hi is None else hi
    if mx <= mn:
        mx = mn + 1.0
    pad = (mx - mn) * 0.08
    return min(0.0, mn - pad) if lo is None else mn, mx + pad if hi is None else mx


def _draw_axes(c: Canvas, x: float, y: float, w: float, h: float, ink: colors.Color, line: colors.Color) -> None:
    c.setStrokeColor(line); c.setLineWidth(0.5)
    c.line(x, y, x, y + h); c.line(x, y, x + w, y)


def _chart_v01(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); sage=hx(p['sage_line'])
    pts=v['data']['series']; vals=[float(q['value']) for q in pts]
    th=v.get('threshold'); ext=vals + ([float(th['value'])] if isinstance(th,dict) and isinstance(th.get('value'),(int,float)) else [])
    lo,hi=_scale(ext); _draw_axes(c,x,y,w,h,ink,sage)
    def py(n): return y+(float(n)-lo)/(hi-lo)*h
    prev=None
    for i,q in enumerate(pts):
        px=x+i*w/max(1,len(pts)-1); yy=py(q['value'])
        if prev: c.setStrokeColor(orange); c.setLineWidth(2); c.line(prev[0],prev[1],px,yy)
        c.setFillColor(orange); c.circle(px,yy,2*mm,stroke=0,fill=1)
        c.setFillColor(ink); c.setFont(FONT_MONO,6); c.drawCentredString(px,y-5*mm,sanitize(q.get('label'))[:12])
        prev=(px,yy)
    if isinstance(th,dict) and isinstance(th.get('value'),(int,float)):
        yy=py(th['value']); c.setStrokeColor(hx('#6D8A83')); c.setDash(3,2); c.line(x,yy,x+w,yy); c.setDash(); c.setFont(FONT_MONO,6); c.setFillColor(hx('#475350')); c.drawRightString(x+w,yy+2*mm,sanitize(th.get('label')))


def _chart_v02(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); line=hx(p['sage_line'])
    pts=v['data']['series']; bands=sorted(v['data']['bands'],key=lambda b:float(b['boundary'])); vals=[float(q['value']) for q in pts]+[float(b['boundary']) for b in bands]
    lo,hi=_scale(vals,0,None); fills=[hx(p['good_surface']),hx(p['warn_surface']),hx(p['bad_surface'])]
    prev=lo
    for idx,b in enumerate(bands):
        top=float(b['boundary']); yy=y+(prev-lo)/(hi-lo)*h; hh=(top-prev)/(hi-lo)*h
        c.setFillColor(fills[min(idx,2)]); c.rect(x,yy,w,hh,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_MONO,6)
        band_label=f"{sanitize(b.get('label'))} · {fmt_num(b.get('boundary'))} · {sanitize(b.get('source'))}"; c.drawString(x+2*mm,yy+2*mm,band_label[:68]); prev=top
    if prev<hi: c.setFillColor(fills[-1]); c.rect(x,y+(prev-lo)/(hi-lo)*h,w,(hi-prev)/(hi-lo)*h,stroke=0,fill=1)
    _draw_axes(c,x,y,w,h,ink,line)
    def py(n): return y+(float(n)-lo)/(hi-lo)*h
    prevp=None
    for i,q in enumerate(pts):
        px=x+i*w/max(1,len(pts)-1); yy=py(q['value'])
        if prevp: c.setStrokeColor(ink); c.setLineWidth(1.5); c.line(prevp[0],prevp[1],px,yy)
        if i==len(pts)-1: c.setFillColor(orange); c.circle(px,yy,2.3*mm,stroke=0,fill=1)
        c.setFillColor(ink); c.setFont(FONT_MONO,5.8); c.drawCentredString(px,y-5*mm,sanitize(q.get('label'))[:10]); prevp=(px,yy)


def _chart_v03(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); sage=hx('#52615E'); light=hx(p['sage_line']); data=v['data']
    groups=data['groups']; series=data['series']; vals=[float(n) for ser in series for n in ser['values']]; lo,hi=_scale(vals,0,None); header_h=9*mm; plot_h=h-header_h; _draw_axes(c,x,y,w,plot_h,ink,light)
    gw=w/len(groups); bw=gw/(len(series)+1.4); cols=[orange,ink,sage]
    c.setFillColor(ink); c.setFont(FONT_MONO,6.1); c.drawString(x,y+h-4*mm,f"EINHEIT: {sanitize(data.get('unit'))}")
    lx=x+42*mm
    for si,ser in enumerate(series):
        c.setFillColor(cols[si]); c.rect(lx+si*42*mm,y+h-6*mm,3*mm,3*mm,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_MONO,5.8); c.drawString(lx+4*mm+si*42*mm,y+h-5.5*mm,sanitize(ser.get('name'))[:18])
    for gi,g in enumerate(groups):
        for si,ser in enumerate(series):
            val=float(ser['values'][gi]); bh=(val-lo)/(hi-lo)*plot_h; bx=x+gi*gw+(si+0.35)*bw
            c.setFillColor(cols[si]); c.rect(bx,y,bw*0.78,bh,stroke=0,fill=1)
        c.setFillColor(ink); c.setFont(FONT_MONO,5.5); c.drawCentredString(x+(gi+.5)*gw,y-5*mm,sanitize(g)[:13])


def _chart_v04(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); sage=hx(p['sage_line'])
    rows=v['data']['rows']; mx=max(float(r['value']) for r in rows) or 1; rh=h/len(rows)
    for i,r in enumerate(rows):
        yy=y+h-(i+0.72)*rh; c.setFillColor(sage); c.roundRect(x+52*mm,yy-2.5*mm,w-62*mm,5*mm,2.5*mm,stroke=0,fill=1)
        c.setFillColor(orange if i==0 else ink); c.roundRect(x+52*mm,yy-2.5*mm,(w-62*mm)*float(r['value'])/mx,5*mm,2.5*mm,stroke=0,fill=1)
        c.setFillColor(ink); c.setFont(FONT,7.5); c.drawString(x,yy-2*mm,sanitize(r.get('label'))[:28]); c.setFont(FONT_MONO,7); c.drawRightString(x+w,yy-2*mm,fmt_num(r['value']))


def _chart_v05(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); classes=v['data']['classes']; rows=v['data']['rows']; fills=[hx(p['good']),hx(p['warn']),hx(p['bad']),hx('#566360')]; header_h=9*mm
    status_fill={'good':hx(p['good']),'warn':hx(p['warn']),'bad':hx(p['bad']),'context':hx('#566360')}; fills=[status_fill.get(cobj.get('status'),hx('#566360')) for cobj in classes]
    lx=x
    for ci,cobj in enumerate(classes):
        c.setFillColor(fills[ci]); c.rect(lx,y+h-6*mm,3*mm,3*mm,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_MONO,5.8); c.drawString(lx+4*mm,y+h-5.5*mm,sanitize(cobj.get('name'))[:15]); lx+=34*mm
    rh=(h-header_h)/max(1,len(rows));
    for ri,r in enumerate(rows):
        yy=y+h-header_h-(ri+0.62)*rh; c.setFillColor(ink); c.setFont(FONT_BOLD,8); c.drawString(x,yy+4*mm,sanitize(r.get('label'))[:26]); xx=x
        for ci,val in enumerate(r['values']):
            ww=w*float(val)/100; c.setFillColor(fills[ci]); c.rect(xx,yy-3*mm,ww,7*mm,stroke=0,fill=1); xx+=ww
        xx=x
        for val in r['values']:
            ww=w*float(val)/100; c.setFillColor(ink); c.setFont(FONT_MONO,5.5); c.drawCentredString(xx+ww/2,yy-6*mm,f"{fmt_num(val)} %"); xx+=ww


def _chart_v06(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); sage=hx('#566360'); light=hx(p['sage_line']); white=hx(p['white']); cols=[orange,ink,sage,light]
    parts=v['data']['parts']; total=float(v['data']['sum']) or sum(float(q['value']) for q in parts) or 1; cx=x+45*mm; cy=y+h/2; r=min(30*mm,h*.38); start=90
    for i,q in enumerate(parts):
        ext=360*float(q['value'])/total; c.setFillColor(cols[i]); c.wedge(cx-r,cy-r,cx+r,cy+r,start,-ext,stroke=0,fill=1); start-=ext
    c.setFillColor(white); c.circle(cx,cy,r*.58,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_BOLD,15); c.drawCentredString(cx,cy+1*mm,fmt_num(v['data']['sum'])); c.setFont(FONT_MONO,6); c.drawCentredString(cx,cy-5*mm,sanitize(v['data'].get('unit','')))
    yy=y+h-12*mm; unit=sanitize(v['data'].get('unit',''))
    for i,q in enumerate(parts):
        pct=100*float(q['value'])/total; c.setFillColor(cols[i]); c.rect(x+88*mm,yy-i*13*mm,4*mm,4*mm,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT,8); c.drawString(x+95*mm,yy-i*13*mm,sanitize(q.get('label'))[:24]); c.setFont(FONT_MONO,7); c.drawRightString(x+w,yy-i*13*mm,f"{fmt_num(q['value'])} {unit} · {fmt_num(pct)} %")


def _chart_v07(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); light=hx(p['sage_line'])
    val=float(v['data']['value']); cx=x+42*mm; cy=y+h/2; r=27*mm
    c.setStrokeColor(light); c.setLineWidth(8*mm); c.circle(cx,cy,r,stroke=1,fill=0); c.setStrokeColor(orange); c.setLineCap(1); c.arc(cx-r,cy-r,cx+r,cy+r,90,-360*val/100); c.setLineWidth(1); c.setFillColor(ink); c.setFont(FONT_BOLD,22); c.drawCentredString(cx,cy,fmt_num(val)); c.setFont(FONT_MONO,7); c.drawCentredString(cx,cy-6*mm,'/ 100')
    yy=y+h-18*mm
    for i,t in enumerate(v['data']['tiles']):
        c.setFillColor(ink); c.setFont(FONT_BOLD,13); c.drawString(x+86*mm,yy-i*25*mm,sanitize(t.get('value'))); c.setFont(FONT,8); c.drawString(x+86*mm,yy-6*mm-i*25*mm,sanitize(t.get('label'))[:42])


def _chart_v08(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); sage=hx('#879995'); line=hx(p['sage_line']); data=v['data']; pts=data['points']; xs=[float(q['x']) for q in pts]; ys=[float(q['y']) for q in pts]; rs=[float(q['r']) for q in pts]; xmin,xmax=_scale(xs); ymin,ymax=_scale(ys); rmax=max(rs) or 1
    # Reserve a little space inside the chart for axis and radius legends. This follows the V08 source contract: both axes and the bubble-area legend are mandatory.
    plot_x=x+9*mm; plot_y=y+9*mm; plot_w=w-13*mm; plot_h=h-15*mm; _draw_axes(c,plot_x,plot_y,plot_w,plot_h,ink,line)
    x_axis=data['x_axis']; y_axis=data['y_axis']
    x_label=sanitize(x_axis.get('name','')) + (f" · {sanitize(x_axis.get('unit',''))}" if sanitize(x_axis.get('unit','')) else '')
    y_label=sanitize(y_axis.get('name','')) + (f" · {sanitize(y_axis.get('unit',''))}" if sanitize(y_axis.get('unit','')) else '')
    c.setFillColor(ink); c.setFont(FONT_MONO,6.2); c.drawCentredString(plot_x+plot_w/2,y+1.5*mm,x_label[:50])
    c.saveState(); c.translate(x+2.5*mm,plot_y+plot_h/2); c.rotate(90); c.drawCentredString(0,0,y_label[:45]); c.restoreState()
    c.setFont(FONT_MONO,5.8); c.drawRightString(plot_x+plot_w,plot_y+plot_h+2.2*mm,sanitize(data.get('radius_legend'))[:55])
    for i,q in enumerate(pts):
        px=plot_x+(float(q['x'])-xmin)/(xmax-xmin)*plot_w; py=plot_y+(float(q['y'])-ymin)/(ymax-ymin)*plot_h; rr=(3+8*float(q['r'])/rmax)*mm
        # Keep large bubbles inside the plotting box so their labels cannot clip at page edges.
        px=max(plot_x+rr,min(plot_x+plot_w-rr,px)); py=max(plot_y+rr,min(plot_y+plot_h-rr,py))
        c.setFillColor(orange if i==0 else sage); c.circle(px,py,rr,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_MONO,5.8); c.drawCentredString(px,py+rr+1*mm,sanitize(q.get('label'))[:18])


def _chart_v09(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); line=hx(p['sage_line']); axes=v['data']['axes']; nets=v['data']['nets']; sc=v['data']['scale']; lo=float(sc['min']); hi=float(sc['max']); cx=x+w/2; cy=y+h/2-2*mm; r=min(w,h)*.34; n=len(axes)
    c.setFillColor(ink); c.setFont(FONT_MONO,6.0); c.drawString(x,y+h-4*mm,f"SKALA {fmt_num(lo)}–{fmt_num(hi)}")
    cols=[orange,ink]
    lx=x+38*mm
    for ni,net in enumerate(nets):
        c.setFillColor(cols[ni]); c.rect(lx+ni*48*mm,y+h-6*mm,3*mm,3*mm,stroke=0,fill=1); c.setFillColor(ink); c.drawString(lx+4*mm+ni*48*mm,y+h-5.5*mm,sanitize(net.get('name'))[:22])
    import math as _m
    for ring in range(1,5):
        rr=r*ring/4; path=c.beginPath();
        for i in range(n):
            a=_m.pi/2-2*_m.pi*i/n; px=cx+rr*_m.cos(a); py=cy+rr*_m.sin(a); path.moveTo(px,py) if i==0 else path.lineTo(px,py)
        path.close(); c.setStrokeColor(line); c.drawPath(path,stroke=1,fill=0)
    for i,aobj in enumerate(axes):
        a=_m.pi/2-2*_m.pi*i/n; px=cx+r*_m.cos(a); py=cy+r*_m.sin(a); c.setStrokeColor(line); c.line(cx,cy,px,py); c.setFillColor(ink); c.setFont(FONT_MONO,5.5); c.drawCentredString(cx+(r+9*mm)*_m.cos(a),cy+(r+9*mm)*_m.sin(a),sanitize(aobj.get('label'))[:14])
    for ni,net in enumerate(nets):
        path=c.beginPath();
        for i,val in enumerate(net['values']):
            a=_m.pi/2-2*_m.pi*i/n; rr=r*(float(val)-lo)/(hi-lo); px=cx+rr*_m.cos(a); py=cy+rr*_m.sin(a); path.moveTo(px,py) if i==0 else path.lineTo(px,py)
        path.close(); c.setStrokeColor(cols[ni]); c.setLineWidth(2); c.drawPath(path,stroke=1,fill=0)


def _chart_v10(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); line=hx(p['sage_line']); data=v['data']; rows=data['rows']; vals=[float(r[k]) for r in rows for k in ('value_a','value_b')]; lo,hi=_scale(vals,0,None); header_h=10*mm; rh=(h-header_h)/len(rows)
    comp=data['comparison']; c.setFillColor(ink); c.setFont(FONT_MONO,6.2); c.drawString(x,y+h-4*mm,f"VERGLEICH: {sanitize(comp.get('definition'))[:55]} · n = {comp.get('n')}")
    for i,r in enumerate(rows):
        yy=y+h-header_h-(i+.5)*rh; c.setStrokeColor(line); c.setLineWidth(4); c.line(x+62*mm,yy,x+w-24*mm,yy)
        def px(n): return x+62*mm+(float(n)-lo)/(hi-lo)*(w-86*mm)
        c.setFillColor(orange); c.circle(px(r['value_a']),yy,2.2*mm,stroke=0,fill=1); c.setFillColor(ink); c.circle(px(r['value_b']),yy,1.8*mm,stroke=0,fill=1); c.setFont(FONT,7.5); c.drawString(x,yy-2*mm,sanitize(r.get('label'))[:30]); c.setFont(FONT_MONO,6.5); c.drawRightString(x+w,yy-2*mm,f"{fmt_num(r['value_a'])} / {fmt_num(r['value_b'])} {sanitize(r.get('unit',''))}")


def _chart_v11(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); orange=hx(p['orange']); line=hx(p['sage_line']); data=v['data']; bins=data['classes']; mx=max(int(q['n']) for q in bins) or 1; header_h=9*mm; plot_h=h-header_h; _draw_axes(c,x,y,w,plot_h,ink,line); bw=w/len(bins)*.68
    c.setFillColor(ink); c.setFont(FONT_MONO,6.2); c.drawRightString(x+w,y+h-4*mm,f"n = {data['total_n']} · Median {fmt_num(data['median'])}")
    for i,q in enumerate(bins):
        bh=plot_h*int(q['n'])/mx; bx=x+(i+.16)*w/len(bins); c.setFillColor(orange if i>=len(bins)-2 else ink); c.rect(bx,y,bw,bh,stroke=0,fill=1); c.setFillColor(ink); c.setFont(FONT_MONO,5.8); c.drawCentredString(bx+bw/2,y-5*mm,sanitize(q.get('label'))[:8]); c.drawCentredString(bx+bw/2,y+bh+2*mm,str(q['n']))


def _chart_v12(c: Canvas, v: dict[str, Any], box: tuple[float,float,float,float], brand: dict[str,Any]) -> None:
    x,y,w,h=box; p=brand['colors']; ink=hx(p['ink']); sage=hx(p['sage_raised']); line=hx(p['sage_line']); rows=v['data']['rows']; cols=[44,28,44,22,42]; scale=w/sum(cols); widths=[q*scale for q in cols]; rh=h/(len(rows)+1); heads=['MESSKONZEPT','WERT','SCHWELLE · HERKUNFT','EVIDENZ','BEWEIST NICHT']; c.setFillColor(sage); c.rect(x,y+h-rh,w,rh,stroke=0,fill=1); xx=x
    for ww,head in zip(widths,heads): paragraph(c,head,xx+2*mm,y+h-2.5*mm,ww-4*mm,rh-2*mm,size=5.8,mono=True,color=ink); xx+=ww
    for ri,r in enumerate(rows):
        yy=y+h-(ri+2)*rh; c.setStrokeColor(line); c.line(x,yy,x+w,yy); vals=[r['metric'],r['value'],r['threshold_origin'],r['evidence'],r['does_not_prove']]; xx=x
        for ww,val in zip(widths,vals): paragraph(c,val,xx+2*mm,yy+rh-2*mm,ww-4*mm,rh-3*mm,size=6.5,leading=7.7,color=ink,mono=(ww<35*mm)); xx+=ww


_CHART_DRAWERS={'V01':_chart_v01,'V02':_chart_v02,'V03':_chart_v03,'V04':_chart_v04,'V05':_chart_v05,'V06':_chart_v06,'V07':_chart_v07,'V08':_chart_v08,'V09':_chart_v09,'V10':_chart_v10,'V11':_chart_v11,'V12':_chart_v12}


def draw_visualizations(c: Canvas, model: dict[str, Any], brand: dict[str, Any], start_page: int) -> int:
    p=brand['colors']; sage=hx(p['sage']); ink=hx(p['ink']); white=hx(p['white']); orange=hx(p['orange']); line=hx(p['sage_line']); page=start_page
    for v in model.get('visualizations',[]):
        new_page(c,sage,model['meta'],page)
        metrics=' · '.join(v.get('metric_refs',[])[:4])
        draw_eyebrow(c,f"{v.get('template_id')} · {sanitize(v.get('category')).upper()} · {metrics}",MARGIN,PAGE_H-38*mm,PAGE_W-2*MARGIN,ink)
        paragraph(c,v.get('title',''),MARGIN,PAGE_H-56*mm,PAGE_W-2*MARGIN,19*mm,size=17.5,leading=21,color=ink,bold=True)
        bx,by,bw,bh=_chart_area(); round_rect(c,bx-5*mm,by-7*mm,bw+10*mm,bh+17*mm,white,stroke=line,radius=2*mm)
        paragraph(c,v.get('metric_label',''),bx,by+bh+7*mm,bw,6*mm,size=6.8,mono=True,color=hx('#475350'))
        if v.get('current_value_label'): paragraph(c,v.get('current_value_label'),bx+bw-38*mm,by+bh+8*mm,38*mm,8*mm,size=12,mono=True,color=orange,bold=True)
        _CHART_DRAWERS[v['template_id']](c,v,(bx,by,bw,bh),brand)
        rx=bx+bw+12*mm; rw=PAGE_W-MARGIN-rx
        round_rect(c,rx,by+54*mm,rw,45*mm,white,stroke=line,radius=2*mm); paragraph(c,'EVIDENZ',rx+5*mm,by+93*mm,rw-10*mm,6*mm,size=6.5,mono=True,color=ink)
        ev=v['evidence']; evline=f"{ev['grade']} · {ev['mode']} · {ev['scope']} · {ev['population']} · {ev['tool']} {ev.get('version','')} · {ev['date']}"; paragraph(c,evline,rx+5*mm,by+83*mm,rw-10*mm,27*mm,size=7.2,leading=9,color=ink)
        th=v.get('threshold'); tlabel=sanitize(th.get('label'))+' · '+sanitize(th.get('source')) if isinstance(th,dict) else 'NONE_OFFICIAL / keine belegte Schwelle'; round_rect(c,rx,by+32*mm,rw,18*mm,hx(p['sage_raised']),radius=2*mm); paragraph(c,'SCHWELLE',rx+5*mm,by+45*mm,rw-10*mm,5*mm,size=6,mono=True,color=ink); paragraph(c,tlabel,rx+5*mm,by+39*mm,rw-10*mm,8*mm,size=6.8,color=ink)
        round_rect(c,rx,by-7*mm,rw,34*mm,hx(p['bad_surface']),radius=2*mm); paragraph(c,'BEWEIST NICHT',rx+5*mm,by+21*mm,rw-10*mm,5*mm,size=6.2,mono=True,color=ink,bold=True); paragraph(c,v.get('does_not_prove',''),rx+5*mm,by+14*mm,rw-10*mm,18*mm,size=7.2,leading=9,color=ink)
        c.showPage(); page+=1
    return page

def draw_findings(c: Canvas, model: dict[str, Any], brand: dict[str, Any], start_page: int) -> int:
    findings = model.get("findings", [])
    p = brand["colors"]
    sage, ink, orange = hx(p["sage"]), hx(p["ink"]), hx(p["orange"])
    page_no = start_page
    for page_idx in range(max(1, math.ceil(len(findings) / 2))):
        bg = sage if page_idx % 2 == 0 else orange
        new_page(c, bg, model["meta"], page_no)
        draw_eyebrow(c, f"{page_no:02d} · PRIORISIERTE BEFUNDE", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
        paragraph(c, "Die wichtigsten Punkte zuerst. Kurz erkl\u00e4rt und direkt l\u00f6sbar.", MARGIN, PAGE_H - 56 * mm, 220 * mm, 19 * mm, size=17.5, leading=21, color=ink, bold=True)
        chunk = findings[page_idx * 2 : page_idx * 2 + 2]
        if not chunk:
            paragraph(c, "Keine priorisierten Schwachstellen im geprüften Umfang.", MARGIN, PAGE_H - 90 * mm, 220 * mm, 20 * mm, size=18, color=ink, bold=True)
        else:
            gap = 8 * mm
            card_w = (PAGE_W - 2 * MARGIN - gap) / 2
            for i, finding in enumerate(chunk):
                draw_finding_card(c, finding, MARGIN + i * (card_w + gap), 30 * mm, card_w, 108 * mm, brand)
        c.showPage()
        page_no += 1
    return page_no


def draw_search_ai(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    sage, ink, white, orange = hx(p["sage_raised"]), hx(p["ink"]), hx(p["white"]), hx(p["orange"])
    new_page(c, sage, model["meta"], page_no)
    draw_eyebrow(c, f"{page_no:02d} · SUCH- UND KI-VERSTÄNDLICHKEIT", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
    paragraph(c, "Gefunden werden und verstanden werden sind zwei verschiedene Aufgaben.", MARGIN, PAGE_H - 56 * mm, 220 * mm, 19 * mm, size=18.5, leading=22, color=ink, bold=True)

    cats = {x.get("category"): x for x in model.get("categories", [])}
    pairs = [
        ("Auffindbarkeit & SEO", cats.get("findability_seo", {}), white),
        ("KI-Verständlichkeit", cats.get("ai_readiness", {}), orange),
    ]
    gap = 8 * mm
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    for i, (label, data, fill) in enumerate(pairs):
        x = MARGIN + i * (card_w + gap)
        y, h = 48 * mm, 80 * mm
        round_rect(c, x, y, card_w, h, fill, stroke=hx(p["sage_line"]) if fill == white else None, radius=5 * mm)
        paragraph(c, label, x + 8 * mm, y + h - 10 * mm, card_w - 16 * mm, 10 * mm, size=12, color=ink, bold=True)
        c.setFillColor(ink)
        c.setFont(FONT_BOLD, 34)
        c.drawString(x + 8 * mm, y + 39 * mm, "-" if data.get("score") is None else str(data.get("score")))
        paragraph(c, f"Coverage {data.get('coverage', 0)}% · {data.get('confidence', 'LOW')}", x + 8 * mm, y + 31 * mm, card_w - 16 * mm, 7 * mm, size=7, mono=True, color=ink)
        paragraph(c, data.get("summary", ""), x + 8 * mm, y + 24 * mm, card_w - 16 * mm, 18 * mm, size=10.5, color=ink)
        cat_findings = [f for f in model.get("findings", []) if f.get("category") == data.get("category")]
        if cat_findings:
            paragraph(c, cat_findings[0].get("action", ""), x + 8 * mm, y + 10 * mm, card_w - 16 * mm, 12 * mm, size=9, color=ink, bold=True)
    c.showPage()


def draw_roadmap(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    sage, ink, white, orange = hx(p["sage"]), hx(p["ink"]), hx(p["white"]), hx(p["orange"])
    new_page(c, sage, model["meta"], page_no)
    draw_eyebrow(c, f"{page_no:02d} · ROADMAP", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
    paragraph(c, "Nicht alles gleichzeitig. Erst die Hebel, die den größten Unterschied machen.", MARGIN, PAGE_H - 56 * mm, 235 * mm, 19 * mm, size=18.5, leading=22, color=ink, bold=True)

    labels = [("JETZT", "now", white), ("NÄCHSTE 30 TAGE", "next_30_days", orange), ("DANACH IM QUARTAL", "next_quarter", white)]
    gap = 7 * mm
    card_w = (PAGE_W - 2 * MARGIN - 2 * gap) / 3
    y, h = 34 * mm, 96 * mm
    for i, (label, key, fill) in enumerate(labels):
        x = MARGIN + i * (card_w + gap)
        round_rect(c, x, y, card_w, h, fill, stroke=hx(p["sage_line"]) if fill == white else None, radius=4 * mm)
        paragraph(c, label, x + 7 * mm, y + h - 10 * mm, card_w - 14 * mm, 8 * mm, size=7.5, mono=True, color=ink)
        yy = y + h - 25 * mm
        items = model["roadmap"].get(key, [])
        if not items:
            paragraph(c, "Keine priorisierte Maßnahme in diesem Zeitfenster.", x + 7 * mm, yy, card_w - 14 * mm, 25 * mm, size=10, color=ink)
        for j, item in enumerate(items[:3], 1):
            paragraph(c, f"{item['priority']} · {item['action']}", x + 7 * mm, yy - (j - 1) * 23 * mm, card_w - 14 * mm, 20 * mm, size=10.2, leading=12.8, color=ink, bold=(j == 1))
    c.showPage()


def draw_recommendation(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    ink, sage, orange = hx(p["ink"]), hx(p["sage_raised"]), hx(p["orange"])
    new_page(c, ink, model["meta"], page_no)
    draw_eyebrow(c, f"{page_no:02d} · EMPFEHLUNG", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, sage, on_dark=True)
    paragraph(c, model["recommendation"]["route"], MARGIN, PAGE_H - 62 * mm, 220 * mm, 28 * mm, size=28, color=sage, bold=True)
    round_rect(c, MARGIN, 58 * mm, PAGE_W - 2 * MARGIN, 58 * mm, orange, radius=5 * mm)
    paragraph(c, "WARUM", MARGIN + 9 * mm, 105 * mm, 30 * mm, 7 * mm, size=7.5, mono=True, color=ink)
    paragraph(c, model["recommendation"]["reason"], MARGIN + 45 * mm, 108 * mm, PAGE_W - 2 * MARGIN - 54 * mm, 21 * mm, size=13, color=ink, bold=True)
    paragraph(c, "NÄCHSTER SCHRITT", MARGIN + 9 * mm, 77 * mm, 35 * mm, 7 * mm, size=7.5, mono=True, color=ink)
    paragraph(c, model["recommendation"]["next_step"], MARGIN + 45 * mm, 80 * mm, PAGE_W - 2 * MARGIN - 54 * mm, 18 * mm, size=12, color=ink)
    paragraph(c, "Die Empfehlung ist eine Diagnoseentscheidung auf Basis des geprüften Umfangs - kein Verkaufszwang zu einem Relaunch.", MARGIN, 34 * mm, PAGE_W - 2 * MARGIN, 12 * mm, size=9.5, color=sage)
    c.showPage()


def compact_text(value: object, limit: int) -> str:
    text = sanitize(value)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def metric_value_text(item: dict[str, Any]) -> str:
    value = item.get("value")
    unit = item.get("unit")
    if value is None:
        return "-"
    return compact_text(f"{value} {unit or ''}".strip(), 48)


def draw_appendix_metrics(c: Canvas, model: dict[str, Any], brand: dict[str, Any], start_page: int) -> int:
    p = brand["colors"]
    white, ink, sage = hx(p["white"]), hx(p["ink"]), hx(p["sage_raised"])
    metrics = model["appendix"].get("metrics", [])
    per_page = 9
    page_no = start_page
    for idx in range(max(1, math.ceil(len(metrics) / per_page))):
        new_page(c, white, model["meta"], page_no)
        draw_eyebrow(c, f"{page_no:02d} · TECHNISCHER ANHANG", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
        paragraph(c, "Metriken, Evidenzklasse und Grenzen.", MARGIN, PAGE_H - 56 * mm, 220 * mm, 14 * mm, size=17, color=ink, bold=True)
        chunk = metrics[idx * per_page : idx * per_page + per_page]
        y = PAGE_H - 82 * mm
        row_h = 11.5 * mm
        # header
        c.setFillColor(sage)
        c.rect(MARGIN, y, PAGE_W - 2 * MARGIN, row_h, stroke=0, fill=1)
        cols = [18, 68, 27, 18, 22, 42, 62]
        x = MARGIN
        heads = ["ID", "METRIK", "KLASSE", "EVIDENZ", "SCORE", "WERT", "METHODE / GRENZE"]
        for ww, head in zip(cols, heads):
            paragraph(c, head, x + 2 * mm, y + 6.6 * mm, ww * mm - 4 * mm, 5 * mm, size=6.3, mono=True, color=ink)
            x += ww * mm
        y -= row_h
        for item in chunk:
            c.setStrokeColor(hx(p["sage_line"]))
            c.setLineWidth(0.25)
            c.line(MARGIN, y, PAGE_W - MARGIN, y)
            values = [
                item.get("id"), item.get("label"), item.get("measurement_class"), item.get("evidence_grade"),
                "-" if item.get("score") is None else item.get("score"), metric_value_text(item),
                compact_text(f"{item.get('source_or_method','')} · {item.get('does_not_prove','')}", 115),
            ]
            x = MARGIN
            for ww, value in zip(cols, values):
                paragraph(c, value, x + 2 * mm, y + 9.5 * mm, ww * mm - 4 * mm, 9.5 * mm, size=6.2, leading=7.7, color=ink, mono=(ww in {18,22,27}))
                x += ww * mm
            y -= row_h
        c.showPage()
        page_no += 1
    return page_no



def draw_appendix_sources(c: Canvas, model: dict[str, Any], brand: dict[str, Any], start_page: int) -> int:
    p = brand["colors"]
    white, ink, sage = hx(p["white"]), hx(p["ink"]), hx(p["sage_raised"])
    sources = model["appendix"].get("sources", [])
    per_page = 7
    page_no = start_page
    pages = max(1, math.ceil(len(sources) / per_page))
    for idx in range(pages):
        new_page(c, white, model["meta"], page_no)
        draw_eyebrow(c, f"{page_no:02d} · QUELLEN & METHODEN", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
        paragraph(c, "Nachvollziehbar statt behauptet: Woher die Aussagen im Bericht kommen.", MARGIN, PAGE_H - 56 * mm, 235 * mm, 19 * mm, size=17.5, leading=21, color=ink, bold=True)
        chunk = sources[idx * per_page : idx * per_page + per_page]
        if not chunk:
            chunk = [{"id": "-", "type": "-", "title": "Keine zusätzlichen Quellen im Reportmodell dokumentiert.", "location": "-", "purpose": "-"}]
        y = PAGE_H - 84 * mm
        for item in chunk:
            round_rect(c, MARGIN, y - 18 * mm, PAGE_W - 2 * MARGIN, 17 * mm, sage, radius=3 * mm)
            paragraph(c, f"{item.get('id','-')} · {str(item.get('type','-')).upper()}", MARGIN + 5 * mm, y - 3 * mm, 43 * mm, 6 * mm, size=6.5, mono=True, color=ink)
            paragraph(c, compact_text(item.get('title',''), 95), MARGIN + 50 * mm, y - 1.5 * mm, 95 * mm, 7 * mm, size=8.4, color=ink, bold=True)
            paragraph(c, compact_text(item.get('location',''), 120), MARGIN + 148 * mm, y - 1.5 * mm, 78 * mm, 7 * mm, size=6.8, mono=True, color=ink)
            paragraph(c, compact_text(item.get('purpose',''), 110), MARGIN + 228 * mm, y - 1.5 * mm, PAGE_W - MARGIN - (MARGIN + 228 * mm), 12 * mm, size=7.3, leading=8.8, color=ink)
            y -= 19.5 * mm
        c.showPage()
        page_no += 1
    return page_no

def draw_client_limits(c: Canvas, model: dict[str, Any], brand: dict[str, Any], page_no: int) -> None:
    p = brand["colors"]
    sage, ink, white, orange = hx(p["sage"]), hx(p["ink"]), hx(p["white"]), hx(p["orange"])
    new_page(c, sage, model["meta"], page_no)
    draw_eyebrow(c, f"{page_no:02d} · MESSBASIS & GRENZEN", MARGIN, PAGE_H - 38 * mm, PAGE_W - 2 * MARGIN, ink)
    paragraph(c, "Was wir sicher sagen k\u00f6nnen - und welche Messungen f\u00fcr mehr Sicherheit noch fehlen.", MARGIN, PAGE_H - 56 * mm, 235 * mm, 19 * mm, size=17.5, leading=21, color=ink, bold=True)

    gap = 7 * mm
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    y, h = 42 * mm, 82 * mm
    round_rect(c, MARGIN, y, card_w, h, white, stroke=hx(p["sage_line"]), radius=4 * mm)
    round_rect(c, MARGIN + card_w + gap, y, card_w, h, orange, radius=4 * mm)
    paragraph(c, "DAS BEWEIST DIE ANALYSE NICHT", MARGIN + 7 * mm, y + h - 9 * mm, card_w - 14 * mm, 7 * mm, size=7.5, mono=True, color=ink)
    yy = y + h - 23 * mm
    limits = list(model.get("client_limits", {}).get("limitations", []))
    if not limits:
        limits = ["Keine weitergehenden Wirkungs- oder Rechtsaussagen aus dem gepr\u00fcften Umfang ableiten."]
    for i, text in enumerate(limits[:5], 1):
        paragraph(c, f"{i:02d}  {text}", MARGIN + 7 * mm, yy - (i - 1) * 12 * mm, card_w - 14 * mm, 10 * mm, size=8.8, color=ink)

    paragraph(c, "FUER MEHR SICHERHEIT NOCH OFFEN", MARGIN + card_w + gap + 7 * mm, y + h - 9 * mm, card_w - 14 * mm, 7 * mm, size=7.5, mono=True, color=ink)
    open_items = list(model.get("client_limits", {}).get("open_evidence", []))
    if not open_items:
        open_items = ["Keine zus\u00e4tzlichen Messungen f\u00fcr die priorisierten Aussagen erforderlich."]
    yy2 = y + h - 23 * mm
    for i, text in enumerate(open_items[:5], 1):
        paragraph(c, f"{i:02d}  {text}", MARGIN + card_w + gap + 7 * mm, yy2 - (i - 1) * 12 * mm, card_w - 14 * mm, 10 * mm, size=8.8, color=ink)
    c.showPage()

def render(model: dict[str, Any], output: Path, brand: dict[str, Any]) -> None:
    story = model.get("client_story", {}) if isinstance(model.get("client_story"), dict) else {}
    real_charts = [v for v in model.get("visualizations", []) if isinstance(v, dict) and str(v.get("template_id", "")) in {f"V{i:02d}" for i in range(1, 12)}]
    if story.get("visual_story_status") != "PASS" or not (2 <= len(real_charts) <= 3):
        raise ValueError("customer PDF requires a PASS visual story with two to three V01-V11 charts")
    if len(model.get("findings", [])) > 4:
        raise ValueError("customer PDF may contain at most four prioritized findings")
    projected_pages = 4 + len(real_charts) + max(1, math.ceil(len(model.get("findings", [])) / 2)) + 3
    if projected_pages > int(story.get("max_customer_pages", 12)):
        raise ValueError(f"customer PDF page budget exceeded: projected {projected_pages}")

    output.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(output), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(f"Pixelkiez Website-Analyse - {sanitize(model['meta'].get('customer'))}")
    c.setAuthor("Pixelkiez")
    c.setSubject("Pixelkiez customer website diagnosis - concise improvement levers and visual evidence")

    page = 1
    draw_cover(c, model, brand, page); page += 1
    draw_exec(c, model, brand, page); page += 1
    draw_categories(c, model, brand, page); page += 1
    draw_coverage(c, model, brand, page); page += 1
    page = draw_visualizations(c, model, brand, page)
    page = draw_findings(c, model, brand, page)
    draw_roadmap(c, model, brand, page); page += 1
    draw_recommendation(c, model, brand, page); page += 1
    draw_client_limits(c, model, brand, page)
    c.save()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("FAIL: usage: render_diagnosis_pdf.py <client-report-model.json> <output.pdf>", file=sys.stderr)
        return 1
    try:
        model = load(Path(argv[1]))
        brand = load(BRAND_PATH)
        render(model, Path(argv[2]), brand)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: rendered {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
