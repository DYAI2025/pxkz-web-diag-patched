"""Packaged Pixelkiez brand fonts: supply, licence, resolution, offline render and fail-closed negatives.

Covers the patch-order checks V-FONT-SUPPLY, V-LICENSE, V-FONT-RESOLVE, V-OFFLINE,
V-NEGATIVE, V-PDF and the font part of V-PACKAGE / V-IDEMPOTENCE. The render tests need
the declared PDF runtime (WeasyPrint, PyMuPDF, fontTools); without it they are skipped and
must be reported as not run, never as passed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_brand_fonts as cbf  # noqa: E402

MANIFEST = json.loads((ROOT / "assets/fonts/font-manifest.json").read_text(encoding="utf-8"))
HAS_FONTTOOLS = importlib.util.find_spec("fontTools") is not None


def _pdf_runtime() -> bool:
    try:
        import fitz  # noqa: F401
        import weasyprint  # noqa: F401
        import jinja2  # noqa: F401
    except Exception:
        return False
    return HAS_FONTTOOLS


HAS_PDF_RUNTIME = _pdf_runtime()
NETWORK_GUARD = '''
import os, socket
_log = os.environ["PXK_NETWORK_LOG"]
def _blocked(*args, **kwargs):
    with open(_log, "a", encoding="utf-8") as handle:
        handle.write(repr(args[1:] if len(args) > 1 else args) + "\\n")
    raise OSError("network access blocked by test")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font_tree_copy(tmp: Path) -> Path:
    root = tmp / "pkg"
    shutil.copytree(ROOT / "assets/fonts", root / "assets/fonts")
    return root


def skill_copy(tmp: Path) -> Path:
    root = tmp / "pixelkiez-website-diagnosis"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "reports", "dist", "__pycache__", ".pytest_cache", "inputs"))
    return root


def isolated_env(tmp: Path) -> dict[str, str]:
    """No PIXELKIEZ_FONT_DIR, no fontconfig font dirs (system/user fonts hidden), fresh HOME, socket guard."""
    guard = tmp / "guard"
    guard.mkdir(exist_ok=True)
    (guard / "sitecustomize.py").write_text(NETWORK_GUARD, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in {"PIXELKIEZ_FONT_DIR", "FONTCONFIG_PATH"}}
    home = tmp / "home"
    home.mkdir(exist_ok=True)
    fontconfig = tmp / "fonts.conf"
    fontconfig.write_text(
        '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
        f"<fontconfig><cachedir>{tmp / 'fc-cache'}</cachedir></fontconfig>\n",
        encoding="utf-8",
    )
    env.update({
        "FONTCONFIG_FILE": str(fontconfig),
        "HOME": str(home),
        "PYTHONPATH": str(guard) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
        "PXK_NETWORK_LOG": str(tmp / "network.log"),
    })
    return env


class FontSupplyAndLicenceTests(unittest.TestCase):
    """V-FONT-SUPPLY and V-LICENSE, re-derived from the files, not from the code under test."""

    def test_every_required_style_is_present_and_pinned(self):
        pairs = {(f["role"], f["style"]) for f in MANIFEST["fonts"]}
        self.assertEqual(pairs, {("display", "Regular"), ("display", "Bold"), ("data", "Regular"), ("data", "Bold")})
        self.assertEqual(len(MANIFEST["fonts"]), 4)
        for entry in MANIFEST["fonts"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file() and not path.is_symlink(), entry["path"])
            self.assertEqual(sha(path), entry["sha256"], entry["path"])
            data = path.read_bytes()
            self.assertEqual(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), entry["upstream_git_blob_sha1"])
            self.assertEqual(path.name, entry["original_filename"])
            self.assertIs(entry["modified"], False)
            self.assertIn(entry["upstream_url"].split("/")[2], {"raw.githubusercontent.com"})

    @unittest.skipUnless(HAS_FONTTOOLS, "fontTools unavailable: name-table check NOT RUN")
    def test_family_metadata_matches_manifest(self):
        from fontTools.ttLib import TTFont

        for entry in MANIFEST["fonts"]:
            font = TTFont(str(ROOT / entry["path"]))
            names = font["name"]
            self.assertEqual(names.getDebugName(1), entry["family"])
            self.assertEqual(names.getDebugName(2), entry["style"])
            self.assertEqual(names.getDebugName(6), entry["postscript_name"])
            self.assertEqual(font["OS/2"].usWeightClass, entry["weight"])
            self.assertNotIn("fvar", font)
            self.assertEqual(font["OS/2"].fsType, 0, "installable embedding expected")
            cmap = font.getBestCmap()
            self.assertFalse([c for c in MANIFEST["required_glyphs"] if ord(c) not in cmap])

    def test_licences_are_ofl_with_attribution(self):
        for family in MANIFEST["families"]:
            path = ROOT / family["license_file"]
            text = path.read_text(encoding="utf-8")
            self.assertEqual(sha(path), family["license_sha256"])
            self.assertEqual(family["license_id"], "OFL-1.1")
            self.assertIn("SIL OPEN FONT LICENSE Version 1.1", text)
            first_line = text.splitlines()[0].strip()
            self.assertEqual(first_line, family["copyright"])
            for notice in family["notice_files"]:
                self.assertEqual(sha(ROOT / notice["path"]), notice["sha256"])
        plex = next(f for f in MANIFEST["families"] if f["family"] == "IBM Plex Mono")
        self.assertEqual(plex["reserved_font_names"], ["Plex"])
        self.assertIn('Reserved Font Name "Plex"', (ROOT / plex["license_file"]).read_text(encoding="utf-8"))
        schibsted = next(f for f in MANIFEST["families"] if f["family"] == "Schibsted Grotesk")
        self.assertNotIn("Reserved Font Name", (ROOT / schibsted["license_file"]).read_text(encoding="utf-8").split("PREAMBLE")[0])
        notices = (ROOT / "references/third-party-notices.md").read_text(encoding="utf-8")
        for family in MANIFEST["families"]:
            self.assertIn(family["family"], notices)
            self.assertIn(family["upstream"]["commit"], notices)


@unittest.skipUnless(HAS_FONTTOOLS, "fontTools unavailable: package verification NOT RUN")
class PackageVerificationNegativeTests(unittest.TestCase):
    """V-NEGATIVE at the verifier: each defect must turn VERIFIED into FAILED with a named issue."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pxk-fonts-")
        self.tmp = Path(self._tmp.name)
        self.root = font_tree_copy(self.tmp)
        self.manifest_path = self.root / "assets/fonts/font-manifest.json"

    def tearDown(self):
        self._tmp.cleanup()

    def manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, data: dict) -> None:
        self.manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def assert_fails(self, marker: str) -> None:
        result = cbf.verify_packaged_fonts(self.root)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(marker in issue for issue in result["issues"]), result["issues"])

    def test_positive_control_copy_verifies(self):
        result = cbf.verify_packaged_fonts(self.root)
        self.assertEqual(result["status"], "VERIFIED", result["issues"])
        self.assertEqual(set(result["fonts"]), {"display_regular", "display_bold", "data_regular", "data_bold"})

    def test_missing_font_file(self):
        (self.root / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf").unlink()
        self.assert_fails("MISSING_FILE")

    def test_corrupted_font_file(self):
        path = self.root / "assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.ttf"
        data = bytearray(path.read_bytes())
        data[len(data) // 2] ^= 0xFF
        path.write_bytes(bytes(data))
        self.assert_fails("HASH_MISMATCH")

    def test_wrong_family_under_expected_filename_even_with_matching_hash(self):
        target = self.root / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf"
        shutil.copyfile(self.root / "assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.ttf", target)
        data = self.manifest()
        for entry in data["fonts"]:
            if entry["path"].endswith("SchibstedGrotesk-Regular.ttf"):
                entry["sha256"] = sha(target)
        self.write_manifest(data)
        self.assert_fails("FAMILY_MISMATCH")

    def test_wrong_style_under_expected_filename(self):
        target = self.root / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf"
        shutil.copyfile(self.root / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf", target)
        data = self.manifest()
        for entry in data["fonts"]:
            if entry["path"].endswith("SchibstedGrotesk-Bold.ttf"):
                entry["sha256"] = sha(target)
        self.write_manifest(data)
        self.assert_fails("STYLE_MISMATCH")

    def test_incorrect_checksum_in_manifest(self):
        data = self.manifest()
        data["fonts"][0]["sha256"] = "0" * 64
        self.write_manifest(data)
        self.assert_fails("HASH_MISMATCH")

    def test_missing_licence(self):
        (self.root / "assets/fonts/ibm-plex-mono/LICENSE.txt").unlink()
        self.assert_fails("LICENSE_MISSING_FILE")

    def test_altered_licence(self):
        path = self.root / "assets/fonts/schibsted-grotesk/OFL.txt"
        path.write_text(path.read_text(encoding="utf-8").replace("Version 1.1", "Version 9"), encoding="utf-8")
        self.assert_fails("LICENSE_HASH_MISMATCH")

    def test_unexpected_font_asset(self):
        shutil.copyfile(self.root / "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf", self.root / "assets/fonts/ibm-plex-mono/Extra.ttf")
        self.assert_fails("UNEXPECTED_FONT_ASSET")

    def test_unsafe_manifest_path(self):
        data = self.manifest()
        data["fonts"][0]["path"] = "assets/fonts/../../escape.ttf"
        self.write_manifest(data)
        self.assert_fails("UNSAFE_PATH")

    def test_symlink_font_rejected(self):
        outside = self.tmp / "outside.ttf"
        target = self.root / "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf"
        shutil.move(str(target), outside)
        target.symlink_to(outside)
        self.assert_fails("SYMLINK_REJECTED")

    def test_malformed_manifest_structure_fails_closed_without_exception(self):
        for mutate in (
            lambda d: d["fonts"][0].__setitem__("weight", "400 regular"),
            lambda d: d.__setitem__("fonts", None),
            lambda d: d["families"][0].__setitem__("notice_files", None),
        ):
            data = self.manifest()
            mutate(data)
            self.write_manifest(data)
            self.assert_fails("MANIFEST_MALFORMED")
        self.manifest_path.write_text("[]\n", encoding="utf-8")
        self.assert_fails("MANIFEST_MALFORMED")

    def test_finder_metadata_is_ignored_but_other_files_are_not(self):
        (self.root / "assets/fonts/schibsted-grotesk/.DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")
        self.assertEqual(cbf.verify_packaged_fonts(self.root)["status"], "VERIFIED")
        (self.root / "assets/fonts/notes.txt").write_text("x", encoding="utf-8")
        self.assert_fails("UNEXPECTED_FILE")

    def test_duplicate_manifest_entry_is_not_idempotent_drift(self):
        data = self.manifest()
        data["fonts"].append(dict(data["fonts"][0]))
        self.write_manifest(data)
        self.assert_fails("DUPLICATE_FONT_ENTRY")

    def test_damaged_package_blocks_exact_even_if_runtime_has_the_fonts(self):
        runtime = self.tmp / "runtime-fonts"
        shutil.copytree(ROOT / "assets/fonts", runtime)
        (self.root / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf").write_bytes(b"\x00\x01\x00\x00broken")
        old = os.environ.get("PIXELKIEZ_FONT_DIR")
        os.environ["PIXELKIEZ_FONT_DIR"] = str(runtime)
        try:
            result = cbf.resolve_fonts(self.root)
        finally:
            if old is None:
                os.environ.pop("PIXELKIEZ_FONT_DIR", None)
            else:
                os.environ["PIXELKIEZ_FONT_DIR"] = old
        self.assertNotEqual(result["status"], "EXACT")
        self.assertFalse(result["customer_release_ready"])
        self.assertEqual(result["package_fonts"]["status"], "FAILED")


@unittest.skipUnless(HAS_FONTTOOLS, "fontTools unavailable: resolver checks NOT RUN")
class ResolverOrderTests(unittest.TestCase):
    """V-FONT-RESOLVE: package first; runtime dirs only when the package is absent; filenames never prove identity."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pxk-resolve-")
        self.tmp = Path(self._tmp.name)
        self.old = os.environ.get("PIXELKIEZ_FONT_DIR")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("PIXELKIEZ_FONT_DIR", None)
        else:
            os.environ["PIXELKIEZ_FONT_DIR"] = self.old
        self._tmp.cleanup()

    def test_package_fonts_resolve_first_over_a_configured_dir(self):
        valid_runtime = self.tmp / "valid-runtime"
        shutil.copytree(ROOT / "assets/fonts", valid_runtime)
        os.environ["PIXELKIEZ_FONT_DIR"] = str(valid_runtime)
        result = cbf.resolve_fonts(ROOT)
        self.assertEqual(result["status"], "EXACT")
        self.assertEqual(result["source"], {"display": "PACKAGED", "data": "PACKAGED"})
        for key, entry in result["verified_fonts"].items():
            self.assertTrue(entry["verified"], key)
        self.assertTrue(result["files"]["display_regular"].endswith("assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf"))
        self.assertTrue(result["files"]["display_bold"].endswith("SchibstedGrotesk-Bold.ttf"))

    def test_configured_dir_override_survives_without_package_fonts(self):
        runtime = self.tmp / "runtime"
        shutil.copytree(ROOT / "assets/fonts", runtime)
        (runtime / "font-manifest.json").unlink()
        os.environ["PIXELKIEZ_FONT_DIR"] = str(runtime)
        bare = self.tmp / "bare-skill"
        bare.mkdir()
        result = cbf.resolve_fonts(bare)
        self.assertEqual(result["package_fonts"]["status"], "ABSENT")
        self.assertEqual(result["status"], "EXACT")
        self.assertEqual(result["source"], {"display": "CONFIGURED_FONT_DIR", "data": "CONFIGURED_FONT_DIR"})

    def test_runtime_font_with_forged_family_name_but_foreign_postscript_name_is_rejected(self):
        from fontTools.ttLib import TTFont

        runtime = self.tmp / "forged-runtime"
        runtime.mkdir()
        for style in ("Regular", "Bold"):
            font = TTFont(str(ROOT / f"assets/fonts/ibm-plex-mono/IBMPlexMono-{style}.ttf"))
            for record in font["name"].names:
                if record.nameID in (1, 16):
                    record.string = "Schibsted Grotesk"
            font.save(str(runtime / f"SchibstedGrotesk-{style}.ttf"))
        os.environ["PIXELKIEZ_FONT_DIR"] = str(runtime)
        bare = self.tmp / "bare-skill"
        bare.mkdir()
        self.assertEqual(cbf.font_identity(runtime / "SchibstedGrotesk-Regular.ttf")["family"], "Schibsted Grotesk")
        self.assertFalse(cbf.resolve_fonts(bare)["exact"]["display"])

    def test_default_glyph_set_equals_manifest(self):
        self.assertEqual(cbf.DEFAULT_REQUIRED_GLYPHS, MANIFEST["required_glyphs"])

    def test_filename_alone_never_proves_exact(self):
        decoy = self.tmp / "decoy"
        decoy.mkdir()
        for name in ("SchibstedGrotesk-Regular.ttf", "SchibstedGrotesk-Bold.ttf"):
            shutil.copyfile(ROOT / "assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.ttf", decoy / name)
        os.environ["PIXELKIEZ_FONT_DIR"] = str(decoy)
        bare = self.tmp / "bare-skill"
        bare.mkdir()
        result = cbf.resolve_fonts(bare)
        self.assertFalse(result["exact"]["display"])
        self.assertNotEqual(result["status"], "EXACT")


@unittest.skipUnless(HAS_FONTTOOLS, "fontTools unavailable: package policy validator NOT RUN")
class PackagePolicyValidatorTests(unittest.TestCase):
    """V-POLICY / V-SECURITY: only manifest fonts; renamed font programs are still caught."""

    def run_validator(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/validate_no_font_binaries.py"), str(root)], capture_output=True, text=True)

    def test_real_package_passes(self):
        proc = self.run_validator(ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("4 manifest-pinned font files verified", proc.stdout)

    def test_arbitrary_font_binaries_fail_even_when_renamed(self):
        with tempfile.TemporaryDirectory(prefix="pxk-policy-") as tmp:
            root = font_tree_copy(Path(tmp))
            (root / "scripts").mkdir()
            shutil.copyfile(ROOT / "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf", root / "scripts/blob.bin")
            proc = self.run_validator(root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("scripts/blob.bin", proc.stderr)
            (root / "scripts/blob.bin").unlink()
            (root / "scripts/other.woff2").write_bytes(b"wOF2fake")
            proc = self.run_validator(root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("scripts/other.woff2", proc.stderr)

    def test_fonts_hidden_in_containers_and_type1_fonts_fail(self):
        import base64
        import gzip
        import zipfile

        plex = (ROOT / "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf").read_bytes()
        hidden = {
            "scripts/bundle.zip": lambda p: zipfile.ZipFile(p, "w").writestr("inner.dat", plex),
            "scripts/blob.gz": lambda p: p.write_bytes(gzip.compress(plex)),
            "assets/inline.css": lambda p: p.write_text("@font-face{src:url(data:application/octet-stream;base64," + base64.b64encode(plex[:600]).decode() + ")}", encoding="utf-8"),
            "assets/type1.dat": lambda p: p.write_bytes(b"%!PS-AdobeFont-1.0: Fake 001\n"),
        }
        for rel, write in hidden.items():
            with self.subTest(rel=rel), tempfile.TemporaryDirectory(prefix="pxk-policy-") as tmp:
                root = font_tree_copy(Path(tmp))
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                write(root / rel)
                proc = self.run_validator(root)
                self.assertEqual(proc.returncode, 1, proc.stdout)
                self.assertIn(rel, proc.stderr)

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory(prefix="pxk-policy-") as tmp:
            root = font_tree_copy(Path(tmp))
            (root / "assets/fonts/font-manifest.json").unlink()
            proc = self.run_validator(root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("MANIFEST_MISSING", proc.stderr)

    def test_archive_font_check_rejects_extra_and_duplicate_entries(self):
        import package_skill

        base = [f"pixelkiez-website-diagnosis/{p}" for p in (
            [f["path"] for f in MANIFEST["fonts"]] + [f["license_file"] for f in MANIFEST["families"]]
            + [n["path"] for f in MANIFEST["families"] for n in f["notice_files"]] + ["assets/fonts/font-manifest.json"])]
        package_skill.check_archive_fonts(ROOT, base, "pixelkiez-website-diagnosis")
        with self.assertRaises(SystemExit):
            package_skill.check_archive_fonts(ROOT, base + ["pixelkiez-website-diagnosis/assets/x.otf"], "pixelkiez-website-diagnosis")
        with self.assertRaises(SystemExit):
            package_skill.check_archive_fonts(ROOT, base + [base[0]], "pixelkiez-website-diagnosis")
        with self.assertRaises(SystemExit):
            package_skill.check_archive_fonts(ROOT, base[1:], "pixelkiez-website-diagnosis")
        renamed = "pixelkiez-website-diagnosis/assets/blob.dat"
        with self.assertRaises(SystemExit):
            package_skill.check_archive_fonts(ROOT, base + [renamed], "pixelkiez-website-diagnosis", {renamed: b"\x00\x01\x00\x00\x00\x10"})


@unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime (WeasyPrint/PyMuPDF/fontTools) unavailable: offline render NOT RUN")
class OfflineStrictRenderTests(unittest.TestCase):
    """V-OFFLINE / V-PDF: strict customer mode, no network, no PIXELKIEZ_FONT_DIR, no user fonts."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="pxk-offline-")
        cls.tmp = Path(cls._tmp.name)
        cls.env = isolated_env(cls.tmp)
        scored = cls.tmp / "scored.json"
        subprocess.run([sys.executable, "-B", str(ROOT / "scripts/compute_score.py"), str(ROOT / "evals/fixtures/synthetic-report.json"), str(scored)], check=True, capture_output=True, env=cls.env)
        cls.out = cls.tmp / "deliverables"
        cls.proc = subprocess.run(
            # Fixture data is refused in customer mode (evidence-bound claims patch); the strict font contract is
            # the same in proof mode with --require-exact-fonts, which is what these tests exercise.
            [sys.executable, "-B", str(ROOT / "scripts/build_audit_deliverables.py"), str(scored), str(cls.out), "--release-mode", "proof", "--require-exact-fonts", "--force-svg-fallback"],
            capture_output=True, text=True, env=cls.env,
        )

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_strict_customer_build_succeeds_with_exact_packaged_fonts(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        receipt = json.loads((self.out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["renderer"], "WEASYPRINT")
        self.assertEqual(receipt["brand_font_status"], "EXACT")
        self.assertEqual(receipt["font_provenance"]["source"], {"display": "PACKAGED", "data": "PACKAGED"})
        self.assertEqual(receipt["font_provenance"]["package_manifest_sha256"], sha(ROOT / "assets/fonts/font-manifest.json"))
        pinned = {f"{f['role']}_{f['style'].casefold()}": f["sha256"] for f in MANIFEST["fonts"]}
        self.assertEqual(receipt["font_resolution"]["font_file_sha256"], pinned)
        embedding = receipt["pdf_font_embedding"]
        self.assertEqual(embedding["status"], "VERIFIED")
        self.assertEqual(embedding["identity_method"], "EMBEDDED_PROGRAM_NAME_TABLE_HEAD_AND_OUTLINES")
        self.assertEqual(embedding["required_embedded"], {k: True for k in pinned})
        self.assertEqual(embedding["unexpected_fonts"], [])
        self.assertTrue(all(r["outline_glyphs_compared"] > 0 for r in embedding["embedded_fonts"]))
        self.assertEqual(receipt["limitations"], [])

    def test_no_network_attempts_and_no_remote_resources(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        log = self.tmp / "network.log"
        self.assertFalse(log.exists() and log.read_text(encoding="utf-8").strip(), "network was attempted during render")
        html = (self.out / "customer_presentation.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"""(?:src|href)\s*=\s*["']https?://""")
        self.assertNotRegex(html, r"url\(\s*[\"']?https?://")

    def test_pdf_embeds_both_families_and_german_glyphs_render_in_brand_fonts(self):
        import fitz

        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        receipt = json.loads((self.out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
        families = {r["family"] for r in receipt["pdf_font_embedding"]["embedded_fonts"]}
        styles = {(r["family"], r["style"]) for r in receipt["pdf_font_embedding"]["embedded_fonts"]}
        self.assertEqual(families, {"Schibsted Grotesk", "IBM Plex Mono"})
        self.assertEqual(styles, {("Schibsted Grotesk", "Regular"), ("Schibsted Grotesk", "Bold"), ("IBM Plex Mono", "Regular"), ("IBM Plex Mono", "Bold")})
        aliases = {r["basefont"].split("+", 1)[-1] for r in receipt["pdf_font_embedding"]["embedded_fonts"]}
        german = set()
        with fitz.open(self.out / "customer_presentation.pdf") as doc:
            for page in doc:
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            if any(ch in span["text"] for ch in "äöüÄÖÜß"):
                                german.add(span["font"])
        self.assertTrue(german, "fixture PDF should contain German umlauts")
        self.assertLessEqual(german, aliases)

    def test_fonts_not_copied_into_customer_deliverables_and_qa_stays_pending(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        fonts = [p for p in self.out.rglob("*") if p.is_file() and cbf.looks_like_font(p)]
        self.assertEqual(fonts, [])
        manifest = json.loads((self.out / "deliverable-manifest.json").read_text(encoding="utf-8"))
        self.assertIs(manifest["customer_release_ready"], False)
        self.assertEqual(manifest["qa_status"], {"visual": "PENDING_ACTUAL_INSPECTION", "semantic": "PENDING_ACTUAL_INSPECTION"})
        bundle = json.loads((self.out / "deliverable-bundle-validation.json").read_text(encoding="utf-8"))
        self.assertIs(bundle["customer_release_ready"], False)
        self.assertEqual(bundle["pdf_font_embedding_status"], "VERIFIED")

    def test_receipt_claim_is_rechecked_against_the_pdf(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        receipt_path = self.out / "presentation-render-receipt.json"
        forged = json.loads(receipt_path.read_text(encoding="utf-8"))
        forged["pdf_font_embedding"]["status"] = "NOT_APPLICABLE_NON_EXACT"
        forged_path = self.tmp / "forged-receipt.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        shutil.copyfile(self.out / "customer_presentation.html", self.tmp / "customer_presentation.html")
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/validate_presentation_brand.py"), str(self.out / "customer_presentation.pdf"), str(forged_path), str(ROOT / "assets/brand-tokens.json")], capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("contradicts PDF", proc.stderr)

    def test_receipt_with_foreign_font_hashes_is_rejected_by_the_cli(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-3000:])
        forged = json.loads((self.out / "presentation-render-receipt.json").read_text(encoding="utf-8"))
        foreign = {key: "f" * 64 for key in forged["font_resolution"]["font_file_sha256"]}
        forged["font_resolution"]["font_file_sha256"] = foreign
        for key, value in forged["font_provenance"]["styles"].items():
            value["sha256"] = foreign[key]
        forged_path = self.tmp / "forged-hash-receipt.json"
        forged_path.write_text(json.dumps(forged), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/validate_presentation_brand.py"), str(self.out / "customer_presentation.pdf"), str(forged_path), str(ROOT / "assets/brand-tokens.json"), "--require-exact-fonts"], capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("RECEIPT_FONT_HASHES_DIFFER_FROM_LIVE_RESOLUTION", proc.stderr)


@unittest.skipUnless(HAS_PDF_RUNTIME, "PDF runtime unavailable: strict negative render NOT RUN")
class StrictRenderNegativeTests(unittest.TestCase):
    """V-NEGATIVE end to end: a damaged package must block strict mode; proof mode discloses the fallback."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="pxk-strict-neg-")
        cls.tmp = Path(cls._tmp.name)
        cls.env = isolated_env(cls.tmp)
        cls.skill = skill_copy(cls.tmp)
        target = cls.skill / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf"
        data = bytearray(target.read_bytes())
        data[-100] ^= 0x01
        target.write_bytes(bytes(data))
        cls.scored = cls.tmp / "scored.json"
        subprocess.run([sys.executable, "-B", str(cls.skill / "scripts/compute_score.py"), str(ROOT / "evals/fixtures/synthetic-report.json"), str(cls.scored)], check=True, capture_output=True, env=cls.env)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_customer_mode_fails_closed_on_corrupted_package_font(self):
        proc = subprocess.run(
            [sys.executable, "-B", str(self.skill / "scripts/build_audit_deliverables.py"), str(self.scored), str(self.tmp / "customer"), "--release-mode", "customer", "--force-svg-fallback"],
            capture_output=True, text=True, env=self.env,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("BRAND_FONT_EXACT_REQUIRED", proc.stderr)
        self.assertIn("HASH_MISMATCH", proc.stderr)
        self.assertFalse((self.tmp / "customer").exists())

    def test_require_exact_cli_fails_and_reports_issue(self):
        proc = subprocess.run([sys.executable, "-B", str(self.skill / "scripts/check_brand_fonts.py"), str(self.skill), "--require-exact"], capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("BRAND_FONT_EXACT_REQUIRED", proc.stderr)

    def test_outline_comparison_distinguishes_styles_of_one_family(self):
        from fontTools.ttLib import TTFont

        regular = ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf"
        bold = ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf"
        program = TTFont(str(regular))
        self.assertEqual(cbf._outlines_match(program, regular)[0], True)
        self.assertEqual(cbf._outlines_match(program, bold)[0], False)

    def render_isolated(self, html: str, name: str) -> Path:
        pdf = self.tmp / f"{name}.pdf"
        script = self.tmp / f"{name}.py"
        script.write_text("import sys\nfrom weasyprint import HTML\nHTML(string=open(sys.argv[1], encoding='utf-8').read()).write_pdf(sys.argv[2])\n", encoding="utf-8")
        source = self.tmp / f"{name}.html"
        source.write_text(html, encoding="utf-8")
        subprocess.run([sys.executable, "-B", str(script), str(source), str(pdf)], check=True, capture_output=True, env=self.env)
        return pdf

    @staticmethod
    def brand_html(overrides: dict[str, Path] | None = None, text: str = "Grüße 0123") -> str:
        faces = {
            ("PixelkiezDisplay", 400): ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf",
            ("PixelkiezDisplay", 700): ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf",
            ("PixelkiezData", 400): ROOT / "assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.ttf",
            ("PixelkiezData", 700): ROOT / "assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.ttf",
        }
        faces.update(overrides or {})
        css = "".join(f'@font-face{{font-family:"{fam}";src:url("{path.as_uri()}");font-weight:{w}}}' for (fam, w), path in faces.items())
        body = "".join(f'<p style="font-family:{fam};font-weight:{w}">{text}</p>' for fam, w in faces)
        return f"<style>{css}</style>{body}"

    def test_genuine_brand_pdf_verifies(self):
        resolution = cbf.resolve_fonts(ROOT)
        result = cbf.verify_pdf_font_embedding(self.render_isolated(self.brand_html(), "genuine"), resolution, resolution["files"])
        self.assertEqual(result["status"], "VERIFIED", result)

    def test_forged_font_with_copied_name_tables_fails_on_outlines(self):
        from fontTools.ttLib import TTFont

        genuine = TTFont(str(ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf"))
        forged = TTFont(str(ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Bold.ttf"))
        forged["name"] = genuine["name"]
        forged["head"].created, forged["head"].fontRevision = genuine["head"].created, genuine["head"].fontRevision
        forged_path = self.tmp / "forged-regular.ttf"
        forged.save(str(forged_path))
        pdf = self.render_isolated(self.brand_html({("PixelkiezDisplay", 400): forged_path}), "forged")
        resolution = cbf.resolve_fonts(ROOT)
        result = cbf.verify_pdf_font_embedding(pdf, resolution, resolution["files"])
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("display_regular", result["family_mismatch"])
        self.assertFalse(result["required_embedded"]["display_regular"])

    def test_notdef_glyphs_in_brand_fonts_fail(self):
        resolution = cbf.resolve_fonts(ROOT)
        pdf = self.render_isolated(self.brand_html(text="Grüße 東京"), "notdef")
        result = cbf.verify_pdf_font_embedding(pdf, resolution, resolution["files"])
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("U+4EAC" in item for item in result["notdef_glyphs"]), result["notdef_glyphs"])

    def test_receipt_identities_are_never_trusted(self):
        resolution = cbf.resolve_fonts(ROOT)
        pdf = self.render_isolated(self.brand_html(), "receipt-forge")
        claimed = {k: "0" * 64 for k in resolution["verified_fonts"]}
        receipt = {"brand_font_status": "EXACT", "font_resolution": {"font_file_sha256": claimed},
                   "font_provenance": {"source": {"display": "SYSTEM_FONT_DIR", "data": "SYSTEM_FONT_DIR"}}}
        check = cbf.reverify_receipt_fonts(pdf, receipt, ROOT)
        self.assertIn("RECEIPT_FONT_HASHES_DIFFER_FROM_LIVE_RESOLUTION", check["issues"])
        self.assertNotEqual(check["embedding"]["status"], "VERIFIED")

    def test_pdf_with_non_brand_font_fails_embedding_verification(self):
        from weasyprint import HTML

        pdf = self.tmp / "fallback.pdf"
        regular = (ROOT / "assets/fonts/schibsted-grotesk/SchibstedGrotesk-Regular.ttf").as_uri()
        HTML(string=f'<style>@font-face{{font-family:"PixelkiezDisplay";src:url("{regular}")}}body{{font-family:"PixelkiezDisplay"}}</style>'
                    '<p>Grüße</p><p style="font-family:monospace">ersatz</p>').write_pdf(str(pdf))
        resolution = cbf.resolve_fonts(ROOT)
        result = cbf.verify_pdf_font_embedding(pdf, resolution, resolution["files"])
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(result["unexpected_fonts"])
        self.assertFalse(result["required_embedded"]["display_bold"])
        self.assertTrue(result["required_embedded"]["display_regular"])


if __name__ == "__main__":
    unittest.main()
