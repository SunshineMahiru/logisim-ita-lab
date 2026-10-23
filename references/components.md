# 组件端口坐标（实测）

坐标一律相对组件的 `loc`（`<comp loc="(x,y)">`）。门与触发器的默认朝向为 `facing=east`，
此时 `loc` 就是输出端。**新增组件前先 `java -cp "$CP" Dump <file.circ> [电路名]` 量一遍，
不要凭记忆推坐标。**

| 组件 | 端口坐标（相对 `loc`） | lib |
|---|---|---|
| NOT / Buffer | 入 `(-20,0)`；出 `(0,0)` | 1 |
| AND / OR | 入 `(-30,±10)`；出 `(0,0)` | 1 |
| NAND / NOR / XOR | 入 `(-40,±10)`；XNOR 为 `(-50,±10)` | 1 |
| n 输入门 | 奇数 n 居中步长 10；偶数 n **跳过 0**（n=4 → `-20,-10,+10,+20`） | 1 |
| Transistor | PMOS 为默认；`type="n"` 为 NMOS；传输门用 `gate="br"` | 0 |
| Splitter | 主干 `(0,0)`、第 i 个扇出 `(+20, -10×fanout + 10×i)` | 0 |
| Constant / Power / Ground | 输出端在 `loc`；Power 恒 1、Ground 恒 0 | 0 |
| D Flip-Flop | `Q(0,0)`、`~Q(0,40)`、`CLK(-60,0)`、`D(-60,40)`、`SET(-30,-20)`、`CLR(-30,60)`（CLR/SET **高有效**） | 5 |
| Register | `Q(0,0)`、`D(-30,0)`、`CLK(-20,20)`、`CLR(-10,20)`、`GATE(-30,10)`、`EN(-30,-10)`、`SET(-10,-20)` | 5 |
| Adder | `X(-40,-10)`、`Y(-40,10)`、`F(0,0)`、`Cin(-20,-20)`、`Cout(-20,20)` | 4 |
| Multiplexer(sel=n) | 数据 `(-40, -160…+150)`、选择 `(-20,+160)`、使能 `(-10,+160)`、出 `(0,0)` | 3 |
| Demultiplexer | 出 `(+40, -160…+150)`、选择 `(+20,+160)`、使能 `(+10,+160)`、入 `(0,0)` | 3 |

## 三条实测注意事项

1. **`Register` 的 `GATE` 才是写使能**。`EN` 拉低会让 `Q` 变成 unknown，不能当写使能用。
2. **`Register` 的 `EN`/`CLR`/`SET` 三个脚全部悬空**，只接 `CLK` 与 `GATE`，实测有效；
   让它们被常量直接接住，读出会是 `0xFFFFFFFF`。
3. **D 触发器的 `trigger` 全部统一为 `falling`**，与模板一致；改过某一位的
   `trigger`（`high`/`low` 电平敏感）会造成「某一位总是错、其余位对」。

## 多输入门的输入位置

输入数 n 决定端口的 y 相对位置：奇数 n 围绕 `loc.y` 居中、步长 10；偶数 n 跳过 0，
向上向下对称展开。`<a name="inputs" val="3"/>` 显式写输入数，省略时默认 2。

## 组件库编号速查

| lib | desc | 常用组件 |
|---|---|---|
| 0 | #Wiring | Pin、Tunnel、Transistor、Power、Ground、Constant、Splitter |
| 1 | #Gates | NOT/AND/OR/NAND/NOR/XOR/XNOR/Buffer Gate |
| 2 | #TTL | 7400/7402/7404/7408/7432/7486 等 74 系列芯片 |
| 3 | #Plexers | Multiplexer、Demultiplexer、Decoder、Priority Encoder |
| 4 | #Arithmetic | Adder、Subtractor、Multiplier、Divider、Comparator、Shifter |
| 5 | #Memory | D/T/J-K/S-R Flip-Flop、Register、Counter、RAM、ROM |
| 6 | #I/O | Button、Switch、LED、Hex Digit Display、Digital Oscilloscope |
| 7 | #Base | Text、Poke Tool、Edit Tool（文字标注） |
| 8 | 子电路文件 | `<lib desc="file#x.circ" name="8"/>` 引用同目录的另一个 `.circ` |

完整对照与 `<lib>` 块的语义见 `circ-format.md` 第 4 节。注意 `<lib>` 块里只列了模板作者放进
工具栏的那几个工具，这不是对可用组件的限制——只要组件名是 Logisim 内置名称即可被识别；但为
评测稳妥，优先用 AND/OR/NOT 组合，除非题目明确要求其他门。

`Text` 属于 lib 7（见 `circ-format.md` 第 8 节），写生成代码时别按 lib 0 处理。

