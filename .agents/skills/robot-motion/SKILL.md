---
name: robot-motion
description: 基于 URDF 的逆运动学与路径规划的机器人运动搭建、生成与校验。当 Codex 需要安装 ROS 2 或 MoveIt 2 依赖、运行或测试本地运动服务器、为 `.urdf` 生成 CAD Explorer 运动产物、创建 MoveIt/SRDF/运动学/规划 sidecar、调试 IK 或路径规划行为，或校验机器人运动命令时使用。
---

# Robot Motion（机器人运动）

在已有机器人 URDF 且任务需要本地运动行为时使用本技能：IK、路径规划、MoveIt 配置、websocket 运动服务器调试或 ROS 依赖安装。只要 `gen_motion()` 中命名的连杆、关节、坐标系与末端执行器在该文件中真实存在，任何有效的仓库内 `.urdf` 均可使用。

## 工作流

1. 从已有的有效 `.urdf` 出发。
2. 使用带零参数 `gen_motion()` 的 Python 源码，通过 `scripts/gen_motion_artifacts/cli.py` 生成运动产物。
3. 若本地运动环境可能已存在，用 `scripts/check-motion-server.sh` 校验；仅在依赖缺失或过期时运行 `scripts/setup.sh`。
4. 使用 `scripts/run-motion-server.sh` 启动 websocket 运动服务器。
5. 在交接运动行为之前测试协议、产物生成与提供者逻辑。
6. 关于启用运动的 `.urdf` 条目的 CAD Explorer 交接，遵从 CAD 技能并将运动专用元数据保留在本技能。

## CAD Explorer 交接

阅读 `.agents/skills/cad/SKILL.md`，仅在任务需要 Explorer URL 时再加载其 `references/rendering-and-explorer.md`。若不可用，使用 [cad-skill](https://github.com/earthtojake/cad-skill)。勿在本技能中重复 Explorer 启动或 URL 语法。在运动产物或 URDF 目标已生成或变更，或用户请求浏览器审阅时，链接仓库内 `.urdf`。运动专用 Explorer 元数据与运动服务器行为保留在本技能。

## 命令

在机器人项目仓库根目录运行。若当前工作目录在其他位置，将 `ROBOT_MOTION_REPO_ROOT` 设为机器人项目根。

```bash
python .agents/skills/robot-motion/scripts/gen_motion_artifacts/cli.py <robot-urdf-source.py> --summary
```

```bash
.agents/skills/robot-motion/scripts/setup.sh
.agents/skills/robot-motion/scripts/check-motion-server.sh
.agents/skills/robot-motion/scripts/run-motion-server.sh
```

运行时与宿主无关，但基于 Conda/RoboStack/Jazzy。安装脚本会从 `environment.yml` 创建或更新专用 conda 环境，以可编辑模式安装 `server/`，并运行 `motion_server --check`。可通过 `ROBOT_MOTION_CONDA_EXE`、`CONDA_EXE`、`PATH` 或常见的 Miniforge/Miniconda/Anaconda 安装根目录使用任意兼容 conda 的安装。不要将 ROS 或 MoveIt 包装入仓库 CAD 的 `.venv`、系统 Python 或系统包管理器。

仅在任务需要非默认仓库根、环境、conda 可执行文件、主机或端口时，才使用 `ROBOT_MOTION_REPO_ROOT`、`ROBOT_MOTION_CONDA_ENV_NAME`、`ROBOT_MOTION_CONDA_EXE`、`ROBOT_MOTION_HOST` 或 `ROBOT_MOTION_PORT`。

## 运动产物

在创建或编辑 `gen_motion()` 封装、运动持有的 sidecar、生成文件预期或求解与规划的命令选择时，使用 `references/motion-artifacts.md`。

## 运动服务器

浏览器通过直连本地 websocket 与 `motion_server` 通信，默认为 `ws://127.0.0.1:8765/ws`。Vite 不会启动或托管该服务器。

服务器包位于 `server/`。它会根据仓库内 robot-motion 的 explorer 元数据与 `robot-motion/motion_server.json` 校验请求的 URDF 文件，从 `robot-motion/` 加载 MoveIt sidecar，并将 `urdf.solvePose` / `urdf.planToPose` 分发给提供者。

## 故障排查

若 `check-motion-server.sh` 找不到 conda，定位已有的 `*/bin/conda` 并以 `ROBOT_MOTION_CONDA_EXE=/path/to/conda` 重跑。勿仅因 conda 发现失败就运行 setup。

在沙箱代理环境中，绑定或连接本地 websocket 可能在 `127.0.0.1:<port>` 上出现 `PermissionError`。使用环境批准的越沙箱/本地网络机制重跑服务器或冒烟命令；仅在实际端口被占用时更改 `ROBOT_MOTION_PORT`。

## 测试

变更后运行针对性测试：

```bash
PYTHONPATH=.agents/skills/robot-motion/server ./.venv/bin/python -m unittest discover .agents/skills/robot-motion/server/tests
PYTHONPATH=.agents/skills/robot-motion/scripts ./.venv/bin/python -m unittest discover .agents/skills/robot-motion/scripts/gen_motion_artifacts/tests
```

MoveIt 适配器测试应保持隔离，除非测试显式需要 ROS，否则在无 source ROS 的环境下也应通过。

## 参考

- 运动产物规格：`references/motion-artifacts.md`
