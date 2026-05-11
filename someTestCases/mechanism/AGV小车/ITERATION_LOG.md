# AGV小车 — Iteration Log

## 2026-05-11：声明式装配 JSON + 流水线脚本

### 参考

- 图纸：`someTestCases/mechanism/AGV小车/preview.png`（典型仓储 AGV 示意）
- 规范：`.agents/skills/cad/references/model-decomposition-assembly-spec.md`

### 产物

- `agv_assembly.json` — 底盘 + 四轮 + 后部立柱示意装配描述

### 工具与命令（cwd 与退出码）

**cwd:** `d:\code\text-to-cad`

```powershell
d:\code\text-to-cad\.venv\Scripts\python .agents\skills\cad\scripts\assembly_from_spec.py `
  someTestCases\mechanism\AGV小车\agv_assembly.json
```

**说明：** `assembly_from_spec.py` 将 JSON transpile 为同目录 `agv_gen.py`，随后在 `.agents/skills/cad/scripts` 下执行 `python -m step <绝对路径>\agv_gen.py`，生成 `agv_gen.step` 与 `.agv_gen.step.glb`。

**退出码：** 0  

**stdout 摘要：** `wrote: ...\agv_gen.py`；`[scripts/step] generated part STEP: someTestCases/mechanism/AGV小车/agv_gen.step`（`Compound` 当前被元数据解析为 part，STEP/GLB 仍正常生成）。

**生成文件：** `agv_gen.py`、`agv_gen.step`、`.agv_gen.step.glb`

### 设计摘要

- `chassis`：920×620×140 mm 箱体为根。
- 四轮：`Cylinder(75,55)`，底盘四角 `rg:si` 底面内法线与轮 `rg:si:0:0:-1` 配对，无 180° 翻转。
- `mast`：260×240×420 立柱，经底盘顶面后部 `rg:s:0:-1/2:1` 与立柱底 `rg:si:0:0:-1` 贴合。
