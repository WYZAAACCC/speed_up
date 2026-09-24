import numpy as np, os
from scipy import ndimage as ndi
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
print("keys:", d.files)
g = d["gid"].astype(np.int32); dx = float(d["dx"]); s0 = d["snaps"][0]
print("gid shape", g.shape, "dx", dx, "gid max", g.max())

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

pool = (s0 == 0)
mask = dilate(pool, 2)
print("pool cells", int(pool.sum()), " mask cells", int(mask.sum()))
print("mask & gid>0:", int((mask & (g>0)).sum()), "  mask & gid==0:", int((mask & (g==0)).sum()))

# 邻居不同 gid 个数分布（只在 mask 内）
ndiff = np.zeros(g.shape, np.int8); nvalid = np.zeros(g.shape, np.int8)
for ax in range(3):
    for s in (1, -1):
        nb = np.roll(g, -s, axis=ax).astype(np.int32)
        ok = np.roll(mask, -s, axis=ax)
        ok = ok & mask
        if s > 0:
            sl = [slice(None)]*3; sl[ax] = slice(None, -1); ok[tuple(sl)] = False
        else:
            sl = [slice(None)]*3; sl[ax] = slice(1, None); ok[tuple(sl)] = False
        ndiff[ok & (nb != g)] += 1
        nvalid[ok & (nb != 0)] += 1
sel = mask & (g > 0)
print("mask 内胞的'邻居中不同gid'个数分布:")
for k in range(7):
    print("   %d 个不同邻居: %d 胞 (%.2f%%)" % (k, int(((ndiff == k) & sel).sum()), 100.0*((ndiff == k) & sel).sum()/sel.sum()))

# 连通域
print("\n各晶粒连通域（6-连通, mask 内）:")
for gid in range(1, g.max()+1):
    m = sel & (g == gid)
    if m.sum() == 0: continue
    lab, n = ndi.label(m)
    sizes = np.bincount(lab.ravel())[1:]
    sizes = np.sort(sizes)[::-1]
    big = sizes[sizes >= 8]
    print("  gid %d: 胞 %6d, 连通域 %5d 个, >=8胞的域 %3d 个, 最大/次大 = %s" % (
        gid, int(m.sum()), n, len(big), sizes[:4]))

# 晶界面对数 & 面积
nface = 0
for ax in range(3):
    a = np.take(mask & (g > 0), range(g.shape[ax]-1), axis=ax)
    b = np.take(mask & (g > 0), range(1, g.shape[ax]), axis=ax)
    ga = np.take(g, range(g.shape[ax]-1), axis=ax)
    gb = np.take(g, range(1, g.shape[ax]), axis=ax)
    nface += int(((ga != gb) & a & b).sum())
print("\nGB 面数(掩膜内) = %d, 面积 = %.3e m^2" % (nface, nface*dx*dx))