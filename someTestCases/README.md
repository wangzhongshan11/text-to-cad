# someTestCases

本工作区内的**实验性 CAD 案例**目录。每个案例放在：

`someTestCases/<domain>/<slug>/`

- **domain**：大类（示例：`ceiling` 吊顶、`furniture` 家具等）。
- **slug**：一般与 Python 生成器主文件名一致（如 `wardrobe`、`shuangyanpidiao_top`）。

每个案例文件夹里通常会有：

- `*.py` — build123d 生成器，含 `gen_step()`（可选 `gen_dxf()` 等）。
- `*.step` — 主 STEP 输出（用 CAD 技能的 `scripts/step` 再生，勿手改）。
- `.*.step.glb` — 生成后 Explorer 用的网格侧车文件。
- `*_build_process.md` 或 `ITERATION_LOG.md` — 可读的过程流水：命令、工具输出、错误与修复（要求见根目录 `AGENTS.md` 中 **「Claude Code：迭代过程全量留痕」**）。

Explorer 的 `file=` 路径相对于**扫描根**（一般为仓库根），例如：  
`?file=someTestCases/furniture/wardrobe/wardrobe.step`。
