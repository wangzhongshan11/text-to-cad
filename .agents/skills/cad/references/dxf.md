# DXF 次要工作流

仅在用户要求从 CAD 几何导出 DXF 或二维图样时阅读本文。

DXF 为次要。若几何源于 CAD 源码，先生成并校验 STEP 包络。勿将 DXF 图层视作 STEP 零件/装配结构。

## 工具

```bash
python scripts/dxf targets...
```

仅预期标准帮助类标志位。

## 源码要求

DXF 目标须为定义以下内容的 Python 源码：

```python
def gen_dxf():
    ...
    return document, dxf_output
```

同一文件还须定义有效 `gen_step()` 包络，因发现流程使用 CAD 源码目录。

```python
def gen_step():
    ...
    return shape_or_compound
```

## 工作流

1. 将用户叙述转为自然语言 CAD 简报。
2. 构建或校验 `gen_step()` 包络。
3. 生成 STEP 并做轻量 facts/planes/positioning 检查。
4. 启动 CAD Explorer 并返回 STEP 的 Explorer 链接。
5. 按请求的投影视图、排版或图样输出添加或更新 `gen_dxf()`。
6. 对明确 Python 源码目标运行 `scripts/dxf`。
7. 报告 DXF 输出以及主 STEP 与 Explorer 链接。

## 命令

```bash
python scripts/dxf path/to/source.py
```

## 报告

```text
Files:
- STEP: path/to/source.step
- DXF: path/to/output.dxf

CAD Explorer:
- http://127.0.0.1:5180/?file=path/to/source.step

Validation:
- STEP geometry: checked with facts/planes/positioning
- DXF: generated from gen_dxf(); drawing-layer content reported if available
```
