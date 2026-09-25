import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import drive_dom as D
s = D.make_input(4.8e-6, 2400, 3.0e-5, "2.0e-7", "0.0", [2.0e-6, 2.6e-6])
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_gen_preview.i", "w",
        encoding="utf-8").write(s)
for tag in ("[Mesh]", "[Postprocessors]", "[VectorPostprocessors]", "[Executioner]",
            "end_time", "xmax", "nx = ", "constant_expressions"):
    for i, l in enumerate(s.splitlines()):
        if l.strip().startswith(tag):
            print("%-24s L%-4d %s" % (tag, i + 1, l.strip()))
            break
print("---- tail ----")
print("\n".join(s.splitlines()[-40:]))