#!/usr/bin/env python3
"""离线自检：不依赖 Java，用纯 Python 跑通「解析 → 生成 → 仿真 → 对拍」。

用法:
    python scripts/selftest.py          # 全部通过返回 0，任一失败返回 1

检查项:
    1. circ_parser 能解出 <main> 与电路名；
    2. circlib 生成的 2 选 1 多路选择器，经门级仿真後与 lab1.3 真值表逐行一致；
    3. validate.py 命令行入口对同一份电路返回 0；
    4. 含晶体管的电路被门级仿真器拒绝，validate.py 返回 2（降级到本地核对）。

改动 scripts/ 下任何脚本后先跑这个，再谈具体实验。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import circlib
import circ_parser
import validate
from circ_simulator import GateSimulator, UnsupportedCircuitError

# 最小 .circ 骨架：一个主电路、三个输入引脚、一个输出引脚。
# 引脚各自接一段 20px 导线再加同名 Tunnel，这样门侧的同名 Tunnel 才能与引脚同网。
TEMPLATE = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<project source="2.16.2.0.jar" version="1.0">
This file is intended to be loaded by Logisim http://logisim.altervista.org
  <lib desc="#Wiring" name="0"/>
  <lib desc="#Gates" name="1"/>
  <main name="main"/>
  <circuit name="main">
    <comp lib="0" loc="(100,120)" name="Pin">
      <a name="label" val="D0"/>
      <a name="output" val="false"/>
    </comp>
    <comp lib="0" loc="(100,150)" name="Pin">
      <a name="label" val="D1"/>
      <a name="output" val="false"/>
    </comp>
    <comp lib="0" loc="(100,180)" name="Pin">
      <a name="label" val="S"/>
      <a name="output" val="false"/>
    </comp>
    <comp lib="0" loc="(520,240)" name="Pin">
      <a name="label" val="Y"/>
      <a name="output" val="true"/>
    </comp>
  </circuit>
</project>
'''

# 引脚到同名 Tunnel 的短导线，坐标与 TEMPLATE 里的 Pin 一一对应。
PINS = (
    ('D0', (100, 120)),
    ('D1', (100, 150)),
    ('S', (100, 180)),
    ('Y', (520, 240)),
)


def _write_template(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(TEMPLATE)


def _add_pin_tunnels(circ):
    for label, loc in PINS:
        end = (loc[0] + 20, loc[1])
        circ.wire(loc, end)
        circ.tunnel(end, label)


def _build_mux(template_path, out_path):
    circ = circlib.Circ(template_path)
    _add_pin_tunnels(circ)
    circ.gate('NOT Gate', (230, 300), ['S'], 'NS')
    circ.gate('AND Gate', (280, 200), ['D0', 'NS'], 'N1')
    circ.gate('AND Gate', (280, 270), ['D1', 'S'], 'N2')
    circ.gate('OR Gate', (370, 230), ['N1', 'N2'], 'Y')
    return circ.write(out_path)


def _build_transistor(template_path, out_path):
    circ = circlib.Circ(template_path)
    _add_pin_tunnels(circ)
    circ.comp('Transistor', (300, 200), {'type': 'n'}, lib='0')
    return circ.write(out_path)


def _run_validate(circ_path, task):
    cmd = [sys.executable, os.path.join(HERE, 'validate.py'), circ_path, '--task', task]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def main():
    work = tempfile.mkdtemp(prefix='logisim-selftest-')
    failures = []
    try:
        template = os.path.join(work, 'template.circ')
        _write_template(template)

        parsed = circ_parser.parse_circ(template)
        if parsed['main'] != 'main' or 'main' not in parsed['circuits']:
            failures.append('[1/4] 解析: 主电路名或电路列表不符合预期')
        else:
            print('[1/4] 解析: 主电路 %s，电路 %s' % (parsed['main'], parsed['circuits'].keys()))

        mux = _build_mux(template, os.path.join(work, 'mux.circ'))
        sim = GateSimulator(circ_parser.parse_circ(mux))
        inputs, outputs, cases = validate.BUILTIN['lab1.3']()
        bad = 0
        for case in cases:
            actual = sim.simulate(dict(zip(inputs, case['in'])))
            if [actual.get(o) for o in outputs] != case['out']:
                bad += 1
        if bad:
            failures.append('[2/4] 仿真: %d/%d 组与真值表不符' % (bad, len(cases)))
        else:
            print('[2/4] 仿真: %d 组用例与 lab1.3 真值表一致' % len(cases))

        code, out = _run_validate(mux, 'lab1.3')
        if code != 0:
            failures.append('[3/4] 命令行: validate.py 返回 %d\n%s' % (code, out))
        else:
            print('[3/4] 命令行: validate.py 返回 0')

        trans = _build_transistor(template, os.path.join(work, 'transistor.circ'))
        try:
            GateSimulator(circ_parser.parse_circ(trans))
        except UnsupportedCircuitError:
            print('[4/4] 降级: 含晶体管的电路被门级仿真器拒绝')
        else:
            failures.append('[4/4] 降级: 含晶体管的电路没有被拒绝')

        code, out = _run_validate(trans, 'lab1.3')
        if code != 2:
            failures.append('[4/4] 命令行: 晶体管电路的 validate.py 返回 %d，预期 2\n%s' % (code, out))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        print('')
        for f in failures:
            print('FAIL ' + f)
        print('SELFTEST: %d 项未通过' % len(failures))
        return 1
    print('SELFTEST: ALL PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
