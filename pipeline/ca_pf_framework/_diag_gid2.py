import numpy as np
from scipy import ndimage as ndi
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
g = d["gid"].astype(np.int32); s0 = d["snaps"][0]; dx = float(d["dx"])
def dilate(m, n):
    out = m.copy()
    for _ in range(n):
        a = out.copy()
        for ax in range(3):
            for s in (1, -1):
                sl = [slice(None)]*3; ds = [slice(None)]*3
                sl[ax] = slice(None, -1) if s > 0 else slice(1, None)
                ds[ax] = slice(1, None) if s > 0 else slice(None, -1)
                a[tuple(ds)] |= out[tuple(sl)]
        out = a
    return out
mask = dilate((s0 == 0), 2)
sel = mask & (g > 0)
nd = np.zeros(g.shape, np.int8)   # 邻居中不同 gid 的个数
nv = np.zeros(g.shape, np.int8)   # 掩膜内有效邻居个数
for ax in range(3):
    n = g.shape[ax]
    lo = list(range(n-1)); hi = list(range(1, n))
    ga = np.take(g, lo, axis=ax); gb = np.take(g, hi, axis=ax)
    ma = np.take(mask, lo, axis=ax); mb = np.take(mask, hi, axis=ax)
    ok = ma & mb; df = ok & (ga != gb)
    sla = [slice(None)]*3; sla[ax] = slice(None, -1)
    slb = [slice(None)]*3; slb[ax] = slice(1, None)
    nd[tuple(sla)] += df; nd[tuple(slb)] += df
    nv[tuple(sla)] += ok; nv[tuple(slb)] += ok
print("掩膜内胞数 =", int(sel.sum()))
print("每个胞的'不同 gid 邻居数'分布：")
for k in range(7):
    c = int(((nd == k) & sel).sum())
    print("   %d: %7d  (%.2f%%)" % (k, c, 100.0*c/sel.sum()))
print("有效邻居数分布：")
for k in range(7):
    c = int(((nv == k) & sel).sum())
    print("   %d: %7d  (%.2f%%)" % (k, c, 100.0*c/sel.sum()))
# 真·孤立胞：6 邻居全部有效且同一个其他 gid
iso = sel & (nv == 6) & (nd == 6)
print("\n完全被另一个晶粒包住(6/6 邻居都是同一个别的 gid)的胞 =", int(iso.sum()))
# 各 gid 的主连通域
print("\n各晶粒在掩膜内的连通域：")
for gid in range(1, g.max()+1):
    m = sel & (g == gid)
    if m.sum() == 0: continue
    lab, n = ndi.label(m)
    sz = np.sort(np.bincount(lab.ravel())[1:])[::-1]
    print("  gid %d: 胞 %6d, 连通域 %3d, 最大 %6d (%.4f%%), 次大 %d" % (gid, int(m.sum()), n, sz[0], 100.0*sz[0]/m.sum(), sz[1] if len(sz)>1 else 0))
nf = 0
for ax in range(3):
    n = g.shape[ax]
    lo = list(range(n-1)); hi = list(range(1, n))
    ga = np.take(g, lo, axis=ax); gb = np.take(g, hi, axis=ax)
    ma = np.take(mask, lo, axis=ax); mb = np.take(mask, hi, axis=ax)
    nf += int(((ga != gb) & ma & mb).sum())
print("\nGB 面数(掩膜内) = %d, 面积 = %.3e m^2, 平均胞 = %.4f um" % (nf, nf*dx*dx, dx*1e6))