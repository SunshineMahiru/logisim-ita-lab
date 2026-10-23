import com.cburch.logisim.circuit.Circuit;
import com.cburch.logisim.comp.Component;
import com.cburch.logisim.comp.EndData;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.file.LogisimFile;
import com.cburch.logisim.instance.StdAttr;

import java.io.File;
import java.util.List;

/** Dump every component's port geometry: name, loc, attrs, ends. */
public class Dump {
    public static void main(String[] a) throws Exception {
        Loader l = new Loader(null);
        LogisimFile f = l.openLogisimFile(new File(a[0]));
        String only = a.length > 1 ? a[1] : null;
        for (Circuit c : f.getCircuits()) {
            if (only != null && !only.equals(c.getName())) continue;
            System.out.println("### circuit " + c.getName());
            for (Component comp : c.getNonWires()) {
                StringBuilder sb = new StringBuilder();
                sb.append("  ").append(comp.getFactory().getName());
                sb.append(" loc=").append(comp.getLocation());
                Object lab = comp.getAttributeSet().getValue(StdAttr.LABEL);
                if (lab != null && !lab.toString().isEmpty()) sb.append(" label=").append(lab);
                Object w = comp.getAttributeSet().getValue(StdAttr.WIDTH);
                if (w != null) sb.append(" w=").append(w);
                sb.append(" ends:");
                List<EndData> ends = comp.getEnds();
                for (int i = 0; i < ends.size(); i++) {
                    EndData e = ends.get(i);
                    sb.append(" [").append(i).append("]").append(e.getLocation())
                      .append(e.isOutput() ? "out" : "in")
                      .append("w").append(e.getWidth().getWidth());
                }
                System.out.println(sb);
            }
        }
    }
}
