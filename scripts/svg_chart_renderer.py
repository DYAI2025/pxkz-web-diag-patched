#!/usr/bin/env python3
"""Deterministic SVG fallback renderer for the approved Pixelkiez visual template set.

The fallback exists so a missing Node/Vega/Mermaid runtime can never silently collapse a
customer presentation into chartless text. It uses only approved template IDs, explicit
Pixelkiez brand tokens, readable type sizes and no truncation markers.
"""
from __future__ import annotations

import html
import textwrap
from typing import Any

W, H = 900, 480
INK = "#0E1414"
ORANGE = "#EC5E43"
SAGE_RAISED = "#C6D4D1"
SAGE_LINE = "#566360"
WHITE = "#FFFFFF"
WARN = "#F59E0B"
BAD_SURFACE = "#FBE3DE"
WARN_SURFACE = "#FBF0DC"
GOOD_SURFACE = "#E4F4EB"
FONT = "PixelkiezDisplay, Schibsted Grotesk, IBM Plex Sans, Noto Sans, DejaVu Sans, sans-serif"
MONO = "PixelkiezData, IBM Plex Mono, Noto Sans Mono, DejaVu Sans Mono, monospace"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def clean(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if "…" in text or "..." in text:
        raise ValueError(f"truncation marker is forbidden in visual text: {text!r}")
    return text


def wrapped(value: Any, width: int, max_lines: int, field: str) -> list[str]:
    text = clean(value)
    if not text:
        return [""]
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) > max_lines:
        raise ValueError(f"{field} needs {len(lines)} lines; maximum is {max_lines}. Rewrite the source text instead of truncating it.")
    return lines


def text_block(
    x: float,
    y: float,
    value: Any,
    *,
    width: int,
    max_lines: int,
    font_family: str = FONT,
    font_size: float = 14,
    line_height: float | None = None,
    fill: str = INK,
    weight: int | None = None,
    anchor: str | None = None,
) -> str:
    lines = wrapped(value, width, max_lines, "SVG text")
    attrs = [f'x="{x}"', f'y="{y}"', f'font-family="{font_family}"', f'font-size="{font_size}"', f'fill="{fill}"']
    if weight is not None:
        attrs.append(f'font-weight="{weight}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    lh = line_height or font_size * 1.18
    tspans = []
    for idx, line in enumerate(lines):
        dy = "0" if idx == 0 else f"{lh}"
        tspans.append(f'<tspan x="{x}" dy="{dy}">{esc(line)}</tspan>')
    return f'<text {" ".join(attrs)}>{"".join(tspans)}</text>'


def svg_open(title: str, subtitle: str) -> list[str]:
    title_lines = wrapped(title, 58, 2, "visual title")
    title_svg = text_block(42, 46, title, width=58, max_lines=2, font_size=24, line_height=27, weight=700)
    subtitle_y = 78 if len(title_lines) == 1 else 102
    subtitle_svg = text_block(42, subtitle_y, subtitle, width=102, max_lines=1, font_size=14.5, fill=SAGE_LINE)
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(clean(title))}">',
        f'<rect width="{W}" height="{H}" rx="18" fill="{WHITE}"/>',
        title_svg,
        subtitle_svg,
    ]


def footer(lines: list[str], visual: dict[str, Any]) -> None:
    # Customer SVGs must not expose audit population, method or limitation boilerplate.
    # Those boundaries remain in visualization-plan.json and render receipts for internal traceability.
    lines += [
        f'<line x1="42" y1="407" x2="858" y2="407" stroke="{SAGE_RAISED}"/>',
        '</svg>',
    ]

def max_value(rows: list[dict[str, Any]], field: str, default: float = 100.0) -> float:
    vals = [float(x[field]) for x in rows if isinstance(x.get(field), (int, float)) and not isinstance(x.get(field), bool)]
    return max(vals) if vals else default


def horizontal_bars(lines: list[str], rows: list[dict[str, Any]], label_field: str, value_field: str, domain: float | None = None) -> None:
    rows = rows[:8]
    left, top, width, available = 335, 132, 485, 245
    domain = max(domain or max_value(rows, value_field), 1)
    step = available / max(len(rows), 1)
    bar_h = min(24, step * .55)
    for i, row in enumerate(rows):
        y = top + i * step
        label_lines = wrapped(row.get(label_field), 43, 2, f"bar label {i+1}")
        label_y = y + bar_h * .70 - (len(label_lines) - 1) * 6.5
        lines.append(text_block(42, label_y, row.get(label_field), width=43, max_lines=2, font_size=13.5, line_height=13))
        lines.append(f'<rect x="{left}" y="{y:.1f}" width="{width}" height="{bar_h:.1f}" rx="5" fill="{SAGE_RAISED}"/>')
        value = float(row.get(value_field, 0) or 0)
        bw = max(2, width * max(0, min(value / domain, 1)))
        lines.append(f'<rect x="{left}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" rx="5" fill="{ORANGE}"/>')
        lines.append(f'<text x="{min(left+bw+10, 850):.1f}" y="{y + bar_h*.72:.1f}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{INK}">{esc(f"{value:g}")}</text>')


def ranked_levers(lines: list[str], rows: list[dict[str, Any]]) -> None:
    """Render ordinal rank only; never encode invented magnitude as bar length."""
    rows = rows[:4]
    top, step = 128, 66
    for i, row in enumerate(rows):
        y = top + i * step
        rank = row.get("priority") if row.get("priority") is not None else i + 1
        lines.append(f'<circle cx="86" cy="{y:.1f}" r="20" fill="{ORANGE}"/>')
        lines.append(f'<text x="86" y="{y+6:.1f}" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="700" fill="{INK}">{esc(rank)}</text>')
        lines.append(text_block(126, y + 6, row.get("label"), width=72, max_lines=2, font_size=14, line_height=15))


def matrix(lines: list[str], rows: list[dict[str, Any]], label_field: str) -> None:
    rows = rows[:8]
    colors = [(0.34, BAD_SURFACE), (0.74, WARN_SURFACE), (1.01, GOOD_SURFACE)]
    top, step = 125, 34
    for i, row in enumerate(rows):
        y = top + i * step
        value = float(row.get("value", 0) or 0)
        color = next(c for boundary, c in colors if value < boundary)
        lines.append(text_block(42, y + 20, row.get(label_field), width=67, max_lines=1, font_size=13))
        lines.append(f'<rect x="520" y="{y}" width="300" height="26" rx="5" fill="{color}" stroke="{SAGE_RAISED}"/>')
        lines.append(f'<text x="535" y="{y+18}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{INK}">{esc(row.get("status") or f"{value:.0%}")}</text>')


def trust_matrix(lines: list[str], rows: list[dict[str, Any]]) -> None:
    rows = rows[:8]
    tones = {"bad": (BAD_SURFACE, ORANGE), "warn": (WARN_SURFACE, INK), "good": (GOOD_SURFACE, INK), "neutral": (SAGE_RAISED, SAGE_LINE)}
    top, step = 125, 34
    for i, row in enumerate(rows):
        y = top + i * step
        fill, accent = tones.get(str(row.get("tone")), (SAGE_RAISED, INK))
        lines.append(text_block(42, y + 20, row.get("signal"), width=67, max_lines=1, font_size=13))
        lines.append(f'<rect x="520" y="{y}" width="300" height="26" rx="5" fill="{fill}" stroke="{accent}" stroke-width="{2 if row.get("tone") == "bad" else 1}"/>')
        # The symbol is text: ink on every tone keeps it at >= 4.5:1; the accent colour stays on the frame only.
        lines.append(f'<text x="536" y="{y+18}" font-family="{MONO}" font-size="14" font-weight="700" fill="{INK}">{esc(row.get("symbol") or "-")}</text>')
        lines.append(f'<text x="566" y="{y+18}" font-family="{MONO}" font-size="13" font-weight="700" fill="{INK}">{esc(row.get("status") or "")}</text>')


def stacked(lines: list[str], rows: list[dict[str, Any]], label_field: str, value_field: str) -> None:
    total = sum(float(x.get(value_field, 0) or 0) for x in rows) or 1
    palette = [ORANGE, INK, SAGE_LINE, SAGE_RAISED, WARN]
    x, y, width, height = 80, 160, 740, 76
    offset = 0.0
    for i, row in enumerate(rows):
        val = float(row.get(value_field, 0) or 0)
        bw = width * val / total
        lines.append(f'<rect x="{x+offset:.1f}" y="{y}" width="{bw:.1f}" height="{height}" fill="{palette[i%len(palette)]}"/>')
        if bw > 70:
            color = WHITE if i in {0, 1, 2} else INK
            lines.append(f'<text x="{x+offset+bw/2:.1f}" y="{y+44}" text-anchor="middle" font-family="{MONO}" font-size="15" font-weight="700" fill="{color}">{esc(f"{val:g}")}</text>')
        offset += bw
    legend_y = 276
    for i, row in enumerate(rows[:5]):
        lx = 80 + (i % 3) * 250
        ly = legend_y + (i // 3) * 34
        lines.append(f'<rect x="{lx}" y="{ly}" width="18" height="18" rx="3" fill="{palette[i%len(palette)]}"/>')
        lines.append(text_block(lx + 27, ly + 14, row.get(label_field), width=28, max_lines=1, font_size=13))


def render_svg(visual: dict[str, Any]) -> str:
    tid = str(visual.get("template_id"))
    data = visual.get("data") if isinstance(visual.get("data"), list) else []
    lines = svg_open(str(visual.get("title") or tid), str(visual.get("subtitle") or ""))
    if tid == "V01_OVERALL_SCORE":
        value = float((data[0] if data else {}).get("value", 0) or 0)
        lines += [
            f'<text x="70" y="210" font-family="{MONO}" font-size="72" font-weight="700" fill="{INK}">{value:.0f}</text>',
            f'<text x="185" y="210" font-family="{MONO}" font-size="24" fill="{SAGE_LINE}">/ 100</text>',
            f'<rect x="70" y="250" width="720" height="42" rx="8" fill="{SAGE_RAISED}"/>',
            f'<rect x="70" y="250" width="{7.2*max(0,min(value,100)):.1f}" height="42" rx="8" fill="{ORANGE}"/>',
        ]
    elif tid in {"V02_CATEGORY_BARS", "V04_FINDABILITY_BENCHMARK", "V09_AGENT_READINESS"}:
        label = "label" if tid == "V02_CATEGORY_BARS" else "entity" if tid == "V04_FINDABILITY_BENCHMARK" else "capability"
        horizontal_bars(lines, data, label, "value", 100 if tid == "V02_CATEGORY_BARS" else None)
    elif tid == "V03_TOP_LEVERS":
        ranked_levers(lines, data)
    elif tid == "V05_RANKING_POSITION":
        rows = data[:8]
        maxp = max(max_value(rows, "position", 100), 10)
        # Rows that carry their own place/device/date get a caption line, so they need a little more pitch:
        # eight captioned rows end at y=387, above the footer rule at y=407.
        pitch = 34 if any(row.get("context_label") for row in rows) else 32
        # Name the scale: better positions sit to the right, position 1 at the right end of the track.
        lines.append(f'<text x="340" y="112" font-family="{MONO}" font-size="13" fill="{SAGE_LINE}">Position {maxp:g}</text>')
        lines.append(f'<text x="810" y="112" text-anchor="end" font-family="{MONO}" font-size="13" fill="{SAGE_LINE}">Position 1</text>')
        for i, row in enumerate(rows):
            y = 130 + i * pitch
            pos = float(row.get("position", 0) or 0)
            # Position maxp sits on the left end (x=340, labelled "Position maxp"), position 1 on the right end (x=810).
            x = min(810.0, max(340.0, 340 + (maxp - pos) / (maxp - 1) * 470))
            lines.append(text_block(42, y + 5, row.get("query"), width=45, max_lines=1, font_size=13.5))
            if row.get("context_label"):
                # Place, device and date belong to each plotted query, not only to the chart subtitle.
                # 13 px is the SVG legibility floor (validate_visual_assets.py); the caption runs under the plot line,
                # below the 8 px position dot, and never truncates (wrapped() raises on overflow).
                lines.append(text_block(42, y + 19, row.get("context_label"), width=100, max_lines=1, font_size=13, fill=SAGE_LINE))
            lines.append(f'<line x1="340" y1="{y}" x2="810" y2="{y}" stroke="{SAGE_RAISED}"/>')
            lines.append(f'<circle cx="{x:.1f}" cy="{y}" r="8" fill="{ORANGE}"/>')
            lines.append(f'<text x="825" y="{y+6}" font-family="{MONO}" font-size="13.5" fill="{INK}">{pos:g}</text>')
    elif tid == "V10_TRUST_MATRIX":
        trust_matrix(lines, data)
    elif tid in {"V06_QUERY_COVERAGE", "V08_AI_ANSWERABILITY"}:
        field = "query" if tid == "V06_QUERY_COVERAGE" else "question"
        matrix(lines, data, field)
    elif tid == "V07_PERFORMANCE_THRESHOLD":
        row = data[0] if data else {}
        value = float(row.get("value", 0) or 0)
        good = float(row.get("good", 0) or 0)
        warn = float(row.get("warn", max(good, 1)) or max(good, 1))
        domain = max(warn * 1.5, value * 1.15, 1)
        x, width, y, h = 90, 720, 190, 70
        # German decimal comma and the metric's own unit on every printed number.
        unit = f" {row['unit']}" if row.get("unit") else ""
        num = lambda v: f"{v:g}".replace(".", ",") + unit
        gx = width * good / domain
        wx = width * warn / domain
        lines += [
            f'<rect x="{x}" y="{y}" width="{gx:.1f}" height="{h}" fill="{GOOD_SURFACE}"/>',
            f'<rect x="{x+gx:.1f}" y="{y}" width="{max(0,wx-gx):.1f}" height="{h}" fill="{WARN_SURFACE}"/>',
            f'<rect x="{x+wx:.1f}" y="{y}" width="{max(0,width-wx):.1f}" height="{h}" fill="{BAD_SURFACE}"/>',
            f'<line x1="{x+width*value/domain:.1f}" y1="{y-18}" x2="{x+width*value/domain:.1f}" y2="{y+h+18}" stroke="{ORANGE}" stroke-width="6"/>',
            f'<text x="{x}" y="{y+120}" font-family="{FONT}" font-size="15" fill="{INK}">Ziel ≤ {esc(num(good))} · Warnschwelle {esc(num(warn))}</text>',
            f'<text x="{x+width*value/domain:.1f}" y="{y-28}" text-anchor="middle" font-family="{MONO}" font-size="25" font-weight="700" fill="{INK}">{esc(num(value))}</text>',
        ]
    elif tid == "V11_SEVERITY_DISTRIBUTION":
        stacked(lines, data, "severity", "count")
    elif tid == "V12_AUDIT_COVERAGE":
        stacked(lines, data, "state", "count")
    elif tid == "V13_IMPACT_EFFORT":
        for idx, row in enumerate(data[:10]):
            effort = float(row.get("effort", 0) or 0)
            impact = float(row.get("impact", 0) or 0)
            x = 110 + effort / 5 * 650
            y = 350 - impact / 5 * 220
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="{ORANGE}" opacity=".9"/>')
            lines.append(text_block(x + 18, y + 5, row.get("label"), width=28, max_lines=2, font_size=13.5))
        lines += [
            f'<line x1="110" y1="350" x2="810" y2="350" stroke="{INK}"/>',
            f'<line x1="110" y1="350" x2="110" y2="110" stroke="{INK}"/>',
            f'<text x="720" y="385" font-family="{FONT}" font-size="14" fill="{INK}">Aufwand →</text>',
            f'<text x="55" y="125" font-family="{FONT}" font-size="14" fill="{INK}">Wirkung</text>',
        ]
    elif tid == "V14_REPEAT_AUDIT":
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in data:
            groups.setdefault(clean(row.get("category")), []).append(row)
        colors = [ORANGE, INK, SAGE_LINE]
        for idx, (label, rows) in enumerate(groups.items()):
            rows = rows[:2]
            pts = []
            for j, row in enumerate(rows):
                x = 250 + j * 400
                value = float(row.get("value", 0) or 0)
                y = 350 - value / 100 * 230
                pts.append((x, y, value))
            if len(pts) == 2:
                lines.append(f'<line x1="{pts[0][0]}" y1="{pts[0][1]:.1f}" x2="{pts[1][0]}" y2="{pts[1][1]:.1f}" stroke="{colors[idx%3]}" stroke-width="5"/>')
                for x, y, v in pts:
                    lines.append(f'<circle cx="{x}" cy="{y:.1f}" r="9" fill="{colors[idx%3]}"/><text x="{x+15}" y="{y+5:.1f}" font-family="{MONO}" font-size="14" fill="{INK}">{v:g}</text>')
                lines.append(text_block(670, pts[1][1] + 5, label, width=24, max_lines=2, font_size=13.5))
        lines += [
            f'<text x="225" y="390" font-family="{FONT}" font-size="14" fill="{INK}">Vorher</text>',
            f'<text x="625" y="390" font-family="{FONT}" font-size="14" fill="{INK}">Nachher</text>',
        ]
    elif tid == "D01_PROCESS_FLOW":
        nodes = data if data else [{"label": "Befund"}, {"label": "Auswirkung"}, {"label": "Maßnahme"}, {"label": "Prüfung"}]
        for i, row in enumerate(nodes[:4]):
            x = 45 + i * 210
            lines.append(f'<rect x="{x}" y="170" width="170" height="90" rx="12" fill="{SAGE_RAISED}" stroke="{SAGE_LINE}"/>')
            lines.append(text_block(x + 85, 210, row.get("label"), width=21, max_lines=2, font_size=14, line_height=17, weight=700, anchor="middle"))
            if i < min(len(nodes), 4) - 1:
                lines.append(f'<path d="M{x+170} 215 L{x+200} 215" stroke="{ORANGE}" stroke-width="5" marker-end="url(#a)"/>')
        lines.insert(1, '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#EC5E43"/></marker></defs>')
    else:
        raise ValueError(f"unsupported fallback template: {tid}")
    footer(lines, visual)
    return "\n".join(lines)
