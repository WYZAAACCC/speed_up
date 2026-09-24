import numpy as np, os, itertools
from scipy import ndimage as ndi
HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
g = d["gid"].astype(np.int32); s0 = d["snaps"][0]; dx = float(d["dx"])
pool = (s0 == 0); inside = pool & (g > 0)
print("== 池内各晶粒连通域（严格池内, 6-连通）==")
for gid in range(1, g.max()+1):
    m = inside & (g == gid)
    if m.sum() == 0: continue
    lab, n = ndi.label(m)
    sz = np.sort(np.bincount(lab.ravel())[1:])[::-1]
    print("  gid %d: 胞 %6d, 连通域 %3d, 最大 %6d (%.4f%%), 次大 %s" % (
        gid, int(m.sum()), n, sz[0], 100.0*sz[0]/m.sum(), list(sz[1:6])))

# 5|6 界面片的连通性（按共享棱，union-find）
def face_components(g, keep, pair):
    parent = {}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def uni(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    facets = []
    for ax in range(3):
        n = g.shape[ax]
        lo = np.arange(n-1); hi = np.arange(1, n)
        klo = np.take(keep, lo, axis=ax); khi = np.take(keep, hi, axis=ax)
        glo = np.take(g, lo, axis=ax); ghi = np.take(g, hi, axis=ax)
        sel = klo & khi & (np.minimum(glo, ghi) == pair[0]) & (np.maximum(glo, ghi) == pair[1])
        for ii in np.argwhere(sel):
            f = []; pl = list(ii); pl[ax] = ii[ax] + 1
            o1, o2 = [k for k in range(3) if k != ax]
            for du, dv in ((0,0),(1,0),(1,1),(0,1)):
                c = list(pl); c[o1] = ii[o1] + du; c[o2] = ii[o2] + dv
                f.append(tuple(c))
            facets.append(tuple(f))
    for i, f in enumerate(facets):
        for e in itertools.combinations(f, 2):
            if sum(abs(a-b) for a, b in zip(e[0], e[1])) == 1:
                parent.setdefault(e, e)
    for i, f in enumerate(facets):
        parent.setdefault(("F", i), ("F", i))
    for i, f in enumerate(facets):
        for e in itertools.combinations(f, 2):
            if sum(abs(a-b) for a, b in zip(e[0], e[1])) == 1:
                uni(("F", i), e)
    comps = {}
    for i in range(len(facets)):
        comps.setdefault(find(("F", i)), 0)
        comps[find(("F", i))] += 1
    sz = sorted(comps.values(), reverse=True)
    return len(facets), sz

for pair in ((5,6),(2,5),(3,5),(2,6),(3,6),(2,3)):
    nf, sz = face_components(g, pool, pair)
    if nf:
        print("界面 %s|%s: 面片 %5d, 连通片 %3d, 最大片 %5d (%.1f%%), 次大 %s" % (
            pair[0], pair[1], nf, len(sz), sz[0], 100.0*sz[0]/nf, sz[1:6]))