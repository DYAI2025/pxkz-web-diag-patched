"""Release-evidence validators share the build digest boundary and still fail closed."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_strategic_relevance_v321_preservation import controlled  # noqa: E402


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

    def test_ordinary_dotfiles_and_nested_names_stay_inside(self) -> None:
        # Only whole path components are excluded; look-alike names are still controlled.
        root = self.tree({".gitignore": "*", "docs/git/notes.md": "n", "scripts/reports_helper.py": "p"})
        self.assertEqual(set(controlled(root)), {".gitignore", "docs/git/notes.md", "scripts/reports_helper.py"})


if __name__ == "__main__":
    unittest.main()
