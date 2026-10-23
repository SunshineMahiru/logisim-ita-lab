import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.comp.EndData;
import com.cburch.logisim.data.Location;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.file.LogisimFile;
import com.cburch.logisim.instance.StdAttr;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Report unconnected component ends.
 * A component end is considered connected when its location coincides with
 * a wire endpoint, lies on a wire segment, or coincides with another end.
 */
public class Conn {
    public static void main(String[] a) throws Exception {
        Loader l = new Loader(null);
        LogisimFile f = l.openLogisimFile(new File(a[0]));
        String only = a.length > 1 ? a[1] : null;
        for (Circuit c : f.getCircuits()) {
            if (only != null && !only.equals(c.getName())) continue;
            Set<String> pts = new HashSet<String>();
            List<int[]> segs = new ArrayList<int[]>();
            for (com.cburch.logisim.circuit.Wire w : c.getWires()) {
                Location p = w.getEnd0(), q = w.getEnd1();
                segs.add(new int[]{p.getX(), p.getY(), q.getX(), q.getY()});
                pts.add(p.getX() + "," + p.getY());
                pts.add(q.getX() + "," + q.getY());
            }
            Set<String> endPts = new HashSet<String>();
            for (Component comp : c.getNonWires())
                for (EndData e : comp.getEnds())
                    endPts.add(e.getLocation().getX() + "," + e.getLocation().getY());

            int bad = 0;
            for (Component comp : c.getNonWires()) {
                for (EndData e : comp.getEnds()) {
                    int x = e.getLocation().getX(), y = e.getLocation().getY();
                    String key = x + "," + y;
                    boolean ok = pts.contains(key) || onSeg(segs, x, y);
                    if (!ok) {
                        // another component end at the same point also counts
                        int cnt = 0;
                        for (Component o : c.getNonWires())
                            for (EndData oe : o.getEnds())
                                if (oe.getLocation().getX() == x && oe.getLocation().getY() == y) cnt++;
                        ok = cnt > 1;
                    }
                    if (!ok) {
                        bad++;
                        Object lab = comp.getAttributeSet().getValue(StdAttr.LABEL);
                        System.out.println("  UNCONNECTED " + comp.getFactory().getName()
                                + " loc=" + comp.getLocation()
                                + (lab == null ? "" : " label=" + lab)
                                + " end=" + e.getLocation() + (e.isOutput() ? " (out)" : " (in)"));
                    }
                }
            }
            System.out.println("### circuit " + c.getName() + " unconnected=" + bad
                    + " wires=" + c.getWires().size() + " comps=" + c.getNonWires().size());
        }
    }

    static boolean onSeg(List<int[]> segs, int x, int y) {
        for (int[] s : segs) {
            if (s[0] == s[2] && s[0] == x) {
                if (y >= Math.min(s[1], s[3]) && y <= Math.max(s[1], s[3])) return true;
            } else if (s[1] == s[3] && s[1] == y) {
                if (x >= Math.min(s[0], s[2]) && x <= Math.max(s[0], s[2])) return true;
            }
        }
        return false;
    }
}
