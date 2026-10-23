# Logisim-ITA `.circ` 文件格式参考手册

本文档描述头歌「计算机组成原理」实验使用的 **Logisim-ITA 2.16.2.0** 所采用的
`.circ` 文件语法。`.circ` 本质是 UTF-8 编码的 XML，可直接用文本编辑。本文档的内容全部
从本地实验样本（成对的「原始模板」与「已通过答案」）反推并交叉验证得出。

---

## 1. 文件整体结构

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="2.16.2.0.jar" version="1.0">
This file is intended to be loaded by Logisim http://logisim.altervista.org
  <lib desc="#Wiring" name="0"> ... </lib>
  <lib desc="#Gates" name="1"> ... </lib>
  ...（其余 lib 定义块）...
  <main name="main"/>
  <options> ... </options>
  <mappings> ... </mappings>
  <toolbar> ... </toolbar>
  <circuit name="main"> ... </circuit>
</project>
```

各层级的顺序与含义：

| 标签 | 说明 |
|------|------|
| `<project source=... version="1.0">` | 根节点。`source` 是保存时的版本（模板为 `2.16.1.4.exe`，环境保存后变为 `2.16.2.0.jar`）。评测对 `source` 不敏感，**不要改动**。 |
| `<lib desc=... name="N">` | 库/组件面板定义。`name` 是库编号，`desc` 是显示名。此块保存的是「该文件编辑器里显示哪些工具」，**不影响**电路逻辑。 |
| `<main name="X"/>` | 指定主电路（顶层电路）的名字。各任务不同：任务1/3/4 为 `main`，任务2 为 `cmos_or`，任务5 为 `4-1MUX`。**不要改**，除非题目明确要求改主电路。 |
| `<options>` `<mappings>` `<toolbar>` | 仿真与界面配置，**保持原样，不要动**。 |
| `<circuit name="X">` | 一个电路（顶层或子电路）。一个文件可有多个 `<circuit>` 块（子电路）。 |

**关键约束**：题目几乎都写明「请勿更改电路封装、修改/移动/增删引脚」。因此生成电路时，
只允许在 `<circuit>` 块内**新增 `<wire>` 和 `<comp>`**，并保持已有的 Pin / Tunnel / Text /
`<appear>`（封装）原样不动。

---

## 2. 坐标系统

- 坐标单位是整数，`loc="(x,y)"` 表示组件锚点。
- 组件一般放在 **10 的倍数** 的坐标上；连线端点必须精确落在组件端口上，否则该端口悬空。
- 连线是**正交的**（水平或垂直），拐角处拆成多段直线。`<wire from="(x1,y1)" to="(x2,y2)"/>`
  的两端点坐标必须满足 `x1==x2` 或 `y1==y2`。

---

## 3. 基本元素

### 3.1 连线 `<wire>`

```xml
<wire from="(10,10)" to="(10,100)"/>
```

- 表示一段直线，从 `from` 到 `to`。
- 交叉但不同时是端点的两条线不导通；**T 形 / 十字**（端点落在另一条线中间）自动导通。
- Logisim 会根据端点自动合并成网络。生成时按「信号名 → 折线路径」逐段写 wire 即可。

### 3.2 组件 `<comp>`

```xml
<comp lib="0" loc="(90,50)" name="Pin">
  <a name="tristate" val="false"/>
  <a name="label" val="X"/>
  <a name="labelloc" val="west"/>
  <a name="labelfont" val="Dialog plain 12"/>
</comp>
```

- `lib`：所属库编号（见第 4 节）。
- `loc`：锚点坐标。
- `name`：组件名。
- 子元素 `<a name="属性" val="值"/>` 描述组件属性；**属性可以缺省**（用默认值）。

### 3.3 引脚 `<comp lib="0" name="Pin">`

| 属性 | 输入引脚 | 输出引脚 |
|------|----------|----------|
| `tristate` | `"false"` | 省略 |
| `facing` | 省略（默认 east，尖端朝右） | `"west"`（尖端朝左） |
| `output` | 省略 | `"true"` |
| `label` | 信号名，如 `X` | 信号名，如 `F` |
| `labelloc` | `"west"` | `"east"` |

连接点就是 `loc`。**输入引脚 = 电路的输入端口，输出引脚 = 输出端口**，评测靠 label 识别，
因此 label 必须与题目给定完全一致，且不得增删。

### 3.4 隧道标签 `<comp lib="0" name="Tunnel">`

```xml
<comp lib="0" loc="(150,200)" name="Tunnel">
  <a name="label" val="X"/>
</comp>
```

- `label` 相同的所有 Tunnel **电气上等同一条线**（无需画线连接）。
- 这是头歌实验的标准用法：题目已放好输入 Tunnel（如 `X`/`Y`/`Z`）与输出 Tunnel（如 `F`），
  学生只需在空白区放置同 label 的 Tunnel 把信号「引下来」再接到门电路上。
- `facing` 只影响 label 文字方向，不影响连接。连接点即 `loc`。

### 3.5 电源与地 `<comp lib="0" name="Power"/Ground">`

```xml
<comp lib="0" loc="(210,210)" name="Power"/>
<comp lib="0" loc="(210,390)" name="Ground"/>
```

- 晶体管级电路（任务2/4/5）必须用 `Power`（VDD，逻辑 1）和 `Ground`（逻辑 0）。

---

## 4. 库编号对照表

| lib 编号 | desc | 常用组件 |
|----------|------|----------|
| `0` | #Wiring | Pin、Tunnel、Transistor、Power、Ground、Constant、Splitter |
| `1` | #Gates | NOT Gate、AND Gate、OR Gate（以及 NAND/NOR/XOR/XNOR/Buffer 等） |
| `2` | #TTL | 7400/7402/7404/7408/7432/7486 等 74 系列芯片 |
| `3` | #Plexers | Multiplexer、Demultiplexer、Decoder、Priority Encoder |
| `4` | #Arithmetic | Adder、Subtractor、Multiplier、Divider、Comparator、Shifter |
| `5` | #Memory | D/T/J-K/S-R Flip-Flop、Register、Counter、RAM、ROM |
| `6` | #I/O | Button、Switch、LED、Hex Digit Display、Digital Oscilloscope |
| `7` | #Base | Text、Poke Tool、Edit Tool（文字标注） |

> 说明：`<lib>` 块里只列了模板作者放进工具栏的那几个工具（如 #Gates 只列了 NOT/AND/OR），
> 但这**不是**对可用组件的限制——`<comp lib="1" name="XOR Gate"/>` 只要组件名是 Logisim 内置
> 名称即可被识别。不过为评测稳妥，**优先使用 AND/OR/NOT 组合**，除非题目明确要求其他门。

---

## 5. 门电路（lib=1）

门电路**默认 facing=east（输出朝右）**，`loc` 是**输出端口**，输入端口在左侧。

### 端口坐标公式（facing=east）

设门锚点 `loc = (x, y)`，输入数为 `n`：

| 门类型 | 输出端口 | 输入端口 |
|--------|----------|----------|
| NOT Gate（n=1） | `(x, y)` | `(x-30, y)` |
| 2 输入门（AND/OR/NAND/NOR/XOR/XNOR） | `(x, y)` | `(x-30, y-10)`、`(x-30, y+10)` |
| n 输入门（`<a name="inputs" val="n"/>`） | `(x, y)` | `(x-30, y + (i - (n-1)/2)·10)`，i=0..n-1 |

> 本规则从真实答案文件验证得出（见 lab1.1 的 3 输入 OR、lab1.3 的 2 输入 AND/NOT）。

### 示例

```xml
<!-- 三输入或门 -->
<comp lib="1" loc="(370,260)" name="OR Gate">
  <a name="inputs" val="3"/>
</comp>
<!-- 二输入与门（inputs 可省略，默认 2） -->
<comp lib="1" loc="(270,210)" name="AND Gate"/>
<!-- 非门 -->
<comp lib="1" loc="(230,300)" name="NOT Gate"/>
```

`inputs` 属性省略时默认 2。多数表决器 `F = XY + YZ + XZ` 的完整门级实现可参照
`references/exp1-tasks.md` 的坐标布局。

---

## 6. 晶体管（lib=0，任务2/4/5 专用）

```xml
<!-- NMOS -->
<comp lib="0" loc="(210,330)" name="Transistor">
  <a name="type" val="n"/>
  <a name="facing" val="north"/>
</comp>
<!-- PMOS（省略 type 即 p 型） -->
<comp lib="0" loc="(210,280)" name="Transistor">
  <a name="facing" val="south"/>
</comp>
<!-- 双向传输门（transmission gate） -->
<comp lib="0" loc="(250,230)" name="Transistor">
  <a name="gate" val="br"/>
</comp>
```

| 属性 | 值 | 含义 |
|------|-----|------|
| `type` | 省略 / `"n"` | 省略=P 型（PMOS），`"n"`=N 型（NMOS） |
| `gate` | `"br"` | 双向传输门（PMOS+NMOS 并联，用于 2 选 1 选择器） |
| `facing` | `north/south/east/west` | 晶体管朝向，决定三个端子（栅极/源/漏）的物理位置 |

- CMOS 静态电路结构：**上拉网络用 PMOS 接 Power（VDD），下拉网络用 NMOS 接 Ground**；
  或非门 = 两个 PMOS 串联在上拉 + 两个 NMOS 并联在下拉；非门 = 一个 PMOS + 一个 NMOS。
- 传输门实现 2 选 1：`Y = (D0·~S) + (D1·S)`，用两对互补控制的传输门。
- 具体晶体管级坐标布局复杂，**以 `references/exp1-tasks.md` 里已通过答案的坐标为准**，
  新任务优先复用同样的拓扑，仅平移坐标。

---

## 7. 子电路（Subcircuit，任务5 专用）

### 7.1 子电路定义

一个 `<circuit name="子电路名">` 块就是一个子电路。其内部结构与顶层电路相同，但可以带一个
`<appear>` 块描述封装外观（符号轮廓 + 端口位置）：

```xml
<circuit name="2-1MUX">
  <a name="circuit" val="2-1MUX"/>
  ...
  <appear>
    <polyline fill="none" points="40,30 40,90" stroke="#000000"/>
    <circ-port height="8" pin="140,40" width="8" x="36" y="46"/>
    <circ-anchor facing="east" height="6" width="6" x="77" y="57"/>
  </appear>
  <wire .../> <comp .../>
</circuit>
```

`<appear>` 是「电路封装外观」，**严禁改动**（题目明令禁止）。子电路的输入/输出端口由内部
`Pin` 组件（input 与 output）定义，端口名即 label。

### 7.2 子电路引用（实例化）

```xml
<comp loc="(340,220)" name="2-1MUX"/>
```

- **没有 `lib` 属性**，`name` 直接是子电路名。
- `loc` 是实例锚点；子电路实例的端口位置由 `<appear>` 里的 `circ-port` 决定，
  连线端点必须落在对应端口坐标上。生成子电路连线时，**严格照抄答案文件的坐标**，不要自己推导。

### 任务5 结构（4 选 1 多路选择器）

```
<main name="4-1MUX"/>
<circuit name="4-1MUX">  ← 顶层，实例化 3 个 2-1MUX
<circuit name="2-1MUX">  ← 子电路，用传输门+晶体管实现
```

---

## 8. 文字标注（lib=7）

```xml
<comp lib="7" loc="(235,166)" name="Text">
  <a name="text" val="3输入多数表决器电路"/>
  <a name="font" val="Dialog plain 12"/>
</comp>
```

仅作提示文字，不参与逻辑。生成电路时**不要新增/删除**这些 Text。

---

## 9. 生成电路的铁律（务必遵守）

1. **只增不改**：在 `<circuit>` 块内新增 `<wire>` 与 `<comp>`，绝不动已存在的 Pin / Tunnel /
   Text / `<appear>` / `<main>` / `<options>`。
2. **引脚标签一致**：输入/输出引脚与 Tunnel 的 label 必须与题目给出的完全一致（区分大小写）。
3. **坐标对齐**：门输出=loc，输入=公式计算；连线端点精确落在端口坐标；全部用 10 的倍数。
4. **正交布线**：每段 wire 只能水平或垂直。
5. **优先门级**：能用 AND/OR/NOT 就用它们；只有题目要求（如「用晶体管」「用传输门」）才用
   Transistor。
6. **复用拓扑**：同类题目（如多数表决器、2 选 1/4 选 1 选择器）直接复用答案文件的拓扑与坐标，
   仅做平移，不重新发明。
7. **保存版本**：生成后不必修改 `<project source>`；环境保存后会自动更新为 `2.16.2.0.jar`。
