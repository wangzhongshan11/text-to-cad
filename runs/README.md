# Agent 运行记录（P0）

本目录存放**单次 CAD 任务**的可复现摘要，不是 Cursor/Codex 的完整 transcript。

## 目录结构

```text
runs/
  README.md                 # 本说明
  tools/record_run.py       # CLI：初始化 / 记意图 / 记轮次 / 记反馈 / 生成 RUN.md
  _templates/               # 空模板
  examples/<run_id>/        # 示例（可进仓）
    manifest.json           # 机器可读全记录
    RUN.md                  # 人类可读一页摘要
    brief.md                # 可选：意图/简报原文
```

## `manifest.json` 记什么

| 区块 | 用途 |
|------|------|
| `intent` | 用户原话、CAD 简报、假设、待澄清 |
| `iterations[]` | 多轮：规划 → 实现 → 校验 → 修正 |
| `iterations[].feedback[]` | 工具反馈（约束 report、inspect、用户纠正） |
| `iterations[].steps[]` | 命令/工具步（cmd、exit、产物路径） |
| `final` | 最终状态、STEP 路径、校验结论 |

**不记录**：工具 stdout 全文、transcript、密钥。

## 常用命令

```bash
# 新建一次运行
./.venv/bin/python runs/tools/record_run.py init \
  --id 2026-05-17_agv-cart \
  --task "AGV 小车混合装配" \
  --agent cursor

# 保存意图理解 / 简报
./.venv/bin/python runs/tools/record_run.py intent \
  --run 2026-05-17_agv-cart \
  --user "生成 AGV，底盘四轮用约束" \
  --brief-file path/to/brief.md

# 新的一轮（实现 / 校验 / 修正）
./.venv/bin/python runs/tools/record_run.py round \
  --run 2026-05-17_agv-cart \
  --phase validate \
  --note "constraint solve + run_validation"

# 挂载一次工具反馈（可多次）
./.venv/bin/python runs/tools/record_run.py feedback \
  --run 2026-05-17_agv-cart \
  --kind constraint_report \
  --path examples/constraint/out/agv_cart_chassis.report.json

# 记录命令步
./.venv/bin/python runs/tools/record_run.py step \
  --run 2026-05-17_agv-cart \
  --tool Shell \
  --cmd "./.venv/bin/python examples/constraint/run_validation.py" \
  --exit 0 \
  --artifact examples/constraint/out/agv_cart_chassis.report.json

# 从 manifest 生成 RUN.md
./.venv/bin/python runs/tools/record_run.py render --run 2026-05-17_agv-cart

# 标记完成
./.venv/bin/python runs/tools/record_run.py finalize \
  --run 2026-05-17_agv-cart \
  --status success \
  --step examples/constraint/assemblies/agv_cart/model/agv_cart.step
```

## 与仓库其他产物的关系

| 产物 | 关系 |
|------|------|
| `examples/constraint/out/*.json` | 由 `feedback --path` 引用，不复制进 manifest |
| `specs/*.json` | 可在 `final.specs` 列出 |
| IDE `agent-transcripts/` | L0 调试源；本目录是 L1+L3 .harness 摘要 |

Agent 在任务结束前应：`finalize` + `render`，把 `RUN.md` 路径写进对用户的回复。
