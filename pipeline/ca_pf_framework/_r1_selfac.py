#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_selfac.py --- ★★★ 实验 7 的判据 S-1：**块/组织是否真的"自协调"**

科学问题
--------
"自协调（self-accommodation）"的操作性定义只有一条：**这套变体搭配让弹性能更低**。
⇒ 判据必须是**对照实验**，不能只看"看起来对称"：

    E_el(观测构型)  vs  E_el(同体积分数的**随机**变体指派)

判据（**先写死**，见 `R1_HANDOFF.md`）
------------------------------------
  S-1  `E_el_obs` 必须**显著低于**随机指派的分布（用 z 分数与分位数报出，
       不以"低一点点"当通过）。
  S-2  各组体积分数是否向**自协调配比**靠拢（Burgers 下同一 packet 内两变体 ≈ 等分；
       判据用 `|f_i − f̄|/f̄`）。
  S-3  **正对照**：把观测构型本身当作"随机"的一个样本喂进去 ⇒ z 分数必须在 0 附近
       （证明量具能分辨"没差别"）。
  ⛔ 若 S-3 不过，S-1 的任何结论都作废。

做法（便宜：只用 `PF3D`，不用重建 `LevelSetMulti` 的 12 个 `argmin_normal`）
----------------------------------------------------------------------------
  从快照 `snap_*.npz` 读 `region()`（int8）⇒ 直接喂给 `PF3D` 的指示场 ⇒ `E_el()`。
  随机对照 = 对**非母相**胞的变体号做随机置换（**保持各变体体积分数不变**）。

用法：
  python3 _r1_selfac.py --snap _exp/e7_selfac/snap_00300.npz --nrand 24
  python3 _r1_selfac.py --selftest          # 量具正对照（随机对随机的 z 分布）
"""
import os
import sys
import glob
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                              # noqa: E402
from T16_verify_rve import C, EPS0, NV, DF, MOB                 # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--snap', default=None)
ap.add_argument('--N', type=int, default=192)
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--nrand', type=int, default=24)
ap.add_argument('--workers', type=int, default=8)
ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--selftest', action='store_true')
a = ap.parse_args()

L = a.L_um * 1e-6
N = a.N
print('=' * 100)
print('_r1_selfac   N=%d  L=%.1f µm  Δx=%.1f nm  随机对照 n=%d'
      % (N, a.L_um, L / N * 1e9, a.nrand))
print('=' * 100, flush=True)

from windowB_pf3d import PF3D                                   # noqa: E402

t0 = time.time()
pf = PF3D(N, L, C, EPS0, gamma=0.0, w90=1e-8, Lmob=0.0,
          workers=a.workers, k0_mode='clamped', phi_dtype=bool, lam_prec='f64')
print('PF3D 构造 %.1f s' % (time.time() - t0), flush=True)


def eel_of(reg):
    """把 `region()`（0=母相，k=变体 k）喂给 PF3D 并返回 `E_el()`（J/m³）。"""
    pf.phi[:] = False
    for v in range(NV):
        pf.phi[v] = (reg == v + 1)
    return float(pf.E_el())


def rand_perm(reg, rng):
    """**保持各变体体积分数**的随机指派：只在"非母相"胞之间置换变体号。"""
    out = reg.copy()
    m = reg > 0
    out[m] = rng.permutation(reg[m])
    return out


if a.selftest:
    # ---- S-3 量具正对照：随机对随机，z 必须在 0 附近 ----
    rng = np.random.default_rng(1)
    print('\n【S-3 正对照】随机构型 vs 随机构型：z 分布必须**以 0 为中心**')
    zs = []
    for _ in range(6):
        r0 = rng.integers(0, NV + 1, size=(N, N, N)).astype(np.int8)
        r0[r0 > NV] = 0
        e0 = eel_of(r0)
        er = [eel_of(rand_perm(r0, rng)) for _ in range(6)]
        er = np.array(er)
        z = (e0 - er.mean()) / max(er.std(), 1e-30)
        zs.append(z)
        print('   一次试验：E_obs=%.4e  随机 mean=%.4e  sd=%.3e  **z=%+.2f**'
              % (e0, er.mean(), er.std(), z))
    print('   ⇒ z 的均值 = %+.2f（应 ≈0）、|z| 最大 = %.2f（6 次里不该有 >3）'
          % (float(np.mean(zs)), float(np.max(np.abs(zs)))))
    print('=' * 100)
    sys.exit(0)

if not a.snap:
    cand = sorted(glob.glob(os.path.join(HERE, '_exp', '*', 'snap_*.npz')))
    if not cand:
        print('✗ 找不到快照'); sys.exit(2)
    a.snap = cand[-1]
    print('（未给 --snap ⇒ 取最新的 %s）' % a.snap)

z = np.load(a.snap if os.path.isabs(a.snap) else os.path.join(HERE, a.snap))
reg = z['region'].astype(np.int8)
step = int(z['step']) if 'step' in z else -1
print('快照 %s  step=%s' % (a.snap, step), flush=True)

frac = {k: float((reg == k).mean()) for k in range(NV + 1)}
nz = {k: v for k, v in frac.items() if v > 1e-6}
print('体积分数：%s' % '  '.join('V%d=%.4f' % (k, v) for k, v in sorted(nz.items())))
if len([k for k in nz if k > 0]) < 2:
    print('⚠ 只有 1 个变体 ⇒ **实验 7 的 S-1 无意义**（自协调需要 ≥2 个变体）')

e_obs = eel_of(reg)
rng = np.random.default_rng(a.seed)
er = np.array([eel_of(rand_perm(reg, rng)) for _ in range(a.nrand)])
zsc = (e_obs - er.mean()) / max(er.std(), 1e-30)
pct = float((er < e_obs).mean())

print('\n' + '=' * 100)
print('S-1 弹性能对照（同一体积分数，随机指派变体）')
print('   E_el(观测)      = %.6e J/m³' % e_obs)
print('   E_el(随机) 均值 = %.6e J/m³   标准差 = %.3e   min = %.6e   max = %.6e'
      % (er.mean(), er.std(), er.min(), er.max()))
print('   **z = %+.2f**   （观测在随机分布中的分位 = %.2f）' % (zsc, pct))
print('   能量降低 = **%+.2f%%**' % (100 * (e_obs / er.mean() - 1)))
if zsc < -2.0:
    print('   ⇒ ✅ **S-1 通过**：观测构型显著低于随机指派 ⇒ 有自协调')
elif zsc > 2.0:
    print('   ⇒ ❌ **S-1 反向**：观测构型**高于**随机 ⇒ 不是自协调')
else:
    print('   ⇒ ⚠ **S-1 不显著**（|z|<2）：观测与随机指派**分不开** ⇒ 没有可测的自协调')

# ---- S-2：体积分数是否向等分靠拢 ----
vs = np.array([frac[k] for k in range(1, NV + 1) if frac[k] > 1e-6])
if vs.size >= 2:
    fbar = vs.mean()
    dev = np.abs(vs - fbar) / max(fbar, 1e-30)
    print('\nS-2 各变体体积分数：%s' % '  '.join('%.4f' % v for v in vs))
    print('   相对均值 %.4f 的偏差：%s   ⇒ 中位 **%.3f**'
          % (fbar, '  '.join('%.3f' % d for d in dev), float(np.median(dev))))
    print('   （判据：自协调的组织应让活跃变体**大致等分** ⇒ 中位偏差小）')
print('=' * 100)
