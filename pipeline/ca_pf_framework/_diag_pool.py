import numpy as np
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
g = d["gid"].astype(np.int32); s0 = d["snaps"][0]
pool = (s0 == 0)
idx = np.argwhere(pool)
lo, hi = idx.min(0), idx.max(0)
dx = float(d["dx"])
print("池 bbox 胞:", lo, hi, " => um:", (hi-lo+1)*dx*1e6)
print("域 shape", g.shape, "域 um", np.array(g.shape)*dx*1e6)
fl = np.argwhere(pool & (np.arange(g.shape[0])[:,None,None] == 0))
print("池在 x=0 平面上的胞数:", len(fl))
for ax, nm in enumerate("xyz"):
    a = np.take(pool, [0], axis=ax)[0]
    b = np.take(pool, [g.shape[ax]-1], axis=ax)[0]
    print("  轴 %s: 在 0 面 %d 胞, 在末面 %d 胞" % (nm, a.sum(), b.sum()))
print("末帧 f_s(全域) =", 1.0 - (d["snaps"][-1] == 0).mean())
print("末帧域内 gid==0 的胞:", int((g == 0).sum()), " (全域 %d)" % g.size)