import com.cburch.logisim.file.*;
import java.io.File;
public class ErrLoad {
  static class L extends Loader {
    L() { super(null); }
    public void showError(String msg) { System.out.println("ERR: " + msg); }
  }
  public static void main(String[] a) throws Exception {
    L l = new L();
    LogisimFile f = l.openLogisimFile(new File(a[0]));
    System.out.println("loaded: " + f.getCircuits().size() + " circuits");
  }
}
