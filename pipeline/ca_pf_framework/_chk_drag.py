#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拖曳判据（P3.3 / K1–K5 + 接进水平集后的两态验证）

D1 闭式拖曳：P(0)=P0、P(∞)=0、单调降、有界（K1 复核）。
D2 隐式解：按 (ΔG, M) 扫面，数值验证**脱钉判据** `(ΔG>P0) 或 (MΔG>v*)`。
D3 线性闭式的失效：在被钉扎的驱动下线性闭式仍给出正速度（K3 复核）。
D4 接进 LevelSetMulti：平界面 + 常数驱动 ΔG = df/M，比较
     (i) 无拖曳 v = MΔG、（ii）隐式拖曳 v = M[ΔG − P_drag(v)]
   ⇒ 必须看到"钉扎（v=0）/ 脱钉（v>0）"两态。
"""
import numpy as np
import windowB_drag as DR
import windowB_surface as W

print('=' * 78)
print('D1 闭式拖曳复核（K1）')
P0, vstar, M = 1.0e7, 1.0e-3, 1.0e-9
print('   P(0)=%.4e (=P0) ; P(∞)→%.3e ; P(0.5v*)=%.4e ; P(v*) = P0/2=%.3e'
      % (DR.pdrag(0.0, P0, vstar), DR.pdrag(1e9, P0, vstar),
         DR.pdrag(0.5 * vstar, P0, vstar), DR.pdrag(vstar, P0, vstar)))

print('=' * 78)
print('D2 脱钉判据数值验证：(ΔG>P0) 或 (MΔG>v*)')
dGs = np.array([0.2, 0.5, 1.0, 2.0, 5.0, 10.0]) * P0
for lM in (0.01, 1.0, 10.0, 1000.0):
    Mv = lM * vstar / P0                     # 让 M·P0/v* = lM
    v, pin = DR.solve_v(dGs, Mv, P0, vstar)
    pred = (dGs > P0) | (Mv * dGs > vstar)
    print('   M·P0/v* = %7.2f : v/v* = %s ; 钉扎 = %s ; 判据预测 = %s ⇒ %s'
          % (lM, np.round(v / vstar, 3), pin.astype(int), (~pred).astype(int),
             'PASS' if np.array_equal(pin.astype(bool), (~pred).astype(bool)) else 'FAIL'))

print('=' * 78)
print('D3 线性闭式 vs 隐式（K3 复核）')
Mv = 1e-9
for r in (0.5, 1.0, 2.0, 5.0, 10.0):
    v_i, pin = DR.solve_v(np.array([r * P0]), Mv, P0, vstar)
    v_l = DR.v_linear(np.array([r * P0]), Mv)
    print('   ΔG/P0 = %5.1f : v_implicit = %.4e %s ; v_linear = %.4e ⇒ 偏差 %s'
          % (r, float(v_i[0]), '(被钉扎)' if pin[0] else '',
             float(v_l[0]),
             '线性闭式凭空给出速度 ✗' if (pin[0] and v_l[0] > 0) else '%.1f%%'
             % (100 * abs(float(v_i[0]) - float(v_l[0])) / max(float(v_i[0]), 1e-300))))

print('=' * 78)
print('D4 接进水平集：平界面 + 常数驱动的**两态**')
N, dx = 48, 2e-9
df_drive = 1.0e7
Mob = 1.0e-9
for tag, drag in (('无拖曳', None), ('拖曳(ΔG<P0 钉扎)', (5.0e7, 1.0e-3)),
                  ('拖曳(ΔG>P0 脱钉)', (2.0e6, 1.0e-3))):
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.0, Mob=Mob, df=[0.0, -df_drive],
                        reinit_every=0)
    # ★ 记账：前一轮用"阶跃初值"（φ=±0.5dx）—— 那对 VDF 是**退化**构型（|∇φ| 在体相为 0），
    #   配对速度的语义会变。这里改用**真正的 SDF**（φ_1 = 有符号距离、φ_0 由 init_parent 定）。
    z = np.arange(N)[None, None, :] * dx
    g.phi[1] = (z - 0.25 * N * dx) * np.ones((N, N, N))
    g.init_parent()
    # ★★ 修（2026-09-25，W-4）：旧写法用**计数法**（数 region 翻转的胞）量位移 ——
    #   与 W2 那次是同一个病：计数法对**均匀亚胞平移失明**、对剖面展宽又系统性偏大，
    #   实测偏差可达 2–2.5x（正是 W-4 记的"拖曳绝对速度差 2–2.5x"）。
    #   改用 **亚胞射线交点**（，与 W2/P1/S1 同一口径）。
    near = 0.25 * N * dx
    n0 = int((g.region() == 1).sum())
    _, z0 = g.iface_offset(1, 0, 2, near=near)
    dt = 0.1 * dx / (Mob * df_drive)
    nstep = 40
    for _ in range(nstep):
        g.advance(dt, drag=drag)
    n1 = int((g.region() == 1).sum())
    _, z1 = g.iface_offset(1, 0, 2, near=near)
    v_ray = abs(z1 - z0) / (nstep * dt)
    v_cnt = abs(n1 - n0) * dx ** 3 / (N * dx) ** 2 / (nstep * dt)
    print('   %-18s : v_射线 = %.4e | v_计数 = %.4e | 解析 MΔG = %.4e => 比(射线) %.3f  比(计数) %.3f'
          % (tag, v_ray, v_cnt, Mob * df_drive, v_ray / (Mob * df_drive),
             v_cnt / (Mob * df_drive)))
print('   （拖曳参数取自 D2 的两支：ΔG<P0 ⇒ 应 v=0；ΔG>P0 ⇒ 应 v>0）')
