# -*- coding: utf-8 -*-
"""Drive a .circ through the real Logisim engine (tools/CircRun.java)."""
import os
import subprocess

import os

# 可用环境变量覆盖：LOGISIM_JAVA / LOGISIM_JAR
JAVA = os.environ.get('LOGISIM_JAVA', 'D:/appInstall/Java/jdk-21.0.6/bin/java.exe')
JAR = os.environ.get('LOGISIM_JAR', 'Logisim-ITA-2.16.2.0/Logisim-ITA.jar')
TOOLS = os.environ.get('LOGISIM_TOOLS', '.workbuddy/tools')
CP = TOOLS + os.pathsep + JAR


def run(circ, circuit, cmds, timeout=180):
    """cmds: list of command lines.  Returns list of parsed >>S snapshots."""
    text = '\n'.join(cmds) + '\nquit\n'
    p = subprocess.run([JAVA, '-Djava.awt.headless=true', '-cp', CP, 'CircRun', circ, circuit],
                       input=text.encode('utf-8'), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    out = p.stdout.decode('utf-8', 'replace')
    snaps, errors, pins = [], [], []
    for line in out.splitlines():
        if line.startswith('>>S '):
            d = {}
            for kv in line[4:].split():
                k, v = kv.split('=', 1)
                d[k] = v
            snaps.append(d)
        elif line.startswith('>>PINS'):
            pins = line.split()[1:]
        elif line.startswith('>>ERR'):
            errors.append(line)
    return {'snaps': snaps, 'errors': errors, 'pins': pins, 'raw': out}


def setline(d):
    return 'set ' + ','.join('%s=%s' % (k, v) for k, v in d.items())
