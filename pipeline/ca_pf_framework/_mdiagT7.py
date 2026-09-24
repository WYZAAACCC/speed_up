import io
src = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import numpy as np
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from ca3d import CA3D, IRF, T_LIQ, T_SOL, M_L
from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT

dx = 4e-6
irf = IRF()
dt = dx / (4.0 * 0.2)
ca = CA3DSolute(40, 40, 56, dx, irf=irf, seed=3, D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
ca.nucleate_substrate_grid(4, 4)
T0 = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
nf = ca.seed_solid_from_substrate(T0, T_SOL)
print("seed_solid_from_substrate 填充 =", nf)
print("初始: 液相胞 =", int((ca.gid == 0).sum()), " 固相胞 =", int((ca.gid > 0).sum()))
print("T0 范围 = %.1f .. %.1f ; T_LIQ=%.1f T_SOL=%.1f" % (T0.min(), T0.max(), T_LIQ, T_SOL))
dT0 = np.clip(T_LIQ - T0, 0, None)
liq = ca.gid == 0
print("液相内 dT 范围 = %.2f .. %.2f" % (dT0[liq].min(), dT0[liq].max()))
nb = 0
for s_ in range(200):
    ca.t = s_ * dt
    T = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
    ca.step_solute(dt, T, window="full", constitutional=True)
    n = ca.nucleate_bulk(T, 12.0, 4.0, 4.0e14, dt, c_l=ca.c_liq, m_L=M_L)
    nb += n
    if s_ % 50 == 0:
        print("  step %3d: t=%.2e 液相=%6d 固相分数=%.4f 新增体核=%d" % (
            s_, ca.t, int((ca.gid == 0).sum()), float((ca.gid > 0).mean()), n))
print("体形核总数 =", nb, " 晶粒总数 =", len(ca.axes) - 1)
print("c_liq 范围 = %.5f .. %.5f" % (ca.c_liq.min(), ca.c_liq.max()))
sizes = []
for g in range(1, len(ca.axes)):
    ii, jj, kk = np.where(ca.gid == g)
    if len(ii) < 30:
        continue
    sizes.append((len(ii), ii.max()-ii.min()+1, jj.max()-jj.min()+1, kk.max()-kk.min()+1, g))
sizes.sort(reverse=True)
print("最大的 6 个晶粒 (ncell, dx, dy, dz, gid):")
for r in sizes[:6]:
    print("   ", r)
'''
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/_diagT7.py", "w", encoding="utf-8").write(src)
print("written")