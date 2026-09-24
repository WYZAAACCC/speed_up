import numpy as np, os
H = "/mnt/f/speed_up/pipeline/ca_pf_framework"
d = np.load(os.path.join(H, "meltpool_growth_gid.npz"))
g = d["gid"]; dx = float(d["dx"])
nf = 0
gbcell = np.zeros(g.shape, bool)
for ax in range(3):
    a = [slice(None)]*3; b = [slice(None)]*3
    a[ax] = slice(None, -1); b[ax] = slice(1, None)
    dd = (g[tuple(a)] > 0) & (g[tuple(b)] > 0) & (g[tuple(a)] != g[tuple(b)])
    nf += int(dd.sum())
    gbcell[tuple(a)] |= dd; gbcell[tuple(b)] |= dd
print("晶界共享面片 = %d 面" % nf)
print("晶界面积     = %.3e m^2   (每面 dx^2 = %.1e m^2)" % (nf * dx * dx, dx * dx))
print("晶界胞       = %d (%.2f%% 体积)  <- 单个胞可能贡献多面" % (int(gbcell.sum()), 100.0*gbcell.mean()))
print("参考: CA3D_REPORT/演示打印的 gb_area() = 4.43e-07 m^2 (定义略不同)")