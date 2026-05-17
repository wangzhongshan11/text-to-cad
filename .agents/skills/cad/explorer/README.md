# CAD Explorer

若你在修改 CAD Explorer，从这里开始。

本文件夹包含 CAD Explorer Web 应用。CAD Explorer 对活动 CAD 扫描目录中的文件为只读。

## 提示词工作流

- CAD Explorer 通过扫描 `EXPLORER_ROOT_DIR` 发现可显示条目，未设置或为空时默认为 Vite 进程的当前工作目录，并从该树加载包内渲染资源及生成 URDF/编写的 DXF XML/文本。
- 面向提示词的 `@cad[...]` 引用应为工作区输出。可接受的 CLI 检查形式摘要见 [检查与校验](../references/inspection-and-validation.md)。
- 常见复制引用形态包括整条目、实例、形状/面/边选择器及同实例分组选择器，例如 `@cad[<workspace-relative-cad-path>]`、`@cad[<workspace-relative-cad-path>#o1.2]`、`@cad[<workspace-relative-cad-path>#f12]`、`@cad[<workspace-relative-cad-path>#o1.2.f12,f13,e7]`。
- `@cad[...]` 内路径相对于 Vite 进程当前工作目录，省略 `.step` 或 `.stp`。
- 生成装配视图首先加载嵌入的装配拓扑索引；STEP 生成也在同一 GLB 中嵌入完整面与边选择器拓扑。
- 绘图工具与截图为沟通辅助，非事实来源。
- 解释 `@cad[...]` 引用的智能体应通过 `python scripts/inspect refs` 解析，其读取生成的包内 GLB STEP 拓扑并对照源 STEP 哈希校验。

## 数据模型

- CAD Explorer 通过扫描现有 `.step`、`.stp`、`.stl`、`.3mf`、`.dxf`、`.urdf` 文件发现条目，不对 Python 生成器做发现。
- STEP 零件条目加载：
  - 包内 `<cad-dir>/.../.<step-filename>.glb` 用于显示与嵌入选择器拓扑
- STEP 装配条目需要包内 `<cad-dir>/.../.<step-filename>.glb`，并从 GLB 根 glTF 扩展下嵌入的 `STEP_topology` 索引中 `assembly.root` 读取装配组合。装配拓扑将 `assembly.mesh` 指向同一 GLB，并把 GLTF 节点 `extras.cadOccurrenceId` 映射到实例 id。
  - 当前拓扑 schema v1 以根 glTF 扩展 `STEP_topology` 嵌入 GLB；生成写入 `{ schemaVersion, entryKind, indexView, selectorView, encoding }`；`indexView` 为小型装配/实例清单，`selectorView` 保存详细形状、面与边选择器行。
  - 面选择与填充通过紧凑面 run 记录映射到 GLB 三角形。边与面/边关系缓冲区存为选择器清单引用的类型化 GLB buffer views。
- 包内 STEP GLB 产物为源 STEP 的渲染代理。保持 STEP/CAD 坐标约定：毫米缩放到 glTF 单位，正 Z 向上，资源中不烘焙 Y-up 查看旋转。
- DXF 条目加载：
  - 直接加载编写 `<cad-dir>/.../*.dxf`
- STL 条目加载：
  - 直接加载独立或配置导出的 `<cad-dir>/.../*.stl` 网格
- 3MF 条目加载：
  - 直接加载独立或配置导出的 `<cad-dir>/.../*.3mf` 网格
- URDF 条目加载：
  - 直接加载生成 `<cad-dir>/.../*.urdf` XML
  - 直接加载 URDF 引用的 STL 网格文件名
  - 可选包内 `<cad-dir>/.../.<urdf-filename>/explorer.json` 元数据用于默认值与姿态
  - 可选包内 `<cad-dir>/.../.<urdf-filename>/robot-motion/explorer.json` 元数据用于本地运动服务器命令
- CAD Explorer UI 位于 `components/CadExplorer.js`。
- 展平图 Explorer UI 位于 `components/DxfExplorer.js`。
- 工作区 UI 位于 `components/CadWorkspace.js`。

常规 CAD 或 CAD Explorer 工作中勿手改包内生成 CAD 资源。

## 持久化

- CAD Explorer 持久化仅在浏览器内，由 `lib/workbench/persistence.js` 负责。
- URL 查询参数共享状态：
  - `?file=` 选择活动 CAD 条目。
  - `?refs=` 将提示引用带入工作区。
  - `?resetPersistence=1` 清除当前源的 CAD Explorer 浏览器状态，随后在应用渲染前从 URL 移除。
- `EXPLORER_DEFAULT_FILE` 在无 `?file=` 时选择默认 CAD 条目。文件缺失时仍保留显式 `?file=` URL，以便工作区显示缺失文件界面。
- `sessionStorage` 键 `cad-explorer:workbench-session:v2` 以规范形态 `{ version, global, tabs: { selectedKey, openOrder, byKey } }` 存储草稿工作区，包含搜索查询、展开目录、统一侧栏/表单打开状态及当前浏览器标签的工具宽度。
- `localStorage` 键 `cad-explorer:workbench-global:v1` 为旧版工作区持久化的仅清理状态，不应再写入新布局。
- `localStorage` 键 `cad-explorer:look-settings` 存储视觉外观设置，`cad-explorer:workbench-glass-tone:v1` 存储工作区玻璃色调，`cad-explorer-theme` 存储强制暗色主题偏好。
- `sessionStorage` 键 `cad-explorer:dxf-bend-overrides:v1` 存储当前浏览器标签下每文件 DXF 弯折覆盖。
- 目录展开不再有单独文件浏览器存储键；其为工作区会话状态的一部分。
- React 状态立即更新。浏览器存储写入短暂合并并在 `pagehide`、`beforeunload` 与工作区卸载时刷新。若存储被阻止或已满则工作区显示状态提示。

## 运行时

- `npm run dev` 启动 `vite dev`，相对推断工作区根扫描 `EXPLORER_ROOT_DIR`，并在匹配 CAD 文件或每 STEP CAD Explorer 资源增删改时更新工作区。开发服务器使用 Vite `strictPort`；若配置端口已被占用，启动报告冲突而非换端口。
- `npm run dev:ensure -- --file path/to/model.step` 通过 `GET /__cad/server` 探测本地 CAD Explorer 开发服务器，当其活动扫描根与请求根一致时复用，否则从 `EXPLORER_PORT` 至 `EXPLORER_PORT_END`（默认 `5180-5200`）首个空闲端口启动新 Vite 开发服务器，并打印该文件应使用的 Explorer URL。
- `GET /__cad/server` 为仅开发环境身份端点，返回进程/根元数据，不扫描 CAD 文件。
- `EXPLORER_DEFAULT_FILE` 可设为扫描根相对文件路径（含扩展），在 URL 无 `?file=` 时默认打开该条目。
- `EXPLORER_GITHUB_URL` 设置顶栏 GitHub 按钮目标，默认 `https://github.com/earthtojake/text-to-cad`。
- URDF CAD Explorer 默认值与姿态从 `.<urdf>/explorer.json` 加载。仅在本地 Vite 开发中，IK 与路径规划控件从可选 `.<urdf>/robot-motion/explorer.json` 加载，并使用单独启动的本地运动 WebSocket 服务器。Vite 永不启动 Python 或 ROS。
- 本地 Vite 开发中，浏览器在设置时使用 `EXPLORER_ROBOT_MOTION_WS_URL`，否则 `ws://127.0.0.1:8765/ws`；`?motionWs=` 可覆盖单次浏览器会话 WebSocket URL。生产构建禁用运动服务器连接。
- 用 robot-motion 技能中的 `scripts/run-motion-server.sh` 启动运动服务器。纯 URDF 条目从不联系运动服务器。
- `npm run build` 扫描 `EXPLORER_ROOT_DIR`，未设置或为空时默认为推断工作区根，并将该扫描烘焙进静态应用。
- 生产构建在构建时读取 `EXPLORER_DEFAULT_FILE`、`EXPLORER_GITHUB_URL`、`EXPLORER_ROOT_DIR`、`EXPLORER_WORKSPACE_ROOT`。若从 `explorer` 运行构建命令，CAD Explorer 回退到上一级工作区根；部署从不同目录布局构建时请显式设置 `EXPLORER_WORKSPACE_ROOT=/path/to/workspace`。
- CAD 资源需变更时，在这些命令之外单独重新生成 CAD 资源。
- STEP 查看器相机、地面/网格、视图立方体与渲染相机预设均为 Z-up。若模型看起来旋转，请修正显示/运行时约定或有意修正源几何；勿仅为 Explorer 旋转生成 STEP/GLB sidecar 作补偿。

## 热更新

- 实时开发更新来自 Vite CAD 目录端点与 WebSocket 事件，而非浏览器轮询。
- 外部工具在活动扫描目录下增删改 `.step`、`.stp`、`.stl`、`.3mf`、`.dxf`、`.urdf`、`.<step-filename>.glb` 或 URDF CAD Explorer 元数据文件时，Vite 请求客户端重新扫描并重新挂载工作区。

## 用户体验约定

- 启用 STEP 选择器的条目从可见 GLB 三角形暴露面选择，从选择器代理几何暴露边选择。
- 形状与实例引用通过检查器状态暴露，无单独画布拾取模式。
- DXF 条目为只读展平图视图。
- URDF 条目为带关节滑块的只读机器人视图；带 robot-motion 元数据且本地运动服务器在线的条目可能暴露姿态求解或路径规划控件。它们不提供拾取、引用或绘图工具。
- 文件选择器使用规范后缀标签：STEP 零件与装配显示 `.step`，STL 显示 `.stl`，3MF 显示 `.3mf`，URDF 显示 `.urdf`，DXF 显示 `.dxf`。
- 工作区一次选择一个文件。再次选择文件时，每文件视图、引用、绘图与工具状态仍从现有会话 `tabs` 状态恢复。
- 侧栏分组严格遵循活动扫描目录下目录结构，非硬编码零件/装配根。

## CAD Explorer 变更的验证

- 纯 CAD Explorer 变更运行 `cd explorer && npm run test && npm run build`。
- 变更触及 explorer 逻辑、解析、持久化、目录扫描、选择器或运动学时运行 `cd explorer && npm run test`。
- 当需要当前生成 CAD 状态常规生产 `dist/` 输出时，从希望扫描的工作区运行 `npm --prefix explorer exec vite -- build --config explorer/vite.config.mjs`。
- 若依赖全新 CAD 派生产物，在 explorer 验证前用 `python scripts/step`、`python scripts/dxf` 或 URDF 技能中的 `scripts/gen_urdf/cli.py` 单独重新生成受影响条目。
- 对渲染约定变更，检查相关包内 `.<step-filename>.glb`、可见 `.stl`、可见 `.3mf`、可见 `.dxf` 或可见 `.urdf` 文件。

## 运行

从 CAD 技能目录：

```bash
npm --prefix explorer install
npm --prefix explorer run dev
```

然后打开：

- `http://localhost:5180`

根感知智能体启动：

```bash
npm --prefix explorer run dev:ensure -- --file path/to/model.step
```

然后打开命令打印的 URL。
