import numpy as np, os
from scipy import ndimage as ndi
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
g = d["gid"].astype(np.int32); s0 = d["snaps"][0]; dx = float(d["dx"])
pool = (s0 == 0); inside = pool & (g > 0)
small = np.zeros(g.shape, bool)
tot_small = 0
for gid in range(1, g.max()+1):
    m = inside & (g == gid)
    if m.sum() == 0: continue
    lab, n = ndi.label(m)
    sz = np.bincount(lab.ravel())
    for L in range(1, len(sz)):
        if 0 < sz[L] < 8:
            small |= (lab == L)
            tot_small += sz[L]
print("碎屑胞(<8 胞的连通块) 共 %d 胞, 占池内 %.3f%%" % (tot_small, 100.0*tot_small/inside.sum()))
nf_tot = 0; nf_spk = 0
for ax in range(3):
    n = g.shape[ax]
    lo = list(range(n-1)); hi = list(range(1, n))
    ga = np.take(g, lo, axis=ax); gb = np.take(g, hi, axis=ax)
    ma = np.take(pool, lo, axis=ax); mb = np.take(pool, hi, axis=ax)
    sa = np.take(small, lo, axis=ax); sb = np.take(small, hi, axis=ax)
    f = (ga != gb) & ma & mb
    nf_tot += int(f.sum()); nf_spk += int((f & (sa | sb)).sum())
print("池内晶界面 %d, 其中与碎屑胞相邻 %d (%.2f%%); 面积 %.3e vs %.3e m^2" % (
    nf_tot, nf_spk, 100.0*nf_spk/nf_tot, nf_tot*dx*dx, nf_spk*dx*dx))
# 池面外皮里有多少是碎屑造成的
print()
print("== 2|3 界面粗糙度 ==")
m2 = inside & (g == 2); m3 = inside & (g == 3)
n23 = 0
for ax in range(3):
    n = g.shape[ax]; lo=list(range(n-1)); hi=list(range(1,n))
    ga=np.take(g,lo,axis=ax); gb=np.take(g,hi,axis=ax)
    ma=np.take(pool,lo,axis=ax); mb=np.take(pool,hi,axis=ax)
    f=(np.minimum(ga,gb)==2)&(np.maximum(ga,gb)==3)&ma&mb
    n23 += int(f.sum())
v2, v3 = int(m2.sum()), int(m3.sum())
print("gid2 胞 %d, gid3 胞 %d, 2|3 界面 %d 面" % (v2, v3, n23))
print("若为两个紧凑块(同体积立方体)拼接，界面约 = (v2**(2/3)+v3**(2/3))/2*... 参考: 团块面积~%.0f 面" % (2*(0.5*(v2+v3))**(2/3)))