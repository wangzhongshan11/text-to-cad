# AGENTS.md

本仓库是面向 Codex、Claude Code 等编程智能体的脚本驱动 CAD 生成脚手架。

若要修改 CAD Explorer 本体，请参阅 `.agents/skills/cad/explorer/README.md`。

## 技能路由

工作流细节请使用内置技能文档：

- `.agents/skills/cad/SKILL.md`：STEP、STL、3MF、DXF、GLB/拓扑产物、渲染图、`@cad[...]` 提示引用，以及 box/cylinder/sphere 约束装配（`constraint_assembly`，`gen_step()` 仍返回 `shape_or_compound`）。
- `.agents/skills/urdf/SKILL.md`：生成的 URDF 文件、`gen_urdf()`、连杆、关节、限位以及 URDF 网格引用。
- `.agents/skills/robot-motion/SKILL.md`：ROS 2/MoveIt 依赖安装、运行 motion 服务端，以及为既有 URDF 生成 IK/轨迹规划产物。

生成或编辑机器人描述时请使用 URDF 技能。若已有合法 URDF，可直接用 robot-motion 技能挂载运动产物；逆运动学、轨迹规划、运动产物生成与 motion 服务端测试请使用 robot-motion。

`AGENTS.md` 刻意聚焦于脚手架层面；可复用的 CAD、URDF、robot-motion 规则写在各技能文档内。

## 脚手架上下文

项目 CAD 文件路径相对于仓库根目录。本脚手架不预留固定的「项目文件」目录。CAD 条目可位于仓库根下的 `STEP/`、`STL/`、`DXF/`、`3MF/` 等文件夹，或由项目自选的其他明确仓库相对路径布局。

CAD 与 URDF 技能工具均以文件为目标，不依赖特定脚手架布局，也不会自动前缀项目根路径。

项目专属上下文可写在简洁的根级笔记（如 `PROJECT.md`）中。请勿把可复用的生成器约定、提示引用规则、校验策略、Explorer/链接规则、图像审阅策略或完整 CLI 语法复制进去；请改为链接到对应技能文档。

CAD Explorer 的扫描根目录、链接行为以及 `@cad[...]` 语义，请以 `.agents/skills/cad/SKILL.md` 及其 Explorer/渲染引用为准。

`docs/internal/` 为维护者设计稿与历史笔记，**不是**代理工作流参考；约束装配日常以 `.agents/skills/cad/references/constraint-assembly.md` 为准。

多轮任务（意图理解、工具反馈、修正）用 **`runs/`** 记录：见 `runs/README.md`，CLI 为 `runs/tools/record_run.py`（`init` → `intent` → `round` / `feedback` / `step` → `finalize` → `render`）。任务结束前生成 `RUN.md` 摘要，不替代 IDE transcript。

## Python 环境

若存在仓库本地的 CAD 运行时，请优先使用：

```bash
./.venv/bin/python
```

该环境包含技能工具所需的 CAD 依赖（含 `build123d` 与 `OCP`）。若缺少 `.venv` 或无法导入上述模块，请在运行 CAD 工具前于仓库根目录创建并安装：

```bash
python3.11 -m venv .venv
./.venv/bin/pip install -r .agents/skills/cad/requirements.txt
```

其他内置技能的 Python 依赖各自定义在对应技能目录；仅在用到相关工作流时再安装。

## 单一事实来源（Source Of Truth）

- 生成的 CAD、URDF、robot-motion 输出、Explorer 侧车文件、渲染、拓扑、网格以及展开图等均为派生产物。
- 除非明确要求，请勿手工编辑派生产物。请先修改所属的源码或其所导入的源码，再用对应技能工具按明确目标重新生成。
- 若重新生成的结果与仓库中已提交的生成文件不一致，以重新生成的结果为准。

## 仓库策略

- 将项目 CAD 文件放在明确的仓库相对路径下。
- 使用明确的生成目标；不要对整个目录做批量生成。
- 生成工具会写入并覆盖当前配置的输出；路径变更时不会自动删除陈旧输出。
- 仅在项目侧重点、入口角色、清单、依赖说明、长期特例或首选重建根发生变化时，再更新项目本地文档。
- CAD 输出常被 LFS 跟踪；大范围 `git status` 可能在生成文件变动时触发 LFS clean 过滤器；CAD 工作期间建议使用限定路径的 `git status`。
- 若仅需记账用的完整状态，可使用 `git -c filter.lfs.clean= -c filter.lfs.smudge= -c filter.lfs.process= -c filter.lfs.required=false status --short`。
- 禁止对 `git add`、提交或其他写入对象的操作禁用 LFS 过滤器。

## 执行要点

- 从尽量窄、且仅限源码的检索开始，以定位直接受影响的文件。
- 除非任务明确针对这些内容，否则默认检索应排除生成产物、二进制 CAD、缓存与构建输出。
- 若第一轮已厘清范围，应先改源码再验证。
- 在同一编辑循环中，几何仍在变动时，不要将可变的生成、检查与渲染/审阅步骤并行执行。应先重建，再检查，最后审阅。
- 在云环境或资源受限环境中，若已知受影响条目，应避免整仓 hydrating；仅拉取编辑并明确重新生成所需的输入、生成输出及对应 LFS 对象。
