#!/usr/bin/env python3
"""对拍验证：加载 .circ -> 门级仿真 -> 与真值表比对。

用法:
    python validate.py <file.circ> --task lab1.1
    python validate.py <file.circ> --table-file truth.json

--task 内置实验1的 5 个任务真值表（从题目文档提取）。
--table-file 自定义真值表，JSON 格式:
    {"inputs": ["X","Y"], "outputs": ["F"],
     "cases": [{"in": [0,0], "out": [0]}, {"in": [1,1], "out": [1]}]}

返回码: 0=全部通过; 1=存在失败; 2=无法自动仿真(晶体管/子电路等，需本地 Logisim-ITA 核对)。
"""
import sys
import json
import argparse
from itertools import product

from circ_parser import parse_circ
from circ_simulator import GateSimulator, UnsupportedCircuitError


# ---- 实验1 内置真值表（程序化生成，来源: 各任务 docx 的「样例输出」）----
def _truth_table_1_1():
    # 多数表决器 F = XY + YZ + XZ
    inputs, outputs = ["X", "Y", "Z"], ["F"]
    cases = [
        {"in": [x, y, z], "out": [1 if (x + y + z) >= 2 else 0]}
        for x, y, z in product([0, 1], repeat=3)
    ]
    return inputs, outputs, cases


def _truth_table_1_2():
    # 晶体管或门 Z = X | Y
    inputs, outputs = ["X", "Y"], ["Z"]
    cases = [{"in": [x, y], "out": [x | y]} for x, y in product([0, 1], repeat=2)]
    return inputs, outputs, cases


def _truth_table_1_3_4():
    # 2 选 1 多路选择器 Y = D0*~S + D1*S
    inputs, outputs = ["D0", "D1", "S"], ["Y"]
    cases = []
    for d0, d1, s in product([0, 1], repeat=3):
        cases.append({"in": [d0, d1, s], "out": [d0 if s == 0 else d1]})
    return inputs, outputs, cases


def _truth_table_1_5():
    # 4 选 1 多路选择器 Y = D[2*S1 + S0]
    inputs, outputs = ["D0", "D1", "D2", "D3", "S0", "S1"], ["Y"]
    cases = []
    for d in product([0, 1], repeat=4):
        for s in product([0, 1], repeat=2):
            sel = 2 * s[1] + s[0]
            cases.append({"in": list(d) + list(s), "out": [d[sel]]})
    return inputs, outputs, cases


BUILTIN = {
    "lab1.1": _truth_table_1_1,
    "lab1.2": _truth_table_1_2,
    "lab1.3": _truth_table_1_3_4,
    "lab1.4": _truth_table_1_3_4,
    "lab1.5": _truth_table_1_5,
}


def load_table(args):
    if args.table_file:
        with open(args.table_file, encoding="utf-8") as f:
            t = json.load(f)
        return t["inputs"], t["outputs"], t["cases"]
    if args.task in BUILTIN:
        return BUILTIN[args.task]()
    raise SystemExit(f"未知任务: {args.task}（内置: {', '.join(BUILTIN)}）")


def main():
    ap = argparse.ArgumentParser(description="对拍验证 Logisim .circ 电路")
    ap.add_argument("circ_file")
    ap.add_argument("--task", help="实验1 任务名，如 lab1.1")
    ap.add_argument("--table-file", help="自定义真值表 JSON 文件")
    args = ap.parse_args()

    inputs, outputs, cases = load_table(args)

    parsed = parse_circ(args.circ_file)
    try:
        sim = GateSimulator(parsed)
    except UnsupportedCircuitError as e:
        print(f"[跳过自动仿真] {e}")
        print("该电路含晶体管/子电路等，门级仿真器无法自动验证。")
        print("请用本地 Logisim-ITA 打开核对（见 SKILL.md 的「本地核对」一节）。")
        sys.exit(2)

    # 校验引脚标签与真值表一致
    sim_in = sim.input_labels()
    sim_out = sim.output_labels()
    if sorted(sim_in) != sorted(inputs):
        print(f"[引脚不一致] 电路输入 {sorted(sim_in)} vs 预期 {sorted(inputs)}")
        sys.exit(1)
    if sorted(sim_out) != sorted(outputs):
        print(f"[引脚不一致] 电路输出 {sorted(sim_out)} vs 预期 {sorted(outputs)}")
        sys.exit(1)

    fail = 0
    total = 0
    for case in cases:
        total += 1
        ins = dict(zip(inputs, case["in"]))
        actual = sim.simulate(ins)
        expected = dict(zip(outputs, case["out"]))
        ok = True
        for o in outputs:
            if actual.get(o) != expected[o]:
                ok = False
        if not ok:
            fail += 1
            if fail <= 10:  # 最多打印 10 条失败
                print(
                    f"[FAIL] in={case['in']} 期望 out={case['out']} 实际 out="
                    f"{[actual.get(o) for o in outputs]}"
                )

    print(f"共 {total} 组测试，失败 {fail} 组")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
