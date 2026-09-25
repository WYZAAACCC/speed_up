import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import drive_var as D
s = D.make_input(8.0e-6, 1600, 4.5e-5, "2.0e-7", "0.0", 200)
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_var_preview.i", "w",
        encoding="utf-8").write(s)
for i, l in enumerate(s.splitlines()):
    if ("interval" in l or "sort_by" in l or "end_time" in l or "num_points" in l
            or "xmax" in l or "nx =" in l or "constant_expressions" in l):
        print("%-4d %s" % (i + 1, l))
print("---has csv=true block? ", "[Outputs]\n  [csv]" in s)