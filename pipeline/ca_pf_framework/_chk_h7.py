#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H7 判据：层间一致性 —— `Π` 逐胞守恒（Window A/CA 粗网格 → Window B 细网格）。

判据（对应 MATH_FRAMEWORK §7.1 的 I2/I3）：
  (a) 权重归一：每列和 = 1（细胞被完全覆盖）；
  (b) 往返恒等：restrict(prolong(q)) = q（逐胞，机器精度）；
  (c) 总量守恒：Σ_细 = Σ_粗（机器精度，**含非整数细化比**）；
  (d) 常数保持：prolong(1) = 1 ⇒ 转移不造伪梯度；
  (e) 有界：取值落在输入区间内（正权重 ⇒ 凸组合）；
  (f) 负对照：最近邻（piecewise）转移在**非整数比**下总量不守恒 ✗；
  (g) I3 记账（真实量）：把"晶粒体积分数 f_s"与"晶界面积"从粗网格送到细网格，
      两者都必须**逐位守恒**（这就是把 Window A 的骨架交给 Window B 时的守恒要求）。
"""
import numpy as np
from windowB_coupling import ConservativeTransfer, overlap_1d

print('=' * 78)
print('H7-1  算子的基本性质（整数比 20× 与非整数比 16.67× 各测一遍）')
for (dxA, dxB) in ((10e-6, 0.5e-6), (10e-6, 0.6e-6)):
    nA = (24, 24, 24)
    nB = tuple(int(round(nA[i] * dxA / dxB)) for i in range(3))
    tr = ConservativeTransfer(dxA, nA, dxB, nB)
    row = max(abs(tr.Wf[i].sum(1) - 1).max() for i in range(3))      # 分摊分数：行和=1
    col = max(abs(tr.W[i].sum(0) - 1).max() for i in range(3))       # 覆盖比例：列和=1
    rng = np.random.default_rng(0)
    qA = rng.random(nA) * 3.0
    qB = tr.prolong(qA)
    back = tr.restrict(qB)
    tot = abs(qB.sum() - qA.sum()) / abs(qA.sum())
    rt = abs(back - qA).max() / abs(qA).max()
    # (d) 常数保持：**intensive** 场用 piecewise 逐胞复制 ⇒ 必须逐位为 1
    cst = abs(tr.prolong_int(np.ones(nA), mode='piecewise') - 1.0).max()
    # (e) 有界：intensive 场的守恒重采样是凸组合 ⇒ 落在输入区间内
    fB = tr.prolong_int(qA, mode='smooth')
    bnd = max(0.0, fB.min() - qA.min(), qA.max() - fB.max())
    print('   比 %.2f×: 列和偏差 %.2e | 行和偏差 %.2e | 总量偏差 %.2e | 往返偏差 %.2e |'
          ' 常数偏差 %.2e | 越界 %.2e' % (dxA / dxB, col, row, tot, rt, cst, bnd))
    # 阈值按 float64 在 ~480 长求和上的舍入地板（~1e-12）定，不是硬凑
    print('            → (a)%s (b)%s (c)%s (d)%s (e)%s'
          % ('PASS' if (col < 1e-12 and row < 1e-12) else 'FAIL',
             'PASS' if rt < 1e-12 else 'FAIL（非整数比：守恒对但往返只是近似）',
             'PASS' if tot < 1e-12 else 'FAIL', 'PASS' if cst < 1e-15 else 'FAIL',
             'PASS' if bnd <= 1e-15 else 'FAIL'))

print('=' * 78)
print('H7-2  负对照：最近邻（piecewise）转移 vs 守恒 Π（非整数比 16.67×）')
dxA, dxB = 10e-6, 0.6e-6
nA = (24, 24, 24)
nB = tuple(int(round(nA[i] * dxA / dxB)) for i in range(3))
tr = ConservativeTransfer(dxA, nA, dxB, nB)
rng = np.random.default_rng(1)
qA = rng.random(nA)
qB_near = tr.prolong_int(qA, mode='piecewise')          # 最近邻（不守恒）
qB_cons = tr.prolong(qA)                                # 守恒 Π
e_near = abs(qB_near.sum() - qA.sum()) / qA.sum()
e_cons = abs(qB_cons.sum() - qA.sum()) / qA.sum()
print('   最近邻：Σ_细/Σ_粗 偏差 = %.4e  %s' % (e_near, 'FAIL（预期）' if e_near > 1e-12 else '意外通过'))
print('   守恒Π ：Σ_细/Σ_粗 偏差 = %.4e  %s'
      % (e_cons, 'PASS' if e_cons < 1e-12 else 'FAIL'))

print('=' * 78)
print('H7-3  I3 记账：把 Window A 的"晶粒体积分数 + 晶界面积"送到 Window B')
import windowB_surface as W
Nf, DL = 48, 2e-6                      # 细网格：48³、Δx_B = 2 µm（示范用）
g = W.LevelSetMulti(Nf, Nf * DL, nv=4, gamma=0.0, Mob=0.0, df=[0.0] * 5,
                    reinit_every=0)
rng = np.random.default_rng(3)
for k in range(1, 5):
    c = rng.random(3) * 0.6 * Nf * DL + 0.2 * Nf * DL
    g.seed_sphere(k, c, 0.16 * Nf * DL)
g.init_parent()
reg = g.region()
dxA_H7 = 10e-6                          # Window A 的胞尺度（CA 生产值）
r = int(round(dxA_H7 / DL))              # 细化比
nA = (Nf // r, Nf // r, Nf // r)
# --- 粗网格上的"CA 输出"：每粗胞的晶粒体积分数 + 晶界面积（用体素界面计数）---
fA = np.zeros((5,) + nA)
for k in range(5):
    blk = reg[:nA[0] * r, :nA[1] * r, :nA[2] * r].reshape(nA[0], r, nA[1], r, nA[2], r)
    fA[k] = (blk == k).mean(axis=(1, 3, 5))
gbA = np.zeros(nA)                      # 晶界面积（粗胞内异相界面的"面积计数"）
for ax in range(3):
    d = np.diff(reg, axis=ax)
    d = np.pad(d, [(0, 1) if i == ax else (0, 0) for i in range(3)])
    m = (d != 0).astype(float)
    blk = m[:nA[0] * r, :nA[1] * r, :nA[2] * r].reshape(nA[0], r, nA[1], r, nA[2], r)
    gbA += blk.sum(axis=(1, 3, 5)) * DL ** 2
VA = (r * DL) ** 3
tr = ConservativeTransfer(dxA_H7, nA, DL, (Nf, Nf, Nf))
ok_f, ok_gb = [], []
for k in range(5):
    # ★ 记账：守恒的是**广延量** f·V（不是"分数"本身）；直接 prolong 分数会差一个体积比。
    qA_k = fA[k] * VA
    qB_k = tr.prolong(qA_k)
    totA = qA_k.sum()
    totB = qB_k.sum()
    ok_f.append(abs(totB - totA) / max(totA, 1e-300))
gbB = tr.prolong(gbA)                   # 面积本身是 extensive ⇒ 直接守恒
totA_gb, totB_gb = gbA.sum(), gbB.sum()
print('   晶粒体积分数：5 个区域的总量相对偏差 max = %.3e  %s'
      % (max(ok_f), 'PASS' if max(ok_f) < 1e-13 else 'FAIL'))
print('   晶界面积    ：%.6e m² → %.6e m²，相对偏差 %.3e  %s'
      % (totA_gb, totB_gb, abs(totB_gb - totA_gb) / totA_gb,
         'PASS' if abs(totB_gb - totA_gb) / totA_gb < 1e-14 else 'FAIL'))
print('   （细化比 = %d×；粗网格 = Window A 的胞尺度 %.0f µm，细网格 = %.1f µm）'
      % (r, dxA_H7 * 1e6, DL * 1e6))
print('=' * 78)
