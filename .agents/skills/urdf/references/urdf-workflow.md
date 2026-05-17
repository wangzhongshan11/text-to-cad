# URDF 工作流

在编辑机器人描述结构、网格引用或生成的 URDF 输出时使用本文。

## 编辑循环

1. 找到定义 `gen_urdf()` 的 Python 源码。
2. 将该 Python 源码视为事实来源，`.urdf` 文件视为生成产物。
3. 对实体机器人连杆，优先包含标准三件套：`inertial`、`visual`、`collision`。
4. 有意识地编辑连杆、关节、限位、轴线、原点、惯量、材质、视觉/碰撞几何及网格文件名。
5. 若项目使用生成的装配网格，保持视觉与碰撞网格引用与源码中的装配或实例载荷一致。
6. 仅用 `scripts/gen_urdf/cli.py <source-file>` 重新生成明确的 URDF 目标。
7. 使用 `--summary` 进行紧凑的 robot/link/joint 检查。
8. 若网格输出变更，仅用所属的 CAD 或网格工作流重新生成受影响的具体输出。

## 标准连杆标签

对每个表示机器人实体几何的连杆使用下列标签：

- `inertial`：仿真器使用的质量、质心与惯量张量。
- `visual`：显示几何及可选材质。
- `collision`：物理与规划使用的接触几何。

纯坐标系连杆（如 `base_footprint` 或工具中心标记坐标系）在不代表实体质量或几何时可有意省略这些标签。

对可动的实体连杆，除非目标仿真器明确支持该建模方式，否则避免质量为零或缺失。若无法获得精确质量属性，使用已文档化的近似值，并便于日后替换。

## Explorer 位姿元数据

当下游 UI 或仿真适配器需要具名机器人位姿、默认关节值或其他面向消费者的描述数据时，将其编码为生成器持有的 sidecar 元数据，而非写入生成 URDF 内的非标准 XML。

- 从 `gen_urdf()` 返回可选的 `explorer_metadata`；生成器将其写入 `.<urdf filename>/explorer.json`。
- 采用宿主定义的元数据模式并文档化预期键。
- 若存储默认值或位姿预设，文档化该消费者期望的单位。
- 将事实来源保留在定义 `gen_urdf()` 的 Python 文件中，然后重新生成明确的 `.urdf` 目标。

示例：

```json
{
  "schemaVersion": 1,
  "kind": "example-urdf-consumer",
  "defaultJoints": {
    "elbow": 45
  },
  "poses": [
    {
      "name": "home",
      "joints": {
        "shoulder": 0,
        "elbow": 45
      }
    }
  ]
}
```

## 网格引用

URDF 网格文件名应从生成 URDF 文件的视角保持稳定，或采用消费者理解的 package URI 约定。

使用 package URI 时，确认消费环境与生成 URDF 对 package 根解析方式一致。

不要将生成的 URDF XML 作为网格摆放的事实来源。优先从拥有网格实例摆放的同源数据推导视觉网格引用。

## 碰撞几何

在每个应参与物理或接触的 `<link>` 下添加碰撞几何。不要在 joint 上编码碰撞行为。

每个 link 可使用一个或多个 `<collision>` 块。`<origin>` 在连杆坐标系中表示，与 `<visual>` 相同，且网格缩放必须与导出网格的单位一致：

```xml
<link name="forearm_link">
  <visual>
    <origin xyz="0 0 0" rpy="0 0 0" />
    <geometry>
      <mesh filename="STL/forearm.stl" scale="0.001 0.001 0.001" />
    </geometry>
  </visual>
  <collision>
    <origin xyz="0 0 0" rpy="0 0 0" />
    <geometry>
      <mesh filename="STL/forearm_collision.stl" scale="0.001 0.001 0.001" />
    </geometry>
  </collision>
</link>
```

优先采用简化碰撞几何而非精细视觉网格。从简到繁的可选方案：

- 当 `<box>`、`<cylinder>` 或 `<sphere>` 基本体能较好近似零件时使用。
- 从 CAD 导出的粗糙闭合 STL 碰撞网格。
- 将视觉 STL 作为加载与冒烟测试的临时后备。

在生成器源码中显式建模碰撞，而非手工编辑生成的 URDF。常见做法是在各连杆规格中于 `visuals` 旁增加 `collisions` 集合，并用与视觉网格相同的文件名、原点与缩放辅助代码输出。
