"""validate_pdf_output layout gate: footer clearance and lever copy on the lever page itself."""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_pdf_output import MM, layout_errors, lever_page_errors  # noqa: E402

W, H = 297 * MM, 210 * MM
FINDINGS = [{"id": f"F-00{i}", "headline": f"Hebel {i} Kopf", "observation": f"Beobachtung {i}",
             "impact": f"Wirkung {i}", "action": f"Schritt {i}"} for i in range(1, 5)]


def squash(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def pdf(pages: list[list[tuple[str, float]]], card_bottom_mm: float | None = None, footer: bool = True) -> Path:
    """Each page: list of (text, baseline y in mm); template-like footer (customer text + page number) at 203mm."""
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page(width=W, height=H)
        for text, y in lines:
            page.insert_text((20 * MM, y * MM), text, fontsize=9)
        if footer:
            page.insert_text((20 * MM, 203 * MM), "Kunde · Website-Analyse", fontsize=8)
            page.insert_text((270 * MM, 203 * MM), f"{doc.page_count:02d}", fontsize=8)
        if card_bottom_mm is not None:
            page.draw_rect(fitz.Rect(20 * MM, 150 * MM, 140 * MM, card_bottom_mm * MM), color=(0, 0, 0))
    path = Path(tempfile.mkdtemp(prefix="pxk-layout-")) / "p.pdf"
    doc.save(str(path))
    return path


def lever_lines() -> list[tuple[str, float]]:
    lines = [("Vier konkrete Hebel", 40.0)]
    y = 60.0
    for f in FINDINGS:
        for key in ("headline", "observation", "impact", "action"):
            lines.append((f[key], y))
            y += 6
    return lines


class FooterClearanceTest(unittest.TestCase):
    def test_clear_page_passes(self) -> None:
        self.assertEqual(layout_errors(pdf([[("Inhalt", 150.0)]], card_bottom_mm=190)), [])

    def test_card_reaching_footer_band_fails(self) -> None:
        errors = layout_errors(pdf([[("Inhalt", 150.0)]], card_bottom_mm=206))
        self.assertEqual(len(errors), 1)
        self.assertIn("page 1", errors[0])

    def test_text_running_into_footer_fails(self) -> None:
        self.assertTrue(layout_errors(pdf([[("Letzte Zeile der Karte", 201.5)]])))


class FooterlessPageTest(unittest.TestCase):
    # Cover-like pages carry no footer; their bottom band is design, so only running off the page counts.
    def test_text_low_on_footerless_page_passes(self) -> None:
        self.assertEqual(layout_errors(pdf([[("Kernaussage unten im Band", 200.0)]], footer=False)), [])

    def test_text_running_off_footerless_page_fails(self) -> None:
        self.assertTrue(layout_errors(pdf([[("Abgeschnittene Zeile", 208.0)]], footer=False)))


class LeverPageTest(unittest.TestCase):
    def test_all_fields_on_lever_page_pass(self) -> None:
        self.assertEqual(lever_page_errors(pdf([lever_lines()]), FINDINGS, squash), [])

    def test_field_only_repeated_on_roadmap_page_fails(self) -> None:
        lever = [line for line in lever_lines() if line[0] != "Schritt 4"]
        roadmap = [("Roadmap", 40.0), ("Schritt 4", 60.0)]
        errors = lever_page_errors(pdf([lever, roadmap]), FINDINGS, squash)
        self.assertEqual(errors, ["lever F-004 action not visible on lever page 1"])

    def test_missing_or_duplicate_lever_page_fails(self) -> None:
        self.assertTrue(lever_page_errors(pdf([[("Roadmap", 40.0)]]), FINDINGS, squash))
        self.assertTrue(lever_page_errors(pdf([lever_lines(), lever_lines()]), FINDINGS, squash))


if __name__ == "__main__":
    unittest.main()
