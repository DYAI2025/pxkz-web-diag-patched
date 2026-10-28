"""Release-evidence validators share the build digest boundary and still fail closed."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_full_48_active import ALLOWED_PROTECTED_CHANGES, apply_protected_changes  # noqa: E402
from validate_strategic_relevance_v321_preservation import controlled  # noqa: E402
from pipeline_ledger import digest_tree  # noqa: E402

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
