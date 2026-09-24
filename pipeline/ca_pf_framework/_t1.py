import numpy as np, os
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
g = d["gid"].astype(np.int32)
print(g.dtype, g.shape)
ax = 0
nb = np.roll(g, -1, axis=ax)
print("raw diff faces axis0:", int((nb != g).sum()))
print("interior diff:", int((nb[:-1] != g[:-1]).sum()))
print("g[0,30,30], g[1,30,30], g[2,30,30] =", g[0,30,30], g[1,30,30], g[2,30,30])