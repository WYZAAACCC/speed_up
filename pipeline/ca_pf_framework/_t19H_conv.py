#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t19H_conv.py --- D17 的**第四条判据（决策性）**：`proj*` 家族把板条长径比从
   8.93:1 压到 2.4:1 —— 到底是 **central 虚高** 还是 **upwind 过度扩散**？

设计（全部满足 MEASUREMENT_SPEC 的 R1/R2/R3）
--------------------------------------------
  ① **Δx 收敛**：固定**物理** `L`、固定**物理**种子（`R=120 nm, t=100 nm`）、
     固定**物理时间**（`steps·0.15·dx = const`）、固定**物理**重初始化间隔
     （`reinit_dt`，不是步数 —— 见 T11 的记账）。
     ⇒ 若 central 的 8.93:1 是**物理**，它应随 Δx 收敛到同一个值；
        若它是**数值伪影**，它应随 Δx 漂移或发散。
  ② **机制诊断（R2：先写下期望）**：
     假设 H1「`|∇φ|` 放大」——central 的更新是 `φ −= dt·v_n·|∇φ|`，
     它在 `|∇φ|≠1` 处**不是纯平移**。薄板的长大是"面内快、厚向极慢"，
     厚向剖面被**拉伸** ⇒ 厚向 `|∇φ| < 1` ⇒ `v_n|∇φ|` 进一步压低厚向速度
     ⇒ **长径比正反馈放大**（= 伪影）。
     期望：**central 的厚向 `|∇φ|` 显著 < 1，而 proj2 的 ≈ 1**。
     反向（H0）：「central 对、upwind 过度扩散」⇒ 两者的厚向 `|∇φ|` 都 ≈ 1。
  ③ **粗糙度**：`界面键数 / 几何面积测度·dx²`（干净阶梯 ≈ 1.5）—— P1 的同一口径。

用法：python3 _t19H_conv.py [--advs central,proj2] [--dxs 25,18.75,12.5]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB = 2.0e8, 1e-9
EXACT = MOB * DF
L = 1.2e-6                  # ★ 固定物理盒子
R_SEED, T_SEED = 0.10 * L, 100e-9   # ★ 固定物理种子
DX_REF, STEP_REF = 25e-9, 120       # 参考档：Δx=25 nm、120 步
DISPL_REF = STEP_REF * 0.15 * DX_REF   # 固定物理位移（米）
REINIT_DT = 25 * (0.15 * DX_REF / EXACT)   # 固定**物理**重初始化间隔


def go(adv, dxn):
    dx = dxn * 1e-9
    N = int(round(L / dx))
    nstep = int(round(DISPL_REF / (0.15 * dx)))
    g = W.LevelSetMulti(N, N * dx, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=REINIT_DT)
    g.seed_plate(1, [N * dx / 2] * 3, np.asarray(NPF[1], float), R_SEED, T_SEED)
    g.init_parent()
    dt = 0.15 * dx / EXACT
    for _ in range(nstep):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5,
                  mob_beta_w=2.3, adv_grad=adv)
    reg = g.region()
    idx = np.argwhere(reg == 1)
    f = float((reg == 1).sum()) / g.N ** 3
    if idx.size < 30:
        return dict(f=f, r_long=np.nan, r_mid=np.nan, ang=np.nan,
                    gthin=np.nan, glong=np.nan, rough=np.nan, N=N, nstep=nstep)
    p = (idx.astype(float) + 0.5) * dx
    ctr = p.mean(0)
    q = p - ctr
    ev, evec = np.linalg.eigh(np.cov(q.T))
    u_thin = evec[:, 0]
    u_long = evec[:, 2]
    ang = float(np.degrees(np.arccos(np.clip(abs(u_thin @ NPF[1]), 0, 1))))
    # ---- H1 诊断：界面带内 |∇φ| 沿**厚向/长向**的分量 ----
    gr = np.gradient(g.phi[1], dx)
    gn = np.sqrt(sum(t ** 2 for t in gr)) + 1e-30
    m = np.abs(g.phi[1]) <= 1.5 * dx
    if m.sum() > 20:
        gv = np.stack([t[m] for t in gr], -1)
        gthin = float(np.mean(np.abs(gv @ u_thin)))
        glong = float(np.mean(np.abs(gv @ u_long)))
        gnorm = float(np.mean(gn[m]))
    else:
        gthin = glong = gnorm = np.nan
    # ---- 粗糙度：键数 / 几何面积测度 ----
    nb = int(sum((reg != np.roll(reg, -1, ax)).sum() for ax in range(3)))
    A = float(g.area_total_geom())
    rough = nb / max(A / dx ** 2, 1e-30)
    return dict(f=f, r_long=float(np.sqrt(ev[2] / ev[0])),
                r_mid=float(np.sqrt(ev[1] / ev[0])), ang=ang,
                gthin=gthin, glong=glong, gnorm=gnorm, rough=rough,
                N=N, nstep=nstep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--advs', default='central,proj2')
    ap.add_argument('--dxs', default='25,18.75,12.5')
    a = ap.parse_args()
    adxs = [s.strip() for s in a.advs.split(',') if s.strip()]
    dxs = [float(s) for s in a.dxs.split(',') if s.strip()]
    print('=' * 108)
    print('_t19H —— 长径比 & 厚向 |∇φ| 的 **Δx 收敛**（固定物理 L=%.2f µm、种子 R=%.0f nm t=%.0f nm、'
          '物理位移 %.0f nm、物理 reinit 间隔 %.3e s）'
          % (L * 1e6, R_SEED * 1e9, T_SEED * 1e9, DISPL_REF * 1e9, REINIT_DT))
    print('  R2 先写下期望：若 central 的 8.93:1 是**物理**，它随 Δx 收敛；若是"|∇φ| 放大"伪影，')
    print('     则 central 的**厚向 |∇φ| 显著 < 1**，且长径比随 Δx 漂移。')
    print('-' * 108)
    res = {}
    for adv in adxs:
        print('  【%s】' % adv)
        print('     %-8s %-7s %-7s %-11s %-9s %-9s %-9s %-9s %-9s'
              % ('Δx(nm)', 'N', '步', 'f', '长:中:薄', '厚向|∇φ|', '长向|∇φ|', '|∇φ|中位', '键/面积'))
        for dxn in dxs:
            r = go(adv, dxn)
            res[(adv, dxn)] = r
            print('     %-8.2f %-7d %-7d %-11.5f %-9s %-9.3f %-9.3f %-9.3f %-9.3f'
                  % (dxn, r['N'], r['nstep'], r['f'],
                     '%.2f:%.2f:1' % (r['r_long'], r['r_mid']),
                     r['gthin'], r['glong'], r['gnorm'], r['rough']), flush=True)
    print('-' * 108)
    print('  ★ Δx 收敛性（长径比 r_long 的最大/最小相对散布）：')
    for adv in adxs:
        vs = [res[(adv, d)]['r_long'] for d in dxs]
        sp = (max(vs) - min(vs)) / max(np.mean(vs), 1e-30)
        print('     %-9s r_long = %s ⇒ 散布 %.3f %s'
              % (adv, ['%.2f' % v for v in vs], sp, '（收敛）' if sp < 0.15 else '（**不收敛**）'))
    print('  ★ H1 判决（厚向 |∇φ|，理想 = 1.000）：')
    for adv in adxs:
        vs = [res[(adv, d)]['gthin'] for d in dxs]
        print('     %-9s 厚向 |∇φ| = %s ⇒ %s'
              % (adv, ['%.3f' % v for v in vs],
                 '**显著 < 1 ⇒ H1 成立（central 的长径比是 |∇φ| 放大的伪影）**'
                 if np.mean(vs) < 0.9 else '≈1 ⇒ H1 不成立'))
    print('=' * 108)


if __name__ == '__main__':
    main()
