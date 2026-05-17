# 定位与配合校验

零件局部坐标系、参数化偏置、生成后 **`inspect`** 校验。多零件 box / cylinder / sphere 之间的摆放见 **`constraint-assembly.md`**（`gen_step()` 仍返回 `shape_or_compound`）。

## 核心规则

- 几何与偏置在 Python 源码中定义，生成后校验。
- 勿通过改导出 STEP 来移动零件。
- 多零件原语配合：编辑 `CONSTRAINTS` 与 `constraint_assembly` 的 `parts`，勿用零件间 `RigidJoint.connect_to()`。

## 术语

- **CLI `inspect mate`**：只读，比较两个 `@cad[...]` 引用之间的平移/对齐误差。
- **CLI `inspect frame` / `measure`**：坐标系与标量距离检查。
- **约束装配**：`CONSTRAINTS` 数据 + `constraint_assembly(...)` 返回已摆放的 `Compound`。

## 零件局部坐标系

建模前约定（写在脚本注释或变量名中）：

```text
- 原点：中心、安装面、或功能轴上的基准点
- +Z：主拉伸/厚度方向（除非另有主基准）
- 命名尺寸：孔距、筋位、间隙、板厚
```

常见默认：对称件原点在形体中心；板件原点在 footprint 中心、厚度沿 Z；轴类原点在旋转轴上。

## 零件内部特征放置

```python
hole_offset_x = 30
hole_offset_y = 17.5
with Locations((-hole_offset_x, -hole_offset_y), (hole_offset_x, hole_offset_y)):
    Hole(radius=hole_d / 2)
```

## 生成与校验

```bash
# macOS / Linux（仓库根目录）
./.venv/bin/python .agents/skills/cad/scripts/step path/to/assembly.py
./.venv/bin/python .agents/skills/cad/scripts/inspect refs path/to/assembly.step --facts --planes --positioning

# Windows（仓库根目录）
.\.venv\Scripts\python.exe .agents\skills\cad\scripts\step path\to\assembly.py
.\.venv\Scripts\python.exe .agents\skills\cad\scripts\inspect refs path\to\assembly.step --facts --planes --positioning
```

直接传入已生成的装配 `.step` 视为导入 STEP；要保留源码组合语义请传入 `.py`。

## `inspect mate`

```bash
python scripts/inspect mate \
  --moving '@cad[path/to/assembly.step#moving_selector]' \
  --target '@cad[path/to/assembly.step#target_selector]' \
  --mode flush \
  --axis z
```

超差时改 `CONSTRAINTS` 或 Python 尺寸，重新 `scripts/step`。

## 检查失败时改什么

- `CONSTRAINTS` / `bodies` 尺寸
- 零件局部原点与特征偏置
- 草图平面、对称符号

然后重新生成；勿手改 STEP。

## 报告示例

```text
Positioning:
- constraint solve: ok
- base/block flush mate: delta 0.00 mm
```

无定位要求时写 `Positioning: not applicable`。未跑的检查写 `not checked`。
