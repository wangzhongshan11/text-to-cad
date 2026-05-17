# 支持的导出格式

用户要求从 CAD 几何导出 STL 或 3MF 时阅读本文。DXF 输出见 `dxf.md`，因其使用单独的 `gen_dxf()` 源码约定。

## 策略

STL 与 3MF 是网格 sidecar，不能替代 STEP。先生成并校验 STEP，然后在同一次 `scripts/step` 运行中导出所请求的 sidecar。勿直接渲染 STL 或 3MF；需要视觉审查时应渲染或检查 STEP。

## 工具

对已生成的 Python 源码使用 `scripts/step`：

```bash
python scripts/step path/to/model.py \
  --stl meshes/model.stl \
  --3mf meshes/model.3mf
```

存在生成器时使用生成器形式。仅在生成器不可用或用户明确将该文件指定为目标时使用直接 STEP/STP：

```bash
python scripts/step --kind part path/to/model.step \
  --stl meshes/model.stl \
  --3mf meshes/model.3mf
```

Sidecar 路径须为相对的 `.stl` 或 `.3mf` 路径，并在 STEP 输出旁解析。

## 网格容差

默认网格密度不合适时使用：

```bash
--mesh-tolerance FLOAT
--mesh-angular-tolerance FLOAT
```

小曲面零件或视觉保真需要更紧容差。大且简单几何在文件体积重要时可放宽。

## 工作流

1. 用 `gen_step()` 与请求的 sidecar 标志生成 STEP。
2. 对 STEP 运行 facts/planes/positioning 检查。
3. 返回 STEP、所请求 sidecar 文件及 CAD Explorer 链接。

示例：

```bash
python scripts/step models/bracket.py \
  --stl meshes/bracket.stl \
  --mesh-tolerance 0.2 \
  --mesh-angular-tolerance 0.2

python scripts/inspect refs models/bracket.step --facts --planes --positioning
```

## 报告

```text
Files:
- STEP: models/bracket.step
- STL: meshes/bracket.stl

CAD Explorer:
- http://127.0.0.1:5180/?file=models/bracket.step

Validation:
- STEP geometry validated; STL/3MF generated as requested sidecars.
- Render not run unless requested or needed.
```
