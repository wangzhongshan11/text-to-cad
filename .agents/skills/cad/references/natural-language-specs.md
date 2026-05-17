# 自然语言 CAD 规格

将用户叙述请求转为 CAD 简报时阅读本文。勿要求用户提供 JSON。若用户自愿提供 JSON，提取相同信息但继续以叙述笔记与 build123d 源码推进工作流。

## 目标

在编写源码或运行工具之前，将自然语言需求转为可执行的建模简报。

简报应回答：

- 建模对象是什么？
- 属于零件、装配体、修改、检查任务还是次要输出请求？
- 指定了哪些尺寸与单位？
- 哪些尺寸缺失但可推断？
- 哪些特征是必需的？
- 哪些面、轴、原点、关节或接口控制定位？
- 请求哪些输出文件？
- 在宣称成功之前必须校验什么？

## 简报格式

使用简洁 Markdown 笔记，勿用面向用户的结构化模式。

推荐结构：

```text
CAD brief:
- Model: <part or assembly name>
- Output: STEP primary; secondary outputs if requested
- Units: <explicit or assumed>
- Coordinate convention: <origin, base plane, up axis>
- Overall dimensions: <width/depth/height or equivalent>
- Functional features: <holes, slots, ribs, bosses, pockets, shells, text, etc.>
- Positioning/mating: <interfaces, datums, constraint types between box/cylinder/sphere bodies, alignment rules>
- Validation targets: <bbox, solid count, labels, measurements, refs>
- Assumptions: <only meaningful inferred choices>
```

## 示例：简单零件

用户原话：

```text
Make a 100 mm by 60 mm by 6 mm mounting plate with rounded corners, four M4 clearance holes 10 mm in from the corners, and a 20 by 12 mm rectangular cutout in the center.
```

智能体简报：

```text
CAD brief:
- Model: mounting_plate, single STEP part.
- Units: millimeters.
- Origin: center of plate; base plane XY; +Z is thickness direction.
- Body: rounded rectangular plate, 100 × 60 × 6 mm.
- Corner radius: not specified; assume 3 mm.
- Holes: four 4.5 mm M4 clearance through-holes, 10 mm in from each corner.
- Cutout: centered rectangular through-cut, 20 × 12 mm.
- Validation: one positive-volume solid, bbox 100 × 60 × 6 mm, four holes, one center cutout, label mounting_plate.
- Explorer: return link to the STEP file.
```

## 示例：装配体

用户原话：

```text
Design a two-piece enclosure, 120 by 80 by 35 mm, with a lid that sits on top and four screw bosses aligned between base and lid.
```

智能体简报：

```text
CAD brief:
- Model: enclosure assembly with base and lid.
- Units: millimeters.
- Assembly origin: center of enclosure footprint; +Z upward.
- Base: hollow lower shell, exterior 120 × 80 mm footprint; height derived from total height minus lid thickness.
- Lid: separate plate on top; assume 3 mm lid thickness unless user gave another value.
- Bosses: four aligned screw bosses; assume M3 unless unspecified dimensions make this unsafe.
- Positioning: base top and lid bottom as mating datums via constraints (box bodies); screw axes aligned; see constraint-assembly.md.
- Validation: labeled base and lid children, bbox near 120 × 80 × 35 mm, aligned hole/boss axes, Explorer link returned.
```

## 澄清策略

仅当缺失信息影响配合、安全、合规或导致无法建模时，提一个聚焦问题；否则带着假设继续并报告假设。

应提问的情况：

- 对物理对象未提供任何尺寸。
- 描述了配合接口但未说明配合几何。
- 零件安全关键、承载、承压、医疗或受合规约束。
- 所请求输出依赖缺失的源码文件或导入几何。

不必提问的情况：

- 默认间隙孔标准已够用。
- 装饰圆角半径可安全假设。
- 原点/方向可选定并说明。
- 用户只要概念初版 CAD 模型。

## 复杂装配简报

用户描述柜体、机箱、多层支架等**多区域**装配时，在简报中显式列出子链路与定位策略，再写源码。

补充字段示例：

```text
Assembly decomposition:
- Region A (shell): bottom, sides, back, top — constraint_assembly, ground=bottom
- Region B (interior): shelves, dividers — Location from inner envelope formulas
- Region links: B placed after A resolves; no body_id overlap between regions
- Constraint scope: only box/cylinder/sphere in CONSTRAINTS; count per region
- Validation: solve specs per constraint region; inspect positioning on full STEP
```

规划顺序：拆区域 → 每区域选 Location 或约束 → 区域间连接 → 再展开 `CONSTRAINTS` / `gen_step()`。实现模式见 `build123d-modeling.md`；约束字段见 `constraint-assembly.md`。

## 成功标准

当简报包含足以定义以下内容的信息时，即可进入建模：

- 源码文件路径
- STEP 目标路径
- 单位
- 局部坐标系
- 命名参数
- 特征方案
- 标签
- 预期包围盒或关键测量
- Explorer 链接目标
