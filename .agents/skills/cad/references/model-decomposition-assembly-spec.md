# 模型拆分装配规范（Model Decomposition & Assembly Spec）

---

## 总览

将产品拆分为若干**几何原语零件**（`box` / `cylinder`），通过 **mates** 声明零件间装配关系。  
输出为一个 JSON，包含 `meta`、`parts`、`mates`。  
由 transpiler 映射为 build123d Python 脚本，调用 `connect_to` 生成 STEP。

**所有 joint 均可在 mates 中直接引用，无需在任何地方预先声明。**  
surface joint 由本规范预定义（可查表），自定义 joint 以对象形式内联写在 mates 中。

---

## 全局约定

| 项目 | 约定 |
|------|------|
| 长度单位 | `mm` |
| 角度单位 | `deg` |
| 坐标系 | 右手系，+Z 朝上，XY 为水平面 |
| `frame` 格式 | `"A:B:C"` 字符串，三个 token 依次为 Joint 局部 **x / y / z 轴**在零件局部坐标中的方向，如 `"+X:+Y:+Z"`。所有 token ∈ `{±X, ±Y, ±Z}`，且三轴构成右手系。 |
| 分数值 | 写为 `"1/2"`、`"-1/3"` 等字符串，或整数 `1`、`-1`；禁用小数 `0.5`（LLM 可推算新分数，如 `"3/8"`） |
| Joint id 格式 | `"{种类}:{法线}:{坐标}"` — 种类 = `rg`（RigidJoint）或 `rv`（RevoluteJoint），法线 = `s`（surface 外法线）/ `si`（surface 内法线）/ `c`（custom）。**坐标统一为归一化分数**：box 用 `x:y:z`（相对 dx/2、dy/2、dz/2），cylinder 用 `r:t:h`（同 surface joint 坐标系）。Custom joint 可定位于零件内外任意位置，且必须提供 `frame`。 |
| Joint 引用形式 | **统一对象形式**：`{ "id": "rg:s:0:0:1" }`；custom joint 另加 `frame` 字段 |
| 装配 JSON 文件名 | 推荐 `assembly.json`（单模型）或 `{模型名}_assembly.json`（如 `wardrobe1_assembly.json`） |
| 一键生成 STEP/GLB | CAD 技能目录下运行 `python scripts/assembly_from_spec.py <路径/_assembly.json>`：先 transpile 为同目录 `*_gen.py`，再调用 `python -m step` 写出 `*_gen.step` 与 `.*_gen.step.glb` |

---

## 输出格式

```json
{
  "meta":  { "schemaVersion": 1, "units": "mm", "angleUnit": "deg", "title": "可选" },
  "parts": [ { "id": "...", "primitive": { ... } } ],
  "mates": [ ... ]
}
```

- **`parts`**：只含 `id` + `primitive`，**不声明 joints**。
- **`mates`**：每条 mate 声明一对 joint 的连接关系；**每个 partB 只能在一条 mate 中出现（装配图为有根树）**。

> ⚠️ **"多父节点"是最常见错误**：同一零件若同时出现在两条 mate 的 `partB` 字段，transpiler 立即报错。  
> 典型场景：顶板想"同时卡在"左侧板和右侧板上方 → **只能选其中一个作为父节点**，或引入公共中间零件（如中隔板）作为顶板的唯一父节点。
>
> ```
> ❌ 错误：top_panel 有两个父节点
>   { "partA": "left_panel",  "partB": "top_panel", ... }
>   { "partA": "right_panel", "partB": "top_panel", ... }  ← 报错
>
> ✅ 修复：以 mid_panel（中隔板）为唯一父节点
>   { "partA": "mid_panel", "partB": "top_panel", ... }    ← mid_panel 居中，顶板也居中
> ```

---

## 完整示例

```json
{
  "meta": { "schemaVersion": 1, "units": "mm", "angleUnit": "deg", "title": "柱立于板角" },
  "parts": [
    { "id": "base",   "primitive": { "kind": "box",      "size": [200, 120, 10] } },
    { "id": "pillar", "primitive": { "kind": "cylinder", "radius": 8, "height": 50 } }
  ],
  "mates": [
    {
      "partA": "base",   "jointA": { "id": "rg:s:1/2:1/2:1"  },
      "partB": "pillar", "jointB": { "id": "rg:si:0:0:-1" },
      "kind": "connect_to"
    }
  ]
}
```

> `jointA` = base 顶面偏角处（归一化 `1/2:1/2` → `(50, 30, 5)`）；  
> `jointB` = pillar 底面**内法线** joint（`si`，z=+Z），与 `jointA`（z=+Z）frame同向  
> → `connect_to` 纯平移，pillar 正立于 base 上方，中心 z=60。✅

---

## 几何原语

### box

```json
{ "kind": "box", "size": [dx, dy, dz] }
```

- `size[dx, dy, dz]`：均 > 0，对应局部 +X / +Y / +Z 方向边长，mm。
- 原点在几何中心：`x∈[−dx/2, +dx/2]`，`y∈[−dy/2, +dy/2]`，`z∈[−dz/2, +dz/2]`。
- **归一化坐标**：`u = x/(dx/2)`，`v = y/(dy/2)`，`w = z/(dz/2)`，体占 `[−1,1]³`。Surface joint id 中的 `x:y:z` 均为归一化值。

### cylinder

```json
{ "kind": "cylinder", "radius": r, "height": h }
```

- `radius`、`height`：均 > 0，mm。
- **轴线恒为局部 +Z**，**原点恒在几何中心**（无 `axis`、`originMode` 字段）。
- 占有区域：`z∈[−h/2, +h/2]`，`x²+y²≤r²`。

---

## Joint 接口参考

### connect_to frame 重合机制（必读）

#### build123d connect_to 的数学定义

`partA.joints[JA].connect_to(partB.joints[JB])` 的效果：

```
world_loc_partB_new = world_loc_partA × loc_JA_in_partA × loc_JB_in_partB⁻¹
```

结果是 **JB 的世界 frame 与 JA 的世界 frame 完全重合（同位置、同 xyz 方向）**。  
这意味着 connect_to **不是「面对面相触」，而是「frame完全对齐」**。

---

#### 本规范的 frame 约定：`s` 外法线 + `si` 内法线

本规范 surface joint 提供**两种法线方向**：

| 类型 | 记法 | z 轴方向 | 典型用途 |
|------|------|---------|---------|
| 外法线（outward） | `rg:s:x:y:z` | 指向**体外**（+Z 面 z=+Z，−Z 面 z=−Z…） | 描述「这一面朝哪里」 |
| 内法线（inward） | `rg:si:x:y:z` | 指向**体内**（+Z 面 z=−Z，−Z 面 z=+Z…） | 作为连接目标，实现无旋转装配 |

**核心配对规律**：同一轴对面的外法线 joint（`s`）与内法线 joint（`si`）frame完全相同：

```
rg:s:0:0:1   (顶面 s,  z=+Z)  ←→  rg:si:0:0:-1  (底面 si, z=+Z)  → 同frame
rg:s:0:0:-1  (底面 s,  z=−Z)  ←→  rg:si:0:0:1   (顶面 si, z=−Z)  → 同frame
rg:s:1:0:0   (右面 s,  z=+X)  ←→  rg:si:-1:0:0  (左面 si, z=+X)  → 同frame
```

因此：**`s(A)` → `si(B_对面)` = 无旋转装配**。

---

### 通用规则

- **`rg:s:...` / `rg:si:...`（surface RigidJoint）**：frame 由本规范完全确定，直接以 `{ "id": "rg:s:..." }` 或 `{ "id": "rg:si:..." }` 引用，不写 `frame`，不可修改。
- **`rv:s:...` / `rv:si:...`（surface RevoluteJoint）**：坐标格式相同，旋转轴 = 该 joint 的 z 轴。frame 同样预定义，不可修改。
- **`rg:c:...` / `rv:c:...`（自定义 joint）**：必须提供 `frame`，坐标与 surface joint **相同归一化体系**（box 用 `x:y:z`，cylinder 用 `r:t:h`）。Custom joint 可在零件内外任意位置。**当 surface joint 仍无法满足时，用 custom joint 精确指定 frame。**

---

### Box Surface Joints：`"rg:s:x:y:z"` / `"rg:si:x:y:z"`

**id 含义**：归一化坐标 `(x, y, z)`；`|x|=1` 或 `|y|=1` 或 `|z|=1`（确定所在面），另两个分量指定面内位置（`0:0` = 面心）。

每个分量 ∈ `{ 0, ±1, ±1/2, ±1/3, ±1/4, ±1/8, ... }`，优先使用 `0、±1、±1/2、±1/4、±1/8`。

#### 六面面心 id 与预置 frame

| 面 | 外法线 `s` id | frame（外） | 内法线 `si` id | frame（内） |
|----|--------------|------------|---------------|------------|
| +Z 顶 | `rg:s:0:0:1`  | `+X:+Y:+Z`  | `rg:si:0:0:1`  | `+X:-Y:-Z`  |
| −Z 底 | `rg:s:0:0:-1` | `+X:-Y:-Z`  | `rg:si:0:0:-1` | `+X:+Y:+Z`  |
| +X 右 | `rg:s:1:0:0`  | `+Y:+Z:+X`  | `rg:si:1:0:0`  | `+Y:-Z:-X`  |
| −X 左 | `rg:s:-1:0:0` | `+Y:-Z:-X`  | `rg:si:-1:0:0` | `+Y:+Z:+X`  |
| +Y 前 | `rg:s:0:1:0`  | `+Z:+X:+Y`  | `rg:si:0:1:0`  | `+Z:-X:-Y`  |
| −Y 后 | `rg:s:0:-1:0` | `+Z:-X:-Y`  | `rg:si:0:-1:0` | `+Z:+X:+Y`  |

> **配对速查**：`rg:s:0:0:1`（顶，外）与 `rg:si:0:0:-1`（底，内）frame 完全一致（均为 `+X:+Y:+Z`）。  
> 面内其他点（如 `rg:si:1/2:0:-1`）frame 与该面面心相同，仅位置不同。

---

### Cylinder Surface Joints：`"rg:s:r:t:h"` / `"rg:si:r:t:h"`

| 分量 | 含义 | 取值 |
|------|------|------|
| `r` | 归一化径向（半径=1） | `{ 0, 1, 1/2, 1/3, 1/4, ... }`（非负） |
| `t` | 归一化周向角（半圈π=1，从+X逆时针） | `{ 0, ±1/2, ±1, ±1/4, ±1/3, ... }` |
| `h` | 归一化轴向（半高=1） | `{ ±1, ±1/2, ±1/3, ... }` |

#### t 方向速查

| t | 方向 | t | 方向 |
|---|------|----|------|
| `0` | +X | `1`（=`-1`） | −X |
| `1/2` | +Y | `-1/2` | −Y |
| `1/4` | +X→+Y（45°） | `-1/4` | +X→−Y（−45°） |

#### 端面（h=±1）

| id（面心） | frame（外，`s`） | frame（内，`si`） |
|------------|-----------------|------------------|
| `rg:s:0:0:1`  / `rg:si:0:0:1`  | `+X:+Y:+Z` | `+X:-Y:-Z` |
| `rg:s:0:0:-1` / `rg:si:0:0:-1` | `+X:-Y:-Z` | `+X:+Y:+Z` |

> `rg:s:0:0:1`（顶外）与 `rg:si:0:0:-1`（底内）frame 完全相同（`+X:+Y:+Z`）。  
> 端面上其他点（h=±1，r/t 任意）frame 与面心相同。

#### 侧面（r=1）

| id（赤道） | frame（外，`s`） | frame（内，`si`） |
|------------|-----------------|------------------|
| `rg:s:1:0:0`    / `rg:si:1:0:0`    | `+Y:+Z:+X`  | `-Y:+Z:-X`  |
| `rg:s:1:1/2:0`  / `rg:si:1:1/2:0`  | `-X:+Z:+Y`  | `+X:+Z:-Y`  |
| `rg:s:1:1:0`    / `rg:si:1:1:0`    | `-Y:+Z:-X`  | `+Y:+Z:+X`  |
| `rg:s:1:-1/2:0` / `rg:si:1:-1/2:0` | `+X:+Z:-Y`  | `-X:+Z:+Y`  |

> 侧面 `si` z 方向 = 径向向内（指向轴线）；y 恒为轴向 +Z；x 右手系。  
> 配对：`rg:s:1:0:0`（+X 侧外）与 `rg:si:1:1:0`（−X 侧内）frame 完全相同（`+Y:+Z:+X`）。

---

## mates 格式

所有 joint 引用统一为**对象形式**：

**① surface 外法线 joint（`s`）→ surface 内法线 joint（`si`），无旋转（推荐）**
```json
{ "partA": "base",   "jointA": { "id": "rg:s:0:0:1"   },
  "partB": "pillar", "jointB": { "id": "rg:si:0:0:-1" }, "kind": "connect_to" }
```

**② 两个 `s` joint 对接，结果有 180° 翻转（仅对称零件可接受）**
```json
{ "partA": "base",   "jointA": { "id": "rg:s:0:0:1"  },
  "partB": "pillar", "jointB": { "id": "rg:s:0:0:-1" }, "kind": "connect_to" }
```

**③ surface RevoluteJoint（铰链）**
```json
{ "partA": "frame",  "jointA": { "id": "rg:s:0:1:0"  },
  "partB": "door",   "jointB": { "id": "rv:s:0:1:0"  }, "kind": "connect_to", "angle": 30 }
```

**④ 自定义 joint（仅在 surface joint 仍无法满足时使用）**
```json
{
  "kind": "connect_to",
  "partA": "cabinet",
  "jointA": { "id": "rg:c:1/2:0:-5/8", "frame": "+X:+Y:+Z" },
  "partB": "shelf",
  "jointB": { "id": "rg:si:0:0:-1" }
}
```

> `rg:c:1/2:0:-5/8` 表示在 `cabinet`（box）的归一化位置 x=1/2、z=−5/8（坐标与 surface joint 完全相同体系，可表达面上或零件内部任意位置）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `partA` / `partB` | string | 零件 id；partA 不动，partB 被移动 |
| `jointA` / `jointB` | object | `{ "id": "rg:s:..." }` 等 |
| `kind` | `"connect_to"` | 目前唯一值 |
| `angle` | number（deg） | 仅含 RevoluteJoint（`rv:s:` / `rv:si:` / `rv:c:`）时有效。零度参考位：两 joint 的 x 轴对齐。正角度 = 绕 RevoluteJoint z 轴逆时针旋转（从 +z 俯视） |

**Joint 对象字段：**

| 字段 | surface joint（`s`/`si`） | custom joint（`c`） | 说明 |
|------|:---:|:---:|------|
| `id` | 必填 | 必填 | surface: `"rg:s:x:y:z"` 或 `"rg:si:x:y:z"`；custom: `"rg:c:x:y:z"`（**归一化坐标**，与 surface joint 相同体系，可表达零件内外任意位置） |
| `frame` | — | 必填 | Joint 局部 x/y/z 轴方向，如 `"+X:+Z:-Y"` |

### connect_to 允许的类型配对

| jointA | jointB | 允许 | 说明 |
|--------|--------|------|------|
| Rigid  | Rigid  | ✅ | 完全刚体对齐，无 DOF |
| Rigid  | Revolute | ✅ | partB 绕 Revolute z 轴，angle 控制初始角 |
| Revolute | Rigid | ✅ | 同上，Revolute 在 partA 侧 |
| Revolute | Revolute | ❌ | 禁止，自由度未封闭 |

---

## Frame 对齐规律与 Cases

**前提**：connect_to 使 partB.jointB frame 与 partA.jointA frame 完全重合（同位置、同 xyz 方向）。

---

### 场景速查

| Case | z_A | z_B | connect_to 实际行为 | 结果 |
|------|-----|-----|---------------------|------|
| **`s` → `si`（对面内法线）** | +Z | **+Z**（si） | z 同向 → **无旋转**，纯平移 | ✅ 推荐 |
| `s` → `s`（同轴同向，如 top→top） | +Z | +Z | 无旋转；partB 与 partA **同侧** | ⚠️ 位置通常不符预期 |
| `s` → `s`（同轴对面，如 top→bottom） | +Z | **−Z** | z 反向 → **partB 翻转 180°** | ⚠️ 翻转（仅对称体可接受） |
| `s` → `s`（跨轴，如 top→right） | +Z | +X | z 不平行 → **partB 旋转 90°** | ⚠️ 旋转 |
| custom joint，z 与 A 同向 | +Z | +Z（自定义） | 无旋转，精确定位 | ✅ fallback |
| RevoluteJoint（Rigid→Revolute） | 任意 | 任意 | frame对齐后 angle 绕 Revolute z 转动 | ✅ 铰链/轴 |

---

### 对面连接翻转的数学推导

以「`s` → `s`（顶面→底面）」为例（box 100×60×20，cyl r=8 h=50）：

```
loc_top  = (I,  (0,0, 10))          # box 顶面，z=+Z
loc_bot  = (R,  (0,0,-25))          # cyl 底面 s，z=−Z，R = diag(1,−1,−1)

world_cyl = loc_top × loc_bot⁻¹ = (diag(1,−1,−1), (0,0,35))
→ cyl 中心 z=35，但绕 X 轴翻转 180°（有向零件方向错误）
```

改用 **`si`（底面内法线）**，z=+Z，R=I：

```
loc_bot_si = (I, (0,0,-25))         # cyl 底面 si，z=+Z（frame与顶面同向）

world_cyl = loc_top × loc_bot_si⁻¹ = (I, (0,0,35))
→ cyl 中心 z=35，无旋转 ✅
```

---

### Custom Joint 精确装配指南

**当 surface joint（`s`/`si`）仍无法满足时**，用 custom joint 精确指定 frame：

| 目标 | jointA | jointB（custom） | frame 含义 |
|------|--------|------------------|------------|
| 零件内部偏心定位 | `rg:s:0:0:1`（z=+Z） | `rg:c:0:0:1/2`，`"+X:+Y:+Z"` | 在 z=dz/4 处（面内 1/4 高处）放置，z=+Z 同向 |
| 精确偏心铰链 | `rg:s:...` | `rv:c:x:y:z`，frame 自定义旋转轴 | RevoluteJoint z = 旋转轴方向 |

> **custom joint 坐标**与 surface joint 完全相同的**归一化体系**：box 用 `x_n:y_n:z_n`（各除以对应半维），cylinder 用 `r:t:h`。例如 `rg:c:1/2:0:-5/8` 在 box [1210,460,1760] 中映射到 (302.5 mm, 0, −550 mm)。

---

## 实用选 Joint 指南

1. **上下堆叠（正立，推荐）**：partA 用顶面 `rg:s:0:0:1`，partB 用**底面内法线** `rg:si:0:0:-1` → frame 同向，纯平移，正立。
2. **横向拼接（无旋转，推荐）**：partA 右面 `rg:s:1:0:0`，partB 左面内法线 `rg:si:-1:0:0` → 同 frame，无旋转拼接。
3. **偏心定位**：调整面内坐标，如 `rg:s:1/2:1/2:1` = 顶面 `(dx/4, dy/4, dz/2)` 处；`si` 同理。
4. **面内任意挂载**：用 custom joint 在零件面内/内部精确指定坐标和 frame，如 `rg:c:0:0:1/2`（dz/4 处）。
5. **对称零件快速堆叠**：也可直接用 `rg:s:0:0:1` → `rg:s:0:0:-1`（翻 180°，对称体视觉无差异）。
6. **铰链**：种类改为 `rv`，如 `rv:s:0:1:0`（绕 +Y 轴），mate 中指定 `angle`；`si` 同样支持 `rv:si:...`。
7. **无法用 surface joint 覆盖时**：用 custom joint `rg:c:x:y:z` + 精确 `frame`，z 轴指向目标方向。
