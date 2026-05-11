---
name: cad
description: Assembly-first build123d harness — decompose inputs into assembly.json, transpile Python with gen_step(), run scripts/step for STEP+Explorer GLB, validate with scripts/inspect, return Explorer links. Secondary DXF/STL/3MF and renders when explicitly requested.
---

# CAD generation

## Purpose

Case inputs → **`assembly.json`** (`references/model-decomposition-assembly-spec.md`) → transpile **`gen_step()`** → **`scripts/step`** (STEP + **`.<name>.step.glb`** Explorer sidecar) → **`scripts/inspect`** → Explorer links. STEP is primary; STL/3MF/DXF/render are optional.

## When to use

CAD / STEP / build123d / **`assembly.json`** / `@cad[...]` / Explorer. Not: pure renders, CAM, certification, BIM (unless CAD is also required).

## Defaults

mm; XY base, +Z up; closed solids + labels unless specified. Internal prose briefs: **`references/natural-language-specs.md`** (does not replace the decomposition spec when using JSON).

## Harness steps

1. Inputs (`preview.png`, `bom.json`, …).  
2. **`assembly.json`** per decomposition spec.  
3. Transpile (`scripts/transpile` or `scripts/assembly_from_spec.py`).  
4. **`./.venv/bin/python .agents/skills/cad/scripts/step path/to/generator.py`** — explicit targets only.  
5. **`inspect refs …`** ([inspection](references/pipeline-reference.md#4-inspection-and-validation)) and optional **`mate` / `measure` / `frame`**.  
6. Explorer: [CAD Explorer](references/pipeline-reference.md#5-cad-explorer) in **`pipeline-reference.md`**.

**Paths:** CLI resolves relative to process **cwd** (prefer repo root + repo-relative paths). Explorer **`file=`** is relative to the active scan root (same doc §5).

## Tooling (cad skill cwd)

```bash
python scripts/step …
python scripts/inspect …
python scripts/transpile …
python scripts/assembly_from_spec.py …
python scripts/render …   # optional
python scripts/dxf …      # optional
npm --prefix explorer run dev:ensure -- --file path/to.step
```

**`--help`** on each tool. Full behavior: **`references/pipeline-reference.md`**.

## Non-negotiables

Derived artifacts only; **`inspect`** + Explorer over **`git diff`** for geometry; report only checks that actually ran.

## References

| Doc | Use |
|-----|-----|
| `references/model-decomposition-assembly-spec.md` | **`assembly.json`** |
| `references/pipeline-reference.md` | STEP/GLB, placement, build123d, inspect, Explorer, mesh/DXF, repair, **LFS / topology GLB** |
| `references/natural-language-specs.md` | Internal prose briefs |

Return: file paths, Explorer URL or reason skipped, validation run, assumptions.
