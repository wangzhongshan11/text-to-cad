# gen_urdf

从带有返回封装的 `gen_urdf()` 函数的 Python 源码重新生成明确的 URDF 输出。

```bash
python <urdf-skill>/scripts/gen_urdf/cli.py path/to/assembly.py
python <urdf-skill>/scripts/gen_urdf/cli.py path/to/assembly.py --summary
```

目标必须是显式的生成用 Python 源码文件，其 `gen_urdf()` 返回包含 `xml` 与 `urdf_output` 的封装；详见 `references/generator-contract.md`。

相对目标从当前工作目录解析。

本工具仅运行 `gen_urdf()`，不会重新生成 CAD、网格/导出、GLB/拓扑或渲染输出。
