# 几何装配约束求解 — 实现方案（text-to-cad）

> **读者**：仓库维护者（开发阶段进度与内核设计）。Codex / 代理日常装配请读 `.agents/skills/cad/references/constraint-assembly.md`，不要依赖本文。

本文档描述在本仓库中落地 **「build123d 零件脚本 + 声明式装配约束 + SciPy 求解」** 融合方案的完整设计。验证期以 **box / cylinder / sphere** 原语与 **手工场景 + `inspect` 对拍** 为主，**不引入 pytest 单测门禁**（可后续再补）。

---

## 1. 目标与非目标

### 1.1 目标

- **领域无关**的刚体装配：点 / 线(轴) / 面关系 + 距离 / 角度 / 重合。
- **与现有 harness 融合**：求解结果写入 `AssemblyInstanceSpec.transform`（16 元矩阵），走现有 `gen_step()` → `scripts/step` → `inspect` 链路。
- **AI 友好**：装配关系用 **小 JSON**（`constraints` 块），零件几何仍用 **build123d Python**；不把约束做成「魔改 build123d API」。
- **可修复闭环**：欠约束 / 过约束 / 缺 gauge 时返回 **短小结构化报告**（非巨大 Jacobian），供 LLM 1–3 轮修补。

### 1.2 非目标（验证期不做）

- 替代 build123d 做零件建模（拉伸、倒角、布尔等）。
- 从一句话自动生成完整柜子拓扑 + 板厚传播（Parameter Graph 仍主要在脚本里）。
- 2D 草图约束（Sketcher / SolveSpace 集成）。
- 替换 OCC / build123d 几何内核。
- 验证期 **不要求** pytest 单测；用固定场景脚本 + `inspect mate` 验收。

---

## 2. 与现有仓库的关系

### 2.1 已有能力（直接复用）

| 组件 | 路径/工具 | 用途 |
|------|-----------|------|
| 装配导出 | `assembly_spec.py` | 只认 `transform` |
| STEP 生成 | `generation.py` → `_write_assembly_step_payload` | 装配 envelope |
| 装配定位说明 | `references/positioning.md` | 与 Joint/Location 分工 |
| 校验 | `scripts/inspect`：`mate`、`measure`、`frame` | 求解后抽检 |
| Python 环境 | `./.venv` + build123d/OCP | 零件 STEP |

### 2.2 融合原则（模式一）

**同一 `assembly.py`，三层分工：**

```text
┌─────────────────────────────────────────┐
│ Parameter 层：width, block1_x, …        │  ← Python 变量
├─────────────────────────────────────────┤
│ Part 层：build123d 建各零件（内存形体）   │
├─────────────────────────────────────────┤
│ Assembly 层：CONSTRAINTS + solve        │  ← constraint_assembly → Compound
└─────────────────────────────────────────┘
```

- LLM 工作流：`gen_step()` **返回 `shape_or_compound`**（与 `build123d-modeling.md` 一致）。
- 实现入口：`constraint.assemble.constraint_assembly(CONSTRAINTS, parts)` → `Compound`；`scripts/step` 导出一个装配 STEP。
- 代理文档：`.agents/skills/cad/references/constraint-assembly.md`（勿要求 `path` / `step_output` / 子件 STEP）。
- 单测：`constraint/tests/test_assemble.py`（`constraint_assembly`）。

### 2.3 `gen_step()` 形态

```python
def gen_step():
    return constraint_assembly(
        CONSTRAINTS,
        {"base": base_solid, "b1": block_solid},
        report_path=...,  # 可选
    )
```

`generation._normalize_step_payload` 亦接受 `{"constraints", "parts"}` 并折叠为 `{"shape": Compound}`。

---

## 3. 代码布局

```text
.agents/skills/cad/scripts/constraint/
  __init__.py
  schema.py           # JSON 校验、封闭词汇表
  features.py         # Point / Axis / Plane 引用解析
  primitives.py       # box | cylinder | sphere 特征表（几何中心原点）
  constraints.py      # 约束类型 → 残差
  state.py            # 四元数 + 平移、4×4 矩阵
  graph.py            # 装配图、语法糖展开
  solver.py           # scipy.optimize.least_squares 封装
  dof.py              # Jacobian 秩、简短 DOF 摘要
  report.py           # 压缩版 LLM 报告
  emit.py             # → 16 元 transform（assembly_spec 兼容）
  errors.py

examples/constraint/          # 验证期手工场景（非 pytest）
  box_on_box.py
  two_boxes_under.py
  cylinder_on_box.py
  sphere_on_box.py

scripts/constraint              # 可选 CLI 入口（Phase 1）
  __main__.py                   # python scripts/constraint solve spec.json
```

依赖：`numpy`、`scipy`（仓库 venv 通常已有或随 cad requirements 增加）。

---

## 4. 坐标与刚体状态

### 4.1 零件局部系（已确认）

- **原点**：几何中心（box、cylinder、sphere 一致）。
- **+Z**：box 顶面法向；cylinder 轴线方向；sphere 仅用于辅助平面/轴命名。

### 4.2 世界系状态变量

每个刚体 `body_id`：

- 平移 `t ∈ R³`（3）
- 单位四元数 `q ∈ R⁴`，残差加 `‖q‖² - 1` 或求解后归一化（权重 10）

变量向量顺序固定：`[t₁, q₁, t₂, q₂, …]`，便于 Jacobian 分块。

### 4.3 Gauge（整体自由度）

- 必须指定 `ground`（等价 `FIX` 该体在 identity 或给定世界位姿）。
- 未固定 gauge 时 **Phase A 直接报错** `missing_gauge`，不进入求解。

---

## 5. Feature 系统（点 / 线 / 面）

验证期 **必须** 有点线面三类原语（数学完备 + 后续扩展非原语零件时同一套引用）。  
在 box / cylinder / sphere 上 **枚举有限、封闭**，不让 LLM 发明名字。

### 5.1 引用语法（字符串，写在 constraints JSON）

```text
"<body_id>.<feature_id>"
```

示例：`base.+z`、`pin.axis`、`b1.center`。

### 5.2 Box `(Lx, Ly, Lz)` — 局部定义

| 类型 | feature_id | 定义 |
|------|------------|------|
| Point | `center` | `(0,0,0)` |
| Point | `+x,-x,+y,-y,+z,-z` | 各面中心点 |
| Axis | `axis_x` | 过 center，方向 `(1,0,0)` |
| Axis | `axis_y` | 过 center，方向 `(0,1,0)` |
| Axis | `axis_z` | 过 center，方向 `(0,0,1)` |
| Plane | `+x` | 法向 `+X`，过 `(Lx/2,0,0)` |
| Plane | `-x` | 法向 `-X`，过 `(-Lx/2,0,0)` |
| Plane | `+y,-y,+z,-z` | 同理（别名 `plane_px` … `plane_nz`） |
| Axis | `edge_px_pz` … `edge_nx_ny` | 12 条棱：两面交线，方向沿剩余轴 |

共：**8 点 + 3 中心轴 + 6 面 + 12 棱 = 29 个**封闭 feature_id（验证期全部实现）。

### 5.3 Cylinder `(r, h)` — 轴沿 +Z

| 类型 | feature_id | 定义 |
|------|------------|------|
| Point | `center` | 原点 |
| Point | `top`, `bottom` | `(0,0,±h/2)` |
| Axis | `axis` | 过 center，`+Z` |
| Plane | `top`, `bottom` | 法向 `±Z`，过对应点 |

### 5.4 Sphere `(r)`

| 类型 | feature_id | 定义 |
|------|------------|------|
| Point | `center` | 原点 |
| Plane | `equator` | 法向 `+Z`，过 center（辅助） |
| Axis | `axis_x`, `axis_y`, `axis_z` | 过 center 的主轴（辅助同轴约束） |

### 5.5 世界系求值

对 body 位姿 `(t, q)`，旋转矩阵 `R(q)`：

- 点：`p_w = R * p_l + t`
- 方向（轴/面法向）：`n_w = R * n_l`
- 平面：`(n_w, d_w)`，其中 `d_w = n_w · p_w`（过面上一点）

---

## 6. 约束系统（验证期最小集）

### 6.1 基础约束

| type | 残差维 | 说明 |
|------|--------|------|
| `fix` | 6 | 锁定 body 位姿（ground） |
| `point_coincident` | 3 | 两点重合 |
| `plane_coincident` | 5 | 法向平行 + 共面（含法向符号处理） |
| `axis_coaxial` | 4 | 方向平行 + 轴上点共线 |
| `plane_distance` | 1 | 沿法向距离 |
| `point_plane_offset` | 1 | 点在平面法向偏移；可拆 `point_plane_offset_x/y` 做平面内定位 |

### 6.2 语法糖（展开为基础约束，不进 JSON schema 必填）

| 糖 | 展开 |
|----|------|
| `contact` | `plane_coincident` + 法向相向规则 |
| `hinge` | `axis_coaxial` + `point_coincident` |

### 6.3 约束 JSON 示例（LLM 输入，宜小）

```json
{
  "ground": "base",
  "bodies": {
    "base": {"primitive": "box", "size": [200, 150, 20]},
    "b1": {"primitive": "box", "size": [40, 30, 25]}
  },
  "constraints": [
    {"type": "plane_coincident", "a": "b1.-z", "b": "base.+z"},
    {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "offset": 0},
    {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "x", "value": 30},
    {"type": "point_plane_offset", "point": "b1.center", "plane": "base.+z", "in_plane": "y", "value": 40}
  ]
}
```

`size` 也可改为引用 Python 变量，由 `gen_step()` 在调用前 `resolve_parameters()` 注入。

---

## 7. 求解器：不自写 LM，自写残差

### 7.1 选型

| 层 | 实现 |
|----|------|
| 优化循环 | **`scipy.optimize.least_squares`**（`method='lm'` 或 `trf`） |
| 残差 `F(x)` | **自写**（本领域） |
| Jacobian | 验证期 **数值** `jac='2-point'`；稳定后可解析加速 |
| DOF 分析 | `numpy.linalg.svd` on `J` at `x*` |

**不**在验证期集成 SolveSpace / FreeCAD GCS / PyBullet（输入模型不同或精度/语义不符）。

### 7.2 残差加权（稳定性）

- 位置 (mm)：`w = 1`
- 方向（单位向量差）：`w = 1`
- 四元数归一：`w = 10`

### 7.3 初值

1. 默认：所有非 ground 体 identity 或略高于 ground 顶面。
2. 可选：`initial_guess: { "b1": [16 floats] }` 来自脚本近似 `Location`。

### 7.4 收敛判据

- `‖F‖∞ < 1e-6`（mm 级装配）
- 失败时进入 `report`，不静默回退到随意位姿

---

## 8. 欠约束 / 过约束：何时检测、如何报告

### 8.1 三阶段

| 阶段 | 时机 | 内容 |
|------|------|------|
| **A 静态** | 求解前 | schema、`ground`、未知 body/feature、重复 id、约束条数启发式 |
| **B 线性化** | 初值 `x0` | `F(x0)`、`rank(J)` 初筛 |
| **C 求解后** | `x*` 或失败点 | 最终 `rank`、最小奇异值、冲突约束对 |

**精确**剩余 DOF 方向主要在 **B/C**（需 `J`）。  
**A** 可捕获：`missing_gauge`、非法 `feature_id`、仅 `contact` 两 box 的 `likely_underconstrained` 提示。

### 8.2 返回给 LLM 的 JSON（压缩版，通常 &lt; 2KB）

原则：**只给可操作建议，不给完整矩阵/奇异向量列表**。

```json
{
  "status": "underconstrained",
  "ground": "base",
  "solve_ok": true,
  "residual_max": 1.1e-9,
  "dof_deficit": 2,
  "free": [
    {"body": "b1", "trans": ["x","y"], "rot": []}
  ],
  "hint": [
    "为 b1 增加相对 base.+z 的 in_plane x/y offset",
    "或为 b2 增加对称/距离约束"
  ],
  "conflict": []
}
```

过约束示例：

```json
{
  "status": "overconstrained",
  "solve_ok": false,
  "residual_max": 2.4,
  "conflict": [
    {"ids": ["c1","c4"], "reason": "既重合又 distance=5"}
  ],
  "hint": ["删除 c4 或改 distance"]
}
```

字段上限建议：

- `free` 最多列 **3** 组 body；
- `hint` 最多 **5** 条字符串；
- `conflict` 最多 **3** 对；
- 不输出 `jacobian`、`singular_values` 全量（调试模式 `--verbose` 才写日志文件）。

### 8.3 Agent 修复循环（写入 skill 时）

1. 只改 `constraints` 或参数变量，不改零件 mesh（除非用户要求）。
2. 最多 **3** 轮。
3. `status == ok` 后再 `scripts/step` + `inspect mate` 抽检。

---

## 9. 与 build123d / inspect 的验收（验证期无单测）

### 9.1 验证场景清单

| 场景 | 意图 | 预期 |
|------|------|------|
| `box_on_box` | FIX + contact + offset | 收敛，`mate` δ &lt; 0.01 mm |
| `two_boxes_under` | 仅双 contact | `underconstrained`，`dof_deficit &gt; 0` |
| `two_boxes_fixed` | 加 in_plane offset | `ok` |
| `cylinder_on_box` | plane + coaxial | `ok` |
| `sphere_on_box` | center + plane | `ok` |
| 改 `block1_x` 重跑 | 参数化 | 仅 b1 平移，贴合仍成立 |

### 9.2 验收命令（手工）

```bash
./.venv/bin/python .agents/skills/cad/scripts/step examples/constraint/assembly_box_on_box.py
./.venv/bin/python .agents/skills/cad/scripts/inspect inspect mate \
  --moving '@cad[...]' --target '@cad[...]' --mode flush --axis z
```

可选：将 `report` 写入 `examples/constraint/out/box_on_box.report.json` 供人工 diff。

### 9.3 为何不强制单测

验证期目标是 **证明残差方程与 harness 对接正确**；`inspect` 已是几何真相源。  
单测可在 API 稳定后补（golden transform、rank 断言）。

---

## 10. 实施阶段

### Phase 0 — 基础设施（约 1 周）

- [x] 创建 `scripts/constraint/` 包：`state`、`primitives`、`features`
- [x] 实现 box/cylinder/sphere 特征表与 world 求值（含 box 12 棱 `edge_*`）
- [x] `schema.py` 校验 JSON
- [x] 文档：本文档 + `SKILL.md` 链接

### Phase 1 — 求解 MVP（约 1–2 周）

- [x] `fix`、`plane_coincident`、`point_plane_offset`（含 in_plane x/y）
- [x] `solver.py` + `emit.py`（16 元 transform）
- [x] `report.py` 压缩 JSON
- [x] `examples/constraint/specs/*` + `run_validation.py` 手工验收

### Phase 2 — 扩展约束与原语（约 1 周）

- [x] `point_coincident`、`axis_coaxial`、`axis_parallel`、`plane_distance`
- [x] `cylinder_on_box`、`sphere_on_box`、`box_edge_align` 场景
- [x] `dof.py`：B/C 阶段 rank 与 `free` 摘要

### Phase 3 — harness 融合（约 1 周）

- [x] `constraint.assemble.constraint_assembly` → `Compound` → `scripts/step`
- [x] `SKILL.md`、`references/constraint-assembly.md`、`positioning.md`、`step-generation.md`
- [x] `scripts/constraint` CLI：`solve`、`validate`
- [x] 端到端示例 `examples/constraint/assembly_box_on_box.py`
- [x] `constraint/tests/test_assemble.py`

### Phase 4 — 可选增强

- [ ] 解析 Jacobian
- [ ] `initial_guess` 从脚本
- [ ] 非原语零件：从 `inspect --planes` 提取特征（后期）

---

## 11. LLM 使用约定（避免「比 Joint 更不熟」）

1. **约束与 build123d 分离**：`CONSTRAINTS = {...}` 纯数据，或旁挂 `.constraints.json`。
2. **参数只在 Python**：`block1_x = 30`，JSON 用 `"$block1_x"` 或 `gen_step` 内联展开。
3. **封闭 `feature_id`**：报错 `unknown feature` 时只从表内选。
4. **首轮允许 `initial_guess`**：脚本写近似，约束写关系，降低一次写全的难度。
5. **失败只看 `report` 的 `hint`**，不回退到在 `instances` 里写魔法数字 transform。

---

## 12. 风险与对策

| 风险 | 对策 |
|------|------|
| 残差写错 | 原语闭集 + `inspect mate` 对拍；`--verbose` 日志 |
| 欧拉角奇异 | **不用欧拉角**，用四元数 |
| 多体不收敛 | 更好初值；后期树形分解装配 |
| LLM 约束不全 | Phase A/C 欠约束报告 + hint |
| 与位置堆砌重复 | 装配层禁止裸 transform；参数层仍用 Python |

---

## 13. 成功标准（验证期结束）

- [x] 6 个 `examples/constraint/specs/*` 场景全部 `status: ok` 或预期 `underconstrained`
- [ ] `inspect mate` 与求解位姿一致（δ &lt; 0.01 mm）
- [ ] LLM 报告 JSON 单场景 &lt; 2KB，无矩阵 dump
- [ ] 现有 `STEP/*.py` **无需修改**仍可生成；新装配 opt-in

---

## 14. 参考

- 讨论记录：`ask.md`（约束图、gauge、三图架构）
- 装配 transform：`assembly_spec.py`
- 定位与 Joint：`references/positioning.md`
- 校验：`references/inspection-and-validation.md`
