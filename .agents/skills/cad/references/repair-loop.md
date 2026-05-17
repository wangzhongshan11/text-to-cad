# 修复循环

生成、导出、检查、定位、渲染审查、Explorer 启动或文档校验失败时阅读本文。

## 循环

1. 阅读失败命令输出。
2. 对失败分类。
3. 做最小必要源码或命令变更。
4. 重新运行失败命令。
5. 重新运行依赖的校验。
6. 报告剩余风险或有意偏差。

## 失败类型与修复

### 源码导入或语法失败

可能原因：

- Python 语法无效
- 缺少 import
- build123d 符号错误
- 函数未命名为 `gen_step()`
- 预期函数外的可执行代码有副作用

修复：

- 纠正 import 与语法
- 确保 `gen_step()` 返回 STEP 就绪 shape 或 compound
- 输出路径放在 CLI 命令中，勿放在 `gen_step()` 内

### 几何无效或缺失

可能原因：

- 开放草图
- 减材轮廓在 targets 外
- 零厚度
- 布尔失败
- 将构造几何当作导出几何

修复：

- 封闭拟成面的轮廓
- 验证尺寸为正
- 贯通切除时让减材工具穿透
- 简化失败特征并增量重建

### 圆角或倒角失败

可能原因：

- 半径/长度超出局部几何
- 所选边包含微小或非预期边
- 布尔产生复杂边拓扑

修复：

- 减小半径/长度
- 更窄地筛选边
- 在模型更晚阶段应用圆角
- 按特征意图拆分边组

### 比例或包围盒错误

可能原因：

- 单位不一致
- 直径/半径搞错
- 拉伸方向或量错误
- 零件未按假设居中
- 直接导入 STEP 使用意外单位

修复：

- 检查参数值
- 检查 facts 与 planes
- 测量关键尺寸
- 纠正源码尺寸或导入处理

### 特征缺失

可能原因：

- 错误的 `Mode.ADD`/`Mode.SUBTRACT`
- 特征轮廓不在目标内
- 盲孔切割过浅
- 先前操作后选择器变化

修复：

- 确认特征模式
- 贯通切除时增加切削长度
- 检查拓扑或平面
- 重新生成并测量/检查特征专用引用

### 选择器脆弱

可能原因：

- 任意下标选择
- 圆角或布尔后拓扑变化
- 相似面/边无法区分

修复：

- 按轴、平面、位置、法向或已检查引用选择
- 用 `refs --facts --planes --positioning` 重新发现稳定引用
- 必要时添加构造基准或简化操作

### 约束装配求解失败

可能原因：

- 缺少 `ground` 或基准 `fix`
- 仅有贴合约束、缺少平面内 `point_plane_offset`
- 约束互相矛盾（例如既 `contact` 又要求 `plane_distance`）
- 未知 `feature_id` 或 `parts` 键与 `bodies` 不一致
- 初值过差导致求解未收敛

修复：

- 阅读求解报告中的 `hint`、`free`、`conflict`（见下「约束求解工具输出」）
- 仅修改 `constraints` 或 Python 参数，勿改零件 mesh（除非用户要求）
- 为欠约束体补充 `in_plane` x/y、距离或对称类约束
- 必要时添加 `initial_guess`（7 个数：`tx ty tz qx qy qz qw`）
- API 与约束语义见 `constraint-assembly.md`；子链路拆分见 `build123d-modeling.md`

### 约束规模超限

可能原因：

- 单张 `CONSTRAINTS` 超过默认 `max_bodies`（40）或 `max_constraints`（240）
- 体数 ≥ `warn_bodies`（30）触发 `large_assembly` 警告

修复：

- 拆子链路或混合 `Location`（`build123d-modeling.md`）
- 必要时在 spec 中显式放宽：`"limits": {"max_bodies": 48}`（绝对上限 64）

### 约束求解工具输出

| 来源 | 内容 |
|------|------|
| `constraint solve` stdout | 紧凑 report JSON（`status`, `residual_max`, `free`, `rotation_issues`, `hint`, `conflict` 等） |
| `constraint solve` 失败 stderr | 同上完整 report |
| `constraint_assembly` 失败 | `RuntimeError`，消息含 `hint` |
| `examples/constraint/out/<spec>.report.json` | `run_validation.py` 写入的 report |
| `examples/constraint/out/<spec>.transforms.json` | 每体 4×4 变换；排查异常旋转 |
| `report_path=` 参数 | 与 report JSON 同结构 |
| `run_validation.py` 行输出 | `status=… expected=… residual=… ok=…` |

字段定义见 `constraint-assembly.md` 求解报告表。

### 求解 status=ok 但装配几何异常

可能原因：

- **box 竖板**只锁 `axis_z`（求解器现会标 `underconstrained` 并写 `rotation_issues`）
- 单个大 `CONSTRAINTS` 混用本应分区域的 Location 与约束
- `offset` 与 `contact` 高度不一致

修复：

- 读 report 中 `rotation_issues`；或 `out/*.transforms.json`、`inspect refs --positioning`
- box 竖板补 `axis_parallel` 锁 `axis_x` 或 `axis_y`；圆柱销竖直只需 `axis`∥`ground.axis_z`
- 拆子链路（`build123d-modeling.md`）；重新 `scripts/step` 与 `inspect mate`

### 定位或配合不一致（已求解）

可能原因：

- 零件局部原点与 `bodies` 尺寸不一致
- `constraints` 特征引用错误（如 `b1.-z` 与 `base.+z`）
- 非求解件 `transform` 矩阵或 Python 偏置错误
- 对称放置符号错误

修复：

- 检查 `refs --positioning`、`frame`、`mate`
- 改 `CONSTRAINTS`、Python 尺寸，或非求解件在传入前的 `.moved(...)`
- 重新 `scripts/step` 并复测

### Explorer 启动或链接失败

可能原因：

- Node/npm 不可用
- Explorer 应用未构建或无法启动
- 扫描根与假定根不一致
- 返回文件路径不相对于活动扫描根

修复：

- 运行 `npm --prefix explorer run dev:ensure -- --file path/to/model.step`
- 若可用则检查 `EXPLORER_ROOT_DIR`
- 返回最佳文档化链接格式
- 若仍未解决则报告启动失败
- 依赖 CLI facts/测量做校验

### 渲染失败

可能原因：

- 尝试渲染 Python 源码、STL 或 3MF
- 目标路径错误
- Explorer/相邻渲染产物缺失
- 渲染标志无效

修复：

- 先生成 STEP
- 渲染 STEP/STP、CAD 路径、生成 GLB/拓扑产物或 `@cad[...]` 引用
- 高级线框/剖视前先用简单 `render view`
- 若校验不需要则跳过渲染

## 修复后 diff

若修复可能影响无关几何，使用 `diff`：

```bash
python scripts/inspect diff path/to/before.step path/to/after.step --planes
```

## 报告无法修复的检查

若某检查在当前环境无法修复，报告：

```text
- what failed
- what was tried
- which artifact is still usable
- which validation claims cannot be made
- what the next source-level correction should be
```

### 配合检查与源码不一致

可能原因：

- `ground` / `fix` 与意图不符
- `parts` 键与 `bodies` 不一致
- 将 CLI `inspect mate` 增量误当作可写约束

修复：

- 对受影响实例检查 `refs --positioning` 与 `frame`
- 改 `CONSTRAINTS` 或 `constraint_assembly` 的 `parts`
- 重新 `scripts/step`，再跑失败的 `measure` 或 `mate`
