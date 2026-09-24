#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仪器化诊断：每步统计 N_iface、p 的分布、实际翻转数，与期望 p·N_iface 逐项比对。
   平面（κ≈0）与球（κ≠0）两个几何都做 —— 目标是找出 H2b 偏慢 60% 的来源。"""
import numpy as np
from windowB_hybrid import HybridBulkSurface, _sphere, DIRS6


def instr(N, dx, kind, M=1e-9, df=1e7, gamma=0.15, nstep=6):
    g = HybridBulkSurface(N, N * dx, gamma=gamma, M_int=M)
    if kind == 'planar':
        g.lab[:, :, : max(2, N // 4)] = 1
    else:
        m, _ = _sphere(N, dx, 1.2e-8)
        g.lab[m] = 1
    dt = 0.05 * dx / (M * df)
    rng = np.random.default_rng(2)
    print('  [%s] N=%d dx=%.1f nm dt=%.3e' % (kind, N, dx * 1e9, dt))
    print('  %5s %8s %8s %11s %11s %9s %9s' %
          ('step', 'N_if', 'p_mean', 'expect', 'actual', 'kappa_max', 'ratio'))
    for k in range(nstep):
        m = g.iface_mask()
        cand = m & (g.lab == 0)          # grow 候选（matrix 侧）
        nif = int(cand.sum())
        kap = g.curvature()
        vn = g.M * (-df + gamma * kap)
        p = np.clip(np.abs(vn) * dt / dx, 0, 1.0)
        pm = float(p[cand].mean()) if nif else np.nan
        expect = pm * nif
        actual = int((cand & (rng.random(g.lab.shape) < p)).sum())
        # 第二次 draw 用于实际推进（避免与统计共用同一随机数）
        ng, ns = g.advance(dt, df=-df, rng=rng)
        print('  %5d %8d %8.4f %11.1f %11d %9.3e %9.3f' %
              (k, nif, pm, expect, ng, float(np.abs(kap[cand]).max()),
               ng / max(expect, 1e-9)))


def disp_per_step(N=48, dx=2e-9, M=1e-9, df=1e7, nstep=8):
    """同 H2b 的 setup，逐步打【实际翻转数】与【位移/步】，直接看两者是否自洽"""
    g = HybridBulkSurface(N, N * dx, gamma=0.15, M_int=M)
    g.lab[:, :, : max(2, N // 4)] = 1
    dt = 0.05 * dx / (M * df)
    A = 2.0 * (N * dx) ** 2
    rng = np.random.default_rng(2)
    print('  [H2b-setup] N=%d dx=%.1f nm dt=%.3e ; 期望位移/步 = M·df·dt = %.3e m (= %.3f 胞)'
          % (N, dx * 1e9, dt, M * df * dt, M * df * dt / dx))
    print('  %5s %9s %9s %12s %12s %10s' %
          ('step', 'n_grow', 'n_shrink', 'dV/A (m)', '期望 dV/A', '比值'))
    for k in range(nstep):
        n0 = int((g.lab > 0).sum())
        ng, ns = g.advance(dt, df=-df, rng=rng)
        n1 = int((g.lab > 0).sum())
        dV = (n1 - n0) * dx ** 3
        print('  %5d %9d %9d %12.3e %12.3e %10.3f' %
              (k, ng, ns, dV / A, M * df * dt,
               (dV / A) / (M * df * dt) if M * df * dt else np.nan))


if __name__ == '__main__':
    disp_per_step()
