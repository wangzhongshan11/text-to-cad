# 约束装配示例

目录约定（仓库根执行，使用 `.venv`）：

```text
examples/constraint/
  specs/          # 仅求解器：CONSTRAINTS JSON，无 build123d 几何
  assemblies/     # 端到端：按案例分子目录
    <case>/
      <case>.py   # gen_step 脚本
      model/      # 导出的 .step 与 Explorer .step.glb
  out/            # 求解/装配过程写出的 JSON（可删后由脚本再生）
  chatExamples/   # 自然语言 prompt 样例
  run_validation.py
```

## `specs/` 是什么

每个 `*.json` 是一份**约束规格**：`ground`、`bodies`（box/cylinder/sphere 尺寸）、`constraints` 列表。  
只给 `constraint solve` / `run_validation.py` 用，**不包含**零件 mesh，也**不导出** STEP。

用途：快速验证约束是否可解、是否欠约束，而不用写 build123d 脚本。

## `out/` 里各 JSON 是什么

| 文件模式 | 谁生成 | 内容 |
|----------|--------|------|
| `<spec>.report.json` | `run_validation.py` 读 `specs/<spec>.json` | 求解报告：`status`、`residual_max`、`free`、`hint`、`conflict` 等 |
| `<spec>.transforms.json` | 同上 | 每个 `body_id` 的 4×4 刚体变换（16 个数），求解器输出 |
| `assembly_<name>.constraint.report.json` | `assemblies/<case>/<case>.py` 里 `constraint_assembly(..., report_path=...)`（跑 `scripts/step` 时） | 与 report 相同结构；端到端装配调试 |

`out/` 是**派生调试产物**，不是源文件；删掉后运行 `run_validation.py` 或重新 `scripts/step` 可再生成。

## `assemblies/` 是什么

每个案例一个子目录，**脚本与模型分离**：

```text
assemblies/
  box_on_box/
    box_on_box.py
    model/
      box_on_box.step
      .box_on_box.step.glb
  wardrobe_closet/
    wardrobe_closet.py
    model/
      wardrobe_closet.step
  ...
```

- `<case>.py`：`CONSTRAINTS` + build123d 零件 + `return constraint_assembly(...)` → 单个 `Compound`；模块级 `STEP_OUTPUT = "model/<case>.step"`
- `model/`：由 `scripts/step` 写入的 STEP 与 Explorer GLB 侧车

**复杂场景**：

| 案例 | 零件数 | 说明 |
|------|--------|------|
| `pin_grid_4x4` | 17（1 底板 + 4×4 柱） | 阵列柱钉 |
| `wardrobe_closet` | 5+9 | 围板约束求解 + 层板/隔板 Location（混合子链路） |
| `optimus_prime` | 5+25 | 卡车底盘约束（平台+四轮）+ 上身/四肢 Location（块状擎天柱） |
| `robot_arm` | 4+19 | 底座柱+转台+肩座约束叠放 + 连杆/末端 Location（工业机械臂） |
| `agv_cart` | 5+17 | 底盘+四轮约束定位 + 甲板/电池/桅杆/保险杠 Location（AGV） |
| `forklift_truck` | 6+27 | 底盘+四轮+配重约束 + 驾驶室/门架/货叉/护顶架/托盘载荷 Location（叉车） |

## 命令

```bash
# 仅求解 specs（写 out/*.report.json 与 out/*.transforms.json）
./.venv/bin/python examples/constraint/run_validation.py

# 端到端导出装配 STEP（写入 assemblies/<case>/model/）
./.venv/bin/python .agents/skills/cad/scripts/step examples/constraint/assemblies/box_on_box/box_on_box.py
./.venv/bin/python .agents/skills/cad/scripts/step examples/constraint/assemblies/wardrobe_closet/wardrobe_closet.py

# 单条 spec 求解
./.venv/bin/python .agents/skills/cad/scripts/constraint solve examples/constraint/specs/box_on_box.json
```

工作流见 `.agents/skills/cad/references/constraint-assembly.md`。

多轮 Agent 任务（意图、反馈、修正）记录见仓库根目录 `runs/README.md`。
