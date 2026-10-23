---
name: logisim-ita-lab
description: 用于完成头歌「计算机组成原理」线上实验的 Logisim-ITA 电路设计：从题面提取引脚与真值表、以文本方式生成 .circ 电路、用门级仿真或真实引擎驱动逐拍对拍验收。当用户给出 Logisim 实验题目或 .circ 模板并要求绘图、补全、验证电路时使用；涉及 Logisim、.circ、头歌、EduCoder、数字逻辑、CMOS、多路选择器、触发器、时序电路时同样适用。
license: MIT
---

# Logisim-ITA 实验电路设计

## 概述

头歌平台的「计算机组成原理」实验使用 **Logisim-ITA 2.16.2.0**（意大利分支）作为电路
编辑器。平台提供模板 `.circ` 文件（已放好输入/输出引脚、隧道标签、提示文字），学生在其上
绘制电路，评测端加载 `.circ` 并用真值表判定是否通过。

`.circ` 本质是 **UTF-8 编码的 XML**，可以完全用文本编辑。本 skill 让工作流为：分析题目
→ 设计电路拓扑 → 生成 `.circ` XML 文本 → 验证。组合逻辑用门级仿真器对拍真值表；时序电路
走真实引擎驱动，规程见 `references/timing-verification.md`。

## 何时使用

- 用户给出实验题目（`.docx` 或文字 + 电路图），要求「做这道 Logisim 实验 / 画这个电路」。
- 用户给出模板 `.circ` 与要求，需要生成/补全电路。
- 需要验证某个 `.circ` 是否符合给定真值表。
- 涉及后续实验模块：同步时序部件、运算部件（ALU/加法器）、存储器与数据通路、单周期 CPU。

不适用：题目要求用 Verilog 仿真、需要改动 Logisim-ITA 自身的 Java 源码，或与 `.circ`
无关的纯理论推导。

## 工作流程

按顺序执行，每步产出可复用的中间结果。

### 第 1 步：提取题目需求

从题目文档（或用户描述）中提取四要素：

1. **逻辑表达式 / 功能**（如 `F = XY + YZ + XZ`、`Y = D0·~S + D1·S`）。
2. **输入/输出引脚 label 与顺序**（必须与模板一致，评测靠 label 识别端口）。
3. **真值表 / 样例输出**（判定标准，用于第 5 步验证）。
4. **实现约束**（「用基本逻辑门」「禁止用逻辑门，只用晶体管」「用传输门」「封装成子电路」）。

若题目是 `.docx`，先解包提取 `word/document.xml` 文本与 `word/media/` 图片。临时目录用
`mktemp -d` 生成，不要写死固定路径：

```bash
WORK=$(mktemp -d) && unzip -o 题目.docx -d "$WORK" && cat "$WORK/word/document.xml"
```

真值表通常在「测试说明 / 样例输出」段。已知任务可跳过此步，直接查
`references/exp1-tasks.md`（实验1 的 5 个任务已沉淀）。

### 第 2 步：读取模板 .circ

解析目标模板，确认已有的引脚、隧道、主电路名：

```bash
python scripts/circ_parser.py <模板.circ>
```

关注：

- `<main name="...">` 指定的主电路名（可能不是 `main`，如 `cmos_or`、`4-1MUX`）。
- 已有 Pin（label、input/output）、Tunnel（label）、Text 提示。这些**必须原样保留**。
- 空白区域，用于放置新组件。

### 第 3 步：设计电路拓扑

根据实现约束选组件类型：

| 约束 | 组件 | lib |
|------|------|-----|
| 基本逻辑门 | AND/OR/NOT（及 NAND/NOR/XOR/XNOR）Gate | 1 |
| 只用晶体管 | Transistor（PMOS=默认 / `type="n"`=NMOS）+ Power/Ground | 0 |
| 传输门 | Transistor `gate="br"` | 0 |
| 子电路级联 | 定义 `<circuit name>` + 实例化 `<comp name>` | — |

同类题目**直接复用** `references/exp1-tasks.md` 里的拓扑与坐标，只做平移，不重新发明。
新拓扑设计时遵循：信号从左到右、输入 Tunnel 在上、输出在下或右。

### 第 4 步：生成 .circ XML

语法与坐标规则以 `references/circ-format.md` 为准，组件端口坐标以
`references/components.md` 为准。生成时必须遵守三条：

- **只增不改**：在目标 `<circuit>` 块内新增 `<wire>` 与 `<comp>`，绝不动已有 Pin/Tunnel/
  Text/`<appear>`/`<main>`/`<options>`。
- **组件端口必须由导线引出**：把 Tunnel 直接压在门或触发器端口上不导通，必须
  `端口 ← 20px 导线 → 隧道`。
- **隧道必须位于导线端点上**：它只认导线端点，不认组件端点；导线穿过某个隧道点时也会连上，
  这是短接的主要来源。

连线 `<wire from="(x,y)" to="(x,y)"/>` 只能水平或垂直，端点位于组件端口上。同 `label` 的
Tunnel 电气等价，无需画线互连。坐标一律取 10 的倍数；引脚与隧道 label 与题目完全一致
（区分大小写）。

产出 = **完整的 .circ 文件文本**（或相对模板的 diff 说明）。交付给用户时给全文，用户可直接
粘贴保存为 `.circ`。

### 第 5 步：验证

按电路类型走三条路，不要混用：

| 电路类型 | 验证手段 | 命令 |
|---|---|---|
| 纯组合逻辑（AND/OR/NOT 等） | 门级仿真对拍真值表 | `python scripts/validate.py <生成.circ> --task lab1.3` |
| 晶体管级 / 子电路级 | 本地 Logisim-ITA 打开人工核对 | 见下节 |
| 时序电路（D 触发器 / Register / Counter / 时钟） | 真实引擎逐拍对拍 | 见 `references/timing-verification.md` |

自定义真值表用 `--table-file truth.json`；`validate.py` 返回码：`0`=全对，`1`=有错，
`2`=无法自动仿真。时序电路不要用门级仿真器，也不要只靠肉眼核对。

执行顺序固定为：`采集期望值 → 生成 → 结构自检 → 功能对拍 → 时序校准 → 全量回归`。
不要跳过结构自检直接跑功能：一个误短接会让几十行全部 `X`，把真正的逻辑错误淹没。

## 本地 Logisim-ITA 核对

晶体管级、子电路级与时序电路需要 GUI 核对，或需要跑真实引擎。用环境变量指路，不要把
本机路径写进脚本：

| 变量 | 含义 | 缺省 |
|---|---|---|
| `LOGISIM_JAVA` | java 可执行文件 | PATH 中的 `java` |
| `LOGISIM_JAR` | `Logisim-ITA.jar` 路径 | `Logisim-ITA-2.16.2.0/Logisim-ITA.jar` |
| `LOGISIM_TOOLS` | `CircRun` 等驱动的编译输出目录 | `tools` |

```bash
export LOGISIM_JAR="<解压目录>/Logisim-ITA-2.16.2.0/Logisim-ITA.jar"
"${LOGISIM_JAVA:-java}" -jar "$LOGISIM_JAR"
```

打开后：File → Open 加载 `.circ` → 用 Poke 工具点击输入引脚改变电平 → 观察输出 LED/引脚
是否符合真值表 → 确认无红色错误标记（悬空/短路）。Java 路径不确定时用 `where java`
（Windows）或 `command -v java` 定位。

## 资源

- `references/circ-format.md` —— `.circ` 语法大全（XML 结构、lib 编号、组件属性、端口坐标
  规则、生成铁律）。**生成电路前必读**。
- `references/components.md` —— 组件端口坐标实测表（门、D 触发器、Register、Adder、
  Multiplexer、Splitter），新增组件前先查这里。
- `references/timing-verification.md` —— 同步时序电路测试与验收规程（期望值固化、结构自检、
  功能对拍、时序约定校准、验收标准、异常对照表、数字时钟参考实现）。
- `references/platform-notes.md` —— 头歌评测机制、时钟约定、外部库引用、文件传输通道、
  提交前自检清单等平台侧实测结论。
- `references/exp1-tasks.md` —— 实验1 的 5 个任务知识库（逻辑、引脚、真值表、拓扑、坐标），
  同时是新任务的范例格式与回归真值表来源。

脚本分两组，按验证路径取用：

- **纯 Python（组合逻辑）**：`scripts/circ_parser.py`（解析 `.circ` 为结构化 JSON）、
  `scripts/circ_simulator.py`（门级仿真器，含多输入门、Tunnel、Power/Ground）、
  `scripts/validate.py`（真值表对拍入口，内置实验1 真值表，支持自定义 JSON）。
- **真实引擎（时序 / 结构检查）**：`scripts/CircRun.java`（无头驱动：加载 `.circ` → poke
  引脚 → `propagate` → 读输出，支持 `set / snap / clk / clkrise`）、`scripts/runner.py`
  （Python 侧封装，`run(circ, circuit, cmds)` 返回逐行快照）、`scripts/circlib.py`
  （`.circ` 文本生成库，自带坐标冲突检查）、`scripts/Conn.java`（列出悬空端点）、
  `scripts/Dump.java`（打印组件实际端口坐标）、`scripts/ErrLoad.java`（捕获加载错误文案）。

自检脚本 `scripts/selftest.py` 用纯 Python 跑通「解析 → 生成 → 仿真 → 对拍」全链路，
不依赖 Java；改动脚本后先跑它。

## 扩展新实验任务

1. 在 `references/exp1-tasks.md` 按同样格式追加任务（逻辑、引脚、真值表、约束、拓扑）。
2. 在 `scripts/validate.py` 的 `BUILTIN` 字典注册该任务的真值表生成函数。
3. 若新任务引入新组件（加法器、寄存器、ROM 等），先 `Dump` 量端口坐标，补进
   `references/components.md`，再写生成代码；不要凭记忆推坐标。
4. **时序电路一律按 `references/timing-verification.md` 的流程验证**：结构自检 → 功能对拍 →
   时序约定校准，三步齐全才算通过。门级仿真器只用于纯组合逻辑。
5. 一个任务一对脚本（`build_labNM.py` / `test_labNM.py`），脚本只依赖 `runner.py` 与
   `circlib.py`；期望值写在测试脚本里，不要为了过测试把常数烧进逻辑。
6. 平台差异（版本、外部库、采样约定）属于环境事实，发现一次就回写
   `references/platform-notes.md`，不要每次重新试。
