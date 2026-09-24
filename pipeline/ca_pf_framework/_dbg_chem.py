#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_dbg_chem.py --- 定位质量守恒爆炸与化学路径分辨率"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, F_MIN, K_V

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=2026)
ca.nucleate_substrate_grid(2, 3)
ca.seed_solid_from_substrate(ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), T_SOL)
V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0])
dt = DX/(4*V_max)
print("初始: A_liq %.4f..%.4f, fs %.2f..%.2f, c_sol %.4f..%.4f, 总溶质均值/c0 = %.4f" % (
    ca.A_liq.min(), ca.A_liq.max(), ca.fs.min(), ca.fs.max(),
    ca.c_sol.min(), ca.c_sol.max(), ca.total_solute().mean()/C0_V))
for s in range(40):
    ca.t = s*dt
    ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, TAU, T_BATH), window=None)
    if s % 10 == 9 or s == 0:
        ts_ = ca.total_solute()
        i = np.unravel_index(np.argmax(ts_), ts_.shape)
        j = np.unravel_index(np.argmax(ca.c_sol), ca.c_sol.shape)
        print("step %2d: A %.4f..%.6g  fs %.2f..%.2f  c_sol %.4f..%.6g (max@%s, ts=%.3g, fs=%.3f)  "
              "总溶质/c0 均值 %.4f 最大 %.4g" % (
            s, ca.A_liq.min(), ca.A_liq.max(), ca.fs.min(), ca.fs.max(),
            ca.c_sol.min(), ca.c_sol.max(), j, ca.ts[j], ca.fs[j],
            ts_.mean()/C0_V, ts_.max()/C0_V))