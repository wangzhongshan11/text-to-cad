---
name: cad
description: 使用 STEP 优先的 build123d/Python 创建、修改、检查、校验并审查 CAD 零件与装配体。适用于自然语言 CAD 规格说明、STEP/STP 生成、build123d 源码（gen_step 返回 shape_or_compound）、box/cylinder/sphere 约束装配、@cad 引用、几何事实、测量、配合增量、CAD Explorer 链接、按条件触发的审查渲染，以及次要 DXF/STL/3MF 输出。
---

# CAD 生成、检查与校验

## 用途

根据自然语言需求创建或修改参数化 CAD 模型，生成经校验的 STEP/STP 产物，检查几何引用，并返回已核对的结果及 CAD Explorer 链接。将 STEP 视为主要 CAD 产物。将 DXF、STL 和 3MF 视为从 STEP 优先流程分支或伴随产生的次要工作流。对于多个 box/cylinder/sphere 零件的装配配合，使用 `constraint_assembly`（见 `references/constraint-assembly.md`），`gen_step()` 仍返回 `shape_or_compound`。

## 何时使用本技能

当用户要求 CAD 文件、STEP/STP 文件、build123d 源码、`@cad[...]` 引用、机械零件、装配体、外壳、支架、夹具、孔、沉孔、埋头孔、槽、腔、凸台、支柱、筋、圆角、倒角、抽壳、源码级关节、配合、测量或 CAD Explorer 审查链接时使用本技能。

当用户要求从 CAD 几何导出 DXF、STL 或 3MF 时也使用。仍将上述流程视为次要，并加载 `dxf.md` 或 `supported-exports.md` 了解详情。

以下情况勿用本技能：仅渲染的概念图、CAM 刀路、工程认证结论、FEA 结论、建筑 BIM，或手绘插图——除非用户同时需要 CAD 几何。

## 默认假设

除非用户另有说明，否则采用：

- 单位：毫米。
- 原点：主零件或装配体中心；若有配合接口或固定根件暗示更佳原点则采用该原点。
- 基准平面：XY。
- 上/拉伸轴：正 Z。
- 输出几何：封闭、正体积实体；除非用户要求曲面或构造几何。
- STEP 结构：一个有效实体、实体组合体，或带标签的装配组合体。
- 装配结构：零件局部坐标系与命名基准；多个 box/cylinder/sphere 零件之间的摆放用 `constraints`（见 `references/constraint-assembly.md`）；单张 `CONSTRAINTS` 默认 ≤40 体（≥30 体会有 `large_assembly` 警告，更大请拆子链路）；生成后用 `inspect` 校验（见 `references/positioning.md`）。
- 小型塑料外壳壁厚：未指定时 2.0–3.0 mm。
- 装饰圆角：局部几何安全时 1.0–3.0 mm。
- M3/M4/M5 普通间隙孔：除非要求其他标准，分别为 3.4/4.5/5.5 mm。

仅当缺失信息导致无法建模、配合关键、安全关键或合规约束时，提一个聚焦的澄清问题；否则带着明确假设继续。

## 仅自然语言规格

勿要求用户提供 JSON 规范，也不要将 JSON 作为面向用户的工作流。将用户叙述转为内部 CAD 简报，包含尺寸、特征、假设、输出路径与校验标准。简报撰写模式见 `references/natural-language-specs.md`。

## 根目录模型

区分以下根目录：

- **CAD 技能目录**：本文件夹。工具入口为 `scripts/step`、`scripts/inspect`、`scripts/render`、`scripts/dxf`。
- **工具进程 cwd**：相对 CAD 目标从命令当前工作目录解析。从技能目录运行时请使用绝对目标路径，或从工作区根目录运行并通过指向本技能目录的路径调用入口脚本。
- **Explorer 扫描根**：若设置 `EXPLORER_ROOT_DIR`，CAD Explorer 从该处扫描；否则扫描由 Vite 从 `EXPLORER_WORKSPACE_ROOT`、npm `INIT_CWD` 或 Vite 进程 cwd 推断的工作区根。Explorer 的 `file=` 链接须相对于活动扫描根。

本技能中的短命令示例相对于 CAD 技能目录。请调整入口或目标路径，使项目 CAD 文件从预期工作区解析，而非误落在技能目录下。

除非用户明确要求，否则优先将 STEP 输出与其 Python 生成器放在同一目录，便于发现源码。除非用户明确要求，否则保持 STEP 基名与生成器基名一致，即使二者无法并排存放。

## 可用工具

在 CAD 技能目录下，入口形态为：

```bash
python scripts/step ...
python scripts/inspect ...
python scripts/render ...
python scripts/dxf ...
npm --prefix explorer run dev
npm --prefix explorer run dev:ensure -- --file path/to/model.step
```

使用活动项目的 Python 解释器。若仅有仓库本地虚拟环境，在明确上述根模型的前提下使用该解释器。

使用 `python scripts/<tool> --help` 查看完整当前命令接口；参考文档展示推荐工作流，而非每个标志位。

## 必需工作流

1. **任务分类。** 判断是新零件、新装配体、源码修改、直接 STEP/STP 检查、引用选择、测量/配合检查、渲染审查，还是次要输出请求。
2. **仅加载所需参考。** 用下方触发条件代替通读整套参考。
3. **撰写自然语言 CAD 简报。** 提取尺寸、单位、坐标约定、特征意图、输出路径、假设与校验目标。
4. **编码前先规划。** 编辑前定义参数、标签、源码路径、预期包围盒以及任何配合/定位基准。
5. **编辑源码，而非生成产物。** 优先使用带 `gen_step()` 的 build123d Python 生成 STEP。
6. **生成明确目标。** 使用 `scripts/step` 生成 STEP/STP 及 sidecar。仅在直接导入 STEP/STP 时使用 `--kind part` 或 `--kind assembly`。勿做目录级批量生成。
7. **几何校验。** 使用 `scripts/inspect refs --facts --planes --positioning`，必要时再定向使用 `measure`、`mate`、`frame` 或 `diff`。
8. **返回 Explorer 链接。** Explorer 启动、扫描根与链接规则见 `references/rendering-and-explorer.md`。
9. **按条件渲染。** 仅在用户请求、Explorer 不可用、仍存在视觉歧义，或剖视/线框审查能回答真实校验问题时使用 `scripts/render`。
10. **修复并重跑。** 若检查失败，修改最小必要源码段，重新生成并重新运行失败的校验。

## 不可协商事项

- 将生成的 STEP/STP、STL、3MF、GLB/拓扑、DXF 输出及 Explorer sidecar 视为派生产物。
- 将 STEP 视为主要经校验的 CAD 产物；除非用户明确说明，否则 DXF/STL/3MF 为次要。
- 若存在 Python 生成器，对生成器运行 `scripts/step`。仅在生成器不可用或用户明确将该 STEP/STP 文件指定为目标时使用直接 STEP/STP 目标。
- 使用命名参数、封闭实体、明确标签与源码控制的几何意图。
- 在源码中用 build123d 参数化建模；`gen_step()` 返回 `shape_or_compound`；box/cylinder/sphere 零件间配合用 `CONSTRAINTS` + `constraint_assembly`。将 CLI `inspect mate` 视为只读校验。
- 勿将 `git status`、`git diff` 或文件体积变动作为大型导出 STEP/STP、GLB/拓扑、STL、3MF 或 DXF 的 CAD 对比手段。应对比源码变更、`scripts/inspect` 摘要、定向渲染或 CAD Explorer 输出；记账时仅对 git status 做路径限定。
- 仅报告实际已运行或由工具输出直接支持的检查。
- 若 Explorer 失败，如实说明并依赖 CLI 检查做校验。

## 渐进式参考

仅在对应触发条件成立时加载：

- `references/natural-language-specs.md` — 将叙述需求转为 CAD 简报，勿要求用户 JSON。
- `references/step-generation.md` — STEP 生成、直接 STEP/STP 目标、零件与装配体行为、生成后检查。
- `references/inspection-and-validation.md` — 校验门槛、`@cad[...]` 引用、facts、planes、拓扑、测量、配合、diff、frame 及最终校验报告。
- `references/positioning.md` — 零件局部基准、`inspect` mate/frame/measure 与定位报告。
- `references/rendering-and-explorer.md` — CAD Explorer 链接与条件性渲染 view/wireframe/section/list。
- `references/dxf.md` — 次要 DXF 工作流。
- `references/supported-exports.md` — 次要 STL/3MF sidecar 工作流。
- `references/build123d-modeling.md` — build123d 建模、拓扑、选择器；**装配子链路分解**（区域内 Location vs 约束、区域间连接）；复杂装配先读装配分解节。
- `references/repair-loop.md` — 诊断与修复流程。
- `references/constraint-assembly.md` — `CONSTRAINTS` / `constraint_assembly` API 与约束语义。

最终回复应包含生成文件、CAD Explorer 链接、实际运行的校验、假设与注意事项。报告结构见 `references/inspection-and-validation.md`。
