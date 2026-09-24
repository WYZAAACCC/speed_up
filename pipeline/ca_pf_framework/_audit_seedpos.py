import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_ablation.py")).read().split("print(\"=== 消融")[0])

def run(seed_mode, nseed=8, capture="decentered"):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture=capture)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    poolT = T0 > T_SOL
    if seed_mode == "corner":                      # 现状: 域底面 2x3
        ca.nucleate_substrate_grid(2, 3)
    else:                                          # 池壁: 在池壁固相胞上撒 nseed 个
        wall = ndi.binary_dilation(poolT) & ~poolT
        wc = np.argwhere(wall).astype(float)
        cen, lab = kmeans2(wc, nseed, minit="++", seed=4)
        for k in range(nseed):
            idx = wc[lab == k]
            if len(idx) == 0: continue
            i, j, kk = idx[len(idx)//2].astype(int)
            ca.add_grain(int(i), int(j), int(kk))
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    ng0 = len(ca.grain_ids())
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max); nst = int(1.2e-3/dt)
    s = 0
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
        if (ca.gid == 0).sum() == 0:
            break
    n_th = getattr(ca, "n_thermal", 0)
    pool = pool0 & (ca.gid > 0)
    mm = metrics(ca.gid, pool)
    print("[%s / %s] 种子 %d 个; 第 %d 步全固; 过冷并入 %d 胞 (占池 %.0f%%); "
          "面 %d, 粗糙度 %.2f, 碎屑 %d, 连通片 %d; 池内晶粒数 %d" % (
        seed_mode, capture, ng0, s, n_th, 100.0*n_th/max(pool0.sum(),1),
        mm[0], mm[2], mm[3], mm[4], len(np.unique(ca.gid[pool]))))

run("corner")
run("wall")