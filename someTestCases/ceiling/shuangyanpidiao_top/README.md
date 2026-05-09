# 双层石膏板吊顶 (shuangyanpidiao_top)

在**仓库根目录**下重新生成 STEP：

```bash
cd D:/code/text-to-cad
.venv/Scripts/python.exe .agents/skills/cad/scripts/step someTestCases/ceiling/shuangyanpidiao_top/shuangyanpidiao_top.py
```

几何检查（示例）：

```bash
.venv/Scripts/python.exe .agents/skills/cad/scripts/inspect refs someTestCases/ceiling/shuangyanpidiao_top/shuangyanpidiao_top.step --facts --planes --positioning
```

CAD Explorer（扫描根 = 仓库根）：

`http://127.0.0.1:4178/?file=someTestCases/ceiling/shuangyanpidiao_top/shuangyanpidiao_top.step`

按 `AGENTS.md` 要求，若需完整**迭代过程留痕**（工具、报错、修复），请在本目录增加 `ITERATION_LOG.md`，并按时间追加每一次实质性操作。
