# URDF 生成器约定

在创建或编辑用于生成 URDF 文件的 Python 源码时使用本文。

## 事实来源

定义 `gen_urdf()` 的 Python 源码为事实来源。配置生成的 `.urdf` 文件为生成产物，不应手工编辑。

## 封装约定

`gen_urdf()` 须为顶层零参数函数，返回包含以下内容的封装：

- `xml`：完整的 URDF XML 字符串
- `urdf_output`：生成的 `.urdf` 文件的相对路径
- `explorer_metadata`（可选）：可 JSON 序列化的对象，写入 `.<urdf filename>/explorer.json`，用于不应嵌入标准 URDF XML 的面向消费者元数据

`urdf_output` 路径：

- 相对于所属的 Python 源码
- 必须使用 POSIX `/` 分隔符
- 必须以 `.urdf` 结尾
- 解析为文件路径，不经过 harness 根目录

宿主项目可自定目录布局策略，但 URDF 技能运行时不会硬编码项目目录。

## 运行时行为

`scripts/gen_urdf/cli.py` 仅运行 `gen_urdf()`。不会重新生成外部 CAD、网格/导出、GLB/拓扑或渲染产物。

若 URDF 视觉或碰撞网格引用依赖已更新的 CAD 或网格输出，请用所属的 CAD 或网格工作流单独重新生成那些明确的目标。
