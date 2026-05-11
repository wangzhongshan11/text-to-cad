# AGENTS.md

Harness for **assembly-first CAD**: inputs → **`assembly.json`** → transpile **build123d** **`gen_step()`** → **`scripts/step`** (STEP + Explorer GLB) → **`scripts/inspect`** → Explorer. End-to-end steps and install: **`README.md`**. Tools, Explorer, optional exports, repair: **`.agents/skills/cad/references/pipeline-reference.md`**. **`assembly.json`** contract: **`.agents/skills/cad/references/model-decomposition-assembly-spec.md`**.

Explorer app development: **`.agents/skills/cad/explorer/README.md`**.

## Skill routing

- **`.agents/skills/cad/SKILL.md`** — CAD harness entry.
- **`.agents/skills/urdf/SKILL.md`** — URDF.
- **`.agents/skills/robot-motion/SKILL.md`** — ROS 2 / MoveIt.

Prose-only ideation: **`natural-language-specs.md`** (do not force end users to write JSON).

## Layout and `someTestCases/`

Cases under **`someTestCases/<domain>/<slug>/`**: generator **`*.py`**, **`*.step`**, hidden **`.*.step.glb`**, optional inputs, **`ITERATION_LOG.md`** (or `*_build_process.md`) with real **cwd**, commands, failures, fixes, outputs — include failed attempts. Logs = process audit; **`scripts/inspect`** = geometry truth. Details: **`someTestCases/README.md`**.

## Python

Prefer **`./.venv/bin/python`**. Bootstrap: **`python3 -m venv .venv`** then **`pip install -r .agents/skills/cad/requirements.txt`** (mirrors / newer Python: see **`README.md`**). Other skills: their **`requirements.txt`** only when needed.

## Source of truth and repo rules

Generated STEP, GLB, meshes, DXF, renders are **derived** — edit spec or generator, then regen explicit paths; do not hand-edit unless asked. Regenerated binaries are authoritative when they differ from checkout.

- No directory-wide **`scripts/step`** sweeps unless a maintainer task says so.
- LFS: path-limited **`git status`** while binaries churn; bookkeeping-only status may use the no-smudge **`git -c filter.lfs.*=… status`** pattern from prior maintainer docs — **never** disable LFS for **`git add`** / commit.

## Execution

Source-first edits; avoid broad searches over STEP/GLB caches. One edit loop: regen STEP → inspect → optional Explorer; do not parallelize mutable geometry on the same paths.
