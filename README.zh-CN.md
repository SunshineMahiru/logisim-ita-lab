<h1 align="center">logisim-ita-lab</h1>

<p align="center">以文本为中心的 Logisim-ITA 电路实验工作流：解析、生成、验证 <code>.circ</code> 文件。</p>

<p align="center"><a href="README.md">English</a> | 简体中文</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white" alt="Python 3">
  <img src="https://img.shields.io/badge/Logisim--ITA-2.16.2.0-informational" alt="Logisim-ITA 2.16.2.0">
</p>

## 特点

- **把电路当文本处理。** `.circ` 是 UTF-8 编码的 XML，电路可以生成、比对、审阅，不必在图形界面里逐个点击。
- **按电路类型分两条验证路径。** 组合逻辑走门级仿真对拍；时序逻辑走真实引擎，逐拍驱动。
- **坐标是量出来的。** 组件端口坐标由 Logisim-ITA 2.16.2.0 的 dump 工具读回，文档记录的是观察到的值。
- **Python 只用标准库。** 解析器、门级仿真器、真值表对拍都不需要第三方包；只有跑真实引擎时才需要 Java。
- **附带任务知识库。** `references/exp1-tasks.md` 记录实验1 的 5 个任务：逻辑、引脚、真值表、拓扑、坐标。
- **离线自检。** `scripts/selftest.py` 串起「解析 → 生成 → 仿真 → 对拍」全链路，不依赖 Java。

## 架构

工作流的输入是题面加模板 `.circ`，中间产物是一份待验证的 `.circ`，然后按电路类型分流到三条验证路径。

```text
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  Problem docx or  │    │    circ_parser    │    │  Topology design  │
│   template .circ  │───▶│  (structure JSON) │───▶│   + circlib emit  │
└───────────────────┘    └───────────────────┘    └─────────┬─────────┘
                                                            │
                                   ┌────────────────────────┘
                         ┌─────────▼─────────┐
                         │   candidate.circ  │
                         └─────────┬─────────┘
          ┌────────────────────────┴────────────────────────┐
          ▼                        ▼                        ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│    validate.py    │    │  Logisim-ITA GUI  │    │    CircRun.java   │
│  gate-level check │    │    manual poke    │    │  runner.py, tick  │
└───────────────────┘    └───────────────────┘    └───────────────────┘
    combinational      transistor / subcircuit         sequential
```

`references/` 放格式手册、组件端口表、时序测试规程与平台笔记；`SKILL.md` 是串起这些材料的操作流程。

## 用法示例

```bash
# 查看模板结构：主电路名、引脚、隧道、空白区
python scripts/circ_parser.py path/to/lab1.3.circ

# 与内置的实验1 真值表对拍
python scripts/validate.py path/to/lab1.3.circ --task lab1.3

# 或使用自定义真值表
python scripts/validate.py path/to/my.circ --table-file truth.json
```

`validate.py` 的返回码：`0` 全部一致，`1` 有用例或引脚 label 不匹配，`2` 无法门级仿真（晶体管、子电路、时序部件）。

自定义真值表格式：

```json
{"inputs": ["X", "Y"], "outputs": ["F"],
 "cases": [{"in": [0, 0], "out": [0]}, {"in": [1, 1], "out": [1]}]}
```

内置表覆盖 `lab1.1` 到 `lab1.5`。

## 安装

依赖：

| 项 | 用途 | 说明 |
|---|---|---|
| Python 3 | 所有脚本 | 只用标准库，无需 `pip install` |
| JDK 8 以上 | `CircRun.java`、`Conn`、`Dump`、`ErrLoad` | 用 `javac` 编译一次 |
| Logisim-ITA 2.16.2.0 | 图形核对与真实引擎 | 与目标平台同版本 |

Java 辅助工具通过环境变量指路，不要把本机路径写进脚本：

```bash
export LOGISIM_JAVA="<jdk>/bin/java"      # 默认取 PATH 中的 java
export LOGISIM_JAR="<dir>/Logisim-ITA-2.16.2.0/Logisim-ITA.jar"
export LOGISIM_TOOLS="<编译输出目录>"      # 默认 tools
```

要在 Agent 里当 skill 使用，把整个目录复制到 skills 目录（WorkBuddy 为 `~/.workbuddy/skills/`）。`SKILL.md` 里带有加载器读取的 frontmatter。

## 快速开始

```bash
git clone git@gitee.com:theangelnextdoor/logisim-ita-lab.git
cd logisim-ita-lab
python scripts/selftest.py
```

当前仓库的实际输出：

```text
[1/4] 解析: 主电路 main，电路 dict_keys(['main'])
[2/4] 仿真: 8 组用例与 lab1.3 真值表一致
[3/4] 命令行: validate.py 返回 0
[4/4] 降级: 含晶体管的电路被门级仿真器拒绝
SELFTEST: ALL PASS
```

自检脚本从最小模板生成一个 2 选 1 多路选择器，跑完八组输入组合，再走一遍命令行入口，并确认晶体管电路在门级仿真层被拒绝。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `SKILL.md` | 操作流程：提取需求、读模板、设计拓扑、生成 XML、验证 |
| `references/circ-format.md` | `.circ` 语法：XML 结构、库编号、组件属性、生成规则 |
| `references/components.md` | 门、D 触发器、寄存器、加法器、多路选择器、分线器的端口坐标表 |
| `references/timing-verification.md` | 时序电路测试与验收规程，附数字时钟参考形态 |
| `references/platform-notes.md` | 评测机制、时钟约定、外部库引用、文件传输通道 |
| `references/exp1-tasks.md` | 实验1 的 5 个任务，兼作范例格式与回归真值表来源 |
| `scripts/*.py` | 解析器、门级仿真器、对拍入口、文本生成库、跑测封装、自检 |
| `scripts/*.java` | 无头引擎驱动、悬空端点列表、端口坐标打印、加载错误捕获 |

## 验证路径

| 电路类型 | 工具 | 能确认什么 |
|---|---|---|
| 组合逻辑（AND/OR/NOT 等） | `validate.py` | 真值表逐行一致 |
| 晶体管级或子电路 | Logisim-ITA 图形界面 | 手动 poke 下网络行为正确 |
| 时序电路（触发器、寄存器、计数器） | `CircRun.java` + `runner.py` | 状态序列逐拍一致 |

时序这条路径还包含结构检查：`Conn` 列出悬空端点，`Dump` 打印组件的真实端口坐标，`ErrLoad` 取回被图形界面吞掉的加载错误文案。

## 适用范围

- 目标版本是 Logisim-ITA 2.16.2.0 与头歌「计算机组成原理」实验系列。其他版本在库编号与端口几何上可能不同。
- `references/platform-notes.md` 里的平台行为来自一次课程部署，逐关细节按观察记录对待，使用前重新核对。
- 本仓库不覆盖 Verilog / Vivado 流程，也不改动 Logisim-ITA 自身。
- 实验答案拓扑属于课程教学材料，请在你适用的规则内使用。

## 许可证

MIT，见 [LICENSE](LICENSE)。Copyright (c) 2026 SunshineMahiru (曦昼Sunshine)。
