# build123d 建模模式

编写或修复 build123d Python 源码时阅读本文。

## 建模目标

创建可供 STEP 输出的有效 BREP 模型，而非视觉网格。优先封闭实体、明确标签与稳定的参数化尺寸。

## 拓扑栈

按此顺序思考：

```text
Vertex → Edge → Wire → Face → Shell → Solid → Compound
```

常规 STEP 输出应返回以下之一：

- 有效 `Solid`
- 有效实体的组合体
- 带标签的装配组合体

除非用户明确要求，否则避免返回松散线、开放面或构造曲面。

## `gen_step()` 返回值

```python
def gen_step():
    ...
    return shape_or_compound
```

只返回 build123d 的 `Solid`、`Compound` 等形体。约束装配用 `return constraint_assembly(CONSTRAINTS, parts)`（同样是 `Compound`，见 `constraint-assembly.md`）。

不要 `return` dict、list 或任何 envelope。STEP 默认写在脚本同目录、与脚本同名的 `.step`；若要改路径，在模块顶层写 `STEP_OUTPUT = "relative/path.step"`，不要从 `gen_step()` 返回路径字段。

## 参数优先

将有意义尺寸放入命名变量：

```python
width = 80.0
depth = 50.0
thickness = 6.0
hole_diameter = 4.5
hole_offset_x = 30.0
hole_offset_y = 17.5
```

避免将重要数值埋在几何调用内部。

## 坐标系

声明或注释约定：

```text
Origin: center of primary part or chosen mating datum
XY: main base/sketch plane
+Z: up/extrusion direction
```

有意使用 `Location`、`Plane` 与 `Axis`。对定位敏感任务与源码级装配关系，见 `positioning.md`。

## 构造器上下文

选用与几何匹配的上下文：

```python
with BuildLine() as path:
    ...

with BuildSketch() as profile:
    ...

with BuildPart() as part:
    ...
```

典型流程：

```text
curves/paths → sketches/profiles → solids/features → labels → STEP
```

## 基本体

设计意图合适时使用规范基本体：

- `Box`：矩形块与板
- `Cylinder`：凸台、杆、销与减材圆柱切除
- `Sphere`：旋钮或球端
- `Torus`：环与圆扫掠
- `Cone`：锥形特征
- `Wedge`：斜面实体

形状由截面驱动时使用草图加 `extrude`、`revolve`、`sweep` 或 `loft`。

## 特征操作

将设计意图映射到操作：

```text
hole              → Hole or subtractive cylinder
counterbore       → CounterBoreHole
countersink       → CounterSinkHole
slot              → slot profile + subtractive extrude
boss/standoff     → cylinder addition + central hole
rib               → extruded rectangular/triangular profile
rounded edge      → fillet
beveled edge      → chamfer
hollow enclosure  → shell or subtractive inner volume
revolved part     → revolve profile
swept tube/rail   → sweep profile along path
```

## 选择实践

尽可能避免脆弱拓扑序。按下述方式选择：

- 轴或法向
- 位置或包围位置
- 平面分组
- 特征意图
- 稳定构造平面
- 用于下游校验的已检查 `@cad[...]` 引用

源码操作中，优先采用鲁棒选择器（如按轴或位置取顶/底），而非任意列表下标。

## 装配与定位

零件局部坐标与 `inspect` 校验见 `positioning.md`。box/cylinder/sphere 约束词汇与 `constraint_assembly` API 见 `constraint-assembly.md`。

### 装配分解（子链路）

复杂装配先按**功能区域**拆子链路，再为每段选定位方式。不要把所有零件默认塞进一个 `CONSTRAINTS`。

| 范围 | 推荐 | 示例 |
|------|------|------|
| 区域内、重复件 | 公式 + `Location` / `GridLocations` | 等距层板、柱阵 |
| 区域内、少量配合 | 小规模 `constraint_assembly` | 围板贴合、双柱 |
| 区域间 | 少量约束，或对子 `Compound` 一次 `.moved(...)` | 托盘装入机箱、台面落四腿 |

规则：

- 同一 `body_id`：只进 `CONSTRAINTS` **或** 只用 `Location`，不要两种同时定位同一零件。
- 已用约束求解的区域，其相关零件不要在区域外再用堆砌补位；应在简报里拆成独立子链路（见 `natural-language-specs.md`）。
- 区域间优先连接面/轴/铰链，避免对大组件重复写全套 in_plane 偏移。

```python
def gen_step():
    shell = constraint_assembly(SHELL_CONSTRAINTS, shell_parts)
    interior = Compound(children=[panel.moved(Location((x, y, z))) for ...])
    return Compound(label="assembly", children=[shell, interior])
```

仓库示例：`examples/constraint/assemblies/wardrobe_closet/wardrobe_closet.py`（围板约束 + 层板 Location）。对话 prompt 样例：`examples/constraint/chatExamples/prompts.md`。

## 标签与装配体

为每个导出零件与装配子项打标签：

```python
base.label = "base"
lid.label = "lid"
assembly.label = "electronics_enclosure"
```

重复零件保持变换或关节连接明确，生成后检查 frame/定位。

## 常见失败模式

- 圆角半径大于局部棱边几何允许值。
- 减材刀具未完全穿透目标材料。
- 开放草图截面导致无效或缺失面。
- 布尔或圆角后面选择器发生变化。
- 用重新导入生成 STEP 代替 Python 装配源码导致源码级装配组合丢失。
- 零件原点随意导致后续配合检查含糊。
- `CONSTRAINTS.bodies` 尺寸与 build123d 实体尺寸不一致。

生成或校验失败时使用 `repair-loop.md`。
