# 渲染与 CAD Explorer 审查

需要 CAD Explorer 链接、视觉审查有用、用户要求截图/预览，或程序化 facts 需视觉确认时阅读本文。

## 策略

在可能时始终为相关 STEP/STP 产物返回 CAD Explorer 链接。勿总是生成图像。渲染为条件触发，因其成本高于几何检查。

仅在以下情况使用渲染：

- 用户明确要求图像、截图、预览、剖视或线框
- 当前环境无法启动或访问 CAD Explorer
- 智能体需要视觉证据消除歧义
- 隐藏/内部特征需剖视或线框审查
- 程序化 facts 无法确认形状意图
- 复杂装配需快速视觉自检且 Explorer 不足

勿将渲染作为尺寸、拓扑、标签、间隙或配合检查的唯一校验手段。

## CAD Explorer

为智能体工作流启动 Explorer：

```bash
npm --prefix explorer run dev:ensure -- --file path/to/model.step
```

该命令形态相对于 CAD 技能目录。`dev:ensure` 探测本地 CAD Explorer 开发服务器，当其扫描根与请求工作区/根一致时复用，否则在配置端口范围内首个空闲端口启动新 Vite 开发服务器。使用该命令打印的 URL 作为最终 Explorer 链接；勿假定端口为 `5180`。

前台手动 Vite 开发使用：

```bash
npm --prefix explorer run dev
```

重要环境变量：

```text
EXPLORER_PORT              default 5180
EXPLORER_PORT_END          dev:ensure default 5200
EXPLORER_ROOT_DIR          scan subdirectory; empty means the inferred workspace root
EXPLORER_DEFAULT_FILE      scan-root-relative file opened when no ?file= is supplied
EXPLORER_GITHUB_URL
EXPLORER_WORKSPACE_ROOT
EXPLORER_ROBOT_MOTION_WS_URL
```

Explorer 链接命令：

```text
npm --prefix explorer run dev:ensure -- --file <path-relative-to-active-scan-root-with-extension>
```

若 STEP 文件为 `models/mounting_plate.step` 且活动扫描根为工作区根：

```text
npm --prefix explorer run dev:ensure -- --file models/mounting_plate.step
```

若所检查选择器重要，在 Explorer 链接旁包含其文本引用：

```text
Explorer: http://127.0.0.1:5180/?file=models/mounting_plate.step
Key ref: @cad[models/mounting_plate.step#<selector>]
```

除非环境文档说明，勿臆造选择器专用 URL 参数。使用文档化的文件链接格式并附带文本 `@cad[...]` 引用。

## 渲染工具

```bash
python scripts/render {view|orbit|wireframe|section|list} ...
```

支持的渲染输入：

- `.step`, `.stp`
- STEP 工具生成的相邻隐藏 GLB/拓扑产物
- CAD 路径
- `@cad[...]` 引用

拒绝的输入：

- Python 生成器
- STL
- 3MF

先生成 STEP，再渲染 STEP/STP、CAD 路径、生成 GLB/拓扑产物或支持的 CAD 引用。

STEP 渲染使用与源码几何相同的 CAD 坐标约定：正 Z 为上。预设相机、自定义 `azimuth:elevation` 相机、坐标轴叠加与 CAD Explorer 地面/网格放置不应要求仅为 Explorer 旋转 STEP 或其包内 GLB sidecar。

`view` 与 `wireframe` 通过 Python Playwright 使用 Playwright 管理的 Chromium，经温热本地渲染守护进程。首次渲染自动启动守护进程并承担浏览器启动成本；后续渲染复用浏览器，通常更快。守护进程在大约空闲 10 分钟或 100 个任务后退出。若活动 CAD Python 环境未安装 Chromium，运行：

```bash
python -m playwright install chromium
```

有用守护进程诊断：

```bash
python scripts/render daemon status
python scripts/render daemon stop
```

仅在渲染调试或测试需要显式一次性 Playwright 运行时使用 `--no-daemon`。

## 渲染命令

当前标志见子命令帮助：

```bash
python scripts/render view --help
python scripts/render orbit --help
python scripts/render wireframe --help
python scripts/render section --help
python scripts/render list --help
```

常见相机包括 `front`、`back`、`left`、`right`、`top`、`bottom`、`iso`，或 `azimuth:elevation[:distance]`。

Explorer 不可用时用 `view` 做显式视觉审查或回退：

```bash
python scripts/render view path/to/model.step \
  --output path/to/model_iso.png \
  --camera iso \
  --preset technical \
  --edges thin
```

用户要循环 GIF 或转盘式视觉时使用 `orbit`：

```bash
python scripts/render orbit path/to/model.step \
  --output path/to/model_orbit.gif \
  --quality standard
```

Orbit GIF 复用浏览器渲染守护进程，从单次加载场景渲染所有帧。质量档控制默认尺寸、帧数与超采样；`very-high` 使用更重 3x 超采样，可能较慢或生成大 GIF。用 `--start-azimuth`、`--elevation`、`--turns`、`--duration-seconds`、`--fps` 或 `--frames` 覆盖运动。v1 中 GIF 导出仅为不透明背景。

隐藏边、实体重叠或装配分离重要时使用 `wireframe`：

```bash
python scripts/render wireframe path/to/model.step \
  --output path/to/model_wire.png \
  --camera iso \
  --hidden-lines faint
```

内部特征、空心零件、槽、孔及被遮挡接口使用 `section`：

```bash
python scripts/render section path/to/model.step \
  --output path/to/model_section.png \
  --plane YZ \
  --offset 0
```

输入存在歧义时使用 `list`：

```bash
python scripts/render list path/to/model.step --format json
```

## 报告视觉审查

如实报告视觉审查：

```text
Visual review: Explorer link returned; no image render generated because geometric validation passed and no visual ambiguity was present.
```

或：

```text
Visual review: Explorer startup failed; generated a lightweight iso render as fallback.
```

或：

```text
Visual review: section render generated to confirm the internal bore and lid/base overlap.
```
