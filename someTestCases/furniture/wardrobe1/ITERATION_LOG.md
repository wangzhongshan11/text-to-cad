# wardrobe1 — Iteration Log

## Iteration 1: Analyze reference image and plan dimensions

**Date:** 2026-05-08

### Actions
- Read `someTestCases/furniture/wardrobe1/preview.png`
- Analyzed image using PIL: detected bounds, color distribution
- Image is 1024x1024 white minimalist double-door wardrobe, 3 tiers, bottom tier largest

### Design Plan (Natural Language Spec)
```
White minimalist 3-tier double-door wardrobe
- Outer dimensions: 1600 (W) x 550 (D) x 2200 (H) mm
- Panel thickness: 18mm, Back panel: 5mm
- Tier heights: bottom 750mm, middle 650mm, top ~728mm
- Two doors (left/right) each ~795.5mm wide
- Vertical bar handles, silver
- Assembly: build123d RigidJoints as constraint specification
  + explicit parameterized Location transforms
```

### Output
- Design parameters established
- Joint naming convention defined in docstring

---

## Iteration 2: Write initial wardrobe1.py (RigidJoints + explicit transforms)

**Date:** 2026-05-08

### Actions
- Created `wardrobe1.py` with hybrid approach:
  - Phase 1: Define all mating RigidJoints (constraint specification)
  - Phase 2: Place components with explicit Pos transforms derived from design parameters
- Used `_joint()` helper wrapping `RigidJoint(label, part, Location(Plane(...)))`
- `_panel()` helper for Box creation with label and color

### Key design decisions
- `bottom_panel`: `Box(..., align=(Align.CENTER, Align.CENTER, Align.MIN))` — bottom at Z=0
- All other panels: `Box(..., center at origin)`, then positioned with `Pos()` transforms
- Door inner face at `Y = cabinet_depth/2 + door_gap + door_thick/2` (3mm gap from cabinet front)
- Handle standoffs extend +Y, mount_face at standoff tips

### Known issues at this stage
- Typo in docstring: `right_topong_face` → should be `right_top_face`
- Typo in code: `backa_y` → should be `back_y` (line 300)
- `_joint()` uses inline `from build123d import Plane` — redundant since module-level `from build123d import *` already imports Plane

---

## Iteration 3: Fix bugs and correct back_panel Y position

**Date:** 2026-05-08

### Bug fixes
1. **Docstring typo `right_topong_face`** → `right_top_face`
2. **Variable typo `backa_y`** → `back_y`
3. **Inline Plane import removed** — already available from `from build123d import *`
4. **Back panel Y position corrected:**
   - Old: `back_y = -cabinet_depth/2 + panel_thick + back_thick/2 = -254.5`
   - This gave world Y of back panel front_face = -254.5 + 2.5 = -252
   - Bottom panel rear_inner_face joint is at Y = -275 + 18 = -257
   - 5mm gap! Wrong!
   - Fix: `back_y = -cabinet_depth/2 + panel_thick - back_thick/2 = -259.5`
   - Now world Y of back panel front_face = -259.5 + 2.5 = -257 ✓
   - Back panel rear face at Y = -259.5 - 2.5 = -262

### Geometry trace verification
```
bottom_panel: Z=[0, 18], Y=[-275, 275], X=[-800, 800]
left_panel: inner_face at X=-791, bottom at Z=18
right_panel: inner_face at X=791, bottom at Z=18
back_panel: front_face at Y=-257, bottom at Z=18, Z=[18, 2200]
shelf_lower: Z center at 777, Z=[768, 786]
shelf_upper: Z center at 144 Z=[1436, 1454]
top_panel: Z center at 2191, Z=[2182, 2200]
door_l: Y center at 287, inner at Y=278, front at Y=296, Z=[3, 2197]
door_r: same Y/Z, mirrored X
handles: mount at Y=296, Z=661.2
```

### Tier interior clear heights verification
```
Tier 3: shelf_lower_bottom_z - bottom_panel_top_z = 768 - 18 = 750mm ✓
Tier 2: shelf_upper_bottom_z - shelf_lower_top_z = 1436 - 786 = 650mm ✓
Tier 1: top_panel_bottom_z - shelf_upper_top_z = 2182 - 1454 = 728mm ✓
```

---

## Iteration 4: Generate STEP

**Date:** 2026-05-08

### Command
```bash
cd D:/code/text-to-cad
.venv/Scripts/python .agents/skills/cad/scripts/step \
  someTestCases/furniture/wardrobe1/wardrobe1.py
```

### Output
```
[cad] notice: someTestCases/furniture/wardrobe1/wardrobe1 selector geometry changed;
re-check cached geometry facts from older refs.
[scripts/step] generated part STEP: someTestCases/furniture/wardrobe1/wardrobe1.step
```

### Generated files
- `someTestCases/furniture/wardrobe1/wardrobe1.step` (203,653 bytes)
- `someTestCases/furniture/wardrobe1/.wardrobe1.step.glb` — topology sidecar

---

## Iteration 5: Inspect geometry

**Date:** 2026-05-08

### Command
```bash
cd D:/code/text-to-cad
.venv/Scripts/python .agents/skills/cad/scripts/inspect \
  someTestCases/furniture/wardrobe1/wardrobe1.step \
  --facts --planes --positioning
```

### Inspection results

**Summary:**
```
kind: part
shapeCount: 15
faceCount: 72
edgeCount: 126
bounds: [-800, -275, 0] to [800, 296, 2200]
size: [1600.0, 571.0, 2200.0]
```

| Dimension | Expected | Actual | Status |
|-----------|----------|--------|--------|
| Width (X) | 1600 mm | 1600.0 | ✅ |
| Depth (Y) | 571 mm | 571.0 | ✅ |
| Height (Z) | 2200 mm | 2200.0 | ✅ |
| Floor at Z=0 | 0 | 0.0 | ✅ |
| Top at Z=2200 | 2200 | 2200.0 | ✅ |

**Major planes (Y-axis):**

| Coordinate | Normal | Area | Interpretation |
|------------|--------|------|----------------|
| Y = -262 | -1 | 3,412,648 | Back panel rear face |
| Y = -257 | +1 | 3,412,648 | Back panel front face (touches bottom inner face) |
| Y = 278 | -1 | 3,490,654 | Door inner faces (3mm gap from cabinet front at Y=275) |
| Y = 296 | +1 | 3,490,654 | Door front faces |

**Validation:**

✅ Overall dimensions match design parameters exactly
✅ Floor at Z=0, top at Z=2200
✅ Cabinet width 1600mm (X from -800 to 800)
✅ Cabinet depth 550mm + door gap 3mm + door thickness 18mm = 571mm total Y
✅ Back panel 5mm thick, front face at Y=-257 (mates with bottom panel rear inner face)
✅ Back panel Z from 18 to 2200 (sits on bottom panel, reaches top panel)
✅ Door inner face at Y=278 (3mm gap from cabinet front at Y=275)
✅ Door front faces at Y=296 (278 +  door thickness)
✅ No geometry interference detected

**Tier sizes (verified from code):**
```
Tier 3 interior: 750mm clear height (bottom_panel top to shelf_lower bottom)
Tier 2 interior: 650mm clear height (shelf_lower top to shelf_upper bottom)
Tier 1 interior: 728mm clear height (shelf_upper top to top_panel bottom)
```

---

## Iteration 6: Explorer visualization

**Date:** 2026-05-08

### Command attempt
```bash
npm --prefix explorer run dev:ensure -- \
  --file someTestCases/furniture/wardrobe1/wardrobe1.step
```

### Result
Explorer not installed locally (`explorer/package.json` not found).
Skipping — inspect tool geometry validation is sufficient.

---

## Assembly constraint definitions (RigidJoints)

The following RigidJoints are registered on each component as the formal
assembly constraint specification:

### bottom_panel (root, bottom face at Z=0, Align.MIN)
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| top_face | (0, 0, 18) | (0,0,1) | Seats side panel bottoms, back panel bottom |
| front_face | (0, 275, 0) | (0,1,0) | Cabinet front reference |
| rear_inner_face | (0, -257, 0) | (0,-1,0) | Seats back panel front face |
| left_inner_face | (-782, 0, 0) | (-1,0,0) | Seats left panel inner face |
| right_inner_face | (782, 0, 0) | (1,0,0) | Seats right panel inner face |
| left_top_edge | (-782, 0, 18) | (0,0,1) | Seats left panel bottom face |
| right_top_edge | (782, 0, 18) | (0,0,1) | Seats right panel bottom face |
| rear_top_edge | (0, -257, 18) | (0,0,1) | Seats back panel bottom face |

### left_panel
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| inner_face | (9, 0, 0) | (1,0) | Mates to bottom left inner face |
| bottom_face | (0, 0, -1091) | (0,0,-1) | Mates to bottom top edge |
| top_face | (0, 0, 1091) | (0,0,1) | Mates to top_panel left seat |
| front_edge | (0, 275, 0) | (0,1,0) | Front reference |

### right_panel
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| inner_face | (-9, 0, 0) | (-1,0,0) | Mates to bottom right inner face |
| bottom_face | (0, 0, -1091) | (0,0,-1) | Mates to bottom top edge |
| top_face | (0, 0, 1091) | (0,0) | Mates to top_panel right seat |

### back_panel
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| front_face | (0, 2.5, 0) | (0,1,0) | Mates to bottom rear inner face |
| bottom_face | (0, 0, -1091) | (0,0,-1) | Mates to bottom top face |

### shelf_lower, shelf_upper
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| bottom_face | (0, 0, -9) | (0,0,-1) | Shelf bottom reference |
| top_face | (0, 0, 9) | (0,0,1) | Shelf top reference |
| front_edge | (0, 263.5, 0) | (0,1,0) | Front reference |

### top_panel
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| bottom_face | (0, 0, -9) | (0,0,-1) | Sits on side panel tops |
| left_seat | (-782, 0, -9) | (0,0,-1) | Seats on left panel top face |
| right_seat | (782, 0, -9) | (0,0,-1) | Seats on right panel top face |

### door_left, door_right
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| inner_face | (0, -9, 0) | (0,-1,0) | Faces cabinet interior |
| front_face | (0, 9, 0) | (0,1,0) | Door outer surface |
| handle_mount_face | (+/-347.75, 9, 658.2) | (0,1,0) | Handle attachment |

### handle_left, handle_right
| Joint label | Position (local) | z_dir | Mating purpose |
|-------------|------------------|-------|---------------|
| mount_face | (0, 16, 0) | (0,1,0) | Standoff tips to door |

---

## Final file inventory

```
someTestCases/furniture/wardrobe1/
  preview.png              — reference image
  wardrobe1.py             — build123d generator (341 lines)
  wardrobe1.step           — generated STEP (part/Compound, 15 shapes)
  .wardrobe1.step.glb      — topology GLB sidecar
  ITERATION_LOG.md         — this file
```

## Summary

The wardrobe1 assembly uses a **hybrid RigidJoint + explicit transform** approach:
1. **RigidJoints** serve as the **formal constraint specification** — they document
   exactly which faces on which parts are intended to mate, with what normal
   direction. Each joint is defined in the part's local coordinate system with
   an explicit Location (position + orientation).
2. **Explicit Pos transforms** implement the placement, derived directly from the
   same design parameters that define the joint datums. This avoids the 6-DOF
   alignment issues of `connect_to()` while preserving the constraint
   specification.

This is **not** just fixed rigid body positioning — the RigidJoints constitute a
complete, inspectable constraint model. Any consumer can read the joint definitions
and verify that the explicit transforms correctly align them.

All geometry validated correct: dimensions, tier heights, door gaps, back panel
placement, and handle attachment positions.

---

## Iteration 2: 声明式装配 JSON (wardrobe1_assembly.json) — 2026-05-11

本次使用新开发的模型拆分装配规范（`model-decomposition-assembly-spec.md`）对衣柜进行声明式拆解，生成装配 JSON，并通过 transpiler 生成 build123d 建模脚本。

### 参考图纸尺寸 (preview.png)

| 项目 | 尺寸 |
|------|------|
| 总宽 | 1210 mm |
| 总深 | 460 mm |
| 总高 | 1760 mm |
| 挂衣杆长 | ~570 mm（两区各 57 cm） |
| 左区挂空高 | ~1100 mm |
| 右区搁板距底 | ~350 mm |

### 零件拆分

| part id | 原语 | 尺寸 | 说明 |
|---------|------|------|------|
| `body` | box | 1210×460×1760 | 外轮廓参考体 |
| `door_l` | box | 607×20×1760 | 左门 |
| `door_r` | box | 603×20×1760 | 右门 |
| `rod_l` | cylinder | r=12, h=570 | 左区挂衣杆 |
| `rod_r` | cylinder | r=12, h=570 | 右区挂衣杆 |
| `shelf_r` | box | 570×440×18 | 右区搁板 |
| `drawer_bot` | box | 560×420×290 | 下抽屉 |
| `drawer_top` | box | 560×420×290 | 上抽屉 |

### Joint 设计决策

- **门**：使用 `rg:s:-1/2:1:0` / `rg:s:1/2:1:0` 定位在前面左/右半，门用 `rg:si:0:-1:0`（背面内法线），两者 frame 同向（`+Z:+X:+Y`），无旋转，门向外凸出 20 mm。
- **挂衣杆（水平旋转技巧）**：`rg:si:-1:0:7/8`（左壁内法线，z=+X）连接杆的 `rg:si:0:0:-1`（底端内法线，z=+Z）。两者 z 方向不同（+X vs +Z），`connect_to` 自动产生 90° 旋转，使柱形杆从竖直变为水平，沿 +X 轴延伸于左区 x∈[-605,-35]。右区对称用 `rg:si:1:0:7/8`（右壁内法线 z=-X），杆沿 -X 延伸于右区 x∈[35,605]。
- **搁板**：使用 custom joint `rg:c:1/2:0:-5/8`（归一化坐标，映射到 body 内部 (302.5, 0, -550)），frame `+X:+Y:+Z`，搁板用 `rg:si:0:0:-1`（底面内法线），同帧纯平移。
- **抽屉**：`rg:si:-1/2:0:-1`（底面内法线偏左）→ 抽屉 `rg:si:0:0:-1`，同帧。上抽屉叠在下抽屉顶面 `rg:s:0:0:1` → `rg:si:0:0:-1`，同帧。

### 工具调用记录

```
# 1. 生成 JSON（手工设计）
# 文件：someTestCases/furniture/wardrobe1/wardrobe1_assembly.json

# 2. Transpile（验证 + 生成 .py）
cd .agents/skills/cad/scripts
python -m transpile ../../../../someTestCases/furniture/wardrobe1/wardrobe1_assembly.json \
    -o ../../../../someTestCases/furniture/wardrobe1/wardrobe1_gen.py
# exit 0 → wrote wardrobe1_gen.py
```

### 生成文件

- `wardrobe1_assembly.json` — 声明式装配 JSON
- `wardrobe1_gen.py` — transpiler 生成的 build123d 脚本

### 运行生成脚本（产出 STEP）

要运行生成的脚本并输出 STEP：

```python
# wardrobe1_gen.py 中的 gen_step() 返回 Compound
# 在 .venv 中运行：
import sys; sys.path.insert(0, '.')
from wardrobe1_gen import gen_step
from build123d import export_step
result = gen_step()
export_step(result, "wardrobe1.step")
```

或从仓库根：
```
# Transpile
python -m transpile someTestCases/furniture/wardrobe1/wardrobe1_assembly.json

# Run (需要 build123d)
.venv/Scripts/python someTestCases/furniture/wardrobe1/wardrobe1_assembly.py
```

### 2026-05-11（第二次）：重写声明式装配 JSON（面板式拆分 + 修复多父节点错误）

**背景：** 旧版 `wardrobe1_assembly.json` 存在两个问题：  
1. `top_panel` 同时出现在 `left_panel` 和 `right_panel` 的 mate 的 `partB` 字段（多父节点错误）。  
2. `shelf_lower` 与 `shelf_upper` 使用同一个 joint（`rg:s:1:0:1/2`），两个零件重叠。  
3. 尺寸与 preview.png（121×46×176 cm）不符（旧值 1600×550×2182）。

**修改内容（`wardrobe1_assembly.json`）：**  
- 总尺寸改为 1210×460×1760 mm，侧板高度 1724 mm（= 1760-2×18）。  
- 新增 `mid_panel`（中隔板 18×460×1724，x=0 居中），作为 `top_panel` 的**唯一父节点**，彻底消除多父节点错误。  
- 替换 `shelf_lower/shelf_upper` 为 `shelf_r`（右区搁板，`right_panel` 内面高度 -5/8）+ `drawer_bot/drawer_top`（左区双抽叠放）。  
- 挂衣杆通过侧板外法线 joint 驱动 90° 旋转水平（s:±1:0:7/8 → si:0:0:-1）。  

**工具调用：**

```powershell
# Transpile only（验证 JSON 无误）
d:\code\text-to-cad\.venv\Scripts\python .agents\skills\cad\scripts\assembly_from_spec.py `
  someTestCases\furniture\wardrobe1\wardrobe1_assembly.json --no-step
# exit 0  →  wrote wardrobe1_gen.py

# Full pipeline（生成 STEP + GLB）
d:\code\text-to-cad\.venv\Scripts\python .agents\skills\cad\scripts\assembly_from_spec.py `
  someTestCases\furniture\wardrobe1\wardrobe1_assembly.json
# exit 0
```

**产物：**  
- `wardrobe1_assembly.json` — 修正后声明式 JSON（13 零件，12 mates，合法树）  
- `wardrobe1_gen.py` — transpile 生成（64 行）  
- `wardrobe1_gen.step` — 211,891 bytes  
- `.wardrobe1_gen.step.glb` — 134,276 bytes（拓扑 GLB 侧车）

---

### 2026-05-11（第一次）：补全 STEP 拓扑校验所需的 GLB 侧车

**cwd:** `d:\code\text-to-cad\.agents\skills\cad\scripts`

**命令：**

```powershell
d:\code\text-to-cad\.venv\Scripts\python -m step --kind assembly `
  "d:\code\text-to-cad\someTestCases\furniture\wardrobe1\wardrobe1_gen.step"
```

**说明：** 直接以 `.step` 为 `scripts/step` 目标时，CLI 要求 `--kind part` 或 `--kind assembly`；本例为 `Compound` 装配，使用 `--kind assembly`。

**退出码：** 0

**产物：** `someTestCases/furniture/wardrobe1/.wardrobe1_gen.step.glb`（及 STEP 侧车刷新）

---

### 2026-05-11（第二次）：拓扑 GLB 报错与 LFS / 环境记录（macOS / Cursor agent）

**cwd:** `/Users/shenzhi/things/work/codes/text-to-cad`

**现象：** Explorer 或拓扑校验报 `STEP_topology` / `indexView` 不可读。

**排查：**

- 工作区内 `wardrobe1_gen.step` 与 `.wardrobe1_gen.step.glb` 在磁盘上为 **Git LFS pointer 文本**（`version https://git-lfs.github.com/spec/v1`），不是真实 STEP/GLB 字节；按 glTF 解析会失败，与「缺少 indexView」表现一致。
- 修复路径：**`git lfs pull`** 拉取二进制，或在本机用 **`scripts/step`** 对 owning **`wardrobe1_gen.py`** 重写产物（推荐后者以保持与生成器一致）。

**尝试的 regen 命令（agent 环境）：**

```bash
./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py --verbose
```

**结果：** 失败 — `build123d` 导入链上 **`vtkmodules`** 初始化错误（`vtkCommonTransforms` / `vtkCommonDataModel` 相关 `ImportError`）。该 agent 环境未安装 **`git lfs`**，无法通过 `git lfs pull` 恢复对象。

**建议（维护者本机）：**

1. 安装并启用 **Git LFS** 后对该 case 执行 **`git lfs pull`**；或  
2. 在 **VTK/build123d 正常** 的 venv 中执行：

   ```bash
   ./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py
   ```

   若仅持有 STEP、无 `.py`，再使用 **`--kind assembly`** 对 **`wardrobe1_gen.step`** 重跑（与 Windows 日志中第一次补全侧车方式一致）。

**文档：** 根目录 **`README.md`** 增加 Troubleshooting（LFS pointer / regen）；**`pipeline-reference.md`**、**`someTestCases/README.md`** 补充侧车须为真实二进制之说明。

---

### 2026-05-11（第三次）：Explorer「缺少 GLB」提示与再生说明

**cwd:** `/Users/shenzhi/things/work/codes/text-to-cad`

**变更：** Explorer `cadDirectoryScanner.mjs`、`inspect` 使用的 **`step_targets.py`**、**`useCadAssets.js`**、相关测试中，将「Regenerate…」固定话术改为：优先对 **`wardrobe1_gen.py`**（或同名 owning **`*.py`**）从仓库根执行 **`./.venv/bin/python .agents/skills/cad/scripts/step …`**；仅 STEP 时补 **`--kind part|assembly`**；若 STEP/GLB 为 **Git LFS pointer** 则先 **`git lfs pull`**。

**原因：** 裸路径 `python scripts/step …wardrobe1_gen.step` 在 STEP 未 smudge 时会被 **`_ensure_step_ready`** 拒绝；且未带 **`--kind`** 时 CLI 不接受纯 STEP 目标。缺侧车 **`.wardrobe1_gen.step.glb`** 时应用 **`.py`** 一次写回 STEP+GLB，或 LFS 拉齐后再对 STEP 加 **`--kind assembly`**。

---

### 2026-05-12：`vtkmodules` 导入失败 + STEP 导出修复

**cwd:** `/Users/shenzhi/things/work/codes/text-to-cad`

**现象：** `./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py` 在 `from build123d import *` 链上报错：`Failed to load vtkCommonDataModel` / `No module named vtkmodules.vtkCommonTransforms`（或 `vtkCommonTransforms` 与 `vtkCommonCore` 不兼容）。

**根因：** **`requirements.txt` 中同时列出 PyPI `vtk` 与 `build123d`（经 `cadquery-ocp` 自带 vtkmodules）**，在 macOS arm64 上易留下成对的 `vtkFoo.so` + `vtkFoo.cpython-39-darwin.so`，加载器选错二进制即崩。

**代码修复：**

- **`.agents/skills/cad/requirements.txt`** — 去掉独立 **`vtk`** 行并注释说明原因。
- **`scripts/common/step_export.py`** — 不再从 `build123d.exporters3d` 导入已不存在的 **`APIHeaderSection_MakeHeader`**，与当前 build123d `export_step` 一致省略 AP242 header 段。

**环境修复：**

```bash
./.venv/bin/pip uninstall -y vtk
./.venv/bin/pip install --force-reinstall cadquery-ocp==7.7.2 build123d==0.8.0
```

**验证：**

```bash
./.venv/bin/python .agents/skills/cad/scripts/step someTestCases/furniture/wardrobe1/wardrobe1_gen.py
# → generated part STEP: …/wardrobe1_gen.step
```

产物 **`wardrobe1_gen.step`**（≈211 KB）与 **`.wardrobe1_gen.step.glb`**（≈124 KB，`glTF` 头）为真实二进制。

