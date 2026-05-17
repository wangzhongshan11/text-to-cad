# 约束装配 — 自然语言对话示例

`gen_step()` 返回 `Compound`（非 `instances`）。规划规则见技能参考：`build123d-modeling.md`（装配分解）、`natural-language-specs.md`（复杂装配简报）、`constraint-assembly.md`（约束 API）。

---

## A — 基础（单链路全约束）

### A1 — 单块叠在底板上

底板 200×150×20，上放 40×30×25 方块；底面贴底板顶面，中心偏移 x=30、y=40。`plane_coincident` + `point_plane_offset`。

### A2 — 三层方块塔

底板 180×140×12，中层 80×60×20，顶层 35×35×30；逐层 `contact` + 相对上层顶面的 `offset`（= 上层高度/2）。

### A3 — 圆柱销

板 220×100×10，竖圆柱 Ø20×40，底面贴合，中心 x=-50，y=0，`axis_parallel` 锁轴线。

### A4 — 双圆柱

同 A3，两销 x=-50 / x=55。

### A5 — 球与双球

平台 + 单球；或底板 + 两球竖直堆叠（第二层 `offset` 用两球半径之和）。

### A6 — 桥式双柱

底板 240×80×14，两柱 50×40×36，x=±70，y 居中。

### A7 — 边缘对齐支架

底板 160×120×16，竖块 24×18×60：`contact` + 边 `edge_*` 对齐 + in_plane 偏移。

### A8 — 欠约束 vs 补全

两小块只 `contact` 贴底板 → 期望 `underconstrained`；再补 in_plane x/y → `ok`。

---

## B — 中等（仍适合单 CONSTRAINTS）

### B1 — 4×4 柱阵

底板 360×280×14，16 根 14×14×32 柱，节距 70，居中阵列。先 `specs/pin_grid_4x4.json`，再 `assemblies/pin_grid_4x4/`。

### B2 — 工字型横梁

底板 300×200×16，横梁 260×40×20 悬空 z=120（仅 `point_plane_offset`，无 contact），两端支撑块 40×40×120 用 contact 落底板。

### B3 — 三层抽屉柜（无抽屉）

外箱五板围合 + 3 块隔板：围板 5 件约束求解；3 层板用 Location 按内空尺寸公式摆放（混合示范）。

### B4 — L 形台面

底板 200×200×18，前块 50×40×30（x=0,y=60），侧块 35×50×25（x=70,y=-20），全约束，status=ok。

---

## C — 复杂（必须拆子链路）

### C1 — 块状擎天柱（混合，高复杂）

风格化玩具尺度：卡车底盘 380×170×52，四轮贴地；上身约 30 个 box（胸甲、驾驶室、头、双臂三段×2、双腿三段×2、排气等）。

- **子链路 1（约束）**：`platform` + 4×`wheel_*`（5 体，~24 约束）
- **子链路 2/3（Location）**：保险杠/侧轨、全身机器人板块
- 实现：`assemblies/optimus_prime/`；底盘 spec：`specs/optimus_prime_chassis.json`

### C2 — 衣柜柜体（混合）

外廓 1200×560×2100，板厚 18。

- **子链路 1（约束）**：底板、左/右/侧板、背板、顶板共 5 件；竖板锁 `axis_z` + 厚度方向 `axis_x` 或 `axis_y`。
- **子链路 2（Location）**：6 层板高度 320/520/…/1320，2 竖隔板，鞋架距底 80；相对内空公式放置。
- `gen_step()`：`Compound([constraint_assembly(shell), interior_compound])`。
- 实现：`assemblies/wardrobe_closet/`。

### C3 — 书桌：台面 + 四条腿

- 子链路 1：四条相同腿用一份 CONSTRAINTS 模板 + 不同 in_plane 偏移（或 1 腿求解后 `moved` 镜像）。
- 子链路 2：台面大块 `Location` 落在四腿顶面中心高度。
- 可选：台面与腿顶面之间 4 条 `contact` 约束（区域间连接）。

### C4 — 两步装配：机箱 + 托盘

- 机箱 U 型围板：约束求解为 `shell` Compound。
- 托盘组（3 层）：`GridLocations` 或循环 `Location` 生成 `trays` Compound。
- 托盘组整体 `trays.moved(Location((0,0,z0)))` 装入机箱。

### C4 — 16 柱 + 中央横梁（组合）

柱阵同 B1；中央横梁单独 CONSTRAINTS 仅 3 件（底板、左柱、右柱）验证桥接，再与柱阵 `Compound` 合并（横梁用 Location 对齐柱顶）。

### C5 — 工业机械臂（混合，按流程验收）

块状 6 轴风格机械臂，总高约 650 mm。

1. 写 `specs/robot_arm_base.json`：`base`(ground) → `column` → `slew` → `shoulder` 逐段 `contact` 叠放（勿全部贴 `base.+z`）；`axis_parallel` 锁三轴。
2. `constraint solve` → `status=ok`，无 `rotation_issues`。
3. `assemblies/robot_arm/robot_arm.py`：`constraint_assembly` 底座 + `_arm_kinematics()` 公式摆放连杆/腕部/夹爪/线束（~19 Location 件）。
4. `scripts/step` → `model/robot_arm.step`；`inspect refs --facts --planes --positioning`。

实现：`assemblies/robot_arm/`。

### C6 — AGV 小车（混合，约束用在车轮）

底盘约 820×620×72，四角麦轮/舵轮占位 box 90×42×90，轮心距约 (±330, ±245)。

- **子链路 1（约束，真正有用）**：`chassis` ground + `wheel_fl/fr/rl/rr` 贴 `chassis.+z` + in_plane 偏移 + 三轴锁。
- **子链路 2（Location）**：甲板、电池仓、驱动器、激光桅杆、前后保险杠、侧裙、导轨、急停。
- 流程：`specs/agv_cart_chassis.json` → solve → `assemblies/agv_cart/agv_cart.py` → `scripts/step`。

### C7 — 平衡重叉车（混合，门架+载荷）

块状平衡重叉车，总高约 2.5 m，带托盘与三箱货物，Explorer 里轮廓清晰（门架+货叉+后配重）。

1. **约束子链路**：`chassis` ground；四角 `wheel_*` 贴 `chassis.+z`；后部 `counterweight` 叠在底盘上（`contact` + in_plane + 三轴锁）。
2. `specs/forklift_truck_chassis.json` → `constraint solve` → `status=ok`。
3. **Location 子链路**：驾驶室、座椅、方向盘柱、双立柱门架、滑架、挡货架、双货叉、护顶架四柱+顶梁、液压箱、前格栅、大灯、后视镜、托盘+三箱载荷、链条轮、门架横梁。
4. `assemblies/forklift_truck/forklift_truck.py` → `scripts/step` → `model/forklift_truck.step`。

实现：`assemblies/forklift_truck/`。

---

## D — 流程与纠错

### D1 — JSON 先行

先 `specs/<name>.json` + `constraint solve` / `run_validation.py`；通过后写 `assemblies/<case>/<case>.py`，`STEP_OUTPUT = "model/<case>.step"`，再 `scripts/step`。

### D2 — 错误用法

用户要「gen_step 返回 instances 引用各零件 STEP」→ 说明应 build123d 建零件 + `constraint_assembly` 或子 Compound 堆砌，无 linked assembly。

### D3 — 求解 ok 但 Explorer 里乱

按 `repair-loop.md`「求解 status=ok 但装配几何异常」排查。

---

## E — 校验清单（Agent 自检）

1. `constraint solve` → `status` 为 `ok`（或预期的 `underconstrained`）
2. `scripts/step` 成功
3. `inspect refs ... --facts --planes --positioning`
4. 关键接口 `inspect mate`（区域间贴合）
5. 有视觉歧义再 `render` / Explorer
