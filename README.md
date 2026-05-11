# Text-to-CAD harness

**Assembly-first, script-driven CAD**: agents read case inputs, produce **`assembly.json`**, transpile to **build123d** Python with **`gen_step()`**, run **`scripts/step`** for **STEP** plus **CAD Explorer** GLB sidecars, then open the model in Explorer.

## Pipeline

1. **Inputs** — e.g. `preview.png`, `bom.json`, notes under a case directory (`someTestCases/…` or your project folder).
2. **Spec** — Follow `.agents/skills/cad/references/model-decomposition-assembly-spec.md` to derive **`assembly.json`**.
3. **Source** — Transpile to Python implementing **`gen_step()`** (see `.agents/skills/cad/references/pipeline-reference.md`).
4. **Build** — From the repository root:

   ```bash
   ./.venv/bin/python .agents/skills/cad/scripts/step path/to/generator.py
   ```

5. **Validate** — `.agents/skills/cad/scripts/inspect` as in `.agents/skills/cad/references/pipeline-reference.md` (inspection section).
6. **Browse** — `.agents/skills/cad/references/pipeline-reference.md` (CAD Explorer section).

Optional internal prose briefs: `.agents/skills/cad/references/natural-language-specs.md`. Agent rules: `AGENTS.md`; CAD skill entry: `.agents/skills/cad/SKILL.md`. Pixel renders (`scripts/render`) are optional and documented via `python .agents/skills/cad/scripts/render --help` when needed.

## Quick start (Python)

This repo is routinely used with **Python 3.9.6+** (3.9.6 is enough for the current `build123d` stack). Create a venv at the repo root and install the CAD skill requirements:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r .agents/skills/cad/requirements.txt
```

If downloads are slow or blocked, use a mirror (example — Tsinghua):

```bash
./.venv/bin/pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
./.venv/bin/pip install -r .agents/skills/cad/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

If you need a **newer Python** than the system one, install it via your usual channel (e.g. **pyenv**) using a domestic mirror for the Python build or tarball where applicable, then point `python3 -m venv` at that interpreter.

Optional URDF / robot-motion stacks: install their `requirements.txt` under `.agents/skills/` only when needed.

## CAD Explorer (local UI)

```bash
npm --prefix .agents/skills/cad/explorer install
npm --prefix .agents/skills/cad/explorer run dev
```

If `npm install` fails on a corporate or flaky registry, retry with a public mirror, for example:

```bash
npm --prefix .agents/skills/cad/explorer install --registry https://registry.npmmirror.com
```

For agent-friendly “open this STEP” behavior, use `dev:ensure` as documented in `.agents/skills/cad/references/pipeline-reference.md` (CAD Explorer).

## Where things live

| Location | Role |
|----------|------|
| `.agents/skills/cad/references/model-decomposition-assembly-spec.md` | Contract: inputs → `assembly.json` |
| `.agents/skills/cad/SKILL.md` | Agent entry: tools, workflow, progressive refs |
| `.agents/skills/cad/references/pipeline-reference.md` | STEP, `gen_step()`, placement, build123d, `inspect`, Explorer, mesh/DXF, repair |
| `.agents/skills/cad/scripts/` | `step`, `inspect`, `transpile`, `render`, `dxf`, … |
| `cad/README.md` | Pointer for optional project-local notes (schema lives in the skill) |
| `someTestCases/<domain>/<slug>/` | Examples, STEP/GLB, logs — see `someTestCases/README.md` |

## Other docs

- `AGENTS.md` — Repository policies (logging under `someTestCases/`, LFS, regen).
- `CLAUDE.md` — Redirects to `AGENTS.md`.

Optional benchmarks under `.assets/` (often LFS) are not required for the main pipeline.

## Troubleshooting

- **`ImportError` from `vtkmodules` / `vtkCommonTransforms` when importing build123d:** do **not** install the PyPI package **`vtk`** on top of **`build123d`** — **`cadquery-ocp`** already bundles **`vtkmodules`**. If you previously ran `pip install vtk`, remove it and refresh OCP:  
  `./.venv/bin/pip uninstall -y vtk && ./.venv/bin/pip install --force-reinstall cadquery-ocp==7.7.2`  
  (or delete `.venv` and reinstall from **`.agents/skills/cad/requirements.txt`** only.)
- **Explorer / topology: “`STEP_topology` / `indexView`” errors on `.*.step.glb`:** the sidecar must be a **real glTF binary**. If Git checked out an **LFS pointer** (plain text starting with `version https://git-lfs.github.com/spec/v1`), run **`git lfs pull`** for that path, or regenerate from the generator (next bullet).
- **Regenerate STEP + GLB:** from repo root, target the **`*.py`** that defines **`gen_step()`** (rewrites `*.step` and the matching hidden GLB):

  ```bash
  ./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py
  ```

  Re-running **`scripts/step`** on a bare **`.step`** file is only for native STEP re-export and requires **`--kind part`** or **`--kind assembly`** (assemblies such as wardrobe1 need **`--kind assembly`**). Prefer the **`.py`** path when you own the generator. **`git lfs pull`** must be run first if the **`.step`** on disk is still an LFS pointer, otherwise **`scripts/step`** will refuse to read it.
