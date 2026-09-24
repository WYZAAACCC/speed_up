import numpy as np
d = np.load("/mnt/f/speed_up/pipeline/ca_pf_framework/meltpool_growth_gid.npz")
g = d["gid"].astype(np.int32); s0 = d["snaps"][0]
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
print("mask sum", mask.sum(), mask.dtype, "g dtype", g.dtype)
ax = 0; s = 1
nb = np.roll(g, -s, axis=ax).astype(np.int32)
ok = np.roll(mask, -s, axis=ax)
ok = ok & mask
print("ok sum", ok.sum())
sl = [slice(None)]*3; sl[ax] = slice(None, -1); ok[tuple(sl)] = False
print("ok sum after edge zero", ok.sum())
d_ = ok & (nb != g)
print("diff & ok", d_.sum())
nd = np.zeros(g.shape, np.int8)
nd[d_] += 1
print("nd sum", nd.sum())