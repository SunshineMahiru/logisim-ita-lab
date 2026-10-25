# 平台侧实测结论（头歌 EduCoder）

以下结论来自实验3 的实测，**不是推测**，新任务直接照用。

## 1. 评测是怎么跑的

```text
提交目录   /data/workspace/myshixun        （NFS rw，评测的 cwd 就是它）
评测链     protectspace/evaluate.sh
             cd /data/workspace/myshixun
             sourceClassNames=("secret/1.sh" … "secret/5.sh")
             echo <用例> | base64 -d | bash secret/N.sh | base64
调度层     platform/eva/{execEva.sh, execStepOut.sh, evaluate.sh, commitImage.sh}
```

- 判定逻辑在 `secret/N.sh` 与 `lab3.N.chk.circ` 里，`platform/eva/*` 只负责调度和进度日志。
- 用例走 **stdin**，结果 base64 回传；一次评测对应一次 commit（`git log` 里是一串 `file change`）。
- 因为 cwd 是 `myshixun`，`.circ` 里的 `file#xxx.circ` 就按该目录解析；指向别处就会报
  `required library file 'xxx.circ' is missing`。
- **`secret/` 在编辑容器里是 0 字节占位**（连 `.git/objects` 都是空的），真实内容只在评测镜像里。
  不要在编辑容器里翻 checker，浪费时间。

## 2. 时钟约定（最容易翻车的一条）

- **边沿方向因关卡而异，不要一概而论**：实验3 中 3.1、3.5 实测必须 `rising`
  （用 falling 时首拍丢失），而 3.2 的通过件里 4 个触发器全是 `falling` 也能过。
  结论：**每关先按题面/参考件确认，再用第 3 节的判据反推**，不要跨关套用。
- 实验3.1 的实测：平台每行产生 `CLK=0 → CLK=1`，**行末停在高电平**。
- 所以 D 触发器必须 `trigger="rising"`。用 `falling` 时，第一行的沿会被推迟到下一行，
  现象是：**第一行「沿后」没有变化，第二行起每行恰好变化一次**。
- 判定表常按「沿前 / 沿后」打印两列。某行两列相同 ⇒ 该行没有产生有效沿，先查边沿方向。

## 3. 从平台回报反推故障（对照表）

| 回报特征 | 结论 | 处置 |
|---|---|---|
| 实际序列整体平移一行 | 采样点或边沿数不匹配 | 调边沿方向，或加/减一个空闲态 |
| 只有第一行错、其余全对 | 首个时钟沿被吃掉 | 触发器改 `rising` |
| 输出恒为全 1 / 全 0 / `X` | 网络短接，或控制脚被常量直接接住 | 查导线端点是否压在别的隧道上；`Register` 的 `EN/CLR/SET` 全悬空 |
| 某一位恒错、其余位对 | 该位 `trigger` 与其它位不一致 | 全部统一 |
| 加载/库错误 | `.circ` 引用了外部文件或缺子电路定义 | 见第 4 节 |

## 4. 子电路与外部引用（按同目录解析）

`<lib desc="file#lab3.1.circ" name="8"/>` 这类引用**按 .circ 所在目录解析**，不是错误写法。
实测：`lab3.5.circ` 里 7 个 `CNTR4U` 实例，就是从同目录的 `lab3.1.circ` 取到子电路的：

```bash
java -jar "$LOGISIM_JAR" -tty stats -nosplash lab3.5.circ | tail -3
# 7   7  CNTR4U   lab3.1      ← 第三列就是来源文件
```

- 好处：跨关复用子电路，不必内联；
- 代价：被引文件缺失或被改坏，引用方连带失败。**改动被引文件前先备份**：
  `WORK=$(mktemp -d)`，再 `cp x.circ "$WORK/x.good"`；
- 单文件审计会误判：只读 `lab3.5.circ` 会以为「缺子电路定义、加载不了」，实际能加载；
  反过来，只看单文件也看不出它依赖同目录的另一份文件；
- 要绝对稳，就把子电路内联成 `<circuit>`；要省事，就接受这条隐式依赖并把它记下来。

## 5. 文件通道（网页编辑器不可靠）

实测：网页编辑器保存后，容器里的文件可能仍是模板或旧稿。**每次提交前用 `ls -l` 与 `md5sum`
和本地对比**，不要相信编辑器的「已保存」。

传输方式（容器无共享目录时唯一可行）。先在本地准备一个会话目录，不要把中间文件写进固定路径：

```bash
WORK=$(mktemp -d)                                   # 本地
gzip -9 < labN.M.circ | base64 > "$WORK/p.b64"
# 再按任意方式切成若干段，只要能逐段核对字符数即可
```

容器侧逐段 `cat >>` 追加，每段后核对字符数：

```bash
tr -d '\n' < "$WORK/p.b64" | wc -c      # 必须等于本地 base64 总长
base64 -di "$WORK/p.b64" | gunzip > /data/workspace/myshixun/labN.M.circ
md5sum /data/workspace/myshixun/labN.M.circ
```

- `base64 -di` 能容忍**插入的空格**（实测：插 5 个空格仍能正确还原）；
- 但**丢字符**会让 `gunzip` 报 CRC error——按段核对字符数即可定位到具体哪一段。

## 6. 提交前自检清单

```bash
grep -c 'desc="file#'           目标.circ   # 0
grep -c 'val="falling"'         目标.circ   # 该关要求 rising 时为 0，见第 2 节
java -cp "$CP" Conn 目标.circ               # 只剩刻意悬空的 ~Q
java -jar "$LOGISIM_JAR" -tty stats -nosplash 目标.circ | head   # 能列出统计即可加载
md5sum 目标.circ                            # 与本地一致
```

五项全过再提交；任何一条不过，先修再评，别浪费一轮。

## 7. 编辑器保存的副作用与两处计数陷阱

1. **保存即整体重写**。页面点一次保存，文件被重新序列化——缩进、属性顺序全变，
   体积可能缩掉上千字节（实测 41,162 → 39,573），`md5` 必然改变；
   但 `<comp>` / `<wire>` 数量不变，**元件不丢、语义不变**。
2. **等于默认值的属性会被删掉**。`trigger` 默认是 `rising`，所以保存后
   `grep 'val="rising"'` 会变成 **0**——这不代表被改回 `falling`。
   校验只看方向是否符合该关要求（第 2 节）。
3. **`grep -c 'name="D Flip-Flop"'` 会把 `<lib>` 里的工具栏条目算进去**，
   真实元件数要减 1；`<comp` 的计数才是准的。

## 8. 上传通道不可靠，写盘才可靠

**实测事实**：网页端「上传/导入」有概率把文件改写（同一文件多次上传，容器里的 md5 会变，
内容可能被截断或只写入一部分）。因此**不要用上传是否成功来推断文件是否正确**。

可靠写法（三选一，都要求写完立刻对账）：

```bash
# A. 直接写盘（推荐，配合 gzip+base64 分段）
base64 -di "$WORK/p.b64" | gunzip > /data/workspace/myshixun/labN.M.circ
md5sum /data/workspace/myshixun/labN.M.circ      # 必须与本地一致

# B. 文本粘贴（在编辑器里粘全文再保存）：可行，但要复核 <comp> 计数
grep -c '<comp' 文件.circ

# C. heredoc 直写纯文本
cat > 文件.circ <<'EOF'
...XML...
EOF
```

判据：**md5（写盘路径）或 `<comp>` 计数（粘贴路径）对上再评测**；
不一致就重写，不要反复重试上传。

## 9. 跨文件 / 跨实验依赖

平台原件里会出现指向别的实验文件的 `<lib>`：

```xml
<lib desc="file#lab2.5.circ" name="8"/>
<comp lib="8" loc="(280,340)" name="32"/>
```

`lab2.5.circ` 不在实验四的工作区，加载时就报
`The required library file 'lab2.5.circ' is missing`；引用它的 `lab4.5` 跟着一起失败。

**副本差异要说清**，否则按字面查会查不到：

| 副本 | 是否带这条 `<lib>` | 原因 |
|---|---|---|
| `测试用目录/myshixun/lab4.4.circ` | 有 | 平台原始下载（`source="2.16.1.3.jar"`） |
| `原始未改动目录/myshixun/lab4.4.circ` | 无 | 曾被 2.16.2.0 打开并重存（`source` 变为 `2.16.1.4.exe`），重存时丢掉 |
| `已完成目录/myshixun/lab4.4.circ` | 无 | 重画成 5 级桶形，不留子电路实例 |

实验4 的完整依赖链见 `exp4-tasks.md` 的「依赖结构」表，这里只留诊断方法与处置原则。

### 诊断三步

```bash
# 1. 列出每份文件的外部依赖
for f in lab4.*.circ; do
  echo -n "$f -> "
  grep -o 'desc="file#[^"]*"' "$f" | sed 's/.*file#//;s/"//' | tr '\n' ' '
  echo
done

# 2. 确认被引文件是否就在同目录（只有同目录才解析得到）
ls

# 3. 用 stats 第三列看实际来源文件
java -jar "$LOGISIM_JAR" -tty stats -nosplash lab4.5.circ | tail -6
#    1  1  Adder32     lab4.3        ← 第三列即来源
#    1  1  Shifter32   lab4.4
```

### 处置原则

1. 被引文件不在本工作区时，**不要指望平台补**——把该功能重画进本文件（实验4 的 `lab4.4`
   是把整个桶形移位器重画，没有搬 `lab2.5` 进来）。把别的实验目录的文件拷进本工作区是否
   有效，未逐条验证；提交时只认本次实验目录，先按无效处理。
2. **从依赖链最底层往上修**：某个文件加载失败，所有引用它的文件都会连带失败。
   先让被引方（如 `lab4.4`）能加载，再看引用方（`lab4.5`）。
3. 修好底层后，上层往往**一行不用改**就能过——实验4 的 `lab4.5` 就是这样，
   说明「逻辑看着对却过不了」时，先查依赖能不能加载，别急着改逻辑。

### 另一个容易误判的点：电路名不一定叫 `main`

实验4：`lab4.4` 的电路名是 `Shifter32`，`lab4.5` 是 `ALU`。用驱动测试前先 `Dump 文件`
看 `### circuit` 行；名字不对会得到「没有任何 snap」的空结果，很容易误以为电路没跑。

