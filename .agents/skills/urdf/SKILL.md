---
name: urdf
description: 针对机器人模型输出的 URDF 生成与校验。当代理需要创建、编辑、重新生成、检查或校验 `.urdf` 文件、`gen_urdf()` 封装、机器人连杆（link）、关节（joint）、关节限位、父子运动学结构、视觉或碰撞网格引用、碰撞几何或 URDF 专用 XML 校验时使用。STEP/STP、STL/3MF/DXF 导出、渲染图、GLB/拓扑 sidecar、CAD Explorer 链接以及 @cad 几何引用请使用所属的 CAD 或网格工作流。
---

# URDF

将本技能用于机器人描述类输出。URDF 与普通 CAD 生成刻意分开，因为其正确性更多关乎运动学、XML 与网格引用，而非主要关乎几何。

当下游 UI 或仿真适配器需要时，允许使用面向消费者的元数据。将该元数据视为生成器持有的扩展数据，而非标准 URDF 的一部分。

CAD 交接细节交给 CAD 技能：阅读 `.agents/skills/cad/SKILL.md`，仅在 URDF 需要 CAD Explorer 链接时再加载其 `references/rendering-and-explorer.md`。若本地 CAD 技能不可用，可使用 [cad-skill](https://github.com/earthtojake/cad-skill) 作为后备参考。URDF 专用生成与 `explorer_metadata` 约定保留在本技能中。

## 工作流

1. 将定义 `gen_urdf()` 的 Python 源码视为事实来源；将配置生成的 `.urdf` 文件视为生成产物。
2. 关于 `gen_urdf()` 封装约定，阅读 `references/generator-contract.md`。
3. 关于机器人描述编辑，阅读 `references/urdf-workflow.md`。
4. 优先保证物理连杆完整：对每个表示机器人实体几何的连杆包含 `inertial`、`visual` 与 `collision`。纯坐标系连杆可有意省略。
5. 有意识地编辑连杆、关节、限位、轴线、原点、惯量、材质、视觉/碰撞几何、网格文件名以及任何面向消费者的 sidecar 元数据。
6. 仅使用 `scripts/gen_urdf/cli.py` 重新生成明确的 URDF 目标。
7. 重新生成后使用 `--summary` 进行紧凑的 robot/link/joint 检查。
8. 关于校验预期，阅读 `references/validation.md`。
9. 若 URDF 网格引用依赖已变更的 CAD、网格或渲染输出，仅用所属的 CAD 或网格工作流重新生成受影响的具体目标。
10. 对已生成 `.urdf` 条目的 CAD Explorer 交接，使用 CAD 技能的 Explorer 交接规则，勿在此重复链接语法。

## 命令

使用项目或工作区的 Python 环境运行。若环境缺少 URDF 校验运行时包，从 `requirements.txt` 安装本技能的脚本依赖。以文件系统脚本方式调用工具，例如 `python <urdf-skill>/scripts/gen_urdf/cli.py ...`。相对目标路径从当前工作目录解析；工具不会前置项目根路径。

- URDF sidecar：`scripts/gen_urdf/cli.py`

命令界面以目标为显式约束。传入定义 `gen_urdf()` 的 Python 生成器；使用 `--summary` 进行紧凑的 robot/link/joint 检查。

## 参考

- URDF 生成：`references/gen-urdf.md`
- 生成器约定：`references/generator-contract.md`
- URDF 编辑工作流：`references/urdf-workflow.md`
- URDF 校验：`references/validation.md`
