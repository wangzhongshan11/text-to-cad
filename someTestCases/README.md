# someTestCases

本仓库内的**实验性 CAD 案例**目录。每个案例放在：

`someTestCases/<domain>/<slug>/`

- **domain**：大类（如 `furniture`、`mechanism`、`ceiling`）。
- **slug**：通常与主生成器 `.py` 同名。

## 典型内容

- **`*.py`** — build123d 生成器，需暴露 **`gen_step()`**（以及按需的 `gen_dxf()` 等）。
- **`*.step`** — 主 STEP；用 CAD 技能的 `scripts/step` 再生，勿手改。
- **`.*.step.glb`**（或同类隐藏侧车）— Explorer 预览用网格/拓扑产物；须为**真实二进制**。若仓库使用 Git LFS 且本地仍是 **pointer 文本**，需 `git lfs pull` 或对 owning **`*.py`** 运行 `scripts/step` 重新生成，否则 Explorer / 拓扑校验会报 `STEP_topology` / `indexView` 相关错误。
- **`preview.png` / `bom.json` / `assembly.json`** — 按项目需要作为分解与转译输入（流程见根目录 `README.md` 与 `.agents/skills/cad/references/model-decomposition-assembly-spec.md`）。
- **`ITERATION_LOG.md` 或 `*_build_process.md`** — 过程流水（要求见根目录 `AGENTS.md`）。

## Explorer 链接

`file=` 路径相对于 **Explorer 扫描根**（一般为仓库根），例如：

`?file=someTestCases/furniture/wardrobe/wardrobe.step`

详见 `.agents/skills/cad/references/pipeline-reference.md`（CAD Explorer 一节）。
