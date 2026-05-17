# 运动产物封装

当需要通过 CAD Explorer 与本地运动服务器对外暴露逆运动学或路径规划时使用 `gen_motion()`。URDF 可来自任意来源，只要是有效的仓库内 `.urdf`，且运动配置引用真实的机器人连杆、关节、坐标系与末端执行器即可。

## 源码形态

在持有 URDF 的 Python 文件或邻近 Python 源码中定义零参数 `gen_motion()`：

```python
def gen_motion() -> dict[str, object]:
    return {
        "urdf": "sample_robot.urdf",
        "provider": "moveit_py",
        "commands": ["urdf.solvePose", "urdf.planToPose"],
        "planningGroup": "arm",
        "jointNames": ["joint_1", "joint_2", "joint_3"],
        "planningGroups": [
            {
                "name": "arm",
                "jointNames": ["joint_1", "joint_2", "joint_3"],
            }
        ],
        "endEffectors": [
            {
                "name": "tool",
                "link": "tool_link",
                "frame": "base_link",
                "parentLink": "tool_mount_link",
                "planningGroup": "arm",
                "positionTolerance": 0.002,
            }
        ],
        "planner": {
            "pipeline": "ompl",
            "plannerId": "RRTConnectkConfigDefault",
            "planningTime": 1.0,
        },
        "disabledCollisionPairs": [
            ["link_2", "link_3"],
        ],
    }
```

## 字段说明

- `urdf`：生成的 `.urdf` 路径，相对于 Python 源码文件。
- `provider`：当前为 `moveit_py`。
- `commands`：仅姿态求解使用 `["urdf.solvePose"]`；需要规划时追加 `urdf.planToPose`。
- `planningGroup`：活动机械臂或链路的 MoveIt 规划组名称。
- `jointNames`：按规划组排序的非固定 URDF 关节。websocket 传输上转动关节值为度；生成的 SRDF 组状态中为弧度。
- `planningGroups`：可选的 MoveIt 规划组数组。当一个 URDF 暴露多条可独立求解的链（例如双臂各自 TCP）时使用。省略时，仅由 `planningGroup` 与 `jointNames` 定义唯一组。
- `endEffectors`：一个或多个具名工具连杆。若代表不同工具或 TCP，允许多个末端执行器；每个应有稳定的 `name`、受控 `link`、目标 `frame` 与 MoveIt `parentLink`。对多组封装，在每个末端执行器上设置 `planningGroup`，以便运动服务器选用匹配的求解组。
- `planner`：仅在启用 `urdf.planToPose` 时需要。
- `disabledCollisionPairs`：在 SRDF 中额外禁碰的连杆对。相邻父子连杆对会根据 URDF 关节自动添加。
- `groupStates`：可选的 SRDF 组状态。每项使用 `jointValuesByNameRad`；定义多组时需包含 `planningGroup`。

## 生成文件

运行：

```bash
python .agents/skills/robot-motion/scripts/gen_motion_artifacts/cli.py sample_robot.py --summary
```

生成器将所有运动持有的输出写入 `.<urdf filename>/robot-motion/`：

- `explorer.json`
- `motion_server.json`
- `moveit2_robot.srdf`
- `moveit2_kinematics.yaml`
- `moveit2_py.yaml`
- 启用 `urdf.planToPose` 时还有 `moveit2_planning_pipelines.yaml`

在变更规划关节、末端执行器、碰撞排除、规划器设置或其引用的 URDF 连杆/关节后，需重新生成运动产物。
