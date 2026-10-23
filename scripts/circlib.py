# -*- coding: utf-8 -*-
"""Build Logisim .circ files as text.

Generation strategy that has been verified against the real Logisim engine
(see tools/CircRun.java):

* every gate input/output gets a 20px wire stub, and a Tunnel sits at the free
  end of the stub.  Tunnels with the same label are electrically identical, so
  a netlist can be described purely by label names -- no long routing needed.
* component ports must be touched by a wire; a Tunnel placed directly on a port
  does NOT connect (verified).
"""
import os
import re


class Circ(object):
    def __init__(self, path):
        with open(path, encoding='utf-8') as f:
            self.text = f.read()
        self.lines = []
        self.used = {}          # coord -> what, to catch accidental shorts
        self._circuits = {}
        for m in re.finditer(r'<circuit name="([^"]*)">', self.text):
            end = self.text.index('</circuit>', m.end())
            self._circuits[m.group(1)] = (m.end(), end)
        self.circuits = list(self._circuits)

    # ---------------- low level ----------------
    def raw(self, line):
        self.lines.append('    ' + line)

    def comp(self, name, loc, attrs=None, lib=None):
        a = '' if lib is None else ' lib="%s"' % lib
        body = ''.join('\n      <a name="%s" val="%s"/>' % (k, v) for k, v in (attrs or {}).items())
        self.raw('<comp%s loc="(%d,%d)" name="%s">%s\n    </comp>' % (a, loc[0], loc[1], name, body))

    def wire(self, a, b):
        self.raw('<wire from="(%d,%d)" to="(%d,%d)"/>' % (a[0], a[1], b[0], b[1]))

    def tunnel(self, loc, label, width=None, facing=None):
        attrs = {}
        if facing:
            attrs['facing'] = facing
        if width:
            attrs['width'] = str(width)
        attrs['label'] = label
        attrs['labelfont'] = 'Dialog plain 12'
        self.comp('Tunnel', loc, attrs, lib='0')
        self._mark(loc, 'tunnel:' + label)

    def _mark(self, loc, what):
        key = (loc[0], loc[1])
        old = self.used.get(key)
        if old is not None and old != what:
            raise AssertionError('coordinate %s used twice: %s vs %s' % (key, old, what))
        self.used[key] = what

    # ---------------- gates ----------------
    # measured against the real engine (see Dump output of tmp/gates.circ)
    XOFF = {'NOT Gate': 20, 'Buffer': 20, 'AND Gate': 30, 'OR Gate': 30,
            'NAND Gate': 40, 'NOR Gate': 40, 'XOR Gate': 40, 'XNOR Gate': 50}

    @staticmethod
    def _ys(y, n):
        """Logisim input-port Y offsets: odd n centred, even n skips 0."""
        if n % 2:
            return [y + (i - (n - 1) // 2) * 10 for i in range(n)]
        half = n // 2
        return [y + ((i - half) if i < half else (i - half + 1)) * 10 for i in range(n)]

    def gate(self, kind, loc, ins, out, inputs=None, width=None, facing=None,
             stub=20, out_stub=20, out_tunnel=True):
        """Place a gate; `ins` is a list of net labels (None = leave open)."""
        n = inputs or 2
        if kind.startswith('NOT') or kind.startswith('Buffer'):
            n = 1
        attrs = {}
        if inputs and inputs != 2:
            attrs['inputs'] = str(inputs)
        if width:
            attrs['width'] = str(width)
        if facing:
            attrs['facing'] = facing
        self.comp(kind, loc, attrs, lib='1')
        self._mark(loc, 'gate:' + kind)

        if n == 1:
            ys = [loc[1]]
        else:
            ys = self._ys(loc[1], n)
        dx = self.XOFF.get(kind, 30)
        for i, y in enumerate(ys):
            port = (loc[0] - dx, y)
            start = (port[0] - stub, y)
            self.wire(start, port)
            if ins and i < len(ins) and ins[i]:
                self.tunnel(start, ins[i], width=width)
        if out:
            end = (loc[0] + out_stub, loc[1])
            self.wire(loc, end)
            if out_tunnel:
                self.tunnel(end, out, width=width)
        return ys

    # ---------------- flip-flop ----------------
    def dff(self, loc, d, q, clk, clr=None, set_=None, trigger='falling'):
        """D flip-flop (lib 5).  Verified port map:
        Q=(x,y) ~Q=(x,y+40) CLK=(x-60,y) D=(x-60,y+40)
        SET=(x-30,y-20) CLR=(x-30,y+60)   (both active high)
        """
        self.comp('D Flip-Flop', loc, {'trigger': trigger}, lib='5')
        self._mark(loc, 'dff')
        # Q
        if q:
            self.wire(loc, (loc[0] + 40, loc[1]))
            self.tunnel((loc[0] + 40, loc[1]), q)
        # D
        dp = (loc[0] - 60, loc[1] + 40)
        self.wire((dp[0] - 20, dp[1]), dp)
        self.tunnel((dp[0] - 20, dp[1]), d)
        # CLK
        cp = (loc[0] - 60, loc[1])
        self.wire((cp[0] - 20, cp[1]), cp)
        self.tunnel((cp[0] - 20, cp[1]), clk)
        # SET / CLR
        if set_:
            sp = (loc[0] - 30, loc[1] - 20)
            self.wire((sp[0], sp[1] - 20), sp)
            self.tunnel((sp[0], sp[1] - 20), set_)
        if clr:
            rp = (loc[0] - 30, loc[1] + 60)
            self.wire(rp, (rp[0], rp[1] + 20))
            self.tunnel((rp[0], rp[1] + 20), clr)

    # ---------------- misc ----------------
    def const(self, loc, value, width=1, label=None):
        attrs = {'width': str(width), 'value': value}
        self.comp('Constant', loc, attrs, lib='0')
        self._mark(loc, 'const')
        self.wire(loc, (loc[0] + 20, loc[1]))
        self.tunnel((loc[0] + 20, loc[1]), label, width=width if width > 1 else None)


    # ---------------- multi bit parts ----------------
    def splitter(self, loc, total, fanout, outs=None, in_label=None, in_width=None):
        """Identity-mapped splitter.  outs: list of labels for the fanout ends."""
        w = total // fanout
        attrs = {'fanout': str(fanout), 'incoming': str(total)}
        for k in range(total):
            attrs['bit%d' % k] = str(k)
        self.comp('Splitter', loc, attrs, lib='0')
        self._mark(loc, 'splitter')
        if in_label:
            self.wire((loc[0] - 40, loc[1]), loc)
            self.tunnel((loc[0] - 40, loc[1]), in_label, width=total if total > 1 else None)
        for i in range(fanout):
            p = (loc[0] + 20, loc[1] - 10 * fanout + 10 * i)
            self.wire(p, (p[0] + 20, p[1]))
            if outs and i < len(outs) and outs[i]:
                self.tunnel((p[0] + 20, p[1]), outs[i], width=w if w > 1 else None)

    def register(self, loc, width, d, q, clk, clr=None, en=None, gate_=None, set_=None):
        """Register (lib 5).  Ports verified against the engine:
        Q(0,0) D(-30,0) CLK(-20,+20) CLR(-10,+20) GATE(-30,+10) EN(-30,-10) SET(-10,-20)"""
        self.comp('Register', loc, {'width': str(width)}, lib='5')
        self._mark(loc, 'reg')
        self.wire(loc, (loc[0] + 20, loc[1]))
        self.tunnel((loc[0] + 20, loc[1]), q, width=width if width > 1 else None)
        self.wire((loc[0] - 50, loc[1]), (loc[0] - 30, loc[1]))
        self.tunnel((loc[0] - 50, loc[1]), d, width=width if width > 1 else None)
        for dx, dy, lab in ((-20, 20, clk), (-10, 20, clr), (-30, 10, gate_), (-30, -10, en), (-10, -20, set_)):
            if not lab:
                continue
            p = (loc[0] + dx, loc[1] + dy)
            if dy > 0:
                self.wire((p[0], p[1] + 20), p)
                self.tunnel((p[0], p[1] + 20), lab)
            else:
                self.wire(p, (p[0], p[1] - 20))
                self.tunnel((p[0], p[1] - 20), lab)

    def adder(self, loc, width, x, y, cin, f, cout, cin_width=None):
        """Adder (lib 4): X(-40,-10) Y(-40,+10) F(0,0) Cin(-20,-20) Cout(-20,+20)"""
        self.comp('Adder', loc, {'width': str(width)}, lib='4')
        self._mark(loc, 'adder')
        for dx, dy, lab, w in ((-40, -10, x, width), (-40, 10, y, width), (-20, -20, cin, 1), (-20, 20, cout, 1)):
            p = (loc[0] + dx, loc[1] + dy)
            if dx == -40:
                self.wire((p[0] - 20, p[1]), p)
                self.tunnel((p[0] - 20, p[1]), lab, width=w if w > 1 else None)
            else:
                self.wire(p, (p[0] - 20, p[1]))
                self.tunnel((p[0] - 20, p[1]), lab, width=w if w > 1 else None)
        self.wire(loc, (loc[0] + 20, loc[1]))
        self.tunnel((loc[0] + 20, loc[1]), f, width=width if width > 1 else None)

    # ---------------- output ----------------
    def write(self, out, circuit=None):
        circuit = circuit or self.circuits[0]
        pos = self._circuits[circuit][1]
        text = self.text[:pos] + '\n'.join(self.lines) + '\n  ' + self.text[pos:]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text)
        return out


def strip_circuit(src_path, out_path, circuit, keep=('Pin', 'Text')):
    """Rewrite a .circ keeping only wires/comp removal in one circuit.

    Wires are dropped and only <comp> whose name is in `keep` are preserved
    (plus the <appear> block and circuit attributes).
    """
    import re
    text = open(src_path, encoding='utf-8').read()
    m = re.search(r'<circuit name="%s">' % re.escape(circuit), text)
    start = m.end()
    end = text.index('</circuit>', start)
    body = text[start:end]
    out = []
    i = 0
    lines = body.split('\n')
    skip = False
    depth = 0
    for ln in lines:
        s = ln.strip()
        if skip:
            if s.startswith('</comp>'):
                skip = False
            continue
        if s.startswith('<wire'):
            continue
        mm = re.match(r'<comp\b[^>]*name="([^"]*)"', s)
        if mm:
            if keep is not None and mm.group(1) not in keep:
                if not (s.endswith('</comp>') or s.endswith('/>')):
                    skip = True
                continue
        out.append(ln)
    new = text[:start] + '\n'.join(out) + text[end:]
    open(out_path, 'w', encoding='utf-8').write(new)
    return out_path
