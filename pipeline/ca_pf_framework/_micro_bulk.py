#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import numpy as np
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from ca3d import CA3D, IRF, T_LIQ, T_SOL, M_L

dx = 4e-6
irf = IRF()
ca = CA3D(20, 20, 20, dx, irf=irf, seed=1)
# 造一个"液相池"：让 T 在 1900 K（dT = 11.1 K）
T = np.full(ca.shape, T_LIQ - 11.0)
for dTm, dTs, Nm in ((6.0, 2.0, 2.0e14), (6.0, 2.0, 2.0e16), (12.0, 4.0, 4.0e14)):
    ca2 = CA3D(20, 20, 20, dx, irf=irf, seed=1)
    n = ca2.nucleate_bulk(T, dTm, dTs, Nm, 5e-6)
    print("dT_mean=%.0f sigma=%.0f N_max=%.1e -> 形核 %d 个" % (dTm, dTs, Nm, n))
ca3 = CA3D(20, 20, 20, dx, irf=irf, seed=1)
n = ca3.nucleate_bulk(T, 6.0, 2.0, 2.0e14, 5e-6, c_l=np.full(ca3.shape, 0.05), m_L=M_L)
print("成分过冷驱动(c_l=0.05, dT_mean=6) -> 形核 %d 个" % n)
