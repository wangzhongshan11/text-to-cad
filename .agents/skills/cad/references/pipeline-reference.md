# CAD pipeline reference

Single doc for **STEP / GLB**, **`gen_step()`**, **placement**, **build123d habits**, **`scripts/inspect`**, **Explorer**, **optional STL·3MF·DXF**, **repair**. Schema for **`assembly.json`**: **`model-decomposition-assembly-spec.md`**. Prose briefs: **`natural-language-specs.md`**.

**Cwd:** Commands below use `python scripts/…` from `.agents/skills/cad/`. From repo root use `./.venv/bin/python .agents/skills/cad/scripts/<tool> …`.

**Python deps:** Install **only** **`.agents/skills/cad/requirements.txt`**. Do not add PyPI **`vtk`** alongside **`build123d`** — **`cadquery-ocp`** already provides **`vtkmodules`**; a second VTK install commonly breaks macOS imports.

---

## 1. STEP generation and Explorer sidecars

- **`assembly.json`** (when used) is intent; transpiled **`.py`** implements **`gen_step()`** → return `Solid`, solid compound, or labeled assembly `Compound`.
- **`scripts/step`** writes STEP/STP and the **hidden** sidecar **`.<basename>.step.glb`** (mesh + `STEP_topology` JSON for Explorer). All derived — regenerate with the same command after source changes.

**`gen_step()`** (no output paths inside the function):

```python
def gen_step():
    ...
    return shape_or_compound
```

**Regenerate (preferred):** run **`scripts/step`** on the owning **`*.py`** so STEP and GLB stay in sync and the GLB contains a readable **`STEP_topology`** extension with **`indexView`**.

```bash
./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py
```

**Native STEP only** (no generator): **`--kind part`** or **`--kind assembly`** is required, e.g.  
`./.venv/bin/python .agents/skills/cad/scripts/step --kind assembly someTestCases/furniture/wardrobe1/wardrobe1_gen.step`  
(only works if the **`.step`** file is real bytes, not an LFS pointer.) Mesh flags: §6.

**LFS:** If `*.step` / `.*.step.glb` are still **Git LFS pointer text** (`version https://git-lfs.github.com/spec/v1`), Explorer and topology checks will fail — run **`git lfs pull`** (or regenerate binaries locally and commit per your LFS policy).

**After build:** `scripts/inspect refs <path>.step --facts --planes --positioning` (add `--topology` only when needed).

---

## 2. Placement and `assembly.json`

Truth order: **`model-decomposition-assembly-spec.md`** → transpiled **`Location` / `Joint` / `connect_to()`** → exported STEP (validated by **`inspect`**, not “constraints” inside STEP).

- **`inspect mate`**: read-only deltas on STEP; fix JSON or source, then regen.
- Re-check with `refs --facts --planes --positioning` and optional `mate` / `measure` / `frame`.

BREP construction habits: §3.

---

## 3. build123d modeling (concise)

- Topology chain: Vertex → … → **Solid** / **Compound**; avoid open shells unless requested.
- Named dimension variables; state origin / XY / +Z when useful.
- **`BuildPart` / `BuildSketch` / …**; primitives when they match intent; sketches for profile-driven shapes.
- Select by axis, normal, position, stable planes — not fragile indices. Use **`inspect refs`** for `@cad[...]` handles.
- **Label** exported children. On failure → §8.

---

## 4. Inspection and validation

**`scripts/inspect`** = geometry truth; Explorer = human pass (§5).

```bash
python scripts/inspect {refs|diff|frame|measure|mate|batch|worker} ...
```

**Default order:** STEP exists → `refs --facts --planes --positioning` → `measure` / `mate` / `frame` as needed → `diff` for before/after → Explorer link if available.

**Snippets:**

```bash
python scripts/inspect refs path/to/model.step --facts --planes --positioning
python scripts/inspect measure --from '@cad[path#A]' --to '@cad[path#B]' --axis z
python scripts/inspect mate --moving '@cad[...]' --target '@cad[...]' --mode flush --axis z
python scripts/inspect frame '@cad[path#sel]'
python scripts/inspect diff before.step after.step --planes
```

**Report** only what ran (generation, labels/bbox, planes/refs, positioning, Explorer or “unavailable”).

---

## 5. CAD Explorer

```bash
npm --prefix explorer run dev:ensure -- --file <path-relative-to-scan-root>.step
```

Use the **URL printed** by `dev:ensure` (port is not fixed). Manual dev: `npm --prefix explorer run dev`.

**Env (common):** `EXPLORER_PORT`, `EXPLORER_PORT_END`, `EXPLORER_ROOT_DIR`, `EXPLORER_WORKSPACE_ROOT`, `EXPLORER_DEFAULT_FILE`, …

**Link:** `http://127.0.0.1:<port>/?file=<scan-root-relative.step>` plus `@cad[...]` text when selectors matter.

---

## 6. Optional STL / 3MF

Same `scripts/step` run as STEP, after STEP is valid:

```bash
python scripts/step path/to/model.py --stl rel/mesh.stl --3mf rel/mesh.3mf
python scripts/step --kind part path/to.step --stl rel/mesh.stl
```

Tuning: `--mesh-tolerance`, `--mesh-angular-tolerance`. Return STEP + sidecars + Explorer URL (§5).

---

## 7. Optional DXF

Requires **`gen_dxf()`** and **`gen_step()`** in the same **`.py`**. Order: good STEP → add `gen_dxf()` → `scripts/dxf path/to/model.py`. Return DXF + STEP + Explorer URL.

---

## 8. Repair loop

1. Read stderr/stdout. 2. Classify. 3. Smallest fix (spec → JSON → Python → flags → env). 4. Rerun failed command + `inspect refs`. 5. State residual risk.

| Area | Fix first |
|------|-----------|
| JSON / transpile | **`model-decomposition-assembly-spec.md`**, align **`assembly.json`** and transpile output |
| Import / `gen_step` | Syntax, imports, no path logic inside `gen_step()` |
| Geometry / fillet / scale | Dimensions, `Mode`, order, `refs` facts |
| Selectors | Axis/position; rediscover `@cad[...]` |
| Placement | JSON / `Location` / joints; `refs --positioning`, `mate`, `frame` |
| Explorer / topology GLB | Scan root, `file=` path, **real** GLB bytes (not LFS pointer); **regen from `*.py`** |
| Pixels only | `python scripts/render --help` after STEP is valid |

**Broad edits:** `scripts/inspect diff before.step after.step --planes`.
