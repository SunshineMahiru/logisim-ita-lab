#!/usr/bin/env python3
"""Logisim-ITA 组合逻辑门级仿真器（仅用标准库）。

支持组件（facing=east，即默认朝向）:
  - Pin(输入/输出)、Tunnel(同 label 合并)、wire
  - AND/OR/NOT/NAND/NOR/XOR/XNOR/Buffer Gate（含多输入）
  - Constant(十六进制 value)、Power(=1)、Ground(=0)

不支持（检测到时抛出 UnsupportedCircuitError）:
  - Transistor / 传输门（晶体管级电路）
  - 子电路引用（Subcircuit 实例化）
  - Splitter / 多 bit 总线 / 时序组件

用法:
    import circ_simulator
    sim = circ_simulator.GateSimulator(parsed_circ)
    outs = sim.simulate({"X": 0, "Y": 1, "Z": 0})   # -> {"F": 1}

端口坐标规则（从真实答案文件验证）:
    门输出端口 = loc=(x,y)；输入端口 x 偏移 -30；
    y 偏移: n=1 -> [0]; n=2 -> [-10,+10]; n=3 -> [-10,0,+10]。
"""
import sys
import json

from circ_parser import parse_circ


class UnsupportedCircuitError(Exception):
    pass


# 门输入端口 y 偏移（相对 loc.y），按输入数 n
def _input_offsets(n):
    if n == 1:
        return [0]
    if n == 2:
        return [-10, 10]
    if n == 3:
        return [-10, 0, 10]
    # n>=4 罕见，均匀分布到 [-10,+10] 并取整
    return [round(-10 + 20 * i / (n - 1)) for i in range(n)]


_GATE_FUNCS = {
    "AND Gate": lambda ins: int(all(ins)),
    "OR Gate": lambda ins: int(any(ins)),
    "NOT Gate": lambda ins: int(not ins[0]),
    "NAND Gate": lambda ins: int(not all(ins)),
    "NOR Gate": lambda ins: int(not any(ins)),
    "XOR Gate": lambda ins: sum(ins) % 2,
    "XNOR Gate": lambda ins: int(sum(ins) % 2 == 0),
    "Buffer": lambda ins: int(ins[0]),
}


class _UF:
    """并查集，用于把 wire 端点 / Tunnel 同 label 合并成电气节点。"""

    def __init__(self):
        self.p = {}

    def add(self, x):
        if x not in self.p:
            self.p[x] = x
        return x

    def find(self, x):
        self.add(x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


class GateSimulator:
    def __init__(self, parsed):
        self.main = parsed["main"]
        self.circuits = parsed["circuits"]
        self._build(self.circuits[self.main])

    # ---- 构建网络 ----
    def _build(self, circ):
        self.uf = _UF()
        self.input_pins = []   # (label, coord)
        self.output_pins = []  # (label, coord)
        self.gates = []        # {"name":, "inputs": [coord], "output": coord}
        self.consts = []       # (coord, value)
        self.unsupported = []
        all_points = set()     # 所有组件端口坐标

        tunnels_by_label = {}

        # 第一遍：识别组件、收集端口坐标
        for c in circ["comps"]:
            name = c["name"]
            loc = c["loc"]
            attrs = c["attrs"]

            if name == "Pin":
                all_points.add(loc)
                if attrs.get("output") == "true":
                    self.output_pins.append((attrs.get("label", ""), loc))
                else:
                    self.input_pins.append((attrs.get("label", ""), loc))
            elif name == "Tunnel":
                all_points.add(loc)
                tunnels_by_label.setdefault(attrs.get("label"), []).append(loc)
            elif name in _GATE_FUNCS:
                x, y = loc
                n = 1 if name in ("NOT Gate", "Buffer") else int(attrs.get("inputs", "2"))
                inputs = [(x - 30, y + o) for o in _input_offsets(n)]
                all_points.add(loc)
                for p in inputs:
                    all_points.add(p)
                self.gates.append({"name": name, "inputs": inputs, "output": loc})
            elif name == "Constant":
                self.consts.append((loc, int(attrs.get("value", "0x0"), 16)))
                all_points.add(loc)
            elif name == "Power":
                self.consts.append((loc, 1))
                all_points.add(loc)
            elif name == "Ground":
                self.consts.append((loc, 0))
                all_points.add(loc)
            elif name == "Text":
                pass  # 忽略文字
            else:
                self.unsupported.append(name)

        if self.unsupported:
            raise UnsupportedCircuitError(
                "不支持的组件: " + ", ".join(sorted(set(self.unsupported)))
            )

        # 第二遍：wire 合并端点，并合并所有落在线段上的端口点
        # （端口可能落在 wire 中间而非端点，如 NOT 输入在 (190,300)-(210,300) 中间）
        for (a, b) in circ["wires"]:
            self.uf.add(a)
            self.uf.add(b)
            self.uf.union(a, b)
            for p in all_points:
                if self._on_segment(p, a, b):
                    self.uf.union(a, p)

        # Tunnel：同 label 合并
        for label, locs in tunnels_by_label.items():
            first = locs[0]
            for l in locs[1:]:
                self.uf.union(first, l)

        # 确保所有端口点入并查集（孤立端口也注册为节点）
        for p in all_points:
            self.uf.add(p)

    @staticmethod
    def _on_segment(p, a, b):
        px, py = p
        x1, y1 = a
        x2, y2 = b
        if y1 == y2:  # 水平线段
            return py == y1 and min(x1, x2) <= px <= max(x1, x2)
        if x1 == x2:  # 垂直线段
            return px == x1 and min(y1, y2) <= py <= max(y1, y2)
        return False

    # ---- 求值 ----
    def simulate(self, input_values):
        """input_values: {label: 0/1}。返回 {label: 0/1}。"""
        # 节点值：root -> value (None 表示未知)
        node_val = {}
        known_roots = set()

        def set_val(coord, val):
            r = self.uf.find(coord)
            if r in node_val and node_val[r] != val:
                # 冲突（如短路），保守置 None
                node_val[r] = None
            else:
                node_val[r] = val
                known_roots.add(r)

        # 常量
        for coord, val in self.consts:
            set_val(coord, val)

        # 输入
        for label, coord in self.input_pins:
            if label in input_values:
                set_val(coord, input_values[label])

        # 迭代传播门输出，直到稳定（组合逻辑无环）
        changed = True
        iters = 0
        while changed:
            changed = False
            iters += 1
            if iters > len(self.gates) + 2:
                raise UnsupportedCircuitError("检测到环 / 反馈回路，非纯组合逻辑")
            for g in self.gates:
                out_r = self.uf.find(g["output"])
                if node_val.get(out_r) is not None:
                    continue
                ins = []
                ok = True
                for p in g["inputs"]:
                    v = node_val.get(self.uf.find(p))
                    if v is None:
                        ok = False
                        break
                    ins.append(v)
                if ok:
                    val = _GATE_FUNCS[g["name"]](ins)
                    if node_val.get(out_r) != val:
                        node_val[out_r] = val
                        known_roots.add(out_r)
                        changed = True

        # 输出
        result = {}
        for label, coord in self.output_pins:
            v = node_val.get(self.uf.find(coord))
            result[label] = v
        return result

    def input_labels(self):
        return [l for l, _ in self.input_pins]

    def output_labels(self):
        return [l for l, _ in self.output_pins]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python circ_simulator.py <file.circ> [<json 输入向量>]", file=sys.stderr)
        sys.exit(1)
    parsed = parse_circ(sys.argv[1])
    sim = GateSimulator(parsed)
    ins = {}
    if len(sys.argv) >= 3:
        ins = json.loads(sys.argv[2])
    print("输入:", sim.input_labels(), "输出:", sim.output_labels())
    print(json.dumps(sim.simulate(ins), ensure_ascii=False))
