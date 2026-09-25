import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import drive_long as D
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_long_preview.i", "w",
        encoding="utf-8").write(D.make_input("2.0e-7", "0.0"))
s = io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/_long_preview.i",
            encoding="utf-8").read().splitlines()
for i, l in enumerate(s):
    if ("VectorPostprocessors" in l or "execute_on" in l or "xmax" in l
            or "end_time" in l or "nx =" in l or "num_points" in l or "AT" in l):
        print("%-4d %s" % (i + 1, l))