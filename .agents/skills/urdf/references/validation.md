# URDF 校验

在校验已生成的 URDF 文件时使用本文。

## 结构检查

校验以下内容：

- 根元素为 `<robot>`
- robot 具有非空名称
- 每个 link 具有唯一非空名称
- 每个 joint 具有唯一非空名称
- 每个 joint 具有有效的 parent 与 child 连杆
- parent/child 连杆存在
- 每个 child 连杆至多有一个 parent
- 图恰好有一个根 link
- 图连通且无环
- 除非设计有意采用其他结构且校验器支持，否则树中 joint 数量恰好为 `links - 1`

## 关节检查

支持的 joint 类型：

- `fixed`
- `continuous`
- `revolute`
- `prismatic`

对 `revolute` 与 `prismatic` 关节，校验上下限。确认轴线与原点符合预期的运动学行为。

## 惯量检查

对每个具有质量或几何的实体连杆，优先提供显式 `inertial` 块：

- `origin` 为连杆坐标系下的质心
- `mass` 为正
- `inertia` 定义 `ixx`、`ixy`、`ixz`、`iyy`、`iyz`、`izz`
- 对角惯量分量为正
- 惯量分量满足基本三角形不等式

纯坐标系连杆可有意省略 `inertial`。

## 网格检查

校验视觉与碰撞网格引用：

- 非空
- 指向支持的网格格式
- 能从生成 URDF 的位置或 package URI 约定解析
- 引用的文件存在

碰撞几何也可使用支持的 URDF 基本体，如 box、cylinder 或 sphere。若 URDF 用于物理仿真，优先采用简化的碰撞几何而非精细视觉网格。

若网格引用发生变化，确认对应的网格输出已单独重新生成。

## 工具

`scripts/gen_urdf/cli.py --summary` 在重新生成后打印紧凑的 robot/link/joint 摘要。

URDF 源码读取器还会用 `yourdfpy` 校验 XML 结构，须在活动的 Python 环境中安装。
