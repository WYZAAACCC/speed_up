import io
src = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, math
import numpy as np
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from scipy.special import erf as _erf
from ca3d import CA3D, IRF, T_LIQ, T_SOL, M_L, C0_V
from ca3d_solute import CA3DSolute, D_L_DEFAULT, DT_F_DEFAULT

dx = 4e-6
irf = IRF()
dt = dx / (4.0 * 0.2)
ca = CA3DSolute(40, 40, 56, dx, irf=irf, seed=3, D_L=D_L_DEFAULT, dt_f=DT_F_DEFAULT)
ca.nucleate_substrate_grid(4, 4)
T0 = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
ca.seed_solid_from_substrate(T0, T_SOL)
for s_ in (0, 3, 6, 10):
    ca.t = s_ * dt
    T = ca.T_meltpool(2500.0, 40e-6, 3.1e-4, 353.0)
    if s_:
        ca.step_solute(dt, T, window="full", constitutional=True)
    liq = ca.gid == 0
    dT = np.clip(T_LIQ - T, 0.0, None)
    cdf = 0.5 * (1.0 + _erf((dT - 6.0) / (2.0 * math.sqrt(2.0))))
    Nv = 2.0e14 * cdf
    expect = Nv * ca.dx ** 3
    print("step %2d: 液相=%5d  dT[liq] max=%.2f  cdf[liq] max=%.4f  expect[liq] max=%.5f  sum(expect[liq])=%.4f"
          % (s_, int(liq.sum()), dT[liq].max() if liq.any() else -1,
             cdf[liq].max() if liq.any() else -1,
             expect[liq].max() if liq.any() else -1,
             float(expect[liq].sum()) if liq.any() else -1))
    n = ca.nucleate_bulk(T, 6.0, 2.0, 2.0e14, dt)
    print("          -> nucleate_bulk 返回 %d ; 晶粒总数 %d" % (n, len(ca.axes) - 1))
'''
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/_micro_bulk2.py", "w", encoding="utf-8").write(src)
print("written")