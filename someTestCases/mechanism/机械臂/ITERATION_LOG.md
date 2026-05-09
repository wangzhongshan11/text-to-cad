# ITERATION_LOG — 机械臂

## 2026-05-09 — STEP topology GLB `cadRef` 与仓库相对路径一致

- **cwd**: `d:\code\text-to-cad\.agents\skills\cad`（与 SKILL 一致，从 skill 目录跑 step）
- **命令**: `$env:PYTHONUTF8='1'; Set-Location "d:\code\text-to-cad\.agents\skills\cad"; & "d:\code\text-to-cad\.venv\Scripts\python.exe" scripts/step "../../../someTestCases/mechanism/机械臂/robot_arm.py" --verbose`
- **退出码**: 0
- **原因**: 原先 GLB 内 `cadRef` 在 cwd 为 skill 目录时被写成 **`D:/code/text-to-cad/someTestCases/...`**（`Path.cwd()` 作 `REPO_ROOT` 导致 `relative_to` 失败），Explorer 校验期望 **`someTestCases/mechanism/机械臂/robot_arm`**，触发 `cad_ref_mismatch`。
- **仓库修复**: 在 `.agents/skills/cad/scripts/common/cad_repo_root.py` 增加 `cad_harness_repo_root()`（由 `.../scripts/common` 上溯 4 级并校验 `AGENTS.md`），`catalog` / `assembly_spec` / `step_scene` / `metadata` / `render` / `glb_topology` / `render/cli` 的 `REPO_ROOT` 改为使用该根路径。
- **产物**: 重跑 step 后读取 `.robot_arm.step.glb` 内 manifest：`cadRef` = `someTestCases/mechanism/机械臂/robot_arm`，`stepPath` = `someTestCases/mechanism/机械臂/robot_arm.step`。

## 2026-05-09 — URDF Explorer 侧车 schema 对齐 v3

- **cwd**: `d:\code\text-to-cad`
- **变更**: `.robot_arm.urdf/explorer.json` 由 `schemaVersion: 1` + `defaultJoints` / `poses[].joints` 改为 Explorer 要求的 **`schemaVersion: 3`**、`**kind**: "texttocad-urdf-explorer"`、`**jointDefaultsByName**`、`**poses[].jointValuesByName**`；`robot_arm.py` 中 `gen_urdf()` 的 `explorer_metadata` 同步，避免再次 `gen_urdf` 写回旧格式。
- **原因**: CAD Explorer `parseUrdf.js` 校验 `schemaVersion === 3` 且 `kind === texttocad-urdf-explorer`，旧侧车触发 `URDF explorer metadata schemaVersion must be 3`。
- **说明**: 重新生成 URDF 应使用 **`python .agents/skills/urdf/scripts/gen_urdf/cli.py someTestCases/mechanism/机械臂/robot_arm.py`**（目标为 `.py`，不是 `.urdf`）。
