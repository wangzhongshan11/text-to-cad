# 约束装配机制优化方案 v1

> **读者**：仓库维护者。本文是对 `docs/internal/constraint-assembly-plan.md` 当前实现的演进设计稿，目标是让 LLM 通过**约束机制**装配一般刚体模型时，难易度与最终效果**至少达到位置堆砌（Location）同级**，并在 Location 做不到的能力维度（父位姿求解、非轴对齐父面、mating 残差验证、跨层复用）**严格优于** Location。
>
> 本方案**不引入二级 LLM**。所有"补全"动作要么由编译器/求解器确定性完成，要么以候选枚举形式写入 `report`，由作者（或更高层 Agent 的下一轮调用）显式选择。
>
> Codex / 代理日常装配仍读 `.agents/skills/cad/references/constraint-assembly.md`，不要把本文当作参考手册。

---

## 0. 文档定位与命名

- **路径**：`docs/internal/constraint-assembly-optimize1.md`
- **关系**：
  - 上游：`constraint-assembly-plan.md`（已实现的 MVP 计划）
  - 下游：实现完成后，相关章节回写至 `.agents/skills/cad/references/constraint-assembly.md`
- **范围**：仅约束装配求解器内核 + DSL + 报告链路；**不**改 build123d、不改 inspect、不改 render。
- **不在范围**：
  - 替代 build123d 做零件建模
  - 2D 草图约束
  - 二级 LLM 自动 gauge 补全（明确排除）
  - 自然语言到 CONSTRAINTS 的端到端 prompt 设计（属于 skill 文档范畴）

### 0.1 单位与尺度约定（全文统一）

| 量 | 单位 | 说明 |
|----|------|------|
| 长度（size / offset / value / place / at） | **mm** | 与现有 build123d / STEP 输出一致 |
| 角度 | **rad** | 仅 `yaw_only` 与 `hinge.angle` 等显式角度字段 |
| 方向向量 | **无量纲单位向量** | feature 表 `axis_*` 已归一化 |
| 残差阈值 `RESIDUAL_TOL` | **1e-6 mm** | 不变 |
| 过约束阈值 | **100 × RESIDUAL_TOL = 1e-4 mm**（可通过 `dof_policy.overconstrained_threshold` 覆盖） | 见 §4.3、§9.4 |
| sensitivity 阈值 | **相对 SVD 最大奇异值的 1e-3 倍** | 见 §10.1 与 §C.4 |

所有数字字段除非另注，均为 mm 或上述无量纲量。下文章节不再重复声明。

---

## 1. 目标、原则、非目标

### 1.1 总目标

让以下命题成立（一般刚体模型，不限定零件类型/数量）：

```text
LLM(写约束 spec).cost   ≤   LLM(写 Location 堆砌).cost
LLM(写约束 spec).quality ≥   LLM(写 Location 堆砌).quality
```

其中 `cost` 包含 token、schema 记忆、引用拼写、错误恢复轮数；`quality` 包含装配几何正确性、可验证性、可复用性、可参数化性。

### 1.2 核心原则

**P0（自主性原则）** —— 全文最高优先级，所有设计决策必须服从。

> **不影响模型装配的自由度用默认；影响模型装配的自由度必须显式给全。**

形式化定义见第 4 章；它把所有 DOF 分为三类（mating / gauge / layout），并规定每类对应的处理路径。

**P1（信息维度对齐原则）**

> 让 LLM 写一条约束所需要的"有效信息"，在 token 维度上与 Location `(x, y, z)` 同级；其余信息通过 schema 默认、policy 全局声明、程序化生成承担。

**P2（坐标变换隐藏原则）**

> 作者从不写跨 frame 的 4×4 矩阵；所有坐标变换由编译器/求解器/接口体承担。作者只写：(a) 父 feature 引用，(b) 在该 feature 切向上的标量参数。

**P3（确定性可审计原则）**

> 任何"默认"都必须在 report 中可见；任何"展开"都必须可 dry-run 回溯。系统不静默替作者选等价解。

**P4（局部失败原则）**

> 失败必须被定位到具体的体 / 关系 / 层 / 维度，且修复建议必须停留在与作者输入同抽象层级（建议补 relation，而非建议补 6 条基础约束）。

### 1.3 非目标

- **不**做 SolidWorks 风格的产品宏库（wheel/drawer/hinge_pin/screw 等数十宏）。
- **不**做基于 LLM 的自动 gauge 补全（连续 DOF 仍由规则默认；语义选择写入候选）。
- **不**追求 `L > 3` 的深度嵌套（超规模走程序化生成）。
- **不**改残差精度阈值（`RESIDUAL_TOL = 1e-6` 保留）。
- **不**替换 scipy（保留 TRF 作为最终数值兜底）。
- **不**引入 SolveSpace / FreeCAD GCS。

---

## 2. 现状审计（一般模型视角）

### 2.1 当前管线本质

```text
spec(bodies + constraints)
  → expand_constraints (仅 contact, hinge 糖)
  → validate (类型枚举 + 规模上限)
  → compile_constraints → F(x) 残差
  → 7N 维状态 (t, q) + scipy TRF least_squares
  → numeric_jacobian + SVD 摘要
  → rotation_audit + status 判定
  → emit transforms → Compound
```

数学本质：在 `SE(3)^N` 上求非线性方程组近似根。

### 2.2 与一般装配的三类错配

| 装配问题类型 | 数学特征 | 当前机制处理 | 错配点 |
|-------------|---------|-------------|--------|
| **布局已知**（设计坐标） | 实际 DOF ≈ 0 | 仍 7N 维优化 | 用搜索代替赋值 |
| **配合已知、位姿未知** | 低维、结构清晰 | 可行但需手写满秩约束 | Authoring 成本高 |
| **配合已知、位姿近似已知** | 仅需残差检查 | 仍 full solve | 多一轮不可见失败 |

一般模型里三类**混在同一图**；当前只有一种出口（full solve + 严 ok），迫使 Authoring 把所有关系都用"锁满 7 维"表达。

### 2.3 实现层短板清单（与规模无关）

按代码位置列出，便于实施时直接对接：

| # | 现象 | 文件 / 函数 | 一般化影响 |
|---|------|------------|-----------|
| S1 | 状态空间统一 7 维四元数 | `state.py STATE_DIM=7` | 轴对齐块体过参数化 |
| S2 | 初值 Z 叠放 | `solver.py _initial_poses` | 树状/外展装配差初值 |
| S3 | 数值差分 Jacobian | `dof.py numeric_jacobian` | O(dim·m·nfev) 不可大 |
| S4 | 宏库极少 | `graph.py expand_constraints` | 仅 contact/hinge |
| S5 | 单图全局 TRF | `solver.py _run_optimizer` | 无树形传播、无分块 |
| S6 | hint 在基础约束层 | `report.py _build_hints` | 修复建议不可粘贴 |
| S7 | status 单态 | `solver.py status 分支` | 缺 `ok_assumed` 等 |
| S8 | 父面 `in_plane` 沿参考平面切向 | `constraints.py point_plane_offset` | 倾斜父件下语义脱节 |
| S9 | 限位硬顶 64/400 | `limits.py ABSOLUTE_MAX_*` | 无图分割机制 |
| S10 | 旋转审计与 dof 摘要分裂 | `audit.py + dof.py` | 缺 mating/gauge 分类 |
| S11 | 无 MUS 冲突诊断 | `report.py conflict` 字段空 | 过约束不可读 |
| S12 | 无 witness / 多解枚举 | — | 等价解错选无救 |

后续章节针对每一项给出方案与对接点。

---

## 3. 信息维度理论与 LLM 易用性判据

### 3.1 LLM 视角下的六个信息维度

把同一份装配信息**等价**地放在以下任一维度，对 LLM 的难易度截然不同：

| 维度 | 形态 | 示例 |
|------|------|------|
| **D1 Token** | 显式字符 | `"offset": 12.5` |
| **D2 Schema** | 字段名 / 枚举值 | `"rotation_mode": "axis_aligned"` |
| **D3 Policy** | 全局声明一次 | `"dof_policy": { ... }` |
| **D4 Reference** | 路径式名字 | `"parent.+z"` |
| **D5 Default** | 系统规则不写 | "ground 自动 fix" |
| **D6 Program** | Python 生成 | `for i in range(rows): ...` |

### 3.2 各维度的 LLM 成本/可靠度（经验定律）

| 维度 | 单条信息成本 | 命中率 | 出错代价 | 可解释性 |
|------|-------------|--------|---------|---------|
| D1 Token | 高（多 token） | 高（自回归强项） | 局部 | 高 |
| D2 Schema | 中（枚举 + 字段） | 高，但**< 30 项**为天花板 | 局部 | 中 |
| D3 Policy | 极低（一次） | 高，但**遗忘存在**率高 | 全局 | 低 |
| D4 Reference | 中（核名） | **最易拼错** | 整条无效 | 高 |
| D5 Default | 0 | 100% | 0 | 低 |
| D6 Program | 中（写代码） | 中-高 | 视范围 | 中 |

四条关键观察（用于设计决策）：

1. **D1 是 LLM 最擅长维度**——按格式重复是自回归强项。
2. **D2 的拐点在 ~30 项**——超过后命中率非线性下降。
3. **D3 是双刃剑**——省 token 但易"忘存在"。
4. **D4 是最大坑**——大装配中 D4 错误占总错误 50%+。

### 3.3 信息分布原则（与 P0 自主性原则对齐）

| 信息语义 | 自主性等级 | 应放维度 | 理由 |
|---------|-----------|---------|------|
| 体的尺寸 | 必须自主 | D1 | 单一事实来源 |
| mating 几何关系（拓扑） | 必须自主 | D1（relations 数组） | 影响装配 |
| mating 参数（at, offset） | 必须自主 | D1（数字） | 影响装配 |
| 旋转模式（轴对齐？） | 影响求解但**不影响最终位姿** | D2 + D5（默认） | 大多数体相同 |
| 全局自由度策略 | 不影响个体 | D3（≤ 5 项） | 全局一致 |
| 父面 / 接口引用 | 必须自主 | D4 + 类型校验 | 必须显式 |
| 标准 gauge 锁 | 不影响装配 | D5（默认 + 审计） | 不必作者写 |
| 阵列、参数化 | 程序性 | D6（Python） | 重复模式 |

### 3.4 "与 Location 同级易生成"的可测判据

每个体的 Authoring 信息量必须满足以下七条，缺一项视为退化：

| 信息项 | 上限（每体） |
|--------|------------|
| D1 显式数字（mating 参数） | ≤ 3 个 |
| D1 显式引用（父面 / 接口） | ≤ 1 个 |
| D2 模式声明 | ≤ 1 个 enum |
| D3 全局策略覆盖率 | ≥ 80% 体可用默认 |
| D4 校验失败可恢复 | 必须有"建议名"输出 |
| D5 默认审计可见 | 必须输出 `assumed_locks` |
| D6 程序化生成 | `solve_assembly(spec_dict)` API 接受由 Python 程序构造的 dict；spec 本身不引入字面变量 / 占位符 |

`(x, y, z)` 的 Location 在这套指标下：D1 数字 3 个、D1 引用 0、D2 0、D3 N/A、D4 0、D5 多（默认轴对齐）、D6 强。新约束 spec 必须在这套指标上**逐项不劣**。

---

## 4. DOF 自主性分类

### 4.1 三类 DOF 的精确定义

对任意刚体图 `G = (B, E)`，体 `b` 的位姿 `T_b ∈ SE(3)`：

| 类别 | 形式定义 | 谁决定 | 默认可否 |
|------|---------|--------|---------|
| **mating DOF** | 改变它使**至少一条已声明 mate 约束**的残差从 0 变为非零 | 必须由 relation / 显式约束 / 求解确定 | **否** |
| **gauge DOF** | 改变它**不改变任何已声明 mate 约束**的残差（绕对称轴空转、整体漂移等） | 策略 / 破缺规则 / 初值 | **可以** |
| **layout DOF** | 该体**未参与任何 mate**，仅影响外观/包络 | `place` / Location / 公式 | **可以** |

### 4.2 sensitivity 分类算法（求解前/中/后均可用）

给定编译后的约束集 `compiled` 与变量 `x`，自由度方向 `v` 的分类：

```text
def classify_direction(v, compiled, x):
    sensitivity = 0
    for c in compiled:
        # 数值或解析地对 c.residual 在 x 处沿 v 求方向导数
        ds = directional_derivative(c.residual_fn, x, v)
        sensitivity += norm(ds) ** 2
    if sensitivity > epsilon_mating:
        return "mating"     # 改 v 影响 mate 残差
    else:
        return "gauge"       # 不影响任何 mate
```

`layout` 类别在 spec schema 层就标定（带 `place` 或 `layout_only:true` 的体），不进入求解变量，不参与上述分类。

### 4.3 status 多态（替换现有单态 ok）

记 `OT = dof_policy.overconstrained_threshold`（默认 `100 × RESIDUAL_TOL`，见 §0.1）。

| status | 含义 | 触发条件 | `mating_policy=strict` 下额外行为 |
|--------|------|---------|---------------------------------|
| `ok` | 所有 mating DOF 已确定，无 gauge 留白 | 残差 < tol，`mating_free == []`，`gauge_free == []` | — |
| `ok_assumed` | mating 满足；剩余仅为 gauge，**全部**被规则补全 | 残差 < tol，`mating_free == []`，规则补全覆盖**所有** `gauge_free` 条目，`assumed_locks` 非空 | `strict_ok=true` 时降级为 warning（不返 ok） |
| `underconstrained` | **存在未声明的 mating DOF** 或 gauge 规则未能覆盖 | 残差 < tol，**且** `mating_free != []` **或**（`gauge_free != []` 且 `gauge_policy != "auto_lock"`，**或** `auto_lock` 后仍有未匹配 gauge） | — |
| `solve_failed` | 数值不收敛 | scipy 失败 / 残差 > OT 且 MUS 空 | — |
| `overconstrained` | 残差超阈值且诊断到冲突 | `residual_max > OT` **且** MUS 非空 | — |

**关键差异**：

1. 今天的 `underconstrained` 把缺 mating 与缺 gauge 锁混为一谈；新 status 按 sensitivity 分离。
2. 过约束阈值不再硬编码 `> 1.0` mm，而是相对 `RESIDUAL_TOL` 的倍数（默认 100×，可配置），见 §0.1。
3. `complete_once`（旧名）后**仍有未匹配 gauge_free** 的情形，明确归入 `underconstrained`（不静默放过）。

### 4.4 与现有 `dof.summarize_dof` / `audit.py` 的关系

现有 `summarize_dof` 输出 `free: [{body, trans, rot}]`，按体分组。**v1 path 保留不变**（与现有测试 `test_limits_audit.py` 兼容）。**v2 path** 在 `diagnostics.classify_free_directions` 输出按 mating/gauge 分类的新结构，并在 `report` 中追加每条 `free` 的标签：

```python
{
    "body": "b1",
    "trans": ["x", "y"],
    "rot": [],
    "category": "mating | gauge:spin_z | gauge:dangling | ...",
    "affects": ["c3", "c7"]
}
```

`affects` 字段直接驱动 `suggested_relations`（见 §10.5）。

**`audit.py` 的迁移路径**：

- v1 path（无 `version` / `version=1`）：继续走 `audit.axis_lock_preflight_warnings` + `audit.rotation_audit_issues`，行为不变。
- v2 path：旋转空转检测由 `diagnostics.classify_free_directions` 统一处理，写入 `gauge_free[*].category = "spin_z_on_support"` 等；`report.rotation_issues` 字段保留（由 gauge_free 投影生成），保证消费方兼容。

---

## 5. 目标架构（五层）

### 5.1 架构图

```text
┌──────────────────────────────────────────────────────────┐
│  Layer 0   顶层 Python                                    │
│    • 参数定义、循环、阵列、跨层参数注入                  │
│    • 拆解决策、子图实例化                                │
├──────────────────────────────────────────────────────────┤
│  Layer 1   Authoring DSL（每子图一份）                    │
│    • bodies / relations / dof_policy / interface         │
│    • D1 mating 数字、D2 mode/enum、D3 policy、D4 引用     │
├──────────────────────────────────────────────────────────┤
│  Layer 2   编译器（pure function）                        │
│    • 宏展开（6 几何 + 3 策略）                            │
│    • mating / gauge sensitivity 预分类                    │
│    • 跨层接口拼接                                        │
│    • dry-run 输出基础约束                                │
├──────────────────────────────────────────────────────────┤
│  Layer 3   求解器（按 body 模式分桶）                     │
│    • axis_aligned 体：解析放置                            │
│    • yaw_only 体：1D 数值                                 │
│    • free 体：scipy + BFS 初值 + 解析 Jacobian            │
│    • DR-style 子簇分解                                    │
├──────────────────────────────────────────────────────────┤
│  Layer 4   诊断与修复                                     │
│    • mating_free vs gauge_free                            │
│    • assumed_locks                                        │
│    • MUS 最小冲突集                                       │
│    • witness 多解枚举（写入候选）                          │
│    • suggested_relations                                  │
└──────────────────────────────────────────────────────────┘
```

### 5.2 数据流

```text
spec(JSON)
  → [Layer 1] schema 校验 + 类型注入
  → [Layer 2] expand → BaseConstraintGraph + BodyModes + DOFCategoryHints
  → [Layer 3] solve_subgraphs（按 body 模式分桶 + 树形传播）
  → [Layer 4] classify_free → assumed_locks → mus → suggested → report
  → transforms + report → Compound
```

每层是纯函数（除 Layer 0 的 Python），便于单元测试与回放。

### 5.3 与现有 `scripts/constraint/` 的映射

| 新层 | 复用 / 新增模块 |
|------|----------------|
| Layer 1 | `schema.py` 扩展 + 新 `dsl.py`（relations / place / layout_only / sub_spec） |
| Layer 2 | `graph.py` 扩展 + 新 `macros.py`（几何/策略宏） |
| Layer 3 | `solver.py` 分桶 + 新 `analytic.py`（axis_aligned 解析） + `dof.py` 解析 Jacobian |
| Layer 4 | `report.py` 扩展 + 新 `diagnostics.py`（sensitivity 分类、MUS、witness） |

**核心契约不变**：`assemble.constraint_assembly(CONSTRAINTS, parts)` 入口签名保持，旧 spec 仍可工作（见 14.2）。

---

## 6. Authoring DSL

### 6.1 顶层 schema 草案（v2）

```json
{
  "version": 2,
  "ground": "platform",
  "limits": { "max_bodies": 48, "max_constraints": 300 },

  "dof_policy": {
    "default_box_on_plane": "fixed_orthogonal",
    "mating_policy": "strict",
    "gauge_policy": "require",
    "strict_ok": false,
    "overconstrained_threshold": 1e-4
  },

  "bodies": {
    "platform": {
      "primitive": "box",
      "size": [400, 180, 55]
    },
    "wheel_fl": {
      "primitive": "box",
      "size": [55, 35, 55],
      "rotation_mode": "axis_aligned"
    },
    "ornament_a": {
      "primitive": "box",
      "size": [20, 20, 20],
      "place": [80, 30, 100],
      "layout_only": true
    }
  },

  "relations": [
    { "type": "flat_on", "child": "wheel_fl", "on": "platform.+z", "at": [-145, 78] }
  ],

  "constraints": [],

  "interface_spec": {
    "interface_body": "platform",
    "exports": ["platform.+z", "platform.center"]
  }
}
```

字段语义：

- `version`：用于兼容（见 14.2）。
- `dof_policy`：见 6.4。
- `bodies[*].rotation_mode`：见第 8 章。
- `bodies[*].place` / `layout_only`：见 6.3。
- `relations`：宏化高阶关系，见第 7 章。**所有 mating 仅通过 relations 表达**（不再支持体级 `mount` 字段）。
- `constraints`：仍接受现有 7 类基础约束（向后兼容，不推荐 v2 新写）。
- `interface_spec`：仅在该 spec 作为子图被引用时使用，见第 11 章。

### 6.2 `bodies` 字段扩展

| 字段 | 类型 | 含义 |
|------|------|------|
| `primitive` | str | `"box"` / `"cylinder"` / `"sphere"`（不变） |
| `size` / `radius` / `height` | num | 原语参数（不变） |
| `rotation_mode` | enum | `"axis_aligned"`（默认） / `"yaw_only"` / `"free"` |
| `yaw_axis` | enum | 仅 `yaw_only` 时使用：`"+z"`（默认）等 |
| `place` | `[x,y,z]` | 直通位置；与该体出现在 `relations` 中作为 child / a / b 互斥 |
| `layout_only` | bool | `true` 时该体不进入求解变量（必须配合 `place`） |
| `sub_spec` | str | 子规约路径或注册 id（见第 11 章） |
| `anchor_body` | str | 仅在 `sub_spec` 存在时使用：子规约内作为接口的 body id（默认沿用子规约的 `interface_spec.interface_body`） |

**互斥关系**：

| 字段组合 | 状态 |
|---------|------|
| `place` × 出现在 relations.child/a/b | ✗ schema 报错 |
| `sub_spec` × `primitive` | ✗ schema 报错（互斥） |
| `layout_only=true` × 缺 `place` | ✗ schema 报错 |
| `sub_spec` × `layout_only` | ✗ schema 报错（子图体不能 layout_only） |

> **注**：v1 中曾构想的体级 `mount` 字段已删除（与 `relations` 双入口冗余）；所有 mating 仅通过 `relations[]` 表达，统一入口、便于程序化生成。

### 6.3 `place` 与 `layout_only` 的精确语义

- `place: [x, y, z]`
  - 在 `world` 系给定平移；旋转由 `rotation_mode` 决定（`axis_aligned` 时为 identity）。
  - **不进入**求解变量，**不进入** sensitivity 分类。
  - 若同时出现在 `relations` 中作为 child / a / b → schema 报错。
- `layout_only: true`
  - 必须配合 `place`（schema 校验）。
  - 即使该体出现在某 relation 中作为参考（如 `on: "ornament_a.+z"`），也只读其 feature，不解它的位姿。
  - 等价于"半接口"：作者承诺该体不需要求解。

### 6.4 `dof_policy` 全局策略

**两个正交开关 + 三项辅助**（D3 维度上限 5 项不变）：

| 字段 | 取值 | 默认 | 控制对象 |
|------|------|------|---------|
| `mating_policy` | `"strict"` / `"permissive"` | `"strict"` | **mating DOF** 残留时是否报 underconstrained |
| `gauge_policy` | `"require"` / `"auto_lock"` / `"enumerate"` | `"require"` | **gauge DOF** 的处理方式 |
| `default_box_on_plane` | `"fixed_orthogonal"` / `"none"` | `"fixed_orthogonal"` | `flat_on` 宏展开时是否自动 emit 三条 axis_parallel（视为宏定义一部分，不计入 `assumed_locks`） |
| `strict_ok` | bool | `false` | CI 模式：要求 `assumed_locks == []` 才返 `ok`（否则强制 `ok_assumed`） |
| `overconstrained_threshold` | float | `1e-4`（= 100×`RESIDUAL_TOL`） | 过约束 status 触发阈值（mm） |

**两个主开关的语义矩阵**：

| `mating_policy` | `gauge_policy` | mating_free ≠ [] | gauge_free ≠ [] | 行为 |
|----------------|---------------|-----------------|-----------------|------|
| `strict`（默认） | `require`（默认） | underconstrained | underconstrained | 严格要求作者显式 |
| `strict` | `auto_lock` | underconstrained | 规则补全 → `ok_assumed`（剩余 → underconstrained） | 推荐生产模式 |
| `strict` | `enumerate` | underconstrained | 写 `witness_branches`，status 仍 underconstrained | 调试与多解探索 |
| `permissive` | `require` | warning + 用初值 → `ok` | underconstrained | 仅 layout 验算 |
| `permissive` | `auto_lock` | warning + 用初值 → `ok` | 规则补全 → `ok_assumed` | verify_only 模式 |

**关键设计**：

- `mating_policy` 与 `gauge_policy` **正交**，组合矩阵完整定义。
- 默认 `(strict, require)` 完全贯彻 P0 原则：mating + gauge 都必须显式。
- 生产推荐 `(strict, auto_lock)`：mating 严格、gauge 用规则透明补全。
- `auto_lock` 与 `enumerate` 互斥（同一时刻只能选一种 gauge 处理）。

### 6.5 接口字段（子图模式）

顶层字段 `interface_spec` 仅在该 spec 被另一 spec 作为子图引入时使用：

```json
"interface_spec": {
  "interface_body": "<body_id>",
  "exports": ["<body>.<feature>", "..."]
}
```

- `interface_body`：本子规约中扮演接口的 body id（**也是该子规约的 `ground`**）。
- `exports`：本子规约对外暴露的 feature 引用白名单（父规约只能引用这些）。

详见第 11 章。

### 6.6 与现有 `constraints` 数组的兼容（v1 / v2 触发规则）

**触发规则**：spec 是否走 v2 path 由以下条件**任一**触发：

- 顶层有 `"version": 2`，**或**
- 顶层有 `"relations"` / `"dof_policy"` / `"interface_spec"` 字段，**或**
- 任一 `bodies[*]` 含 `place` / `rotation_mode` / `layout_only` / `sub_spec` / `anchor_body` 字段

满足以上任一条件**且 `version` 缺失** → schema 报错「missing version: 2」（防止 v2 字段被误当成 v1）。

**共存规则**：

- v2 spec 中 `relations` 与 `constraints` 可**共存**（先展开 relations，再合并 constraints），但不推荐同时写。
- 旧 spec（无 `version` 且无任何 v2 字段）→ 走 v1 path，行为完全不变。
- v1 path 测试用例（`test_assemble.py`、`test_limits_audit.py`）必须**全部通过**且无需修改。

---

## 7. 几何宏与策略宏（6 + 2）

### 7.1 设计原则

- **宏是几何骨架，不是产品语义**。`wheel` / `panel` 等产品名**不进** schema，仅作为文档示例（"用 `flat_on` + `lock_orthogonal_to` 写一个轮"）。
- **宏总数 = 6 几何 + 2 策略 = 8 个**（D2 schema 维度 < 30 项天花板的安全区）。
- **每个宏精确展开为现有 7 类基础约束**，求解器内核零改动。
- **宏定义中的约束是宏语义的一部分**，不计入 `assumed_locks`（与 P3 一致：宏展开过程对 dry-run 完全可见）。
- **每个宏标注 mating DOF 数**，用于 sensitivity 预分类。

### 7.2 六个几何宏

| 宏 | 必填字段 | 选填字段 | 展开到基础约束 | mating DOF（child） |
|----|---------|---------|---------------|---------------------|
| `flat_on` | `child`, `on`（父面 ref）, `at:[u,v]` | `gap`, `face`（child 默认 `-z`） | 见 §7.2.1 详解 | 2（u, v） |
| `coax` | `a:axis ref`, `b:axis ref` | `offset` | axis_coaxial(a, b) + （若 `offset` 给定）point_plane_offset(a.origin, b 端面, offset) | 1（沿轴） |
| `align` | `a:axis`, `b:axis` | `opposed` | axis_parallel(a, b, opposed) | 0（方向锁） |
| `fix_to` | `child`, `parent` | `local:[x,y,z]` | 见 §7.2.2 详解（纯组合，不引新基础约束） | 0（完全绑定） |
| `hinge` | `a`, `b` | `angle` | axis_coaxial(a, b) + point_coincident（保留现有糖） | 1（角度，若 angle 未给） |
| `slider` | `a:axis`, `b:axis` | `displacement` | axis_coaxial(a, b) + 沿 b 切向 point_plane_offset 锁切向位移 | 1（沿轴位移） |

#### 7.2.1 `flat_on` 详解

**支持矩阵**（child × parent 原语类型）：

| child \ parent | parent=box face (`+x`/`-x`/`+y`/`-y`/`+z`/`-z`) | parent=cylinder face (`top_plane`/`bottom_plane`) | parent=sphere |
|----------------|-----|-----|-----|
| **child=box** | ✅ 完整支持（含三轴锁） | ✅ 仅 child 的 `axis_z` 锁到 parent 的 `axis_z` | ✗ 不支持 |
| **child=cylinder** | ✅ 仅锁 child.`axis_z` ↔ parent 法向 | ✅ 同上 | ✗ 不支持 |
| **child=sphere** | ⚠ 仅 plane_coincident + offset（不锁旋转） | ⚠ 同上 | ✗ 不支持 |

**face 与 offset 符号规则**：

设 `face ∈ {+x, -x, +y, -y, +z, -z}`，记 `axis_index(face) = {x:0, y:1, z:2}[axis(face)]`，`sign(face) = +1 if face 含 "-" else -1`（注：child 的 `-z` 面贴在父面"上方"时 child.center 在父面 **+法向**侧 → offset 取正；child 的 `+z` 面贴时 child.center 在 **-法向**侧 → offset 取负）。

```text
child_half = child.size[axis_index(face)] / 2
offset_value = sign(face) * (child_half + gap)
```

**展开为基础约束**（以 child=box, face="-z", parent=box.+z 为例）：

```text
flat_on(child=wheel_fl, on=platform.+z, at=[-145, 78], gap=0, face="-z")

c{r}_pc:   plane_coincident  wheel_fl.-z ↔ platform.+z  (opposed=True)
c{r}_oux:  point_plane_offset  wheel_fl.center on platform.+z  in_plane=x value=-145
c{r}_ouy:  point_plane_offset  wheel_fl.center on platform.+z  in_plane=y value=78
c{r}_off:  point_plane_offset  wheel_fl.center on platform.+z  offset=+sign(-z)*(lz/2 + 0) = +lz/2

若 child.rotation_mode == "axis_aligned" 且 policy.default_box_on_plane == "fixed_orthogonal":
  c{r}_par_x: axis_parallel  wheel_fl.axis_x ↔ platform.axis_x
  c{r}_par_y: axis_parallel  wheel_fl.axis_y ↔ platform.axis_y
  c{r}_par_z: axis_parallel  wheel_fl.axis_z ↔ platform.axis_z

  （三条 axis_parallel 是 flat_on 宏在该 rotation_mode 下的标准展开，
    通过 dry-run 完全可见；不计入 assumed_locks。）
```

**父体类型限制**：

- 父面为 cylinder 的 `top_plane` / `bottom_plane` 时：仅 emit `axis_parallel(child.axis_z, parent.axis_z)`（不锁 axis_x/axis_y，因 cylinder 的 axis_x/axis_y 是辅助轴无几何意义）；面内 (u,v) 仍按 `plane.tangent_axes()` 解释。
- 父体不能是 sphere（无可定向的 `face`）。

#### 7.2.2 `fix_to` 详解（纯组合，不引新基础约束）

```text
fix_to(child=A, parent=B, local=[x, y, z])

展开为：
c{r}_off_x: point_plane_offset  A.center on B.plane_px  offset=x（即 A.center 沿 B 的 +x 方向距 B.center 为 x mm）
c{r}_off_y: point_plane_offset  A.center on B.plane_py  offset=y
c{r}_off_z: point_plane_offset  A.center on B.plane_pz  offset=z
c{r}_par_x: axis_parallel  A.axis_x ↔ B.axis_x
c{r}_par_y: axis_parallel  A.axis_y ↔ B.axis_y
c{r}_par_z: axis_parallel  A.axis_z ↔ B.axis_z
```

**实现要点**：

- `local=[0,0,0]` 时退化为 `point_coincident(A.center, B.center) + 三轴 axis_parallel`，但展开仍写 3 条 offset=0（保持一致格式）。
- B 必须是 `box`（提供 `plane_px/py/pz`）；cylinder/sphere 父体不支持 `fix_to`。
- 该宏 **完全用现有 7 类基础约束** 实现，不需要扩展 `constraints.py`。

### 7.3 两个策略宏

| 宏 | 用途 | 展开 |
|----|------|------|
| `lock_orthogonal_to` | 显式三轴锁（不依赖 `flat_on` 自动展开） | 三条 axis_parallel（child.axis_{x,y,z} ↔ target.axis_{x,y,z}） |
| `yaw_free` | 仅锁两轴（允许绕 yaw_axis 自由转） | 两条 axis_parallel（不含 yaw_axis） |

> **注**：v1 中曾构想的 `layout` 策略宏已删除——layout 体仅通过 body 级 `place` + `layout_only` 字段声明（见 §6.3），不再有第二个入口。

### 7.4 dry-run、双向追踪与 id 命名规则

**relation id 命名规则**：

- relation 未给 `id` 时自动命名 `r{i}`（i 为 relations[] 中的 1-based 索引）
- 展开后的基础约束 id 命名 `{relation_id}_{slot}`，slot 包括：
  - `pc`（plane_coincident）、`pt`（point_coincident）、`pc_ax`（axis_coaxial）、`par_x`/`par_y`/`par_z`（axis_parallel）
  - `off_x` / `off_y` / `off_z` / `off`（point_plane_offset，按 in_plane 或 normal offset 区分）
- 每条展开约束写 `triggered_by: "{relation_id}:{relation_type}[:{sub_role}]"`
  - 例：`triggered_by: "r1:flat_on:lock_orthogonal"`、`"r1:flat_on:tangent_u"`
- 作者写的 `constraints[]` 项保留作者给的 id（未给则 `c{i}`）+ `triggered_by: "user"`

**relations 与 constraints 共存的命名空间隔离**：

- relations 展开的 id 一律以 `r` 开头；作者写 constraints 不得以 `r` 开头（schema 校验，冲突时报错）
- 矛盾约束的检测**不在编译期**完成（保留给求解后 MUS）

**新 CLI 子命令**（在 `cli.py` 中加 subparser，与现有 `solve` / `validate` 并列）：

```bash
./.venv/bin/python -m constraint expand spec.json --out spec.expanded.json
```

输出展开后的完整 v1 风格 spec（`relations` 折叠为基础 `constraints` + `triggered_by` 字段），LLM/作者可直接 diff 验证：

```json
{
  "version": 2,
  "ground": "platform",
  "bodies": { ... },
  "constraints": [
    {
      "id": "r1_oux",
      "type": "point_plane_offset",
      "point": "wheel_fl.center",
      "plane": "platform.+z",
      "in_plane": "x",
      "value": -145,
      "triggered_by": "r1:flat_on:tangent_u"
    }
  ]
}
```

`report.hint` 中提到的 constraint id 同样可追溯到 relation，保证 P4 局部失败原则。

### 7.5 不会引入的宏（明确排除）

| 宏名 | 排除理由 |
|------|---------|
| `wheel` / `panel` / `pillar` / `drawer` | 产品语义，覆盖率诅咒（参见 ask1.md 讨论） |
| `grid_repeat` / `array` | D6 维度更合适（Python 循环 + relations.append） |
| `mate_to_face` 自由变体 | 已被 `flat_on` + `coax` 覆盖 |
| `layout` 策略宏（旧设计） | 与 body 级 `place + layout_only` 重复 |

阵列由 Layer 0 Python 程序生成 `relations[]`，**不在 schema 层提供阵列宏**。LLM 写 spec 时若需阵列，应通过 Python 顶层（D6 维度）生成 dict，而非在 JSON spec 文本中展开重复块。

---

## 8. Body 模式与求解器分桶

### 8.1 三种 `rotation_mode`

| 模式 | 求解时有效维度 | 旋转表示 | 适用 |
|------|---------------|---------|------|
| `axis_aligned` | 3（仅平移） | identity（强制） | box 块、对齐围板（一般装配 70%+） |
| `yaw_only` | 4（平移 + 1 角度） | 绕 `yaw_axis` 的旋转 | 圆盘、对称轮、需绕单轴转动 |
| `free` | 7（平移 + 四元数） | 现有 | 斜配合、非对齐铰链 |

默认 `axis_aligned`（与 P0 原则的"gauge 默认"对齐）。

> **重要实现约定**：`state.BodyPose` 与 `state.STATE_DIM = 7` **保持不变**。三种模式仅在**求解流程**上分流：
>
> - analytic 桶：直接构造 `BodyPose(t, identity_quat)`，不进数值优化
> - yaw 桶：scipy 子问题用自定义 4 维向量封装，输出后写回 `BodyPose`
> - free 桶：维持现有 7N 向量与 scipy TRF
>
> 这样 `pack_poses` / `unpack_poses` / `emit.transforms_for_instances` 等所有现有调用方零修改。"变长状态"是一个**求解流程内部概念**，不是 `BodyPose` 接口的变更。

### 8.2 编译期分桶

```text
def bucket_bodies(spec):
    buckets = {"layout": [], "analytic": [], "yaw": [], "free": []}
    for bid, body in spec.bodies.items():
        if body.layout_only:
            buckets["layout"].append(bid)
        elif body.rotation_mode == "axis_aligned":
            buckets["analytic"].append(bid)
        elif body.rotation_mode == "yaw_only":
            buckets["yaw"].append(bid)
        else:
            buckets["free"].append(bid)
    return buckets
```

### 8.3 analytic 桶的解析放置

对 `analytic` 桶的体，若其参与的所有 relation 都属于 `flat_on` / `fix_to` / `align` / `coax`（且父位姿已确定），可**完全解析**算出位姿：

```text
def place_analytic(child, relations, solved_poses):
    # 收集所有 flat_on / fix_to 给出的 (parent, u, v, normal_offset)
    # 在父 frame 下计算 child.center 的世界坐标
    # rotation = identity（mode 强制）
    return Pose(translation=t, quaternion=(0,0,0,1))
```

**优势**（一般模型，与具体案例无关）：

- 零数值优化，零 nfev
- 不受初值影响
- 不产生旋转歧义（多解、180° 翻转都不可能）
- Jacobian 不需要

**约束条件**（必须满足，否则该体回退到 `yaw` 或 `free` 桶）：

- 父位姿已知（由其他桶先解或为 ground）
- 所有引用 relation 是已支持的"解析友好"类型
- 体无 `free` 模式邻居参与同一 relation

### 8.4 yaw 桶的 4D 联合解

`yaw_only` 体：**平移与旋转角 θ 联合求解**（一般情况下平移依赖 θ，例如绕轴转后再被 flat_on 引用其某面的位置——不能解耦先算平移）。

- 单体子问题：4 维（tx, ty, tz, θ），scipy LM 单次解（残差仅取该体直接参与的约束）。
- 多体 yaw 子问题：若彼此通过约束耦合，合并为同一子图，状态空间 4·|cluster| 维，scipy TRF 一次解。

### 8.5 free 桶的 scipy 兜底

进入 scipy 的变量数从全局 `7N` 降到 `7 × |free_bucket|`。对一般装配，`|free_bucket|` 通常 < 10（铰链、斜接点）。Jacobian 维度大幅压缩。

### 8.6 求解顺序（一般模型）

```text
1. ground (固定 identity pose；若 ground 自身在 analytic 桶视为已解)
2. layout 桶：直接读 place 构造 BodyPose
3. analytic 桶：BFS 拓扑序逐体解析放置 → BodyPose（**这是最终位姿，不进 scipy**）
   - 每个体的父位姿来自步骤 1/2 或前序 analytic 体
4. yaw 桶：4D 联合解（每子簇一次 scipy LM/TRF）
5. free 桶：scipy 全局解
   - 初值由 BFS 提供（步骤 9.2）：基于已解的 analytic + yaw 邻居 + relation 几何估计
6. verify：对所有约束（含已解析放置的 analytic 体）跑残差检查
```

**关键职责区分**：

| 步骤 | BFS 用途 | 输出 |
|------|---------|------|
| 步骤 3 | 拓扑序 + 每体解析放置 | **最终位姿**（不再优化） |
| 步骤 5 | 仅作为 scipy 初值估计 | scipy 输入向量 |

若某 analytic 体在编译期被判定不可解析（依赖 free/yaw 邻居），降级到 free 桶；降级在编译期完成，运行时不会回滚。

---

## 9. 求解器优化

### 9.1 Jacobian 稀疏化与解析化（分两步实施）

拆为两个独立工作项（见 §15.1 优先级表 P2c-1 / P2c-2）：

#### 9.1.1 稀疏化（P2c-1，1-2 天）

按 `CompiledConstraint.body_ids` 标记非零块，**仍由数值差分填充**：

```text
J[i, j*STATE_DIM:(j+1)*STATE_DIM] = ∂F_i / ∂x_j （仅当 body j ∈ constraint i.body_ids）
```

- 优势：差分次数 O(nnz / STATE_DIM)，节省大量 `residual_fn` 求值
- 复杂度从 `O(dim · m · nfev)` 降到 `O(nnz(J)/STATE_DIM · m · nfev)`
- 不需要约束类型推导

#### 9.1.2 解析化（P2c-2，5-8 天）

对每类基础约束推导闭式 Jacobian：

| 约束类型 | 残差对 t 的导数 | 残差对 q 的导数 |
|---------|---------------|----------------|
| `fix` | identity（直接） | identity |
| `point_coincident` | ±I（对每端） | ∂(R·p_l)/∂q 链式 |
| `plane_coincident` | 0 / 法向投影 | 含归一化方向的导数（较繁） |
| `axis_coaxial` | 含 cross 与归一化 | 同上 |
| `axis_parallel` | 0 | ∂(R·d_l)/∂q |
| `plane_distance` | 法向单一项 | 含法向导数 |
| `point_plane_offset` | 法向 / 切向投影 | 链式 |

- 数值差分保留为 `--verify-jacobian` 调试开关（与解析 J 对拍，元素差 < 1e-4 视为正确）
- 这一步在 P2c-1 完成后做，便于回归验证

### 9.2 BFS 初值（替换 Z 叠放，仅用于 free 桶）

```text
def bfs_initial_poses_for_free(compiled, solved_analytic_and_yaw):
    """
    输入：已解的 analytic + yaw 体位姿
    输出：free 桶各体的初值估计
    """
    poses = dict(solved_analytic_and_yaw)
    queue = neighbors_in_free_bucket(poses.keys())
    while queue:
        b = queue.popleft()
        if b in poses: continue
        poses[b] = estimate_from_relations(b, poses)
        queue.extend(free_neighbors(b) - poses.keys())
    return poses
```

约束图按"relation 是否给出明显位姿信息"加权——`flat_on` 边权高（可直接算位姿）、`coax` 中等、`align` 低（仅方向）、`hinge` 低（角度未知）。BFS 优先沿高权边推进。

**与 analytic 桶的关系**：analytic 桶 BFS（§8.6 步骤 3）已直接得出最终位姿；本节 BFS 仅为 free 桶的 scipy 提供初值。

### 9.3 DR 风格子簇分解（推到 P3，**未来工作**）

完整 DR-Planner 过重；本方案**主路径走 §11 接口体方案**（作者显式声明子图边界）。

DR 风格自动分簇仅作为 P3 增量优化（见 §15.1 P3a），目的是在**单 spec 内部**对 free 桶做自动子簇切割，与跨 spec 的接口体方案**互不冲突**：

- 接口体（P2a）：跨 spec 文件、作者显式声明
- DR 子簇（P3a）：单 spec 内、求解器自动、对作者透明

P3 之前，free 桶整体作为一个 scipy 子问题求解。

### 9.4 收敛策略

- 主路径：scipy TRF（保留）
- 失败回退：scipy LM（method 切换）
- 二次回退：自实现 damped Gauss-Newton（保留）
- 终止判据：`residual_max < RESIDUAL_TOL = 1e-6 mm`（不变）
- 过约束判定阈值：`dof_policy.overconstrained_threshold`（默认 `100 × RESIDUAL_TOL = 1e-4 mm`，见 §0.1 与 §4.3）

---

## 10. 诊断与修复闭环（无二级 LLM）

### 10.1 mating_free vs gauge_free 分离（含 sensitivity 归一化）

**分类算法关键**：不同约束类型的残差量纲不同（方向无量纲、距离 mm），单一阈值不安全。计算前对每条约束的 Jacobian 行做**残差尺度归一化**：

```text
def normalize_jacobian_rows(J, constraints):
    """对每条约束的残差行除以其特征尺度，使所有行无量纲化"""
    J_norm = J.copy()
    for i, c in enumerate(constraints):
        for k in range(c.residual_dim):
            row = c.start_row + k
            scale = residual_scale(c, k)  # 方向项 = 1；距离项 = max(1mm, |residual|)
            J_norm[row, :] /= scale
    return J_norm
```

**sensitivity 阈值**：相对 SVD 最大奇异值，**不是绝对阈值**：

```text
epsilon_mating = 1e-3 * S[0]   # S[0] = 归一化 Jacobian 的最大奇异值
```

**输出结构**（替换现有 `dof.summarize_dof` 的 free 字段，仅在 v2 path 生效）：

```json
{
  "rank": 56,
  "dof_deficit": 3,
  "mating_free": [
    { "body": "b1", "trans": ["x"], "rot": [], "affects": ["c3"] }
  ],
  "gauge_free": [
    { "body": "b2", "trans": [], "rot": ["z"], "category": "spin_z_on_support" }
  ]
}
```

**status 派生规则**（与 §4.3 / §6.4 配合）：

| 条件 | mating_policy | gauge_policy | status |
|------|--------------|-------------|--------|
| 都为空 + 残差 < tol | * | * | `ok` |
| `mating_free=[]` + `gauge_free≠[]` | * | `require` | `underconstrained` |
| `mating_free=[]` + gauge 全被规则覆盖 | * | `auto_lock` | `ok_assumed` |
| `mating_free=[]` + gauge 部分未匹配 | * | `auto_lock` | `underconstrained`（warning: "unmatched_gauge"） |
| `mating_free=[]` + gauge 有候选 | * | `enumerate` | `underconstrained` + `witness_branches` 写入 |
| `mating_free≠[]` | `strict` | * | `underconstrained` |
| `mating_free≠[]` | `permissive` | * | warning + 用初值固定 → `ok`（仅 verify_only 场景） |
| 残差 > OT 且 MUS 非空 | * | * | `overconstrained` |
| 数值不收敛或残差 > OT 且 MUS 空 | * | * | `solve_failed` |

### 10.2 `assumed_locks` 审计

`gauge_policy == "auto_lock"` 时，对每条 `gauge_free` 逐一尝试规则补全：

```text
matched = []
unmatched = []
for gf in gauge_free:
    rule = pick_lock_rule(gf)  # e.g. category="spin_z_on_support" → axis_parallel
    if rule is None:
        unmatched.append(gf)
        continue
    new_constraint = build_constraint_from_rule(rule, gf)
    constraints.append(new_constraint)
    assumed_locks.append({
        "body": gf.body,
        "rule": rule.name,
        "added": [new_constraint.id],
        "reason": gf.category
    })
    matched.append(gf)

re-solve once（不再迭代）

# status 三分支：
if not unmatched:
    status = "ok_assumed"
elif matched and unmatched:
    status = "underconstrained"     # + warning "unmatched_gauge: <bodies>"
else:
    status = "underconstrained"     # 规则匹配 0 条
```

`assumed_locks` 写入 `report.assumed_locks`：

```json
{
  "assumed_locks": [
    {
      "body": "wheel_fl",
      "rule": "fixed_orthogonal_to_platform",
      "added": ["c_auto_1", "c_auto_2"],
      "reason": "spin_z_on_support"
    }
  ]
}
```

CI 模式 `strict_ok: true` 时若 `assumed_locks` 非空，`status` 强制降为 `ok_assumed`（即使本该是 ok），可被 harness 标记。

### 10.3 MUS（最小不可解子集）

**前置条件**：仅在以下情况启动 MUS：

```text
solve_ok == True   且   residual_max > overconstrained_threshold
```

（即 scipy 成功收敛但仍有约束残差超阈值。**不**在 `solve_failed` 时启动——数值不收敛只报 `solver_message`，不算冲突）

算法（delta-debugging 风格）：

```text
def find_mus(constraints, x_star, threshold):
    # 1. 找残差超阈值的约束集 over = {c | |F_c(x*)| > threshold}
    over = [c for c in constraints if max(abs(c.residual_at(x_star))) > threshold]
    if len(over) > 20:
        return {"hint": "conflict_set_too_large", "candidates": over[:20]}
    # 2. delta-debugging：每次移除一条 c，重新 solve 子集；若剩余仍 over 则保留
    mus = list(over)
    for c in list(mus):
        subset = [x for x in constraints if x != c]
        x_sub = solve(subset).x_star
        if any(max(abs(cc.residual_at(x_sub))) > threshold for cc in mus if cc != c):
            continue  # c 可被去除，残余仍冲突
        mus.remove(c)
    return mus
```

写入 `report.conflict[]`：

```json
{
  "conflict": [
    { "ids": ["c1", "c4", "c7"], "reason": "plane_coincident + plane_distance 矛盾" }
  ]
}
```

复杂度 O(|over|² × solve_cost)，对一般冲突 |over| < 10 完全可接受；|over| > 20 时直接返候选集而不做最小化。

### 10.4 witness 多解枚举（离散候选写入报告）

`gauge_policy: "enumerate"` 时，对每条 `gauge_free`：

```text
def enumerate_witness(gauge_free_entry, current_pose):
    # 对 1D 连续 gauge：采样 2-4 个角度（0°, 90°, 180°, 270°）
    # 对离散 gauge：枚举所有等价解
    candidates = []
    for candidate_lock in candidate_locks_for(gauge_free_entry):
        pose = solve_with_extra(candidate_lock)
        candidates.append({
            "id": f"cand_{i}",
            "rule": candidate_lock.name,
            "delta_pose": pose - current_pose,
            "description": candidate_lock.human_readable
        })
    return candidates
```

写入 `report.witness_branches[<body_id>][]`：

```json
{
  "witness_branches": {
    "wheel_fl": [
      { "id": "cand_a", "rule": "axis_x_aligned_+x", "description": "wheel axis_x 朝 +X" },
      { "id": "cand_b", "rule": "axis_x_aligned_-x", "description": "wheel axis_x 朝 -X" }
    ]
  }
}
```

作者（或更高层 Agent 的下一轮调用）显式从候选中选一个，加入 `relations[]` 重跑——**完全确定性，无 LLM 自动选**。

### 10.5 suggested_relations（宏级建议）

替换现有 `report.hint` 的"加 axis_parallel"建议：

```text
def suggest_relations(mating_free):
    suggestions = []
    for mf in mating_free:
        # 根据 free 方向与该体已有 relation，反推宏
        if mf.trans == ["x", "y"] and has_contact_with(mf.body):
            parent = find_contact_parent(mf.body)
            suggestions.append({
                "type": "flat_on",
                "child": mf.body,
                "on": f"{parent}.+z",
                "at": [0, 0]  # 占位，作者填
            })
    return suggestions
```

写入 `report.suggested_relations[]`，LLM/作者直接复制粘贴。

### 10.6 完整 report schema

```json
{
  "schema_version": 2,
  "status": "ok | ok_assumed | underconstrained | overconstrained | solve_failed",
  "ground": "platform",
  "solve_ok": true,
  "residual_max": 1.1e-9,

  "dof_deficit": 0,
  "mating_free": [],
  "gauge_free": [],

  "assumed_locks": [],
  "rotation_issues": [],
  "conflict": [],

  "witness_branches": {},
  "suggested_relations": [],

  "hint": [],
  "warnings": []
}
```

`schema_version` 字段用于消费方版本判断：

- v1 path 输出 `schema_version: 1`，**不**输出 `mating_free` / `gauge_free` / `assumed_locks` / `witness_branches` / `suggested_relations` 五个新字段（保持现有格式）
- v2 path 输出 `schema_version: 2`，包含全部字段
- `rotation_issues` 在两个版本中都输出，保证消费方平滑过渡（v2 由 gauge_free 投影生成）

字段上限（防 token 爆炸）：

| 字段 | 最大条数 |
|------|---------|
| `mating_free` | 5 |
| `gauge_free` | 5 |
| `assumed_locks` | 10 |
| `conflict` | 3（每条 MUS） |
| `witness_branches[*]` | 4（每体候选） |
| `suggested_relations` | 5 |
| `hint` | 6 |

整个 report 目标 < 4 KB，保证 LLM 单轮可读完。

---

## 11. 子链拆解与接口体

### 11.1 接口体方案（P2 坐标变换隐藏原则的工程实现）

**核心结构**：

```text
父 spec (parent.json):
  bodies:
    chassis_sub: { sub_spec: "child.json", anchor_body: "platform" }
                              # anchor_body 可省略，默认沿用子规约的 interface_spec.interface_body
  relations:
    flat_on(chassis_sub, on=ground.+z, at=[0, 0])
                              # 父规约中 chassis_sub 当作普通 box body，
                              # 几何来自子规约 anchor_body 的世界包络（见 §11.2）

子 spec (child.json):
  ground: "platform"          # 子规约的接口 body 自身就是 ground
  bodies:
    platform: { primitive: "box", size: [400, 180, 55] }
    wheel_fl: { primitive: "box", size: [55, 35, 55] }
  relations:
    flat_on(wheel_fl, on=platform.+z, at=[-145, 78])
  interface_spec:
    interface_body: "platform"
    exports: ["platform.+z", "platform.center"]
```

父 spec **只**通过 `chassis_sub`（在父系内即子规约的 `interface_body` 在父系中的代理）接触子图；子图内部其他 body 对父 spec 不可见。

### 11.2 拼接算法

```text
def resolve_subgraph(parent_spec):
    # 1. 找到所有 body 带 sub_spec 字段的体
    sub_bodies = [b for b in parent_spec.bodies if "sub_spec" in b]
    # 2. 对每个 sub_spec：
    for sub_id, sub_body in sub_bodies:
        sub_spec_obj = load(sub_body.sub_spec)
        # a. 独立 solve_assembly(sub_spec_obj) → sub_transforms（子规约 ground=interface_body 时为 identity）
        sub_result = solve_assembly_v2(sub_spec_obj)
        # b. 取子规约的 interface_body 在子规约内的形状作为父规约中 sub_id 的"代理几何"
        anchor = sub_body.anchor_body or sub_spec_obj.interface_spec.interface_body
        proxy_primitive = sub_spec_obj.bodies[anchor]
        # → 父规约 bodies[sub_id] 在编译期被替换为该 box/cylinder 原语（仅几何用于 feature 引用）
        parent_proxy[sub_id] = proxy_primitive
        sub_transforms[sub_id] = sub_result.transforms  # 缓存供步骤 4 使用
    # 3. 父 spec 求解：sub_id 是普通 body，参与父 relations；ground 为父 ground
    parent_result = solve_assembly_v2(parent_spec_with_proxies)
    # 4. 拼接世界位姿：
    #    每个子 body 的世界位姿 = parent_T(sub_id) · sub_local_T(body)
    return assemble_world_transforms(parent_result, sub_transforms)
```

实现要点：

- 子图独立求解，**无跨层迭代**。
- 子规约的 `interface_body` 在子图内是 ground（identity pose）；在父图内是父规约中名为 `sub_id` 的 body 的代理（继承该 body 的几何 feature）。
- 跨层只通过 `interface_spec.exports` 列出的 feature 通信；父规约引用 `sub_id.<feature>` 必须在 exports 中（否则 schema 报错）。
- 子图缓存：若同一 sub_spec 文件被多处实例化，子图独立求解结果可缓存。

### 11.3 切割规则（重申）

只在 mating 维度 = 0 或近 0 的位置切：

```text
d(C) = Σ_{e ∈ C} dim(residual(e))
```

- `d(C) = 0`：子图完全独立 → 推荐
- `d(C) > 0`：子图无法独立解 → 退化为单图，不切

编译器检测：若声明了 sub-spec 但跨界 relation 维度 > 0，报错并建议合并。

### 11.4 层数上限 L ≤ 3

| L | 最大 N | 工作流 |
|---|-------|--------|
| 1 | 30 | 单图 |
| 2 | 80 | 1 个 sub-spec |
| 3 | 200 | 嵌套 sub-spec |
| > 3 | — | 程序化生成（D6），不嵌套 |

编译器在 L > 3 时报错。

### 11.5 跨层契约（每子图最小暴露）

- 每个子 spec 通过 `interface_spec.interface_body` 暴露 **1 个接口体** + `interface_spec.exports` 列出的 **≤ 3 个 feature**。
- 其他 body **严格私有**（schema 校验：父规约 relations 中引用 `sub_id.<feature>` 时，`<feature>` 必须在该子规约的 `exports` 中）。
- 父 spec **禁止**引用子图内部其他 body（如 `chassis_sub.wheel_fl.+z` 非法，编译期报错 `error.cross_layer_internal_ref`）。
- 跨层参数通过 Layer 0 Python 注入；spec 文件之间不跨层引用变量。

### 11.6 误差累积

每层残差上界 `ε = 1e-6 mm`，杠杆 1 m，L = 3：

```text
err_total ≈ L · ε · lever_arm = 3 × 1e-3 mm
```

工程上完全可忽略。**层数限制纯粹来自认知，不来自精度**。

### 11.7 循环依赖检测（DAG 校验）

**循环定义**：sub_spec 文件之间的 `bodies[*].sub_spec` 引用关系构成有向图；若该图含环则非法。

```text
def check_sub_spec_dag(root_spec_path):
    visiting = set()
    visited = set()
    def dfs(path):
        if path in visiting:
            raise SchemaError(f"sub_spec cycle: {' → '.join(visiting | {path})}")
        if path in visited:
            return
        visiting.add(path)
        spec = load(path)
        for body in spec.bodies.values():
            if "sub_spec" in body:
                dfs(resolve_path(path, body.sub_spec))
        visiting.remove(path)
        visited.add(path)
    dfs(root_spec_path)
```

- 检测时机：P2a 实现时，在 schema 校验阶段（编译前）调用。
- 错误信息格式：`error.cycle: "A.json → B.json → A.json"`

### 11.8 不实现的方向（明确排除）

- 跨层 feature 直接引用（`sub.internal_body.face`）
- 跨层联合求解（lazy frame、整体迭代）
- L > 3 的嵌套
- 子图之间循环依赖

---

## 12. 失败模式归属表

| 失败模式 | 归属层 | 检测方法 | 输出字段 |
|---------|-------|---------|---------|
| 引用拼错 | Layer 1 / 2 | schema 校验 + 建议名 | `error.suggested_names` |
| relation 字段缺失 | Layer 1 | schema 校验 | `error.field` |
| place 与 relation 冲突 | Layer 1 | schema 校验 | `error.conflict` |
| mating 欠声明 | Layer 4 sensitivity | mating_free 非空 | `mating_free`, `suggested_relations` |
| gauge 留白 | Layer 4 | gauge_free 非空 | `gauge_free`, `assumed_locks` 或 `witness_branches` |
| 过约束（数值） | Layer 4 MUS | 残差超阈值 + MUS | `conflict` |
| 跨层接口错位 | Layer 2 | interface feature 校验 | `error.interface_mismatch` |
| 跨层参数错配 | Layer 0 | 顶层 Python 单一来源（约定） | — |
| 求解不收敛 | Layer 3 | scipy 失败 | `solver_message`, `status=solve_failed` |
| 假 ok（旋转空转） | Layer 4 rotation_audit | gauge_free 中 `category: spin_*` | `rotation_issues` |
| 等价解错选 | Layer 4 witness | witness_branches 非空 | `witness_branches` |
| 跨层循环依赖 | Layer 1 | DAG 校验 | `error.cycle` |
| 子图体数超 64 | Layer 1 | limits | `error.scale` |

---

## 13. 与 Location 的兼容与对齐

### 13.1 `layout_only` 等价 Location 路径

```json
{
  "bodies": {
    "ornament": {
      "primitive": "box",
      "size": [20, 20, 20],
      "place": [80, 30, 100],
      "layout_only": true
    }
  }
}
```

等价于：

```python
ornament = _box(20,20,20).moved(Location((80, 30, 100)))
```

但有三个 Location 缺失的能力：

- 同一 spec 内可与 relation 体共存（统一报告）
- 编译期 schema 校验（防错位）
- 可选 `verify_mates` 检查残差

### 13.2 `verify_only` 模式

`policy.underconstrained == "permissive"` + 所有 mating 体带 `place` 初值：

```text
求解器跳过优化，仅对每条 constraint 计算残差并报告。
若残差 < tol → status = ok（layout 与 mate 自洽）
否则 → status = solve_failed + 残差最大的约束 id
```

用于"已有 Location 草稿，仅做几何验证"。

### 13.3 Python 程序化生成（D6）

`relations` 在 Python 中生成：

```python
relations = []
for col in range(4):
    for row in range(4):
        relations.append({
            "type": "flat_on",
            "child": f"pin_{col}_{row}",
            "on": "base.+z",
            "at": [col * 70 - 105, row * 70 - 105]
        })

CONSTRAINTS = {
    "version": 2,
    "ground": "base",
    "bodies": { ... },  # 也由 Python 生成
    "relations": relations,
}
```

- 与 Location 循环堆砌等价（D6 维度同级）
- 但获得 mating 验证与报告

### 13.4 双向工具（可选 P3）

- `layout_to_relations(layout_dict)` → 推荐 relations 列表
- `relations_to_layout(spec)` → 求解后导出 place 字典（调试可读）

非必需，作为后期增强。

---

## 14. 与现有实现的映射与迁移

### 14.1 文件级改动表

| 文件 | 改动类型 | 内容 |
|------|---------|------|
| `schema.py` | 扩展 | 支持 `version`, `relations`, `dof_policy`, `rotation_mode`, `place`, `layout_only`, `sub_spec`, `anchor_body`, `interface_spec`；v1/v2 双 path 分离 |
| `graph.py` | 保持 | `expand_constraints`（contact/hinge）保留在 v1 path；v2 path 不调用 |
| `macros.py` | **新增** | v2 几何宏（flat_on/coax/align/fix_to/hinge/slider）+ 策略宏（lock_orthogonal_to/yaw_free） |
| `primitives.py` | 保持 | 不改原语 feature 表 |
| `state.py` | **保持** | `STATE_DIM=7`、`BodyPose` 不变（见 §8.1 实现约定） |
| `constraints.py` | 保持 | 7 类基础约束残差不变 |
| `solver.py` | 重构 | 增加分桶（layout/analytic/yaw/free）+ analytic 路径 + free 桶 BFS 初值；v1 path 走原 `_run_optimizer` 不变 |
| `analytic.py` | **新增** | axis_aligned 解析放置 + 拓扑序 |
| `dof.py` | 扩展 | 稀疏化 numeric_jacobian（P2c-1）；解析 Jacobian（P2c-2，独立任务） |
| `audit.py` | 保持 | v1 path 继续使用；v2 path 由 `diagnostics` 替代 |
| `diagnostics.py` | **新增** | sensitivity 分类、MUS、witness 枚举、suggested_relations、归一化 Jacobian |
| `report.py` | 扩展 | 新字段（mating_free / gauge_free / assumed_locks / witness_branches / suggested_relations / schema_version） |
| `emit.py` | 保持 | transform 输出不变 |
| `assemble.py` | 扩展 | 支持 sub_spec body（接口体）；status 多态分支处理（见下） |
| `cli.py` | 扩展 | 新 `expand` 子命令（与现有 `solve`/`validate` 并列） |
| `errors.py` | 扩展 | 新错误类型（`SubSpecCycleError`、`CrossLayerInternalRefError` 等） |
| `dsl.py` | **新增** | v2 schema 校验与展开入口（与 schema.py 配合） |

`assemble.py` 的 status 分支变更：

- v1 path：仅当 status ∈ {ok, underconstrained} 时返回 Compound，否则 raise（**与现有行为兼容**）
- v2 path：
  - `ok` / `ok_assumed` → 返回 Compound（warning 写入 report）
  - `underconstrained` → 返回 Compound + warning（与 v1 一致）
  - `overconstrained` / `solve_failed` → raise `ConstraintAssemblyError`

### 14.2 schema 向后兼容策略

**v1 / v2 触发判定**（与 §6.6 一致）：

```text
if spec.get("version") == 2:                                          → v2 path
elif any v2-only fields present (relations / dof_policy / ...):       → schema error: "missing version: 2"
else:                                                                  → v1 path（行为不变）
```

**兼容保证**：

- v1 测试用例（`test_assemble.py`、`test_limits_audit.py`）必须**全部通过**且无修改。
- v1 path 与 v2 path 在 `solver.py` 中由顶层 if 分流为两个独立函数（`_solve_v1` / `_solve_v2`），避免互相污染。
- v2 path 中若 `relations == []` 且 `constraints != []`，仍走 v2 编译流程（启用新报告字段），但展开后等价于 v1。

### 14.3 与现有糖（contact / hinge）的迁移

- **v1 path**：`graph.expand_constraints` 中 `contact` → `plane_coincident`、`hinge` → `axis_coaxial + point_coincident` 的展开保留，旧 spec 不受影响。
- **v2 path**：
  - `contact` 在 v2 中**标记 deprecated**，但仍可工作（自动按 v1 糖展开后并入基础约束流）。
  - `hinge` 在 v2 中作为正式几何宏（`macros.py`），与 v1 糖逻辑一致但 `triggered_by` 追踪更完整；v2 spec 推荐写 `hinge` relation，不再走 `graph.expand_constraints`。

### 14.4 与 `references/constraint-assembly.md` 的关系

实现完成后，按以下顺序回写 skill 文档：

1. 先在 `references/constraint-assembly.md` 标注 v2 spec 入口、新字段（不删 v1 节）。
2. 新增 `references/relations.md`（或合并）描述 8 个宏（6 几何 + 2 策略）。
3. 在 SKILL.md 路由处加上"用 v2 relations 优先"的提示。

### 14.5 测试目录组织

旧测试位置不变，新增测试一一对应到新模块：

| 文件 | 状态 | 覆盖范围 |
|------|------|---------|
| `tests/test_assemble.py` | **保持** | v1 path 端到端 |
| `tests/test_limits_audit.py` | **保持** | v1 path + limits + 旋转审计 |
| `tests/test_macros.py` | 新增 | 8 个宏的展开行为（含 dry-run）|
| `tests/test_analytic.py` | 新增 | analytic 桶解析放置（v1 vs v2 对拍） |
| `tests/test_diagnostics.py` | 新增 | sensitivity 分类、MUS、witness、suggested_relations |
| `tests/test_sub_spec.py` | 新增 | 接口体拼接 + 跨层引用校验 + 循环检测 |
| `tests/test_dsl.py` | 新增 | v2 schema 校验、互斥关系、触发规则 |
| `tests/test_jacobian.py` | 新增（P2c） | 稀疏化与解析 J 对拍 |

---

## 15. 落地优先级与验收

### 15.1 优先级矩阵

| P | 项目 | 主收益维度 | 依赖 | 预估工作量 |
|---|------|----------|------|----------|
| **P0a** | `flat_on` 宏 + dry-run + relation id 命名空间 + v2 触发规则 | D1 token 量 | macros.py, dsl.py, schema.py, cli.py | 2-3 天 |
| **P0b** | `rotation_mode: axis_aligned` + analytic 桶 + 求解顺序分桶 | 速度、初值、旋转歧义 | solver.py, analytic.py（state.py 不动） | 3-4 天 |
| **P0c** | mating/gauge sensitivity 分类（含归一化）+ `assumed_locks` + status 多态 | P0 原则落地 | diagnostics.py, dof.py, report.py | 2-3 天 |
| **P1a** | free 桶 BFS 初值 | 一般树状装配收敛 | solver.py | 1-2 天 |
| **P1b** | 其他几何宏（coax / align / fix_to / slider / hinge 迁 v2） | 覆盖率 | macros.py | 2-3 天 |
| **P1c** | 策略宏（lock_orthogonal_to / yaw_free） | gauge 透明 | macros.py | 1 天 |
| **P1d** | `place` / `layout_only` / verify_only | 与 Location 对齐 | schema.py, solver.py | 2 天 |
| **P1e** | `suggested_relations` | 修复闭环 | diagnostics.py, report.py | 1-2 天 |
| **P2a** | 子图接口体（L=2，含循环检测） | 突破单图规模 | assemble.py, schema.py | 3-5 天 |
| **P2b** | MUS 冲突诊断 | 过约束可读 | diagnostics.py | 2-3 天 |
| **P2c-1** | **Jacobian 稀疏化**（仍数值差分） | 中等性能 | dof.py | 1-2 天 |
| **P2c-2** | **解析 Jacobian**（每类约束逐一推导 + `--verify-jacobian`） | 大子图性能 | dof.py, constraints.py | 5-8 天 |
| **P2d** | witness 多解枚举（写入候选） | 离散 gauge | diagnostics.py | 2-3 天 |
| **P2e** | yaw_only **4D 联合**求解 | 一般装配覆盖率 | solver.py | 2-3 天 |
| **P3a** | DR 风格子簇（自动分簇，对作者透明） | 大装配性能 | solver.py | 5-7 天 |
| **P3b** | L=3 嵌套 sub_spec | 大规模 | assemble.py | 3-4 天 |
| **P3c** | `layout_to_relations` / `relations_to_layout` | 调试 | dsl.py | 2 天 |

总计：P0 ≈ 7-10 天；P0+P1 ≈ 2-3 周；P0+P1+P2（不含 P2c-2）≈ 4 周；含 P2c-2 ≈ 5-6 周。

### 15.2 每项验收标准

**P0a `flat_on` + dry-run + 命名规则**：

- 单条 `flat_on` relation 展开为：4 条基础约束（plane_coincident + 3 条 point_plane_offset） + 当 `rotation_mode=axis_aligned` 时再加 3 条 axis_parallel
- 展开后每条带 `triggered_by`，id 遵循 `r{i}_{slot}` 规则
- `dry-run` CLI 输出可直接喂回 `solve` 子命令获得相同结果（编译/求解幂等）
- 父体支持矩阵（§7.2.1）的不支持组合 → schema 报错
- offset 符号在所有 face 值（±x/±y/±z）下与 v1 等价 spec 求解结果差 < 1e-9 mm
- 旧 `examples/constraint/specs/*` 全部仍通过

**P0b `rotation_mode: axis_aligned` + analytic 桶**：

- `solve_assembly` v2 path 对 analytic 桶 `nfev = 0`（不调 scipy）
- analytic 桶位姿与 v1 全 scipy 结果差异 < 1e-9 mm
- `BodyPose` 与 `STATE_DIM` 未改（diff 不涉及 `state.py`）
- BFS 拓扑序：父位姿先于子（顺序错时编译期报错）

**P0c sensitivity 分类**：

- 故意构造只缺 `axis_parallel` 的 spec → `mating_free == []`, `gauge_free != []`，category 标 `spin_z_on_support`
- 故意缺 `in_plane` 的 spec → `mating_free != []`，对应体的 axes 含 x/y
- `(gauge_policy=auto_lock)` 时规则覆盖所有 → `ok_assumed` + `assumed_locks` 非空
- `(gauge_policy=auto_lock)` 时规则仅覆盖部分 → `underconstrained` + warning `"unmatched_gauge"`
- sensitivity Jacobian 归一化后阈值 `1e-3 * S[0]` 对不同尺度 spec（μm/mm/m）行为一致

**P1a BFS 初值**：

- 对深度 ≥ 3 的链式 spec（free 桶），scipy `nfev` 比当前 Z 叠放减少 ≥ 50%
- analytic 桶在 §8.6 步骤 3 直接出最终位姿，BFS 不重复

**P1b/P1c 宏**：

- `fix_to(A, B, local=[x,y,z])` 展开为 3 条 offset + 3 条 axis_parallel，纯组合（不引新基础约束）
- `coax(a, b, offset=d)` 展开为 `axis_coaxial` + 沿轴 offset 约束，求解后 a.origin 沿 b 方向距 b.origin 为 d
- 所有展开通过 `dry-run` 可见

**P1d `place` / `layout_only`**：

- `layout_only: true` 体不出现在求解变量中（pack_poses 不包含其状态）
- `place` 与同名 relation 共存时 schema 报错 `error.conflict`
- `(mating_policy=permissive, gauge_policy=auto_lock)` 下，所有 mating 体带 place → verify_only 模式工作

**P2a sub_spec**：

- 双层装配（chassis sub + body）总体数 > 40
- 子图 transforms 拼接后世界坐标与单图等价差异 < 1e-9 mm
- 跨层引用子图内部 body（非 exports）时 schema 报错 `error.cross_layer_internal_ref`
- sub_spec 自引用或互引用 → 编译期 `SubSpecCycleError`

**P2b MUS**：

- 故意冲突 spec（如 plane_coincident + plane_distance 矛盾）→ `conflict[]` 含最小冲突集，条数 ≤ 3
- MUS 仅在 `solve_ok=True 且 residual_max > OT` 时启动
- 冲突集 > 20 条时直接返候选不做最小化

**P2c-1 稀疏化**：

- numeric_jacobian 调用次数下降至 ≈ nnz(J)/STATE_DIM 量级
- 求解结果与 v1 等价 spec 差 < 1e-9 mm

**P2c-2 解析 Jacobian**：

- 单大子图（N=30）求解时间下降 ≥ 5×（相对 P2c-1 稀疏数值版本）
- `--verify-jacobian` 模式下解析 J 与数值 J 元素差 < 1e-4
- 7 类基础约束全部覆盖

**P2d witness**：

- 仅缺 `axis_x` 锁的 spec（`gauge_policy=enumerate`）→ `witness_branches.*` 包含 2-4 候选
- 候选 id 可被加入新 relation 重跑得到不同 transforms

**P2e yaw_only**：

- 单 yaw 体子问题 4 维 scipy 解，状态向量包含 (tx, ty, tz, θ)
- 与"先平移后旋转"分步解法结果差 < 1e-6 mm（用于反证联合解必要性）

### 15.3 不在 P0-P3 中的项

- 二级 LLM 候选选择器（**整本文档不实现**）
- L > 3 嵌套
- 非原语 feature 提取
- 自然语言 → spec 端到端

---

## 16. 风险与对策

| 风险 | 对策 |
|------|------|
| 宏隐藏过多导致调试难 | `expand --dry-run` + `triggered_by` 双向追踪（强制） |
| `flat_on` 自动锁被误认为 "默认" | §7.2.1 明确为宏定义一部分，dry-run 完全可见；不计入 `assumed_locks` |
| `axis_aligned` 解析错（坐标系误用 / face 符号错） | golden test：v1 全 scipy vs v2 analytic 对拍 ±x/±y/±z 全部 face 值 < 1e-9 mm |
| sensitivity 分类阈值不稳定 | Jacobian 行残差尺度归一化 + 相对阈值 `1e-3 × S[0]`；golden test 覆盖不同尺度 spec |
| `assumed_locks` 选错对称分支 | 必须**审计输出**；`strict_ok` 模式可禁用；`gauge_policy=enumerate` 提供多解候选 |
| `gauge_policy=auto_lock` 未匹配残留 | status 降为 `underconstrained` + warning，不静默放过（§10.2 三分支） |
| 过约束阈值硬编码 | 改为 `dof_policy.overconstrained_threshold`，默认 `100×RESIDUAL_TOL`，可配置 |
| 子图接口字段命名重载 | `interface_spec.interface_body`（顶层字段）与 ground body id 分离命名 |
| `sub_spec` 与 build123d Compound 混淆 | 字段统一用 `sub_spec`，文档全局不再用 `compound` 描述子规约 |
| `anchor` 字段语义模糊 | 统一为 `anchor_body: <body_id>`，附录 A 明确 |
| 旧 v1 spec 行为变化 | 严格回归测试集；v1 path 与 v2 path 在 solver.py 顶层分流 |
| v2 字段被误当 v1（缺 version） | §6.6 触发规则：含任一 v2-only 字段必须有 `version: 2`，否则 schema 报错 |
| `place` 与 `relation` 双套真相 | schema 强制互斥 + 编译期报错 |
| `mount` 字段与 relation 双入口 | 已删除体级 `mount`，仅保留 `relations[]` 单一入口 |
| yaw 桶解耦平移与旋转不成立 | yaw 桶改为 4D 联合解（D17） |
| MUS 启动条件 | 仅在 `solve_ok=True 且 residual > OT` 时；solve_failed 不走 MUS |
| MUS 性能（O(|over|² × solve)） | 上限 `|over| ≤ 20`；否则只返候选不做最小化 |
| witness 候选过多 | 单体上限 4 候选；超过时截断并报警 |
| 解析 Jacobian 错（推导繁） | 拆 P2c-1（稀疏化）/ P2c-2（解析化）；`--verify-jacobian` 数值对拍 |
| DR 自动子簇与接口体冲突 | DR 推到 P3，主路径走 §11 接口体；两者作用域不同（单 spec 内 vs 跨 spec） |
| 跨层 feature 错引用 | schema 校验父规约只能引用子规约 `exports` 列出的 feature |
| sub_spec 循环依赖 | DAG 校验（§11.7），编译期 DFS 检测 |
| 跨层误差累积 | L ≤ 3 + 残差 1e-6 mm 强约束 |
| report 字段集变化破坏消费方 | `report.schema_version: 1/2`，v1 path 不输出新字段 |

---

## 17. 未来扩展（不在本方案范围）

- **非原语零件特征**：从 `inspect --planes` 自动提取 feature 表
- **斜接 / 自由曲面 mate**：`free` 桶下的高维 scipy 加速
- **完整 DR-Planner**：研究级，覆盖一般机构
- **自动 spec 生成**：从 NL/草图，独立 skill 范畴
- **二级 LLM 候选选择**：本方案明确不做，留待未来评估

---

## 附录 A：完整 schema 草案

> **触发规则**：spec 含以下任一字段时必须设 `"version": 2`（缺则 schema 报错）：
> `relations` / `dof_policy` / `interface_spec` / `bodies[*].place` / `rotation_mode` / `layout_only` / `sub_spec` / `anchor_body`。

```json
{
  "$schema": "constraint-assembly-v2",
  "version": 2,

  "ground": "<body_id>",

  "limits": {
    "max_bodies": 48,
    "max_constraints": 300,
    "warn_bodies": 32,
    "max_layers": 3
  },

  "dof_policy": {
    "default_box_on_plane": "fixed_orthogonal | none",
    "mating_policy": "strict | permissive",
    "gauge_policy": "require | auto_lock | enumerate",
    "strict_ok": false,
    "overconstrained_threshold": 1e-4
  },

  "bodies": {
    "<body_id>": {
      "primitive": "box | cylinder | sphere",
      "size": [0, 0, 0],
      "radius": 0,
      "height": 0,

      "rotation_mode": "axis_aligned | yaw_only | free",
      "yaw_axis": "+z",

      "place": [0, 0, 0],
      "layout_only": false,

      "sub_spec": "<path to sub spec json or registered id>",
      "anchor_body": "<body_id in sub spec, optional>"
    }
  },

  "relations": [
    {
      "type": "flat_on",
      "id": "r1",
      "child": "<body_id>",
      "on": "<parent>.<plane_feature>",
      "at": [0, 0],
      "gap": 0,
      "face": "-z"
    },
    {
      "type": "coax",
      "a": "<body_id>.<axis_feature>",
      "b": "<body_id>.<axis_feature>",
      "offset": 0
    },
    {
      "type": "align",
      "a": "<body_id>.<axis_feature>",
      "b": "<body_id>.<axis_feature>",
      "opposed": false
    },
    {
      "type": "fix_to",
      "child": "<body_id>",
      "parent": "<body_id>",
      "local": [0, 0, 0]
    },
    {
      "type": "hinge",
      "a": "<body_id>.<axis>",
      "b": "<body_id>.<axis>",
      "angle": 0
    },
    {
      "type": "slider",
      "a": "<body_id>.<axis>",
      "b": "<body_id>.<axis>",
      "displacement": 0
    },
    {
      "type": "lock_orthogonal_to",
      "child": "<body_id>",
      "target": "<body_id>"
    },
    {
      "type": "yaw_free",
      "child": "<body_id>",
      "yaw_axis": "+z"
    }
  ],

  "constraints": [],

  "initial_guess": { "<body_id>": [0, 0, 0, 0, 0, 0, 1] },

  "interface_spec": {
    "interface_body": "<body_id, equals this spec's ground>",
    "exports": ["<body_id>.<feature>", "..."]
  }
}
```

**互斥关系矩阵**（schema 校验阶段强制）：

| 字段组合 | 处理 |
|---------|------|
| `place` × 在 `relations.child/a/b` 中出现 | ✗ 报错 `error.conflict` |
| `sub_spec` × `primitive` | ✗ 报错（互斥） |
| `sub_spec` × `place` | ✗ 报错（子图体不支持 layout） |
| `sub_spec` × `layout_only` | ✗ 报错 |
| `sub_spec` × `rotation_mode` | ✗ 报错（子规约自己管） |
| `layout_only=true` × 缺 `place` | ✗ 报错 |
| 同一 body 出现多条 `place` 或多条同名 relation | ✗ 报错 |
| `relations` 与 `constraints` 共存且 id 冲突 | ✗ 报错（命名空间隔离：r* vs 非 r*） |
| 含任一 v2 字段但 `version != 2` | ✗ 报错 `missing version: 2` |

**relations / constraints 共存与 id 命名空间**：

- relations 展开的基础约束 id 均以 `r` 开头（`r{i}_{slot}`）
- 作者 constraints 项的 id 不得以 `r` 开头（强制 schema 检查）
- 矛盾检测不在编译期，由求解后 MUS 报告

---

## 附录 B：示例 spec

### B.1 简单单图（与 Location 同信息量）

```json
{
  "version": 2,
  "ground": "base",
  "bodies": {
    "base":   { "primitive": "box", "size": [200, 150, 20] },
    "block1": { "primitive": "box", "size": [40, 30, 25] },
    "block2": { "primitive": "box", "size": [40, 30, 25] }
  },
  "relations": [
    { "type": "flat_on", "child": "block1", "on": "base.+z", "at": [30, 40] },
    { "type": "flat_on", "child": "block2", "on": "base.+z", "at": [-30, -40] }
  ]
}
```

每体信息量：`size`（3 数） + `at`（2 数） + `on`（1 引用） = 与 Location 的 3 个数同级，但带 mating 验证。

### B.2 含 layout_only

```json
{
  "version": 2,
  "ground": "base",
  "bodies": {
    "base":  { "primitive": "box", "size": [200, 150, 20] },
    "mate1": { "primitive": "box", "size": [40, 30, 25] },
    "logo":  { "primitive": "box", "size": [10, 10, 2],
               "place": [0, 0, 22], "layout_only": true }
  },
  "relations": [
    { "type": "flat_on", "child": "mate1", "on": "base.+z", "at": [50, 30] }
  ]
}
```

### B.3 双层 sub_spec（L = 2）

父 spec：

```json
{
  "version": 2,
  "ground": "world_root",
  "bodies": {
    "world_root": { "primitive": "box", "size": [1, 1, 1] },
    "chassis":    { "sub_spec": "chassis.json" }
  },
  "relations": [
    { "type": "fix_to", "child": "chassis", "parent": "world_root" }
  ]
}
```

> 说明：父规约中 `chassis` 不写 `primitive`（与 `sub_spec` 互斥）；其代理几何来自子规约 `interface_spec.interface_body` 所指向的 body 原语。

子 spec `chassis.json`：

```json
{
  "version": 2,
  "ground": "platform",
  "bodies": {
    "platform": { "primitive": "box", "size": [400, 180, 55] },
    "wheel_fl": { "primitive": "box", "size": [55, 35, 55] }
  },
  "relations": [
    { "type": "flat_on", "child": "wheel_fl", "on": "platform.+z", "at": [-145, 78] }
  ],
  "interface_spec": {
    "interface_body": "platform",
    "exports": ["platform.+z", "platform.center"]
  }
}
```

### B.4 程序化生成（D6）

```python
import json

relations = [
    {"type": "flat_on", "child": f"pin_{c}_{r}", "on": "base.+z",
     "at": [c * 70 - 105, r * 70 - 105]}
    for c in range(4) for r in range(4)
]

bodies = {"base": {"primitive": "box", "size": [400, 400, 20]}}
for c in range(4):
    for r in range(4):
        bodies[f"pin_{c}_{r}"] = {"primitive": "box", "size": [14, 14, 32]}

spec = {
    "version": 2,
    "ground": "base",
    "bodies": bodies,
    "relations": relations,
}

# spec 直接传 API（不经 JSON 文件）
from constraint.solver import solve_assembly
result = solve_assembly(spec)
print(json.dumps(result["report"], indent=2))
```

注意：`version: 2` 必填（B.4 是含 `relations` 的 v2 spec，缺 version 会被 schema 报错）。

---

## 附录 C：核心算法伪代码

### C.1 编译 pipeline

```python
def compile_spec_v2(spec):
    # 1. schema validate（含 v1/v2 触发规则、互斥关系、sub_spec DAG）
    validated = validate_v2(spec)

    # 2. expand macros（relations → 基础约束，带 triggered_by）
    base_constraints = []
    for r in validated.relations:
        base_constraints.extend(expand_macro(r, validated.bodies, validated.dof_policy))
    # 作者写的 constraints 直接并入（标 triggered_by="user"，id 不得以 r 开头）
    base_constraints.extend(annotate_user(validated.constraints))

    # 3. bucket bodies
    buckets = bucket_bodies(validated.bodies)

    # 4. resolve sub_spec bodies（编译期，不递归求解）
    sub_specs = {b: load_sub(validated.bodies[b].sub_spec)
                 for b in validated.bodies
                 if "sub_spec" in validated.bodies[b]}

    # 5. predict mating/gauge sensitivity hints（基于 relation 类型 + body 模式）
    sensitivity_hints = preclassify_sensitivity(base_constraints, validated.bodies)

    return CompiledSpec(
        bodies=validated.bodies,
        constraints=base_constraints,
        buckets=buckets,
        sub_specs=sub_specs,
        sensitivity_hints=sensitivity_hints,
        policy=validated.dof_policy,
    )
```

### C.2 求解 pipeline

```python
def solve_compiled(compiled):
    # 1. resolve sub-specs first
    sub_transforms = {}
    for body_id, sub in compiled.sub_specs.items():
        sub_transforms[body_id] = solve_compiled(compile_spec_v2(sub))

    # 2. layout bucket: direct read
    poses = {}
    for bid in compiled.buckets["layout"]:
        poses[bid] = pose_from_place(compiled.bodies[bid].place)

    # 3. analytic bucket: BFS topological order
    for bid in topological_order(compiled.buckets["analytic"], compiled.constraints):
        poses[bid] = place_analytic(bid, compiled.constraints, poses)

    # 4. yaw bucket: 4D joint solves (per cluster)
    for cluster in yaw_clusters(compiled.buckets["yaw"], compiled.constraints):
        poses.update(solve_yaw_cluster_4d(cluster, compiled.constraints, poses))

    # 5. free bucket: scipy with BFS initial guess
    if compiled.buckets["free"]:
        bfs_init = bfs_initial_poses_for_free(compiled, poses)
        poses.update(scipy_solve(compiled.buckets["free"], compiled.constraints,
                                  initial=bfs_init))

    # 6. verify all residuals
    residuals = compute_all_residuals(compiled.constraints, poses)
    solve_ok = max(abs(r) for r in residuals) < RESIDUAL_TOL

    # 7. classify free directions (normalized SVD)
    J = analytic_jacobian_or_sparse_numeric(compiled.constraints, poses)
    free_summary = classify_free_directions(J, compiled.constraints, poses,
                                             compiled.sensitivity_hints)

    # 8. apply mating_policy × gauge_policy
    OT = compiled.policy.overconstrained_threshold
    if not solve_ok and max(abs(r) for r in residuals) > OT:
        # 仅在 solve_ok=True 且超阈值时跑 MUS；这里 solve_ok=False 直接 solve_failed
        mus = []  # 留空，由调用方根据条件决定是否跑 §10.3 MUS
        return Report(status="solve_failed", residual_max=max(abs(r) for r in residuals),
                       solver_message="not converged")

    assumed_locks = []
    witness_branches = {}
    unmatched_gauge = []
    if free_summary.gauge_free:
        if compiled.policy.gauge_policy == "enumerate":
            witness_branches = enumerate_witnesses(free_summary.gauge_free, poses)
        elif compiled.policy.gauge_policy == "auto_lock":
            assumed_locks, unmatched_gauge, poses = apply_gauge_rules(
                free_summary.gauge_free, poses, compiled)

    # 9. status (§4.3 / §6.4 矩阵)
    status = pick_status(residuals, free_summary, assumed_locks,
                          unmatched_gauge, compiled.policy)

    return Report(
        schema_version=2,
        status=status,
        poses=poses,
        transforms=transforms_for(poses, sub_transforms),
        residual_max=max(abs(r) for r in residuals),
        mating_free=free_summary.mating_free,
        gauge_free=free_summary.gauge_free,
        assumed_locks=assumed_locks,
        witness_branches=witness_branches,
        suggested_relations=suggest_from_mating(free_summary.mating_free,
                                                  compiled.bodies),
    )
```

### C.3 `flat_on` 展开（含 face 符号修正、父类型支持矩阵、axis_parallel 视为宏定义一部分）

```python
AXIS_INDEX = {"x": 0, "y": 1, "z": 2}

def axis_of(face: str) -> str:
    # "+z" -> "z", "-x" -> "x"
    return face[1]

def sign_of(face: str) -> int:
    # "-z" → child 负 Z 面贴在 plane "上方" → child.center 在 plane +法向 侧 → offset = +half
    # "+z" → child 正 Z 面贴在 plane "下方" → child.center 在 plane -法向 侧 → offset = -half
    return +1 if face.startswith("-") else -1

def expand_flat_on(rel, bodies, dof_policy):
    rid = rel.get("id") or auto_id(rel)            # § 7.4 命名规则
    child_id = rel["child"]
    child = bodies[child_id]
    parent_ref = parse_feature_ref(rel["on"])      # e.g. "platform.+z"
    parent_id = parent_ref.body_id
    parent_body = bodies[parent_id]
    u, v = rel["at"]
    gap = rel.get("gap", 0)
    face = rel.get("face", "-z")

    # 父体类型校验（§ 7.2.1 支持矩阵）
    if parent_body.primitive == "sphere":
        raise SchemaError("flat_on: parent cannot be sphere")
    parent_face_is_cylinder = (parent_body.primitive == "cylinder")
    child_is_box = (child.primitive == "box")
    child_is_cylinder = (child.primitive == "cylinder")
    child_is_sphere = (child.primitive == "sphere")

    # face 符号 + 法向 offset
    if child_is_box:
        child_half = child.size[AXIS_INDEX[axis_of(face)]] / 2
    elif child_is_cylinder:
        # face 仅接受 "-z" 或 "+z"（cylinder 顶/底面贴接）
        if axis_of(face) != "z":
            raise SchemaError("flat_on: cylinder child must face ±z")
        child_half = child.height / 2
    else:  # sphere
        child_half = child.radius
    offset_value = sign_of(face) * (child_half + gap)

    out = [
        # 1. 贴面
        {"id": f"{rid}_pc", "type": "plane_coincident",
         "a": f"{child_id}.{face}", "b": rel["on"], "opposed": True,
         "triggered_by": f"{rid}:flat_on"},
        # 2. 面内 u
        {"id": f"{rid}_oux", "type": "point_plane_offset",
         "point": f"{child_id}.center", "plane": rel["on"],
         "in_plane": "x", "value": u,
         "triggered_by": f"{rid}:flat_on:tangent_u"},
        # 3. 面内 v
        {"id": f"{rid}_ouy", "type": "point_plane_offset",
         "point": f"{child_id}.center", "plane": rel["on"],
         "in_plane": "y", "value": v,
         "triggered_by": f"{rid}:flat_on:tangent_v"},
        # 4. 法向偏移（含符号修正）
        {"id": f"{rid}_off", "type": "point_plane_offset",
         "point": f"{child_id}.center", "plane": rel["on"],
         "offset": offset_value,
         "triggered_by": f"{rid}:flat_on:normal"},
    ]

    # 5. axis_parallel：宏定义的一部分（不是 assumed_locks）
    #    sphere child 不锁；cylinder 父或 child 仅锁 axis_z；box-box 锁三轴
    if dof_policy.default_box_on_plane == "fixed_orthogonal" and not child_is_sphere:
        if child_is_box and not parent_face_is_cylinder:
            axes = ["axis_x", "axis_y", "axis_z"]
        else:
            axes = ["axis_z"]  # 仅锁法向轴
        for axis in axes:
            out.append({
                "id": f"{rid}_par_{axis[-1]}",
                "type": "axis_parallel",
                "a": f"{child_id}.{axis}",
                "b": f"{parent_id}.{axis}",
                "triggered_by": f"{rid}:flat_on:lock_orthogonal",
            })

    return out
```

**关键点**：

- `offset_value` 含 `sign(face)`，所有 ±x/±y/±z face 值通用
- 三条 axis_parallel 是宏定义的一部分（dry-run 可见、有 `triggered_by`），**不**进入 `assumed_locks`
- 父子原语类型组合受 §7.2.1 支持矩阵限制
- relation id 命名遵循 §7.4 规则

### C.4 sensitivity 分类（含残差归一化）

```python
def residual_scale(constraint, k):
    """每条残差的特征尺度：方向项=1，距离项=max(1mm, |r|)"""
    if constraint.type in {"axis_parallel", "axis_coaxial", "plane_coincident"}:
        if k < 3:  # 前 3 项通常是方向残差
            return 1.0
    return max(1.0, abs(constraint.residual_at(x_star)[k]))


def normalize_jacobian_rows(J, constraints, x_star):
    J_norm = J.copy()
    row = 0
    for c in constraints:
        for k in range(c.residual_dim):
            J_norm[row, :] /= residual_scale(c, k)
            row += 1
    return J_norm


def classify_free_directions(J_raw, constraints, x_star, sensitivity_hints,
                              relative_epsilon=1e-3):
    # 1. 残差归一化 → 无量纲化
    J = normalize_jacobian_rows(J_raw, constraints, x_star)

    # 2. SVD（基于归一化 J）
    U, S, Vt = svd(J)
    rank = sum(S > 1e-4)
    null_vectors = Vt[rank:]

    # 3. mating 阈值：相对最大奇异值
    epsilon_mating = relative_epsilon * S[0]

    # 4. 对每个 null 方向分类
    mating_indices = [i for i, c in enumerate(constraints) if not c.is_gauge_only()]
    mating_block = J[mating_indices, :]  # 已归一化

    mating_free, gauge_free = [], []
    for v in null_vectors:
        sens = norm(mating_block @ v)
        body, dof_axes = locate_body_axis(v)
        if sens > epsilon_mating:
            mating_free.append({
                "body": body, "axes": dof_axes,
                "affects": [constraints[i].id for i in nonzero_rows(mating_block @ v)]
            })
        else:
            gauge_free.append({
                "body": body, "axes": dof_axes,
                "category": classify_gauge_category(v, body, constraints, sensitivity_hints)
            })

    return FreeSummary(mating_free=mating_free, gauge_free=gauge_free)
```

**要点**：

- 归一化让方向/距离残差可比，避免单位差异导致阈值失效
- `relative_epsilon = 1e-3 × S[0]` 是与 SVD 最大奇异值的比值，对任何尺度 spec 通用
- `is_gauge_only()`：约束是否只锁 gauge（例如 dof_policy 推导的纯破缺锁），由编译器标注

### C.5 witness 枚举

```python
def enumerate_witnesses(gauge_free, current_poses):
    branches = {}
    for gf in gauge_free:
        candidates = []
        candidate_locks = [
            ("axis_parallel_x", "axis_x", "+x"),
            ("axis_parallel_x", "axis_x", "-x"),
            ("axis_parallel_y", "axis_y", "+y"),
            ("axis_parallel_y", "axis_y", "-y"),
        ]
        for rule, axis, direction in candidate_locks[:4]:
            try:
                new_poses = solve_with_extra_lock(gf.body, axis, direction,
                                                    current_poses)
                candidates.append({
                    "id": f"{gf.body}_{rule}_{direction}",
                    "rule": rule,
                    "description": f"{gf.body}.{axis} aligned {direction}",
                    "delta_translation": new_poses[gf.body].translation,
                })
            except Exception:
                continue
        branches[gf.body] = candidates[:4]
    return branches
```

---

## 18. 一句话总结

> 让约束机制达到「与 Location 同级易生成」的核心，是**按自主性等级把信息正确分布到 6 个维度**（D1 mating 自主、D2+D5 gauge 默认、D3 policy 全局、D4 强校验引用、D6 Python 程序化）；辅以**几何骨架级宏 6 几何 + 2 策略 = 8 个**（不引产品宏，dry-run 双向追踪）、**业界成熟的 DOF/MUS 诊断**（含残差归一化、可配阈值）、**L ≤ 3 的接口体分层（sub_spec + interface_body）**、**正交的 mating_policy × gauge_policy 双开关**、**确定性 gauge 补全 + witness 候选写入报告（无二级 LLM）**——这套组合既保留 Location 的简洁性，又获得 Location 无法提供的"父位姿求解、非轴对齐父面透明、mating 验证、跨层复用"能力。实施起点：P0a `flat_on` + dry-run + 命名规则 → P0b `rotation_mode: axis_aligned` 解析 + 分桶 → P0c mating/gauge 分类 + status 多态，三项正交、可并行。

实施推荐起点：P0a `flat_on` → P0b `rotation_mode: axis_aligned` → P0c mating/gauge 分类。三项正交，可并行实施。
