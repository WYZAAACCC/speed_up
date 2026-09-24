import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_ablation.py")).read().split("print(\"=== 消融")[0])

def run(capture="decentered", fac=1.0, win=None, tag=""):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026, capture=capture)
    ca.nucleate_substrate_grid(2, 3)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH)
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
    dt = DX/(4*V_max)/fac; nst = int(1.2e-3/dt)
    s = 0
    for s in range(nst):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=win)
        if (ca.gid == 0).sum() == 0:
            break
    n_th = getattr(ca, "n_thermal", 0); pool = pool0 & (ca.gid > 0)
    mm = metrics(ca.gid, pool)
    print("%-42s 第 %4d 步; 过冷并入 %5d 胞 (%.0f%% 池); 面 %5d, 粗糙度 %.2f, 碎屑 %3d, 连通片 %d" % (
        tag, s, n_th, 100.0*n_th/max(pool0.sum(),1), mm[0], mm[2], mm[3], mm[4]))

run("decentered", 1.0, None, "decentered + 并入 (基线)")
run("analytic",   1.0, "full", "analytic(正确包络) + 并入")
run("decentered", 2.0, None, "decentered + 并入, dt/2")
run("decentered", 4.0, None, "decentered + 并入, dt/4")
run("decentered", 0.5, None, "decentered + 并入, dt*2")