import io, sys, numpy as np
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read().splitlines()
print("--- fig script lines 196-206 ---")
for i in range(195, 206):
    print("%3d %s" % (i + 1, s[i]))
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
print("--- npz keys ---", list(d.keys()))
if "snaps" in d:
    print("snaps shape", d["snaps"].shape, "snap_t", d["snap_t"])