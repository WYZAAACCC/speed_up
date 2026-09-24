# -*- coding: utf-8 -*-
"""深度数据核查：熔池/晶粒/晶界 到底是多少"""
import numpy as np, os
H = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(H, "meltpool_growth_gid.npz"))
g = d["gid"]; dx = float(d["dx"]); snaps = d["snaps"]; ts = d["snap_t"]
nx, ny, nz = g.shape
Vcell = dx ** 3
Vdom = nx * ny * nz * Vcell
print("域       : %dx%dx%d  dx=%.1f um  -> %.0f x %.0f x %.0f um" % (
    nx, ny, nz, dx * 1e6, nx * dx * 1e6, ny * dx * 1e6, nz * dx * 1e6))
print("域体积   : %.3e m^3" % Vdom)
print("")
print("== 各快照的液相占比 ==")
for k in range(len(snaps)):
    nliq = int((snaps[k] == 0).sum())
    Vliq = nliq * Vcell
    D = (6 * Vliq / np.pi) ** (1.0 / 3.0) if nliq else 0.0
    print("  t=%.2e s  液相胞=%7d  占比=%5.2f%%  等效球直径=%6.1f um" % (
        ts[k], nliq, 100.0 * nliq / snaps[k].size, D * 1e6))
print("")
print("== 末态晶粒 ==")
print("  域总胞数 = %d (全固相 f_s=%.4f)" % (nx * ny * nz, float((g > 0).mean())))
tot = 0
for gid in range(1, int(g.max()) + 1):
    m = g == gid
    n = int(m.sum()); tot += n
    ii, jj, kk = np.where(m)
    ex = (ii.max() - ii.min() + 1, jj.max() - jj.min() + 1, kk.max() - kk.min() + 1)
    print("  gid=%d  胞=%7d  体积占比=%5.2f%%  包围盒=%2dx%2dx%2d 胞 (=%3.0fx%3.0fx%3.0f um)  z向长径比 dz/max(dx,dy)=%.2f"
          % (gid, n, 100.0 * n / g.size, ex[0], ex[1], ex[2],
             ex[0] * dx * 1e6, ex[1] * dx * 1e6, ex[2] * dx * 1e6,
             ex[2] / max(ex[0], ex[1])))
print("  合计 = %d / %d" % (tot, g.size))
# 晶界面片数（与渲染同定义）
nf = 0; area = 0.0
for ax in range(3):
    a = [slice(None)] * 3; b = [slice(None)] * 3
    a[ax] = slice(None, -1); b[ax] = slice(None, 1, None)
    dd = (g[tuple(a)] > 0) & (g[tuple(b)] > 0) & (g[tuple(a)] != g[tuple(b)])
    nf += int(dd.sum()); area += float(dd.sum()) * dx * dx
print("  晶界共享面片 = %d 面,  面积 = %.3e m^2" % (nf, area))