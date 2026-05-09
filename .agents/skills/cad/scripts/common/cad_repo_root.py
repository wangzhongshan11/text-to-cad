"""Resolve the text-to-cad repository root for CAD skill CLIs.

`Path.cwd()` is wrong when commands are run from `.agents/skills/cad` (see
SKILL.md). Topology manifests embed `cadRef` relative to this root; using cwd
there produced absolute paths and `cad_ref_mismatch` validation failures.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def cad_harness_repo_root() -> Path:
    """Return repo root (directory that contains ``AGENTS.md``), or cwd as fallback."""
    # This file: .agents/skills/cad/scripts/common/cad_repo_root.py
    common_dir = Path(__file__).resolve().parent
    candidate = common_dir.parents[4]
    if (candidate / "AGENTS.md").is_file():
        return candidate
    return Path.cwd().resolve()
