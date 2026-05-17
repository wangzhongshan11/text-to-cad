# 约束装配

`gen_step()` **返回 `shape_or_compound`**。多零件 box / cylinder / sphere 配合：模块级 `CONSTRAINTS` + `constraint_assembly(CONSTRAINTS, parts)` → `Compound`。零件几何在 build123d 中建模（局部原点 = 几何中心）；零件间不用 `RigidJoint.connect_to()` 定位。

装配分解（子链路、区域内 `Location` vs 约束、区域间连接）见 `build123d-modeling.md` 装配分解一节；自然语言需求如何拆区域见 `natural-language-specs.md`。

---

## `gen_step()` 模板

```python
from constraint.assemble import constraint_assembly

CONSTRAINTS = {
    "ground": "base",
    "bodies": {
        "base": {"primitive": "box", "size": [200, 150, 20]},
        "b1": {"primitive": "box", "size": [40, 30, 25]},
    },
    "constraints": [
        {"type": "plane_coincident", "a": "b1.-z", "b": "base.+z", "opposed": True},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "offset": 12.5},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "x", "value": 30},
        {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "y", "value": 40},
    ],
}

def _make_box(size):
    from build123d import Box, BuildPart
    with BuildPart() as part:
        Box(*size)
    return part.part

def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {"base": _make_box((200, 150, 20)), "b1": _make_box((40, 30, 25))},
    )
```

| 项 | 说明 |
|----|------|
| `CONSTRAINTS` | `ground`、`bodies`（box/cylinder/sphere）、`constraints` |
| `parts` | 键与 `bodies` 一致；局部坐标下的 build123d 形体 |
| 返回值 | `Compound` |
| `report_path` | 可选；写入紧凑求解报告 JSON（字段见下表） |

`bodies` 的 `size` 与 build123d 尺寸共用同一组 Python 变量。

### 规模上限（`schema` 强制）

| 项 | 默认值 | 说明 |
|----|--------|------|
| `max_bodies` | 40 | 超出抛 `ConstraintSchemaError`，除非 spec 内 `limits` 放宽 |
| `warn_bodies` | 30 | 超出写入 `warnings`（`large_assembly`），建议拆子链路 |
| `max_constraints` | 240 | 同上 |
| 绝对上限 | 64 体 / 400 约束 | `limits` 不可超过 |

```json
"limits": { "max_bodies": 48, "max_constraints": 300, "warn_bodies": 32 }
```

更大装配：拆多个 `CONSTRAINTS` 或 Location 子 `Compound`（见 `build123d-modeling.md`）。

---

## 零件与 `parts` 映射

- 列入 `bodies` 的刚体由求解器放置；勿对同一 `body_id` 再单独 `Location`。
- 未列入 `bodies` 的件：在 `gen_step()` 中用 `Location` 建子 `Compound`，再与求解结果 `Compound(children=[...])` 合并（见 `build123d-modeling.md`）。

---

## 特征引用（`<body_id>.<feature_id>`）

**Box**：`center`，`±x`…`±z`，`axis_*`，`edge_*`（12 棱）。  
**Cylinder**（轴 +Z）：`center`，`top`/`bottom`，`axis`。  
**Sphere**：`center`，`equator`，`axis_x`/`axis_y`/`axis_z`。

---

## 约束类型

`fix`、`point_coincident`、`plane_coincident`、`axis_coaxial`、`axis_parallel`、`plane_distance`、`point_plane_offset`（含 `in_plane` x/y）、`contact`、`hinge`（语法糖）。

### `point_plane_offset`

- 无 `in_plane`：`offset` 为点到参考平面的有符号距离（沿法向）。
- 有 `in_plane: x|y`：`value` 为点在平面切向轴上的坐标分量。
- 与 `contact` 叠用时，`offset` 须与贴合关系一致（常见：贴底时 `offset` = 该体高度/2，相对 `ground.+z`）。

### 竖板姿态

竖板/立柱：`axis_parallel` 锁 `axis_z` 后，再锁厚度向 `axis_x` 或 `axis_y` 之一与 `ground` 同向；仅锁 `axis_z` 时绕 Z 仍可能自由旋转且残差可≈0。

---

## 求解报告 JSON（`report_path` / `constraint solve` stdout）

| 字段 | 含义 |
|------|------|
| `status` | `ok` / `underconstrained` / `overconstrained` / `solve_failed` |
| `ground` | 接地体 id |
| `solve_ok` | 残差低于阈值 |
| `residual_max` | 最大约束残差 |
| `free` | 欠约束自由度摘要（≤3 条） |
| `hint` | 修复建议（≤5 条） |
| `conflict` | 冲突约束（≤3 条） |
| `rotation_issues` | 求解后旋转审计（如仅锁 `axis_z` 可绕 Z 空转） |

`status=ok` 要求：残差达标、无 `free` 自由度摘要、无 `rotation_issues`。仅锁竖板 `axis_z` 时通常为 `underconstrained`。

`constraint_assembly` 在 `status` 非 `ok`/`underconstrained` 时抛错。生成后仍须 `inspect`（`repair-loop.md`、`inspection-and-validation.md`）。

示例 JSON 规格与 `out/*.transforms.json` 见 `examples/constraint/README.md`。

---

## 命令

```bash
./.venv/bin/python .agents/skills/cad/scripts/step examples/constraint/assemblies/box_on_box/box_on_box.py
./.venv/bin/python .agents/skills/cad/scripts/constraint solve examples/constraint/specs/box_on_box.json
./.venv/bin/python examples/constraint/run_validation.py
```

求解失败：改 `CONSTRAINTS` 或尺寸；`status == "ok"` 后 `scripts/step`，再 `inspect`（`positioning.md`）。
