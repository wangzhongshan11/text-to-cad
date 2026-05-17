# 检查与校验

对每个生成 STEP 产物，以及用户请求几何 facts、引用、尺寸、配合、diff 或 frame 检查时阅读本文。

## 原则

以程序化几何检查作为校验事实来源。CAD Explorer 与渲染用于视觉审查，不能替代测量、facts、planes、标签或定位检查。

## 工具

入口位于 CAD 技能目录：

```bash
python scripts/inspect {refs|diff|frame|measure|mate|worker|batch} ...
```

检查目标除绝对路径外从命令 cwd 解析。选择从工作区根还是 skill 目录运行时，使 `SKILL.md` 中的根模型保持明确。

多数非渲染命令的常见数据输出标志：

- `--format json|text`；默认为机器可读输出。
- `--quiet`
- `--verbose`

可接受目标形式：

```text
@cad[path/to/entry#selector]
path/to/entry
path/to/entry.step
```

## 与约束装配的关系

多零件 box/cylinder/sphere 摆放由 `constraint_assembly` 在 `gen_step()` 内求解并写入返回的 `Compound`。CLI `inspect mate` 只读验证导出 STEP。配合失败时改 `CONSTRAINTS` 或 Python 尺寸，见 `constraint-assembly.md` 与 `positioning.md`。

约束求解阶段 JSON（`status`、`hint`、`transforms` 等）不是 `inspect` 输出；见 `repair-loop.md`「约束求解工具输出」。生成后几何反馈以本节 `refs` / `measure` / `mate` 为准。

## 校验层级

默认校验顺序：

1. 生成完成且 STEP/STP 文件存在。
2. `refs --facts --planes --positioning` 确认比例、标签、主要平面与可用于放置的引用。
3. `measure` 确认关键尺寸与偏置。
4. `mate` 确认装配接口或引用间定位的只读对齐增量。
5. `frame` 确认实例或所选引用的世界坐标系。
6. `diff` 在修改前后对比几何。
7. 返回 CAD Explorer 链接供人工审查。
8. 仅当能回答校验问题或 Explorer 不可用时使用 `scripts/render`。

## 引用发现

紧凑 facts 与平面：

```bash
python scripts/inspect refs path/to/model.step \
  --facts --planes --positioning
```

详细选择器检查：

```bash
python scripts/inspect refs '@cad[path/to/model.step#selector]' \
  --detail --positioning
```

拓扑枚举，仅在需要时：

```bash
python scripts/inspect refs path/to/model.step --topology
```

平面选项：

```bash
--plane-coordinate-tolerance FLOAT
--plane-min-area-ratio FLOAT
--plane-limit INT
```

常规校验使用较低平面限制与紧凑 facts。拓扑枚举仅用于选择器发现、复杂调试或无法通过 facts/planes/测量验证的特征。

## 测量检查

对包围距离、间隙、偏置、零件间距、板厚、孔到面距离与对齐验证使用 `measure`。

```bash
python scripts/inspect measure \
  --from '@cad[path/to/model.step#selector_a]' \
  --to '@cad[path/to/model.step#selector_b]' \
  --axis x
```

轴在可能时推断，为确定性检查请指定 `x`、`y` 或 `z`。

## 配合检查

当两个导出 STEP 引用应贴合或居中时使用 CLI `mate`。它返回只读平移增量；不编辑源码。约束装配与显式 `transform` 装配均用 `refs --positioning`、`frame`、`measure`、`mate` 校验导出几何。

```bash
python scripts/inspect mate \
  --moving '@cad[path/to/assembly.step#moving_selector]' \
  --target '@cad[path/to/assembly.step#target_selector]' \
  --mode flush \
  --axis z
```

所需修正应在 Python 源码中通过 `CONSTRAINTS`、`constraint_assembly` 的 `parts`、或零件尺寸与局部 `Location` 完成。重新 `scripts/step` 并重新检查。

## Frame 检查

用 `frame` 校验实例变换与所选引用的世界坐标系：

```bash
python scripts/inspect frame '@cad[path/to/model.step#selector]'
```

Frame 输出对装配体、零件局部到世界转换与放置调试有用。

## Diff 检查

对修改任务，对比前后产物：

```bash
python scripts/inspect diff path/to/before.step path/to/after.step --planes
```

在修复、增特征或源码编辑可能影响无关几何时使用 diff。

## CAD Explorer 链接

涉及 STEP/STP 产物的每次最终回复，在可能时返回 CAD Explorer 链接。启动、扫描根与链接格式见 `rendering-and-explorer.md`。若检查了重要选择器，在所属 Explorer 链接旁返回文本 `@cad[...]` 引用。

## 校验报告内容

仅报告实际已运行或由工具输出直接支持的检查。

使用以下结构：

```text
Validation:
- STEP generation: passed/partial/failed
- Solids/assembly: <counts and labels>
- Bounding box: <dimensions and units>
- Major planes/refs: <summary>
- Positioning: <frame/measure/mate results if relevant>
- Feature checks: <holes, cutouts, bosses, etc.>
- Visual review: Explorer link returned; render run/not run and why
```

勿声称：

- 结构安全性
- 工艺认证
- 公差合规
- 超出几何合理性的可制造性

除非已明确执行相关分析或制造数据。
