# 模型拆分装配规范（Model Decomposition & Assembly Spec）

---

## 总览

将产品拆分为若干**几何原语零件**（`box` / `cylinder`），通过 **mates** 声明装配关系，由 transpiler 生成 build123d Python 脚本（`connect_to`）并输出 STEP。

**所有 joint 均可在 mates 中直接引用，无需预先声明。**  
Surface joint 查本规范表格即可使用；surface joint 无法精确表达时改用 custom joint。

---

## 全局约定

| 项目 | 约定 |
|------|------|
| 长度单位 | `mm` |
| 角度单位 | `deg` |
| 坐标系 | 右手系，+Z 朝上，XY 为水平面 |
| `frame` 格式 | `"A:B:C"` 字符串 — 依次为 joint 局部 x/y/z 轴方向，如 `"+X:+Y:+Z"`。三轴 ∈ `{±X, ±Y, ±Z}`，构成右手系 |
| 分数值 | 写为 `"1/2"`、`"-3/4"` 等字符串或整数；禁用小数 `0.5`（可推算新分数如 `"3/8"`） |
| Joint id 格式 | `"{种类}:{法线}:{坐标}"` — 种类 = `rg`（RigidJoint）/ `rv`（RevoluteJoint）；法线 = `s`（外法线）/ `si`（内法线）/ `c`（custom）。坐标：box 用归一化 `x:y:z`（各除以对应半维），cylinder 用 `r:t:h` |
| Joint 引用形式 | 统一对象：`{ "id": "rg:s:0:0:1", "frame": "+X:+Y:+Z" }`。**所有 joint 均须写出 `frame`** |
| 装配 JSON 文件名 | `assembly.json` 或 `{模型名}_assembly.json` |
| 一键生成 STEP/GLB | `python scripts/assembly_from_spec.py <路径/_assembly.json>` |

---

## 输出格式

```json
{
  "meta":  { "schemaVersion": 1, "units": "mm", "angleUnit": "deg", "title": "可选" },
  "parts": [ { "id": "part_id", "primitive": { "kind": "box", "size": [dx, dy, dz] } } ],
  "mates": [
    {
      "partA": "...", "jointA": { "id": "rg:s:0:0:1",   "frame": "+X:+Y:+Z" },
      "partB": "...", "jointB": { "id": "rg:si:0:0:-1",  "frame": "+X:+Y:+Z" },
      "kind": "connect_to"
    }
  ]
}
```

- **`parts`**：只含 `id` + `primitive`，不声明 joints。
- **`mates`**：partA 不动，**partB 被移动**；每个 partB 只能出现在**一条** mate 中（装配为有根树）。未被任何 mate 移动的零件为根节点，位于原点。

> ⚠️ **多父节点错误**：同一零件出现在两条 mate 的 `partB` → transpiler 立即报错。  
> 需要被多处支撑的零件（如横跨两侧板的顶板），只选一个作父节点，或引入中间零件（如中隔板）作为唯一父节点：
>
> ```
> ❌  { "partA": "left_panel",  "partB": "top_panel", ... }
>     { "partA": "right_panel", "partB": "top_panel", ... }  ← 报错
>
> ✅  { "partA": "mid_panel", "partB": "top_panel", ... }    ← 居中的 mid_panel 作唯一父节点
> ```

### 快速示例

```json
{
  "meta": { "schemaVersion": 1, "units": "mm", "title": "柱立于板角" },
  "parts": [
    { "id": "base",   "primitive": { "kind": "box",      "size": [200, 120, 10] } },
    { "id": "pillar", "primitive": { "kind": "cylinder", "radius": 8, "height": 50 } }
  ],
  "mates": [{
    "partA": "base",   "jointA": { "id": "rg:s:1/2:1/2:1", "frame": "+X:+Y:+Z" },
    "partB": "pillar", "jointB": { "id": "rg:si:0:0:-1",   "frame": "+X:+Y:+Z" },
    "kind": "connect_to"
  }]
}
```

> `rg:s:1/2:1/2:1` = base 顶面偏右前角（归一化 `1/2:1/2` → 50, 30 mm）；  
> `rg:si:0:0:-1` = pillar 底面内法线；两 frame 同为 `+X:+Y:+Z` → 纯平移，柱正立，中心 z = 30 mm。 ✅

---

## 几何原语

> **尺寸约定：按零件最终摆放姿态给定参数。**  
> `size[dx, dy, dz]` / `height` 对应零件装配完成后实际占据的 x/y/z 方向尺寸，与世界坐标系对齐。  
> 例如竖立侧板应写 `"size": [18, 460, 1724]`（z=1724 为高度），而非躺平后再用 mate 旋转竖起。  
> 与最终姿态对齐可大幅减少 mate 中的旋转。

### box

```json
{ "kind": "box", "size": [dx, dy, dz] }
```

原点在几何中心，体占 x∈[−dx/2, dx/2]，y∈[−dy/2, dy/2]，z∈[−dz/2, dz/2]。  
归一化：`x_n = x/(dx/2)`，体占 `[−1, 1]³`。Surface joint id 中的 `x:y:z` 均为归一化值。

### cylinder

```json
{ "kind": "cylinder", "radius": r, "height": h }
```

轴线恒为 +Z，原点在几何中心，z∈[−h/2, h/2]，x²+y²≤r²。

---

## Joint 参考

### connect_to 工作原理

`partA.joints[JA].connect_to(partB.joints[JB])` 的效果：**JB 的世界 frame 与 JA 的世界 frame 完全重合**（同位置、同 xyz 轴方向）。

因此：`z_A = z_B` → 纯平移（无旋转）；z 方向不同 → partB 旋转（旋转量 = z 夹角）。

---

### 外法线 `s` 与内法线 `si` 的配对规律

**同轴对面**的外法线（`s`）与内法线（`si`）frame 完全相同。  
利用此规律：**partA 用 `s`，partB 用对面 `si`** → 两 frame 一致 → **纯平移，无旋转**。

| partA 外法线（`s`） | partB 内法线（`si`） | frame | 说明 |
|---------------------|---------------------|-------|------|
| `rg:s:0:0:1`（顶外） | `rg:si:0:0:-1`（底内） | `+X:+Y:+Z` | **最常用，上下堆叠** |
| `rg:s:0:0:-1`（底外） | `rg:si:0:0:1`（顶内） | `+X:-Y:-Z` | |
| `rg:s:1:0:0`（右外） | `rg:si:-1:0:0`（左内） | `+Y:+Z:+X` | 横向拼接 |
| `rg:s:-1:0:0`（左外） | `rg:si:1:0:0`（右内） | `+Y:-Z:-X` | |
| `rg:s:0:1:0`（前外） | `rg:si:0:-1:0`（后内） | `+Z:+X:+Y` | |
| `rg:s:0:-1:0`（后外） | `rg:si:0:1:0`（前内） | `+Z:-X:-Y` | |

---

### Box Surface Joints

**face 由绝对值最大的坐标轴确定（优先级 x > y > z）；其余分量为面内偏移，`0` = 面心。**  
面内其他点（如 `rg:s:1/2:0:1`）frame 与面心完全相同，仅位置不同。  
当需在棱边/角点定位（如同时 |x|=|z|=1）时，**改用 custom joint 并明确 frame**，避免面轴歧义。

| 面 | 外法线 `s` id（面心） | frame（外） | 内法线 `si` id（面心） | frame（内） |
|----|----------------------|------------|----------------------|------------|
| +Z 顶 | `rg:s:0:0:1`  | `+X:+Y:+Z` | `rg:si:0:0:1`  | `+X:-Y:-Z` |
| −Z 底 | `rg:s:0:0:-1` | `+X:-Y:-Z` | `rg:si:0:0:-1` | `+X:+Y:+Z` |
| +X 右 | `rg:s:1:0:0`  | `+Y:+Z:+X` | `rg:si:1:0:0`  | `+Y:-Z:-X` |
| −X 左 | `rg:s:-1:0:0` | `+Y:-Z:-X` | `rg:si:-1:0:0` | `+Y:+Z:+X` |
| +Y 前 | `rg:s:0:1:0`  | `+Z:+X:+Y` | `rg:si:0:1:0`  | `+Z:-X:-Y` |
| −Y 后 | `rg:s:0:-1:0` | `+Z:-X:-Y` | `rg:si:0:-1:0` | `+Z:+X:+Y` |

---

### Cylinder Surface Joints

坐标 `r:t:h`：r = 归一化径向（0=轴线，1=圆周）；h = 归一化轴向（±1=端面，0=赤道）；t = 归一化周向角。

#### t 方向速查

| t | 指向 | t | 指向 |
|---|------|---|------|
| `0` | +X | `1`（≡`-1`） | −X |
| `1/2` | +Y | `-1/2` | −Y |
| `1/4` | 45°（+X→+Y） | `-1/4` | −45°（+X→−Y） |

#### 端面（h=±1）

| 面 | 外法线 `s` id（面心） | frame（外） | 内法线 `si` id（面心） | frame（内） |
|----|----------------------|------------|----------------------|------------|
| 顶（h=+1） | `rg:s:0:0:1`  | `+X:+Y:+Z` | `rg:si:0:0:1`  | `+X:-Y:-Z` |
| 底（h=−1） | `rg:s:0:0:-1` | `+X:-Y:-Z` | `rg:si:0:0:-1` | `+X:+Y:+Z` |

> 端面上任意 r/t 偏移点（h=±1，r/t 任意）frame 与面心相同。  
> 配对：`rg:s:0:0:1`（顶外）↔ `rg:si:0:0:-1`（底内）frame 均为 `+X:+Y:+Z`。

#### 侧面（r=1，赤道 h=0）

| 方向 | 外法线 `s` id | frame（外） | 内法线 `si` id | frame（内） |
|------|--------------|------------|---------------|------------|
| +X（t=0）   | `rg:s:1:0:0`    | `+Y:+Z:+X`  | `rg:si:1:0:0`    | `-Y:+Z:-X`  |
| +Y（t=1/2） | `rg:s:1:1/2:0`  | `-X:+Z:+Y`  | `rg:si:1:1/2:0`  | `+X:+Z:-Y`  |
| −X（t=1）   | `rg:s:1:1:0`    | `-Y:+Z:-X`  | `rg:si:1:1:0`    | `+Y:+Z:+X`  |
| −Y（t=−1/2）| `rg:s:1:-1/2:0` | `+X:+Z:-Y`  | `rg:si:1:-1/2:0` | `-X:+Z:+Y`  |

> 侧面任意 h 偏移点（如 h=1/2）frame 不变，仅位置沿轴移动。  
> 侧面所有 `si` 的 y 轴恒为 +Z（轴向），z 轴指向圆心。

---

### Custom Joint

```json
{ "id": "rg:c:x:y:z", "frame": "+X:+Y:+Z" }
```

坐标与 surface joint **相同归一化体系**，可定位于零件面上或内部任意点。**frame 完全由使用者指定**。

三种典型用途：
1. **任意计算坐标**：坐标值由实际尺寸推算，不限于 ±1/2、±1/4 等预设分数，如 `596/605`、`7/12`
2. **零件内部非面点**：坐标不在任何面上（如 `0:0:1/2`，轴线中段）
3. **自定义 frame 方向**：在某位置指定任意 z 轴方向，不受 surface joint 面法线约束

---

### 通用规则

| 种类 | id 前缀 | frame | 说明 |
|------|---------|-------|------|
| surface RigidJoint 外法线 | `rg:s:` | 由坐标确定（查表），**必须写出** | face 内 x/y 偏移不改变 frame |
| surface RigidJoint 内法线 | `rg:si:` | 由坐标确定（查表），**必须写出** | 与对面 `s` frame 相同 |
| surface RevoluteJoint | `rv:s:` / `rv:si:` | 同上，必须写出；旋转轴 = z 轴 | |
| custom joint | `rg:c:` / `rv:c:` | **必须显式指定** | 坐标归一化，可超出 ±1 |

---

## mates 格式

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `partA` | string | 不动件（参考） |
| `partB` | string | 被移动件；每个零件只能作一次 partB |
| `jointA` | `{ "id": "...", "frame": "..." }` | partA 上的 joint |
| `jointB` | `{ "id": "...", "frame": "..." }` | partB 上的 joint；connect_to 使 JB frame = JA frame |
| `kind` | `"connect_to"` | 目前唯一值 |
| `angle` | number（deg） | 仅含 RevoluteJoint 时有效；0 = 两 joint x 轴对齐；正值 = 绕 Revolute z 轴逆时针 |

**Joint 对象字段：**

| 字段 | surface joint | custom joint | 说明 |
|------|:---:|:---:|------|
| `id` | 必填 | 必填 | 见上表；custom 坐标归一化，可超出 ±1 |
| `frame` | **必填（校验）** | **必填（定义）** | surface frame 由坐标确定，填写以校验；custom frame 由填写者完全控制 |

---

### connect_to 类型配对

| jointA | jointB | 允许 | 行为 |
|--------|--------|------|------|
| Rigid  | Rigid  | ✅ | 完全刚体，无 DOF |
| Rigid  | Revolute | ✅ | partB 绕 Revolute z 轴，`angle` 控制初始角 |
| Revolute | Rigid | ✅ | 同上，Revolute 在 partA 侧 |
| Revolute | Revolute | ❌ | 禁止，自由度未封闭 |

---

### 装配意图速查

frame 相同 → 纯平移（无旋转）；frame 不同 → partB 旋转（z 夹角即旋转量）。

| 装配意图 | z_A | z_B | 行为 | jointA 示例 | jointB 示例 |
|---------|-----|-----|------|-------------|-------------|
| **正立堆叠**（推荐） | +Z | +Z | 纯平移，B 正立 | `rg:s:0:0:1` `"+X:+Y:+Z"` | `rg:si:0:0:-1` `"+X:+Y:+Z"` |
| **横向拼接**（推荐） | +X | +X | 纯平移，B 侧贴 | `rg:s:1:0:0` `"+Y:+Z:+X"` | `rg:si:-1:0:0` `"+Y:+Z:+X"` |
| **铰链**（RevoluteJoint） | any | same | 按 `angle` 转动 | `rg:s:0:1:0` `"+Z:+X:+Y"` | `rv:s:0:1:0` `"+Z:+X:+Y"` |
| 翻转 180° | +Z | −Z | B 上下翻转 | `rg:s:0:0:1` `"+X:+Y:+Z"` | `rg:s:0:0:-1` `"+X:-Y:-Z"` |
| 旋转 90°（如水平杆） | +X | +Z | B 旋转 90° | `rg:s:1:0:h` `"+Y:+Z:+X"` | `rg:si:0:0:-1` `"+X:+Y:+Z"` |
| 精确定位（custom） | f | f（same） | 纯平移 | `rg:c:x:y:z` frame `f` | `rg:si:...` frame `f` |

---

## 具体 Cases

### Case 1：正立堆叠

```json
{ "partA": "base",   "jointA": { "id": "rg:s:1/2:1/2:1", "frame": "+X:+Y:+Z" },
  "partB": "pillar", "jointB": { "id": "rg:si:0:0:-1",   "frame": "+X:+Y:+Z" }, "kind": "connect_to" }
```
`rg:s:1/2:1/2:1` = base 顶面偏右前角（in-face x=1/2, y=1/2）；frames 同 → 纯平移，pillar 正立。

---

### Case 2：横向面板拼接

```json
{ "partA": "left_panel",  "jointA": { "id": "rg:s:1:0:0",   "frame": "+Y:+Z:+X" },
  "partB": "right_panel", "jointB": { "id": "rg:si:-1:0:0", "frame": "+Y:+Z:+X" }, "kind": "connect_to" }
```
frames 同 → 纯平移，right_panel 紧贴 left_panel 右侧。

---

### Case 3：边沿对齐捷径（棱/角点 joint）

**核心**：将两个零件**对应棱/角点**分别作为 joint 锚点，connect_to 后该棱/角点精确重合 → 边沿自动对齐，无需计算任何偏移。

**选哪个棱对哪个棱**：对应位置保持相同的面内坐标（x, y），z 方向一个 +1（上棱）一个 -1（下棱）即可叠放。

```
bottom_panel 顶-左棱 (-1, 0, +1)  ↔  left_panel 底-左棱 (-1, 0, -1)
                   ↑ 同 x=-1（左缘对齐） ↑
                   ↑ z: 一个朝上，一个朝下（叠放）↑
```

```json
{ "partA": "bottom_panel", "jointA": { "id": "rg:c:-1:0:1",  "frame": "+X:+Y:+Z" },
  "partB": "left_panel",   "jointB": { "id": "rg:c:-1:0:-1", "frame": "+X:+Y:+Z" }, "kind": "connect_to" }
```
结果：left_panel 底面贴合 bottom_panel 顶面（面接触），左缘完全齐平。改 `x=-1` 为 `x=1` 即变为右缘齐平。

**角点同理**（三面齐平）：

```json
{ "partA": "base_plate", "jointA": { "id": "rg:c:1:1:1",  "frame": "+X:+Y:+Z" },
  "partB": "foot",       "jointB": { "id": "rg:c:1:1:-1", "frame": "+X:+Y:+Z" }, "kind": "connect_to" }
```
右-前-顶角 ↔ 右-前-底角 → foot 正立，右面、前面、外缘三面齐平。

> 注：棱/角点坐标含多个 ±1，surface joint 会选错面，故用 custom joint 并显式给定 frame。

---

### Case 4：旋转 90° 挂载（水平杆）

```json
{ "partA": "left_panel", "jointA": { "id": "rg:s:1:0:7/8", "frame": "+Y:+Z:+X" },
  "partB": "rod_l",      "jointB": { "id": "rg:si:0:0:-1", "frame": "+X:+Y:+Z" }, "kind": "connect_to" }
```
z_A=+X，z_B=+Z → rod_l 旋转 90°，杆轴由竖直转为水平 +X。`7/8` 将挂点置于 left_panel 近顶处。

---

### Case 5：RevoluteJoint 铰链（门）

```json
{ "partA": "cabinet",
  "jointA": { "id": "rg:s:1/4:1:0", "frame": "+Z:+X:+Y" },
  "partB": "door",
  "jointB": { "id": "rv:si:0:-1:0", "frame": "+Z:+X:+Y" },
  "kind": "connect_to", "angle": 0 }
```
frames 同（z=+Z，前面法线方向）→ 纯平移定位，RevoluteJoint 绕 z=+Z（竖轴）转动。`angle:0` 门关，`angle:90` 门开 90°。

---

### Case 6：Custom Joint — 三种场景

| 场景 | id 示例 | frame | 用途 |
|------|---------|-------|------|
| **任意计算坐标** | `rg:c:596/605:0:-1` | `+X:+Y:+Z` | 由实际尺寸推算：底板半宽 605mm，边缘内移 9mm → 596/605 |
| **零件内部** | `rg:c:1/2:0:-5/8` | `+X:+Y:+Z` | 非面上锚点，cabinet 内部指定位置 |
| **自定义 frame** | `rg:c:1/2:0:0` | `+Z:+X:+Y` | 在某位置指定任意旋转轴方向，不受面法线约束 |

**任意坐标 + 内部定位示例**（cabinet 内部，左缘内移精确对齐，放 shelf）：

cabinet（box 1210×460×1760）半维 (605, 230, 880)；底板半宽 605，侧板半厚 9：

```json
{ "partA": "cabinet",
  "jointA": { "id": "rg:c:596/605:0:-5/8", "frame": "+X:+Y:+Z" },
  "partB": "shelf",
  "jointB": { "id": "rg:si:0:0:-1",        "frame": "+X:+Y:+Z" }, "kind": "connect_to" }
```
`596/605` = 精确右区 x 位置（边缘内移 9mm）；`-5/8 × 880 = -550mm` → 距底 330mm。frames 同 → 纯平移。

---

## 实用决策指南

1. **上下堆叠（正立）**：A 顶面 `rg:s:0:0:1`，B 底面内法线 `rg:si:0:0:-1` → 同 frame，纯平移。
2. **横向拼接**：A 对应面 `rg:s:±1:0:0`，B 对面内法线 `rg:si:∓1:0:0` → 同 frame，纯平移。
3. **面内偏心定位**：调整面心坐标为 `1/2`、`1/4` 等，frame 不变。
4. **需要 surface joint 面法线以外的方向，或坐标为任意计算值**：用 custom joint，frame 完全自定义；见 Case 3、6。
5. **边沿对齐捷径**：在两个零件的对应棱/角点处各放 custom joint（frame 相同），连接后该棱/角自动重合，左/右/前/后缘齐平无需计算偏移；见 Case 3。
6. **旋转 90° 挂载**：故意让 z_A ≠ z_B（如 +X vs +Z）；常用于将竖直圆柱转为水平杆。
7. **铰链**：partB joint 改 `rv` 前缀；`angle` 控制初始角；旋转轴 = joint z 轴；见 Case 5。
8. **内部任意位置**：用 custom joint `rg:c:x:y:z` + 精确 `frame`；见 Case 6。
