<div align="center">

<img src=".assets/text-to-cad-demo.gif" alt="text-to-cad 脚手架生成并预览 CAD 几何的演示" width="100%">

<br>

# ⚙ 开源文本转 CAD 脚手架 ⚙

面向常用编程智能体的开源脚手架，用于生成三维模型

[演示项目](https://text-to-cad.earthtojake.com)

[![GitHub stars](https://img.shields.io/github/stars/earthtojake/text-to-cad?style=for-the-badge&logo=github&label=Stars)](https://github.com/earthtojake/text-to-cad/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/earthtojake/text-to-cad?style=for-the-badge&logo=github&label=Forks)](https://github.com/earthtojake/text-to-cad/network/members)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Follow @soft_servo](https://img.shields.io/badge/Follow-%40soft__servo-000000?style=for-the-badge&logo=x)](https://x.com/soft_servo)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](.agents/skills/cad/requirements.txt)
[![build123d](https://img.shields.io/badge/build123d-CAD-00A676?style=for-the-badge)](https://github.com/gumyr/build123d)
[![OCP](https://img.shields.io/badge/OCP-OpenCascade-2F80ED?style=for-the-badge)](.agents/skills/cad/requirements.txt)
[![STEP](https://img.shields.io/badge/STEP-Export-4A5568?style=for-the-badge)](.agents/skills/cad/SKILL.md)
[![STL](https://img.shields.io/badge/STL-Export-4A5568?style=for-the-badge)](.agents/skills/cad/SKILL.md)
[![3MF](https://img.shields.io/badge/3MF-Export-4A5568?style=for-the-badge)](.agents/skills/cad/SKILL.md)
[![URDF](https://img.shields.io/badge/URDF-Robots-6B46C1?style=for-the-badge)](.agents/skills/urdf/SKILL.md)
[![Robot Motion](https://img.shields.io/badge/Robot%20Motion-IK%20%2B%20Planning-6B46C1?style=for-the-badge)](.agents/skills/robot-motion/SKILL.md)
[![Node.js](https://img.shields.io/badge/Node.js-CAD%20Explorer-339933?style=for-the-badge&logo=node.js&logoColor=white)](.agents/skills/cad/explorer/package.json)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=111111)](.agents/skills/cad/explorer/package.json)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=for-the-badge&logo=vite&logoColor=white)](.agents/skills/cad/explorer/package.json)

</div>

## ✨ 特性

- **生成** — 配合 Codex、Claude Code 等编程智能体，创建可纳入版本控制的 CAD 模型源码。
- **导出** — 输出 STEP、STL、3MF、DXF、GLB、拓扑数据以及 URDF 机器人描述。
- **浏览** — 在 CAD Explorer 中查看生成的几何。
- **引用** — 复制稳定的 `@cad[...]` 引用，便于智能体做精确的后续修改。
- **审阅** — 在迭代循环中快速渲染审阅图以便检查。
- **复现** — 先改源码文件，再按明确目标重新生成。
- **本地** — 脚手架与 CAD Explorer 均在本地运行，无需自建后端。

## 🧰 内置技能（Skills）

本脚手架内置面向文件的 CAD、机器人描述、机器人运动与制造预检等技能副本。本地 CAD 项目可直接使用此处自带的副本；若在脚手架之外单独安装技能，可使用对应的独立仓库。

- **CAD 技能** — STEP、STL、3MF、DXF、GLB/拓扑、渲染图以及 `@cad[...]` 几何引用。[内置副本](.agents/skills/cad/SKILL.md) · [独立仓库](https://github.com/earthtojake/cad-skill)
- **URDF 技能** — 生成的 URDF XML、连杆、关节、限位、校验与网格引用。[内置副本](.agents/skills/urdf/SKILL.md) · [独立仓库](https://github.com/earthtojake/urdf-skill)
- **Robot Motion 技能** — ROS 2/MoveIt 环境、CAD Explorer 运动产物、逆运动学、轨迹规划，以及对既有 URDF 的运动服务端测试。[内置副本](.agents/skills/robot-motion/SKILL.md)

技能在 Codex 侧以 `.agents/skills` 为权威位置；Claude Code 通过 `.claude/skills` 中按技能的符号链接保持兼容。

## 📸 截图

<table>
  <tr>
    <td width="33%">
      <a href="./.assets/text-to-cad-demo.gif">
        <img src="./.assets/text-to-cad-demo.gif" alt="CAD 技能演示：在 CAD Explorer 中查看生成的几何" width="100%">
      </a>
      <a href="./.agents/skills/cad/SKILL.md"><strong>CAD</strong></a>
    </td>
    <td width="33%">
      <a href="./.assets/urdf-demo.gif">
        <img src="./.assets/urdf-demo.gif" alt="URDF 技能演示：在 CAD Explorer 中查看机器人描述输出" width="100%">
      </a>
      <a href="./.agents/skills/urdf/SKILL.md"><strong>URDF</strong></a>
    </td>
    <td width="33%">
      <a href="./.assets/robot-motion-demo.gif">
        <img src="./.assets/robot-motion-demo.gif" alt="Robot Motion 技能演示：在 CAD Explorer 中查看逆运动学" width="100%">
      </a>
      <a href="./.agents/skills/robot-motion/SKILL.md"><strong>Robot Motion</strong></a>
    </td>
  </tr>
</table>

## 🔁 工作流

1. **描述** — 向智能体说明你想要的零件、装配、夹具、机器人或机构。
2. **编辑** — 由编程智能体更新仓库内的 CAD 源码文件。
3. **重新生成** — 生成明确的 STEP、STL、3MF、DXF、GLB 或 URDF 目标。
4. **检查** — 打开 CAD Explorer 查看生成的模型。
5. **引用** — 在做几何感知类修改时复制 `@cad[...]` 句柄。
6. **提交** — 模型就绪后，将源码与生成产物一并保存提交。

## 🧪 基准测试

仓库通过 Git LFS 存放 `.assets/**`，并在默认 LFS 拉取中排除该目录，以便轻量克隆不会拉取 GIF 资源或基准详情页。若仅需在本地拉取基准相关资源，可执行：

```bash
git lfs pull --include=".assets/benchmarks/**"
```

<table>
  <thead>
    <tr>
      <th>#</th>
      <th>目标</th>
      <th>提示词</th>
      <th>输出</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td>
      <td><a href=".assets/benchmarks/01-rectangular-calibration-block.md">带四个孔的矩形标定块</a></td>
      <td>创建一个居中的 100×60×20 mm 长方体，带有四个直径 8 mm 的竖直通孔。仅在顶部外轮廓添加 2 mm 倒角。</td>
      <td><img src=".assets/benchmarks/benchmark_01_rectangular_calibration_block.gif" alt="矩形标定块环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>2</td>
      <td><a href=".assets/benchmarks/02-circular-flange.md">带螺栓孔分布圆的圆形法兰</a></td>
      <td>创建一个直径 80 mm、厚度 10 mm 的圆形法兰，中心为直径 30 mm 的贯穿孔。在直径 60 mm 的螺栓分布圆上布置六个直径 6 mm 的贯穿孔，并对外侧圆周棱边倒圆角。</td>
      <td><img src=".assets/benchmarks/benchmark_02_circular_flange.gif" alt="圆形法兰环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>3</td>
      <td><a href=".assets/benchmarks/03-l-bracket.md">带加强筋与双向孔的 L 形支架</a></td>
      <td>由底板和后侧竖板构成 L 形支架。添加底板竖向孔、背板水平孔、两块三角形加强筋，并对底板与背板的过渡处倒圆角。</td>
      <td><img src=".assets/benchmarks/benchmark_03_l_bracket.gif" alt="L 形支架环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>4</td>
      <td><a href=".assets/benchmarks/04-stepped-shaft-keyway.md">带键槽的阶梯轴</a></td>
      <td>沿 X 轴创建总长 120 mm 的阶梯轴，三段直径分别为 20/30/20 mm。两端添加倒角，并在中间段顶部加工浅矩形键槽。</td>
      <td><img src=".assets/benchmarks/benchmark_04_stepped_shaft_keyway.gif" alt="阶梯轴环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>5</td>
      <td><a href=".assets/benchmarks/05-open-top-electronics-enclosure.md">带支柱的敞开顶电子外壳</a></td>
      <td>创建一个空心开口外壳，壁厚与底板厚度均为 3 mm。添加四个内部支柱（凸台），中心为盲孔；外壳外侧竖向转角处倒 2 mm 圆角。</td>
      <td><img src=".assets/benchmarks/benchmark_05_open_top_electronics_enclosure.gif" alt="敞开顶电子外壳环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>6</td>
      <td><a href=".assets/benchmarks/06-clevis-bracket-lightening-cutouts.md">航空风格带减重孔的叉形支架</a></td>
      <td>创建对称的叉形支架：含底板、两个圆角耳片、底板安装孔以及水平的耳片贯穿孔。添加三角形减重孔、加强筋以及圆角过渡。</td>
      <td><img src=".assets/benchmarks/benchmark_06_clevis_bracket_lightening_cutouts.gif" alt="叉形支架环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>7</td>
      <td><a href=".assets/benchmarks/07-radial-engine-cylinder.md">星型发动机风格带散热片的缸体</a></td>
      <td>创建立式发动机气缸形态：含中央缸筒、12 片散热鳍片、底部法兰与顶部端盖。添加倾斜 35° 的火花塞凸台，并带有同轴贯穿孔。</td>
      <td><img src=".assets/benchmarks/benchmark_07_radial_engine_cylinder.gif" alt="星型发动机风格缸体环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>8</td>
      <td><a href=".assets/benchmarks/08-centrifugal-impeller.md">后弯叶片的离心叶轮</a></td>
      <td>创建离心叶轮：含背板、轮毂与中心贯穿孔。添加 12 片与轮毂连成一体的后弯叶片，从根部到顶部扫掠约 45°。</td>
      <td><img src=".assets/benchmarks/benchmark_08_centrifugal_impeller.gif" alt="离心叶轮环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>9</td>
      <td><a href=".assets/benchmarks/09-spiral-staircase.md">带螺旋扶手的旋转楼梯</a></td>
      <td>创建微型螺旋楼梯：含中央立柱、底座圆盘以及 20 级上升的楔形踏步。添加一整圈的螺旋扶手，并在踏步外缘布置竖向栏杆立柱。</td>
      <td><img src=".assets/benchmarks/benchmark_09_spiral_staircase.gif" alt="旋转楼梯环绕预览 GIF" width="220"></td>
    </tr>
    <tr>
      <td>10</td>
      <td><a href=".assets/benchmarks/10-planetary-gear-stage.md">简化的行星齿轮级</a></td>
      <td>创建平面行星齿轮机构：太阳轮、行星轮、齿圈、行星架与销轴为独立零件。采用简化的梯形齿廓，并将三颗行星轮布置在以太阳轮为中心、半径 42 mm 的圆周上。</td>
      <td><img src=".assets/benchmarks/benchmark_10_planetary_gear_stage.gif" alt="行星齿轮级环绕预览 GIF" width="220"></td>
    </tr>
  </tbody>
</table>

## 🚀 快速开始

克隆仓库：

```bash
git clone https://github.com/earthtojake/text-to-cad.git
cd text-to-cad
```

安装 Python CAD 依赖：

```bash
python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r .agents/skills/cad/requirements.txt
```

仅在需要对应工作流时再安装其他内置技能的依赖：

```bash
./.venv/bin/pip install -r .agents/skills/urdf/requirements.txt
```

安装 CAD Explorer 依赖：

```bash
npm --prefix .agents/skills/cad/explorer install
```

在你希望扫描的项目目录下启动本地 CAD Explorer：

```bash
npm --prefix .agents/skills/cad/explorer run dev
```

随后在浏览器打开 [http://localhost:5180](http://localhost:5180)，或设置 `EXPLORER_PORT` / 使用 `dev:ensure`（会打印实际 URL）。

若在多个项目间做根目录感知的智能体工作流，可让 CAD Explorer 复用已有服务或在空闲端口启动：

```bash
npm --prefix .agents/skills/cad/explorer run dev:ensure -- --file STEP/sample_part.step
```

然后打开该命令输出的 URL。
