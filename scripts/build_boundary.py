"""One file boundary for the build digest, the v3.2.1 preservation check and skill.zip.

skill.zip ships every file that is not never_shipped(). The build digest covers exactly those files minus the
top-level reports/ evidence, so nothing can ship without being digested.
"""
from __future__ import annotations

from pathlib import PurePath

EVIDENCE_TOP_LEVEL = "reports"  # shipped evidence, outside the build digest
OUTPUT_TOP_LEVEL = "dist"  # build output, never shipped
EXCLUDED_DIRS = frozenset({"__pycache__", ".git", ".pytest_cache"})  # at any depth
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})  # compiled code is never shipped, so it cannot shadow a module


def never_shipped(rel: PurePath) -> bool:
    return rel.parts[0] == OUTPUT_TOP_LEVEL or bool(set(rel.parts) & EXCLUDED_DIRS) or rel.suffix in EXCLUDED_SUFFIXES


def excluded(rel: PurePath) -> bool:
    """True when rel is outside the build digest."""
    return never_shipped(rel) or rel.parts[0] == EVIDENCE_TOP_LEVEL
