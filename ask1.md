。

超超超深入分析下如果要求绝大部分用约束实现，效果如何？和位置堆砌相比呢？当前约束机制还有优化的空间吗？

结论先说： 若强制「绝大部分用约束」——在当前实现下，对 transformers_robot 这类 ~48 件的块状人形，数学上勉强能塞进去，工程上明显劣于混合/堆砌；造型、像不像、一次生成合理几乎不会变好，反而在规模、求解、Authoring、可维护性上全面变差。约束机制还有很大优化空间，但优化方向应是「让该用约束的地方更好用」，而不是「把所有 Location 硬改成约束」。

1. 先量化：「绝大部分约束」对 transformers_robot 意味着什么
现状	若 ~90% 约束化
约束：7 体（platform + 6 轮）	~44 体进 bodies（trim + 全身块）
Location：~41 件	仅剩极少数或 0
约束条数：~36	粗估 220–320（每件 5–7 条：贴面 + 高 + 面内 x/y + 三轴平行）
默认上限	40 体 / 240 约束 → 必须 limits 提到接近 64 / 400 绝对顶
优化变量	7×6≈42 维（除 ground）
上身与底盘关系	z0 = PLATFORM_TOP_Z 公式
求解报告里已有 dof_deficit: 7（仅 7 体底盘）——说明即使用小图，零空间也不为空；放大到 48 体后，欠约束 / 假 ok / 初值敏感 只会更严重。

上身件虽全是无旋转的 Location（只平移），理论上可用「父顶面 + in_plane + axis_parallel」逐件钉死；但臂/腿在 X/Y 上大偏移（例如 sign*170），每件都要对 父件顶面切向 写 in_plane，不能再用「相对 ground 的 (x,y)」偷懒——Authoring 量接近 手工写 40 份小型 spec。

2. 效果预期：和 Location 堆砌逐项对比
2.1 几何正确性（配合 / 残差）
维度	纯 Location	绝大部分约束（现状求解器）
轴对齐、贴面、轮位	公式错就错，无自动验	contact + offset + axis_parallel + report
绕 Z 空转（竖板）	以前可「看起来 ok」	rotation_issues / missing_in_plane_axis_lock
非轴对齐配合（斜肩、铰链）	Location+欧拉角即可（若支持）	需 plane_coincident / axis_coaxial / point_coincident 组合；无「相对父件位移」语法糖
过约束 / 冲突	无概念	非线性最小二乘，可能 solve_failed / 局部极小
与 parts 尺寸一致	一处 Python 即可	bodies.size 与 _box() 必须双份维护
判断： 在 重复、对称、接地（轮、柱阵、围板）上约束更稳；在 长链、大偏移、装饰件 上，约束不自动更对，只是换了一种写法。

2.2 一次生成 / 合理造型（你关心的「像不像」）
维度	Location	绝大部分约束
语义（机器人 vs 叉车）	由 Agent 写坐标决定	完全相同——约束不编码语义
视觉验收	需看图 / render	同样需看图
LLM 写错时	偏一个数 → 歪一块	可能 solve 失败 或 ok 但另一套等价解
迭代修复	改 (x,y,z)	改 JSON + 可能改 initial_guess + 读 report
判断： 提高约束占比 不会 减少「二次看图」；最多把部分错误从「肉眼发现」变成「solve 报错」——对造型帮助有限。

2.3 开发与运行成本
pin_grid_4x4:  17 体, ~64 约束  → 全约束的「甜区」上限附近
wardrobe 围板:  5 体,  约束有意义（防旋转）
transformers 若 48 体:  超默认 40；Jacobian 数值差分；MAX_NFEV=4000
初值：_initial_poses 把非 ground 体沿 Z 叠一串 (0,0,z)——对「双臂外展、头前移」极差的初值，易陷局部极小（solver.py 里 TRF + 数值 Jacobian）。
性能：numeric_jacobian 对每个自由度做有限差分；329 维 × 数百残差 × 数千 nfev → 比写 41 次 Location 慢几个数量级。
Agent token：41 件 × 6 条约束 ≈ 250 行 JSON，且 feature 引用易错（chest.+z vs waist.+z）。
2.4 可维护性 / 改参
场景	Location	约束
平台加高 20mm	改 PLATFORM_TOP_Z 链式公式	改 platform 尺寸 + 所有 offset + 可能重 solve
轮距加宽	改 WHEEL_X	改 in_plane value（尚可）
手臂外展角度	改几个 Location	需改父面 in_plane 或引入旋转自由度
3. 分场景：什么时候「绝大部分约束」值得 / 不值得
值得（甚至应全约束）
柱阵 / 钉板（pin_grid_4x4）：重复模式、件数 17、关系同质。
围板壳体（wardrobe 5 体）：贴底 + 竖板姿态 + 必须防绕 Z 转。
底盘四轮 + 接地（AGV / optimus / transformers 底盘）：4–6 体，spec 可回归。
不值得（应 Location 或公式）
人形上身、机械臂链、叉车门架上的 20+ 装饰——关系是「设计坐标」，不是「未知配合」。
阵列层板（衣柜 interior）——公式 for z in (...) 比 N 套约束短一个数量级。
>30 体且互不 mating 的「摆造型」——约束只是在解 已知布局，没有自由度需求。
黄金比例（与仓库文档一致）
约束：区域内、少件、重复 mating、要防旋转
Location：区域内阵列、长链造型、区域间已合并的 Compound
transformers_robot 的 7/48 ≈ 15% 约束占比，从问题性质看 接近合理；若拉到 90%，是 用错工具，不是「更高级」。

4. 若硬做 90% 约束，实际会遇到的机制墙
4.1 规模与策略硬顶

limits.py
Lines 8-12
DEFAULT_MAX_BODIES = 40
WARN_BODIES = 30
DEFAULT_MAX_CONSTRAINTS = 240
ABSOLUTE_MAX_BODIES = 64
ABSOLUTE_MAX_CONSTRAINTS = 400
transformers 全约束 → 触发 large_assembly 警告 + 顶格 limits。
再做大（整机 60+ 件）→ 必须拆图，不能「一张 CONSTRAINTS」。
4.2 求解器能力边界
状态：每体 7 维（平移 + 四元数），全局非线性最小二乘。
无 2D 草图式双向约束传播；无 装配树自顶向下「先解父再解子」。
point_plane_offset 的 in_plane 沿参考平面切向（plane.tangent_axes()）——对 ground 好；对 已倾斜父件 可用但 Authoring 难。
缺少：stack_on(parent, dx,dy,dz)、mate_face_to_face 宏、distance_along_axis、软约束/优先级、只平移不旋转模式（块状件常用）。
4.3 「假 ok」与审计
status=ok 要求：残差小 + 无 rotation_issues + 平移自由体 <2 等（solver.py）。
仍可能出现：等价解、轮子在平台上方（contact 贴 platform.+z 顶面而非接地）、造型离谱但约束满足。
transformers 轮只锁 axis_z + axis_x（未锁 axis_y）——比 AGV 松，靠对称盒勉强唯一。
4.4 LLM 一次生成
约束路径多一步 不可见的求解：

写 CONSTRAINTS → solve → 读 report → 改约束 → 再 solve → 再 gen_step
比 Location 多 1–3 轮；且 report 不告诉你「不像机器人」。
绝大部分约束不会提高一次成功率，只会提高 「solve 失败率」 或 JSON 语法错误率。

5. 和 Location 相比的总表（超深入版）
层级	Location 堆砌	绝大部分约束
问题本质	直接编码布局（已知自由度=0）	解几何方程（假装未知，其实已知）
信息量	N 个 (x,y,z) 或公式	N 组 mating 关系；冗余度高
验证	inspect 量 bbox/mate	solve report + inspect
失败模式	静默错位	显性 solve_failed / underconstrained
造型/语义	不保证	同样不保证
规模	几乎无限件	40/64 体、240/400 约束
性能	O(N) 放置	O(nfev × dim × 残差) 数值优化
Agent 难度	中（算术）	高（几何+词汇+初值）
改参	改常量链	改 spec + 可能改初值
适合 harness 回归	弱（无标准 report）	强（run_validation.py）
一句话：

约束 = 用求解器做 「配合验证器 + 少量自由度求解」；
Location = 「参数化布置」。
把已知布局硬塞进求解器，等于 用搜索代替赋值，没有免费午餐。
6. 当前约束机制：优化空间（按性价比排序）
P0 — 明显短板，改完投入产出高
stack_on / mate_box_on_plane 语法糖
生成 contact + offset + in_plane x/y + 三 axis_parallel，避免每件 6 行 JSON；Agent 错误率降一半。

块状件「仅平移」模式（6 DOF → 3 DOF）
人形/叉车类全轴对齐体：锁死旋转，只解 t_x,t_y,t_z → 维数砍半、Jacobian 良态、无四元数歧义。

解析 Jacobian / 稀疏
替换 numeric_jacobian（dof.py）——48 体才可能实用。

初值策略
按约束图 BFS：ground → 贴 ground 的 → 贴父的；或从 Location 预览生成 initial_guess（混合闭环：公式给初值，约束做验算）。

统一轴锁模板
transformers 轮应和 agv_cart 一样锁满 z/x/y；preflight 对 轮子 而不仅是竖板。

P1 — 能力扩展
子图级联求解
chassis solve → 固定 platform 变换 → upper_body 以 platform 为 ground（或固定 6DOF 接口）。突破单图 64 体，又不必全 Location。

parent_frame 偏移
{"type":"offset_in_body","parent":"chest","local":[150,10,15]}，避免在 ground 切向写 in_plane。

软约束 / 权重 / 冲突报告增强
过约束时指出最小冲突集（plan 文档里提过 LLM 友好报告）。

宏：hinge / grid_repeat
grid_repeat 生成 pin_grid 类；减少重复 JSON。

P2 — 与「像不像」正交但有用
装配后规则 inspect（剪影规则，非求解器）
叉齿 Y 延伸、配重 X 在后——补「语义合理」，不增加约束维度。

从 CONSTRAINTS 自动生成 Location 回退
solve ok 后导出 transforms 供阅读；debug 友好。

圆柱/销轴配合
已有 primitive；加强 axis_coaxial 在轮轴场景的模板。

不宜做
强迫 >30 体造型件全进约束——违背 WARN_BODIES=30 的设计意图。
用约束替代 render/看图——语义层不在方程里。
7. 战略结论（针对你的三个隐含问题）
若要求绝大部分用约束，效果如何？

配合正确性：底盘/围板类略升；全身造型类 无升，失败模式更「硬」。
造型 / 一次合理：基本无改善。
成本：Authoring、solve 时间、调试轮次 显著上升。
transformers 实证：现在 15% 约束已覆盖 唯一真需要 的 6 轮；其余 41 件用约束是 重复劳动。
和位置堆砌比？

不是优劣替代，是 分工：堆砌 = 布局；约束 = mating + 回归。
90% 约束 < 90% Location 对此类示例；最佳实践仍是 10–30% 约束 + 70–90% Location。
机制还有优化空间吗？

有，且大——但在 宏、平移子集、Jacobian、子图、初值、父系坐标；不在 把 Location 全改成约束。
优化目标应是：让 15% 的那一段更稳、更好写、更快解，而不是扩大约束占比。
若你愿意做实验，最有说服力的 A/B 是：
同一 transformers_robot 做「仅底盘约束（现状）」vs「上身 20 体约束链」——我可以按你指定只改一版 spec/脚本，用 run_validation 的 nfev、耗时、status 对比给你看数据（会故意不做到 48 体全约束，避免无意义的 400 约束顶格工程）。

我觉得有些地方用约束应该相当简单啊，如何优化约束机制才能使得其比location堆砌更易生成呢？肯定有方法的，比如一些约束的剩余自由度存在默认（这样llm不就不需要生成所有的约束来锁死全部自由度了吧）等等，超超超超深入全面分析探索机制

你的直觉对：很多配合在语义上就是「一句话」，现在却要求 LLM 写满 6 条基础约束去「锁死」7 维位姿——这是机制在要求解全 DOF，而不是在声明配合。要让约束比 Location 更易生成，方向不是「更严的全锁」，而是 「少写 + 默认补全 + 能算就别迭代」。

下面按机制层做超深入探索（含可落地的 spec 形态与实现路径）。

0. 根本矛盾：现在在解决两个不同的问题
模式	实际问题	合适工具
布局已知（人形块、货叉高度）	「放在 (x,y,z)，轴与世界对齐」	Location / 公式
配合已知、位姿未知（轮心距、贴底、共面）	「满足 mating，坐标由方程给出」	约束求解
配合已知、位姿也大致已知	「差不多这，顺便验一下」	校验型约束（不必 full solve）
当前 harness 几乎只有一种出口：least_squares 直到 status=ok（且还要过旋转审计）。
LLM 被迫用 「方程锁死」 表达 「我就是想放这儿」 → 比一行 Location((x,y,z)) 难得多。

要比 Location 更易生成，机制必须承认：

大量零件的剩余自由度应有 默认策略（policy），不必由 LLM 逐条写出。

1. 你说的「剩余自由度默认」——四种语义层级
先分清「默认」指什么，否则实现会打架。

L0 — 求解后默认（post-solve gauge fix）【风险最大】
求解器发现 free: rot z → 自动加 axis_parallel 锁上。
问题：多个等价解（绕 Z 转 180°）时，默认可能选错且残差仍为 0。
适用：仅当策略与 对称性破缺 绑定（如「体心 x>0 朝 +X」）。
L1 — 展开时默认（compile-time expand）【推荐主路径】
LLM 写 {"type":"stack_on","child":"waist","parent":"pelvis.+z","at":[0,-8]}
编译器 确定性地 展开为 4–6 条基础约束（类似今天的 contact→plane_coincident）。
LLM 不写 axis_parallel；宏自带「块状件标准锁」。
L2 — 角色默认（body role + mount）【最易写】
"wheel_fl": {
  "primitive": "box",
  "size": [55, 35, 55],
  "mount": { "kind": "on_plane", "plane": "platform.+z", "x": -145, "y": 78 }
}
constraints 数组可为空；validate 阶段根据 mount.kind 生成 全套约束。
LLM 只提供 3 个数（x,y + 隐含贴面），等价于 Location 的信息量。
L3 — 布局直通（layout-first，无非线性求解）【对 80% 件】
"pelvis": { "primitive": "box", "size": [...], "place": [0, -10, 87.5] }
引擎直接 transform = T(place) · align(ground)，不调用 scipy。
可选：verify_mates: true 用残差检查是否真贴在 platform 上。
对 LLM：和 Location 一样好写，但仍在 CONSTRAINTS 统一 schema 里。
结论：

「默认」应主要在 L1/L2（编译展开） 和 L3（明确布局），而不是 L0 静默猜解。
status=ok 不应再等价于「人类写了 6N 条锁」；应等价于 「声明完整 +（求解或直通）成功」。
2. 目标形态：比 Location 更短的 Authoring 接口
2.1 信息量对比（同一轮子）
Location（今天）：

_box(WHEEL).moved(Location((-145, 78, PLATFORM_TOP_Z + WHEEL[2]/2)))
当前约束（6 条 JSON）：

contact, offset, in_plane x, in_plane y, axis_parallel z, axis_parallel x
目标：一条 relation（≤2 行）：

{ "type": "wheel", "body": "wheel_fl", "on": "platform", "at": [-145, 78] }
或 Python 糖：

CONSTRAINTS = {
  "ground": "platform",
  "bodies": { "platform": {...}, "wheel_fl": {...}, ... },
  "relations": [
    ["wheel", "wheel_fl", "platform", [-145, 78]],
  ],
}
编译后展开为今天那 6 条 + 自动补 axis_y（修 transformers 少锁的问题）。

2.2 躯干叠放（链式）
{ "type": "stack", "child": "waist", "on": "pelvis.+z", "xy": [0, -8] }
展开：contact(waist.-z, pelvis.+z) + offset + in_plane + 默认 align_box_axes(pelvis)。

LLM 不写四元数、不写 6 条平行；只写 父面 + 平面内 2 个数——与 Location 公式同信息量，但 feature 引用由编译器填（少写 b1.-z 笔误）。

2.3 柱阵（比 Location 更简单）
{ "type": "grid_pins", "base": "base", "size": [14,14,32], "pitch": 70, "rows": 4, "cols": 4 }
一条替代 16×4 条约束；比 for 循环 Location 还短。

3. 核心机制：dof_policy + 自动补全（你要的探索重点）
3.1 在 spec 顶层声明策略
{
  "ground": "platform",
  "dof_policy": {
    "default_box_on_plane": "fixed_orthogonal",
    "underconstrained": "complete_then_ok",
    "spin_z_on_ground": "forbid"
  },
  "bodies": { ... },
  "relations": [ ... ]
}
策略值	含义
fixed_orthogonal	贴地 box：自动 axis_parallel 锁 z,x,y 与 ground（或父体）
allow_spin_z	仅用于圆盘、对称件（显式声明）
complete_then_ok	求解后若 dof_deficit>0，按规则 追加约束 再解一轮（最多 1 轮）
layout_only	有 place:[x,y,z] 的体 不参与 优化，只验 mate
3.2 自动补全算法（可实现伪代码）
1. expand relations → base constraints
2. apply role defaults (wheel, stack, panel_edge)
3. solve → report
4. if policy.complete_then_ok and status==underconstrained:
     for each free entry in report.free:
       if trans in_plane: emit point_plane_offset on supporting plane
       if rot includes z: emit axis_parallel for missing in-plane axis lock
     resolve conflicts (don't add duplicate)
     solve again (max 1–2 rounds)
5. if still underconstrained and policy.strict: fail with hint
   else if policy.permissive: freeze remaining DOF at initial_guess (≈ Location)
关键： 第 5 步的 permissive 模式 = 「约束 + 默认位姿」，LLM 只写关键 mate，其余 DOF 用初值/布局固定——这正是你说的「不必生成所有约束」。

3.3 与今天 status=ok 的差异
今天：ok ≈ 残差小 + 无 rotation_issues + 平移自由体 <2。

建议拆成：

status	含义	LLM 行动
ok	声明完整，位姿确定（解出或 layout 直通）	继续 step
ok_assumed	关键 mate 满足，剩余 DOF 用 policy 固定	可继续，report 列出 assumed_locks
underconstrained	缺 必要 声明（非缺锁）	补 relation
solve_failed	矛盾或数值失败	改 mate
这样 不必为了 ok 而写满锁；只有 strict 评测模式才要求全锁。

4. 为什么这样能比 Location「更易生成」
4.1 Token 与认知负荷
任务	Location	当前约束	目标 relation
1 轮贴地	1 行，心算 z+h/2	4–6 JSON 对象	1 relation
4 轮	4 行或循环	24–28 对象	4 relation 或 wheels: corners
竖板	易忘旋转	易忘 axis_x/y	panel 宏自带
改轮距	改 1 个数	改 2 个 in_plane	改 at:[x,y] 1 处
4.2 错误类型
Location：静默错位（数错 10mm）
当前约束：solve 失败 或 假 ok 旋转
目标：编译期报错（未知 role、非法 mount）+ mate 残差报告 + 可选 assume
对 Agent：失败要早、要可修；relation 编译错误比 scipy 不收敛友好。

4.3 「简单」的数学事实
对 轴对齐 box，位姿空间是 R³（平移），不是 SO(3)×R³。
用四元数 + 6 条锁是 过参数化；应默认：

rotation_mode: "axis_aligned"  → 状态 3 维，解析放置
rotation_mode: "free"          → 才用四元数 + 求解
transformers 全身 41 件全是 axis_aligned → 本不该进 scipy；用 L3 place + L1 stack 即可。

5. 机制模块全景（探索地图）
Authoring 层
编译层 graph.py
求解层
输出
relations / roles
place 布局
parameters
expand macros
role defaults
dof_policy
axis_aligned 解析
scipy 仅剩余 DOF
verify-only
transforms
report + assumed_locks
模块 A — Relation 宏库（扩 graph.expand_constraints）
宏	LLM 输入	展开 / 行为
wheel	on, at[x,y]	6–7 基础约束 + 三轴锁
stack	child, on, xy?, z_gap?	贴 parent.+z + offset + in_plane
panel	edge, on, side	contact + 双轴锁（防绕 Z）
grid_pins	pitch, rows, cols	N 体 + N 组约束
coincident	a, b	point_coincident
hinge	已有	axis_coaxial + point
实现成本： 低（纯 Python 展开，已有 contact/hinge 先例）。

模块 B — Body mount / place 字段（扩 schema.py）
place: [x,y,z] → 直通 transform（L3）
mount: {kind, plane, x, y} → 生成 relation（L2）
二者互斥；与 constraints[] 互斥（同一 body）
模块 C — rotation_mode
默认 axis_aligned（块体装配）
显式 free 才用四元数
Jacobian 从 7×N 降到 3×N → 快、稳、初值不敏感
模块 D — 两阶段装配图
Stage1: ground + chassis (solve or relations)
Stage2: upper_body compound 以 stage1.platform 为 frame
        - 子 spec 的 ground = "interface"
        - 或 relations 里 parent 引用上一 stage export 的 frame
突破 64 体，且 LLM 按区域写短 spec。

模块 E — Layout 导入 / 双向
# Agent 先写 Location 草稿（快）
layout = {"pelvis": (0,-10,87.5), ...}
# 工具：layout_to_relations(layout) → 建议 relations
# 或：verify_layout(layout) → mate 残差
比 Location 易： 改一处 → 自动同步 constraint 声明；比纯约束易： 不必手写 6 条。

模块 F — 智能 hint（扩 report.py）
今天 hint 是「加 in_plane / axis_parallel」。

应升级为：

"suggested_relations": [
  {"type": "stack", "child": "waist", "on": "pelvis.+z", "xy": [0, 0]}
]
从 free[] 反推宏，LLM 复制粘贴即可——补全方向是升维（宏）不是加基础约束条数。

模块 G — assumed_locks 透明度
"assumed_locks": [
  {"body": "wheel_fl", "rule": "fixed_orthogonal_to_platform", "added": ["axis_parallel wheel_fl.axis_y platform.axis_y"]}
]
避免静默猜错；评测时可要求 assumed_locks 为空。

6. 三种运行模式（建议写进 skill）
模式	何时用	LLM 写什么	与 Location 比
strict_solve	回归、少体配合	relations，policy=strict	难一点，最严
assist	默认生产	relations + 少量 place	更易（宏短）
layout	造型块、人形	place + verify	与 Location 同级，统一 schema
verify_only	已有 gen_step	只验 mate	不改代码
「绝大部分用约束」在 assist/layout 下才合理——不是 48 体 × 6 条，而是 48 体 × (place 或 1 relation)。

7. 针对 transformers_robot 的「易生成」改写示例
今天（7 体 × 手写 helper）： ~35 行约束逻辑。

目标 spec 片段：

{
  "ground": "platform",
  "dof_policy": { "default_box_on_plane": "fixed_orthogonal" },
  "bodies": {
    "platform": { "primitive": "box", "size": [400, 180, 55] },
    "wheel_fl": { "primitive": "box", "size": [55, 35, 55] }
  },
  "relations": [
    { "type": "wheel", "body": "wheel_fl", "on": "platform", "at": [-145, 78] },
    { "type": "wheel", "body": "wheel_fr", "on": "platform", "at": [145, 78] },
    { "type": "wheel_pair", "on": "platform", "x": [-120, 120], "y_inner": 46, "y_outer": 86, "suffix": "rl" },
    { "type": "wheel_pair", "on": "platform", "x": [-120, 120], "y_inner": 46, "y_outer": 86, "suffix": "rr" }
  ],
  "compounds": {
    "robot_body": { "source": "location_module", "module": "_robot_body" }
  }
}
底盘：4 条 relation 替代 36 条基础约束。
上身：仍用 Location 模块（compound 引用），不硬塞进求解器。
LLM 比写 _wheel_on_platform 更易（声明式、无 Python）。
8. 风险与对策（必须写进设计）
风险	对策
默认锁选错 180°	assumed_locks + 对称件要求 break_symmetry: "+x"
与 parts 尺寸不一致	schema 校验 bodies.size 唯一来源；build123d 从 size 生成
宏隐藏过多	expand --dry-run 输出展开 JSON 供调试
过度依赖 permissive	默认 assist；strict 仅 CI
和 Location 两套真相	place 与 relation 冲突时编译报错
9. 实施路线图（按「比 Location 更易」排序）
wheel / stack / panel 宏 + 展开测试（1–2 天）→ 立即缩短 agv/transformers 底盘
rotation_mode: axis_aligned 解析求解（2–3 天）→ 速度 + 初值
place 字段 + layout 模式（1 天）→ 人形件与 Location 等价
dof_policy.complete_then_ok + assumed_locks（2 天）→ 你要的「剩余 DOF 默认」
suggested_relations in report（1 天）→ 修约束比今天轻松
Stage 分图（3–5 天）→ 大规模
解析 Jacobian（性能，非易用性）
10. 直接回答你的命题
「有些地方用约束应该相当简单」 —— 对，但简单的是 关系（relation），不是 7 维方程组。今天难，是因为把 关系 降维成 最大数量的基础约束 + 全秩求解。

「默认处理剩余自由度」 —— 应该有，且应分：

编译期默认（宏/role）→ 主路径，确定、可审计
求解后补全（complete_then_ok）→ 辅助，限轮数
permissive 固定初值→ 等价于 Location，用于纯造型块
「肯定有方法比 Location 更易」 —— 有，条件是：

别对每件求 scipy；轴对齐用解析 place/stack。
别让 LLM 写满锁；用宏 + policy。
失败时给 relation 级 hint，不是「再加 axis_parallel」。
保留 Location 为 compound 子模块（上身），约束只管真 mating。
这样约束在 轮位、围板、柱阵 上会比 Location 更短、更不易错；在 人形造型 上与 Location 一样短（共用 place），并多一层 mate 验证——才是合理分工，而不是强迫 90% 约束。

若你希望我落地第一步（例如在 graph.py 实现 wheel + stack 展开，并把 transformers_robot 底盘改成 relations 风格），可以说一下优先 wheel 还是 stack，我可以直接改代码 + 补测试。




哪些不影响模型装配的自由度就用默认就好，但是影响了的必须给全