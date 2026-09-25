import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import drive_phys as D
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_pp.i", "w",
        encoding="utf-8").write(D.make_input(1.2e-5, 2400, 1.0e-4, "2.0e-7", "aphiform", 400))
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_pp.i", encoding="utf-8").read()
for i, l in enumerate(s.splitlines()):
    if ("at_susc" in l or "A_AT" in l or "aexpr" in l or "DG" in l or "outputs" in l
            or "execute_on" in l or "constant_names" in l or "expression" in l):
        print("%-4d %s" % (i + 1, l[:200]))