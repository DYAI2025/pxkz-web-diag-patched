"""Release-evidence validators share the build digest boundary and still fail closed."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_full_48_active import ALLOWED_PROTECTED_CHANGES, apply_protected_changes  # noqa: E402
from validate_strategic_relevance_v321_preservation import controlled  # noqa: E402
from pipeline_ledger import digest_tree  # noqa: E402
from package_skill import packaged_files, write_archive  # noqa: E402

SCHEMA = "schemas/diagnosis-report.schema.json"
A, B, C = "a" * 64, "b" * 64, "c" * 64


class V321BoundaryTest(unittest.TestCase):
    def tree(self, files: dict[str, str]) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="pxk-v321-"))
        for rel, text in files.items():
            path = tmp / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return tmp

    def test_vcs_and_cache_dirs_are_outside_the_boundary(self) -> None:
        root = self.tree({
            "SKILL.md": "x",
            ".git/HEAD": "ref: refs/heads/main",
            ".git/objects/ab/cdef": "blob",
            ".pytest_cache/v/cache/nodeids": "[]",
            "scripts/__pycache__/a.cpython-312.pyc": "c",
            "reports/r.json": "{}",
            "dist/skill.zip": "z",
        })
        self.assertEqual(set(controlled(root)), {"SKILL.md"})

    def test_nested_reports_or_dist_dirs_are_controlled(self) -> None:
        # Only the top-level reports/ and dist/ are evidence/output; a nested one ships with the package.
        root = self.tree({"SKILL.md": "x", "scripts/reports/payload.py": "p", "assets/dist/a.json": "{}"})
        self.assertEqual(set(controlled(root)), {"SKILL.md", "scripts/reports/payload.py", "assets/dist/a.json"})

    def test_build_digest_sees_nested_reports_dir(self) -> None:
        root = self.tree({"SKILL.md": "x"})
        before = digest_tree(root)
        (root / "scripts/reports").mkdir(parents=True)
        (root / "scripts/reports/payload.py").write_text("p", encoding="utf-8")
        self.assertNotEqual(digest_tree(root), before)
        (root / "reports").mkdir()
        (root / "reports/r.json").write_text("{}", encoding="utf-8")
        after_nested = digest_tree(root)
        (root / "reports/r.json").write_text('{"x": 1}', encoding="utf-8")
        self.assertEqual(digest_tree(root), after_nested)

    def test_ordinary_dotfiles_and_nested_names_stay_inside(self) -> None:
        # Only whole path components are excluded; look-alike names are still controlled.
        root = self.tree({".gitignore": "*", "docs/git/notes.md": "n", "scripts/reports_helper.py": "p"})
        self.assertEqual(set(controlled(root)), {".gitignore", "docs/git/notes.md", "scripts/reports_helper.py"})


class PackageMatchesDigestTest(unittest.TestCase):
    """skill.zip ships exactly the build-digest files plus the top-level reports/ evidence."""

    def test_packaged_set_equals_digest_set_plus_reports(self) -> None:
        root = V321BoundaryTest.tree(None, {
            "SKILL.md": "x", "scripts/a.py": "a", "scripts/jsonschema.pyc": "shadow", "scripts/b.pyo": "o",
            ".pytest_cache/v/x": "c", "scripts/.pytest_cache/y": "c", "scripts/__pycache__/a.cpython-312.pyc": "c",
            "scripts/reports/payload.py": "p", "reports/r.json": "{}", "dist/skill.zip": "z", "assets/dist/a.json": "{}",
        })
        packaged = set(packaged_files(root))
        self.assertEqual(packaged - {p for p in packaged if p.startswith("reports/")}, set(controlled(root)))
        self.assertIn("reports/r.json", packaged)
        for never in ("scripts/jsonschema.pyc", "scripts/b.pyo", ".pytest_cache/v/x", "scripts/.pytest_cache/y", "dist/skill.zip"):
            self.assertNotIn(never, packaged)


class PackageOutputDirTest(unittest.TestCase):
    def test_out_dir_inside_shipped_tree_is_refused(self) -> None:
        # build/ would ship: the archive (and earlier archives) would land in the package.
        root = V321BoundaryTest.tree(None, {"SKILL.md": "x", "build/old.txt": "o"})
        with self.assertRaises(SystemExit):
            write_archive(root, root / "build", "s")
        with self.assertRaises(SystemExit):
            write_archive(root, root / "scripts" / "dist", "s")
        with self.assertRaises(SystemExit):
            write_archive(root, root, "s")

    def test_top_level_dist_and_outside_dirs_work(self) -> None:
        root = V321BoundaryTest.tree(None, {"SKILL.md": "x"})
        for out in (root / "dist", Path(tempfile.mkdtemp(prefix="pxk-out-"))):
            with zipfile.ZipFile(write_archive(root, out, "s")) as handle:
                self.assertEqual(handle.namelist(), ["s/SKILL.md"])


class ReleaseGateLiveChecksTest(unittest.TestCase):
    """A code change outside the protected set fails the release gate even when reports/ is untouched."""

    def gate_output(self, mutate: bool) -> str:
        tmp = Path(tempfile.mkdtemp(prefix="pxk-gate-")) / ROOT.name
        shutil.copytree(ROOT, tmp, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache"))
        if mutate:
            helper = tmp / "scripts/legal_customer_projection.py"
            helper.write_text(helper.read_text(encoding="utf-8") + "\n# reverted\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", str(tmp / "scripts/validate_release_gate.py"), str(tmp)],
                              capture_output=True, text=True, timeout=300)
        shutil.rmtree(tmp.parent)
        return proc.stdout + proc.stderr

    def test_live_v321_check_catches_unreported_code_change(self) -> None:
        # Asserted on the mutated path, so a dirty working tree (untracked files) cannot decide the result.
        flagged = "v3.2.1 preservation live check failed"
        path = "scripts/legal_customer_projection.py"
        control, mutated = self.gate_output(mutate=False), self.gate_output(mutate=True)
        self.assertNotIn(path, control)
        self.assertIn(flagged, mutated)
        self.assertIn(path, mutated.split(flagged, 1)[1])


class ProtectedChangeChainTest(unittest.TestCase):
    def report(self, *rows: tuple[str, str, str], status: str = "PASS") -> dict:
        return {"status": status, "changes": [
            {"path": SCHEMA, "previous_sha256": prev, "current_sha256": cur, "reason": reason} for prev, cur, reason in rows]}

    def test_no_report_keeps_pins(self) -> None:
        self.assertEqual(apply_protected_changes({SCHEMA: A}, None), {SCHEMA: A})

    def test_reasons_are_fixed_in_code(self) -> None:
        self.assertEqual(set(ALLOWED_PROTECTED_CHANGES), {"IMPRESSUM_CUSTOMER_RISK_SCHEMA", "VIBECHECK03_DIAGNOSTICS_SCHEMA"})

    def test_chain_advances_pin(self) -> None:
        rep = self.report((A, B, "IMPRESSUM_CUSTOMER_RISK_SCHEMA"), (B, C, "VIBECHECK03_DIAGNOSTICS_SCHEMA"))
        self.assertEqual(apply_protected_changes({SCHEMA: A, "x": A}, rep), {SCHEMA: C, "x": A})

    def test_broken_chain_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "chain"):
            apply_protected_changes({SCHEMA: A}, self.report((B, C, "IMPRESSUM_CUSTOMER_RISK_SCHEMA")))

    def test_unknown_reason_or_path_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "reason"):
            apply_protected_changes({SCHEMA: A}, self.report((A, B, "ANYTHING_GOES")))
        rep = {"status": "PASS", "changes": [{"path": "scripts/compute_score.py", "previous_sha256": A,
                                             "current_sha256": B, "reason": "IMPRESSUM_CUSTOMER_RISK_SCHEMA"}]}
        with self.assertRaisesRegex(ValueError, "reason"):
            apply_protected_changes({"scripts/compute_score.py": A}, rep)

    def test_report_not_pass_or_malformed_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "PASS"):
            apply_protected_changes({SCHEMA: A}, self.report((A, B, "IMPRESSUM_CUSTOMER_RISK_SCHEMA"), status="PENDING"))
        with self.assertRaisesRegex(ValueError, "sha256"):
            apply_protected_changes({SCHEMA: A}, self.report((A, "nothex", "IMPRESSUM_CUSTOMER_RISK_SCHEMA")))
        with self.assertRaisesRegex(ValueError, "not protected"):
            apply_protected_changes({}, self.report((A, B, "IMPRESSUM_CUSTOMER_RISK_SCHEMA")))


if __name__ == "__main__":
    unittest.main()
