# AGENTS.md

This repository is a harness for script-driven CAD generation with coding agents like Codex and Claude Code.

If you are modifying CAD Explorer itself, go to `.agents/skills/cad/explorer/README.md`.

## Skill Routing

Use the bundled skills for workflow details:

- `.agents/skills/cad/SKILL.md` for STEP, STL, 3MF, DXF, GLB/topology artifacts, render images, and `@cad[...]` prompt references.
- `.agents/skills/urdf/SKILL.md` for generated URDF files, `gen_urdf()`, robot links, joints, limits, and URDF mesh references.
- `.agents/skills/robot-motion/SKILL.md` for ROS 2/MoveIt dependency setup, running the motion server, and generating IK/path-planning artifacts for an existing URDF.

Use the URDF skill when generating or editing a robot description. If an existing valid URDF already exists, the robot-motion skill can attach motion artifacts to it directly; use robot-motion for inverse kinematics, path planning, motion artifact generation, and motion-server testing.

`AGENTS.md` is intentionally harness-focused. Reusable CAD, URDF, and robot-motion workflow rules live inside the skills.

## Harness Context

Project CAD files are repo-relative. This harness does not reserve a
project-file directory. Project CAD entries may live at the repository root
under folders such as `STEP/`, `STL/`, `DXF/`, and `3MF/`, or in another
explicit repo-relative layout chosen by the project.

### someTestCases 目录约定（本仓库）

本克隆里的实验模型与构建过程说明放在 `someTestCases/<domain>/<slug>/`
（总览见 `someTestCases/README.md`）。每个案例尽量自洽：同目录下放生成器
`.py`、主 STEP、Explorer 侧车文件，以及**过程记录**（见下节）。

### Claude Code：迭代过程全量留痕（`someTestCases/**` 下强制）

在 `someTestCases/` 下**新建或修改**任何内容时，必须维护**完整过程记录**，
不能只写最终「干净」的成功步骤。在该案例目录中维护 `ITERATION_LOG.md` 或
`*_build_process.md`，按**时间顺序**记录：

- **所有实质性工具使用**：逐字记录 shell 命令行与 **cwd**；CAD 技能 CLI
 （`scripts/step`、`scripts/inspect`、`scripts/render`、`scripts/dxf` 等）；
  `npm` / Explorer 相关命令；以及影响本案例的 Claude Code 内置工具调用
  （Read / Edit / Bash / WebFetch 等）及要点。
- **返回与产物**：退出码；stdout/stderr 中关键片段；生成或覆盖的**文件路径**。
- **失败**：每次失败尝试的报错全文或必要摘要（有用时附栈信息）。
- **修复与重试**：重跑前在源码或环境里改了什么、**为何**这样改。

刻意省略失败尝试或「难看」的中间命令，违背本条目的。该记录与
`.agents/skills/cad/SKILL.md` 中的几何校验流程**互补**：前者是**过程审计**，
后者是**几何正确性门槛**。

The CAD and URDF skill tools are file-targeted. They do not depend on a harness
layout or prepend a project root.

Project-specific context may live in compact root-level notes such as
`PROJECT.md`. Do not copy reusable generator contracts, prompt-reference rules,
validation policy, Explorer/link rules, image review policy, or full CLI syntax
into them; link to the relevant skill references instead.

For CAD Explorer scan-root, link, and `@cad[...]` behavior, defer to
`.agents/skills/cad/SKILL.md` and its Explorer/rendering references.

## Python Environment

Prefer the repo-local CAD runtime when it exists:

```bash
./.venv/bin/python
```

This environment has the CAD dependencies required by the skill tools, including
`build123d` and `OCP`. If `.venv` is missing or cannot import those modules,
create/install it from the repo root before running CAD tools:

```bash
python3.11 -m venv .venv
./.venv/bin/pip install -r .agents/skills/cad/requirements.txt
```

Other bundled skills own their Python dependencies in their skill directories; install them only when using those workflows.

## Source Of Truth

- Generated CAD, URDF, robot-motion outputs, Explorer sidecars, renders, topology, meshes, and flat-pattern artifacts are derived artifacts.
- Do not hand-edit derived artifacts unless explicitly instructed. Edit the owning source file or imported source file first, then regenerate explicit targets with the relevant skill tool.
- If regenerated output differs from checked-in generated files, the regenerated output is authoritative.

## Repo Policies

- Keep project CAD files in explicit repo-relative locations.
- Use explicit generation targets. Do not run directory-wide generation.
- Generation tools write and overwrite current configured outputs. They do not delete stale outputs when paths change.
- Update project-local documentation only when project focus, entry roles, inventory, dependency notes, durable quirks, or preferred rebuild roots change.
- CAD outputs are often LFS-tracked, and broad status checks can invoke LFS clean filters while generated files are changing; prefer path-limited `git status` during CAD work.
- For bookkeeping-only full status, use `git -c filter.lfs.clean= -c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false status --short`.
- Never disable LFS filters for `git add`, commits, or other object-writing operations.

## Execution Notes

- Start with the narrowest source-only search that can identify directly affected files.
- Exclude generated artifacts, binary CAD files, caches, and build outputs from default searches unless the task explicitly targets them.
- If the first pass makes scope clear, edit the source first and validate after.
- Do not run mutable generation, inspection, and render/review steps in parallel against geometry that is still changing in the same edit loop. Rebuild first, then inspect, then review.
- In cloud or constrained environments, avoid full-repo hydration when affected entries are known. Fetch only the needed inputs, generated outputs, and LFS objects for the entries being edited and explicitly regenerated.
