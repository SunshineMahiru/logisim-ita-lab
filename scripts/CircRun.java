import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.circuit.CircuitState;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.data.BitWidth;
import com.cburch.logisim.data.Value;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.file.LogisimFile;
import com.cburch.logisim.instance.InstanceState;
import com.cburch.logisim.instance.StdAttr;
import com.cburch.logisim.proj.Project;
import com.cburch.logisim.std.wiring.Pin;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.UnsupportedEncodingException;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Headless Logisim-ITA driver.
 *
 * Commands (one per line on stdin):
 *   set NAME=VALUE [...]   poke input pins (dec or 0x hex), then propagate
 *   get NAME               print one pin
 *   clk                    propagate, then drive CLK 1->0 (falling edge)
 *   clkrise                propagate, then drive CLK 0->1
 *   snap                   print every output pin as NAME=hex
 *   snapall                print every pin as NAME=hex
 *   osc                    report oscillation flag
 *   quit
 */
public class CircRun {
    static Project proj;
    static CircuitState cs;
    static Circuit circuit;
    static Map<String, Component> pins = new LinkedHashMap<String, Component>();
    static PrintStream out;

    public static void main(String[] args) throws Exception {
        try {
            out = new PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8");
        } catch (UnsupportedEncodingException e) {
            out = System.out;
        }
        if (args.length < 1) {
            System.err.println("usage: CircRun <file.circ> [circuit]");
            System.exit(2);
        }
        Loader loader = new Loader(null);
        LogisimFile lf = loader.openLogisimFile(new File(args[0]));
        proj = new Project(lf);
        circuit = args.length > 1 ? lf.getCircuit(args[1]) : lf.getMainCircuit();
        if (circuit == null) {
            System.err.println("circuit not found");
            System.exit(3);
        }
        cs = proj.getCircuitState(circuit);

        for (Component c : circuit.getNonWires()) {
            if (c.getFactory() == Pin.FACTORY) {
                Object lab = c.getAttributeSet().getValue(StdAttr.LABEL);
                if (lab != null && !lab.toString().isEmpty()) pins.put(lab.toString(), c);
            }
        }
        cs.markComponentsDirty(circuit.getNonWires());
        cs.getPropagator().propagate();

        StringBuilder sb = new StringBuilder(">>PINS");
        for (String s : pins.keySet()) sb.append(' ').append(s);
        out.println(sb.toString());

        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, "UTF-8"));
        String line;
        while ((line = in.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] t = line.split("\\s+");
            String cmd = t[0];
            try {
                if (cmd.equals("set")) {
                    // rest of the line: comma separated, names may be quoted
                    String rest = line.substring(3).trim();
                    for (String item : splitTop(rest)) {
                        int eq = indexOfTop(item, '=');
                        String nm = unquote(item.substring(0, eq)).trim();
                        setPin(nm, parseVal(item.substring(eq + 1)));
                    }
                    cs.getPropagator().propagate();
                } else if (cmd.equals("get")) {
                    out.println(">>G " + t[1] + "=" + fmt(getPin(t[1])));
                } else if (cmd.equals("clk")) {
                    String ck = pins.containsKey("CLK") ? "CLK" : "Clock";
                    cs.getPropagator().propagate();
                    setPin(ck, 1);
                    cs.getPropagator().propagate();
                    setPin(ck, 0);
                    cs.getPropagator().propagate();
                } else if (cmd.equals("clkrise")) {
                    cs.getPropagator().propagate();
                    setPin("CLK", 0);
                    cs.getPropagator().propagate();
                    setPin("CLK", 1);
                    cs.getPropagator().propagate();
                } else if (cmd.equals("snap")) {
                    StringBuilder o = new StringBuilder(">>S");
                    for (Component c : pins.values()) {
                        if (isOutput(c)) o.append(' ').append(label(c)).append('=').append(fmt(getPin(label(c))));
                    }
                    out.println(o.toString());
                } else if (cmd.equals("snapall")) {
                    StringBuilder o = new StringBuilder(">>A");
                    for (Component c : pins.values()) {
                        o.append(' ').append(label(c)).append('=').append(fmt(getPin(label(c))));
                    }
                    out.println(o.toString());
                } else if (cmd.equals("osc")) {
                    out.println(">>OSC " + cs.getPropagator().isOscillating());
                } else if (cmd.equals("quit") || cmd.equals("exit")) {
                    break;
                } else {
                    out.println(">>ERR unknown cmd " + cmd);
                }
            } catch (Exception e) {
                out.println(">>ERR " + e);
            }
            out.flush();
        }
        out.flush();
        Runtime.getRuntime().halt(0);
    }

    static java.util.List<String> splitTop(String s) {
        java.util.List<String> out = new java.util.ArrayList<String>();
        StringBuilder cur = new StringBuilder();
        boolean q = false;
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '"') { q = !q; cur.append(ch); }
            else if (ch == ',' && !q) { out.add(cur.toString()); cur.setLength(0); }
            else cur.append(ch);
        }
        if (cur.length() > 0) out.add(cur.toString());
        return out;
    }

    static int indexOfTop(String s, char c) {
        boolean q = false;
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '"') q = !q;
            else if (ch == c && !q) return i;
        }
        return -1;
    }

    static String unquote(String s) {
        s = s.trim();
        if (s.length() > 1 && s.charAt(0) == '"' && s.charAt(s.length() - 1) == '"')
            return s.substring(1, s.length() - 1);
        return s;
    }

    static boolean isOutput(Component c) {
        Object o = c.getAttributeSet().getValue(Pin.ATTR_TYPE);
        return o instanceof Boolean && ((Boolean) o).booleanValue();
    }

    static String label(Component c) {
        Object l = c.getAttributeSet().getValue(StdAttr.LABEL);
        return l == null ? "" : l.toString();
    }

    static int parseVal(String s) {
        s = s.trim();
        if (s.startsWith("0x") || s.startsWith("0X")) return (int) Long.parseLong(s.substring(2), 16);
        return (int) Long.parseLong(s);
    }

    static int width(Component c) {
        Object w = c.getAttributeSet().getValue(StdAttr.WIDTH);
        return w instanceof BitWidth ? ((BitWidth) w).getWidth() : 1;
    }

    static void setPin(String name, int v) {
        Component c = pins.get(name);
        if (c == null) throw new RuntimeException("no pin " + name);
        InstanceState is = cs.getInstanceState(c);
        ((Pin) c.getFactory()).setValue(is, Value.createKnown(BitWidth.create(width(c)), v));
        cs.markComponentAsDirty(c);
    }

    static Value getPin(String name) {
        Component c = pins.get(name);
        if (c == null) throw new RuntimeException("no pin " + name);
        return ((Pin) c.getFactory()).getValue(cs.getInstanceState(c));
    }

    static String fmt(Value v) {
        if (v == null) return "NULL";
        if (v.isErrorValue()) return "ERR";
        if (v.getWidth() <= 1) return v == Value.TRUE ? "1" : (v == Value.FALSE ? "0" : "X");
        try {
            return String.format("%x", v.toIntValue());
        } catch (Exception e) {
            return "X";
        }
    }
}
