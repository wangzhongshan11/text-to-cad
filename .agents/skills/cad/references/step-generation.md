# STEP 生成

从 build123d Python 源码或直接 STEP/STP 目标生成或重新生成 STEP/STP 产物时阅读本文。

## 工具

入口位于 CAD 技能目录：

```bash
python scripts/step [--kind {part|assembly}] targets... [flags]
```

仅使用明确目标路径。目标路径除绝对路径外从命令 cwd 解析。从工作区根运行时须在路径前加 CAD 技能目录；从技能目录运行时传入绝对或正确相对的工作区目标路径。勿依赖目录级批量生成。

## 生成的 Python 源码

生成的 build123d 源码应定义：

```python
def gen_step():
    ...
    return shape_or_compound
```

多零件 box/cylinder/sphere 约束装配：`return constraint_assembly(CONSTRAINTS, parts)`（返回值仍是 `shape_or_compound`）。见 `constraint-assembly.md`。

生成的 Python 目标根据其源码元数据与 `gen_step()` 返回值推断 kind；直接传入源码路径。存在生成器时，此为运行 `scripts/step` 的首选方式。

```bash
# macOS / Linux（仓库根目录）
./.venv/bin/python .agents/skills/cad/scripts/step path/to/model.py
./.venv/bin/python .agents/skills/cad/scripts/inspect refs path/to/model.step --facts --planes --positioning

# Windows（仓库根目录）
.\.venv\Scripts\python.exe .agents\skills\cad\scripts\step path\to\model.py
.\.venv\Scripts\python.exe .agents\skills\cad\scripts\inspect refs path\to\model.step --facts --planes --positioning
```

直接传入已生成的装配体 `.step` 会将其视为导入的原生 STEP。若须保留源码级装配组合，请传入 `.py` 装配源码。

## 直接 STEP/STP 目标

仅当生成器不可用或用户明确将某 STEP/STP 文件指定为目标时使用直接目标：

```bash
python scripts/step --kind part path/to/imported.step
python scripts/inspect refs path/to/imported.step --facts --planes --positioning
```

直接目标可使用 sidecar mesh 相关标志，但存在生成器时仍以生成器优先。STL 与 3MF sidecar 见 `supported-exports.md`。

## 相邻 Explorer 产物

`scripts/step` 生成明确 STEP 目标及相邻隐藏 Explorer GLB/拓扑产物。它们支持 Explorer 与渲染工作流。勿为其单独要求校验子命令。

Explorer 启动与链接格式见 `rendering-and-explorer.md`。

## 生成后检查

生成后用 `scripts/inspect` 做轻量检查。

规则：

- 常规生成使用 facts 与平面分组。
- 若模型有配合面、装配子项、基准或重复特征，加入 positioning facts。
- 仅在选择器枚举需要时加入拓扑；大模型上可能较昂贵。

推荐检查：

```bash
python scripts/inspect refs path/to/model.step --facts --planes --positioning
```

偏重选择器的校验：

```bash
python scripts/inspect refs path/to/model.step --topology
```

## 生成清单

运行命令前：

- 确认用户请求已转为自然语言 CAD 简报。
- 确认源码定义了 `gen_step()`。
- 若 Python 生成器与已生成 STEP/STP 同时存在，优先 Python 生成器。
- 确认已为导出零件与装配子项分配标签。
- 确认目标路径明确。
- 确认预期 bbox、标签与定位检查已知。

运行命令后：

- 确认进程成功。
- 确认 STEP 文件存在且非空。
- 运行相应 `scripts/inspect` 命令并解析输出。
- 按 `rendering-and-explorer.md` 返回 Explorer 链接，或说明不可用原因。
- 若 facts/planes 不足，继续定向检查。
