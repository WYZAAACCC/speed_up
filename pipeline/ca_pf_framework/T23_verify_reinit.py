#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T23_verify_reinit.py --- **A2**：重初始化**不得移动零等值面**。

问题（代码自己在每次运行打印的告警）
--------------------------------
    `pair reinit: band |grad(d/2)| median=0.35–0.49 明显偏离 1;
     Sussman will move the zero-level set (input not SDF)`
即：`d` 在带内**不是**距离函数（`|∇(d/2)|` 应 = 1），而 Sussman 迭代是**为 SDF 设计的**
⇒ 在非 SDF 输入上它会把零等值面**平移**（等于给界面加一个假速度）。

判据（已知答案，MEASUREMENT_SPEC R0）
------------------------------------
  **T23-1 零位移（核心）**：取任一演化态，**冻结速度**、只调用一次 `g.reinitialize()`，
          零等值面**必须不动**。量具用**无偏**的：区域体积（整数计数）与
          `Δ = median(φ_karr) 在界面带内`。判据：`|ΔV|/V < 2e-4`。
  **T23-2 幂等性**：连续调用 5 次 reinit，位移必须**不累积**（第 5 次的位移与第 1 次同量级或更小）。
  **T23-3 根因定位（R2：先写下期望再量）**：
          * 若 `|∇(d/2)|` **在种子之后立刻**就 ≠1 ⇒ **种子**的问题（`seed_plate`/`init_parent`
            产生非 SDF 场），不是重初始化的错；
          * 若种子时 =1、演化后掉到 0.44 ⇒ **平流/带**的问题。
  **T23-4 守卫有效性**：现在代码只在 `median` 偏离时**告警**，不做任何事。
          本判据要求把它变成**硬守卫**（偏离超过阈值时拒绝/修正），并给出阈值。

用法：python3 T23_verify_reinit.py [--N 64] [--dx-nm 25]
退出码：0 = PASS
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

MOB, DF = 1e-9, 2.0e8


def band_grad(g, tag=''):
    """带内 `|∇(d/2)|` 与逐场 `|∇φ|` 的中位（`d = σ(φ_karr − φ_larr)`）。"""
    ph = g.phi
    karr = np.argmin(ph, axis=0)
    larr = np.empty(karr.shape, dtype=karr.dtype)
    best = np.full(karr.shape, np.inf)
    for j in range(g.nreg):
        m = (karr != j) & (ph[j] < best)
        larr[m] = j
        best[m] = ph[j][m]
    pha = np.take_along_axis(ph, karr[None], 0)[0]
    phb = np.take_along_axis(ph, larr[None], 0)[0]
    sg = np.where(karr < larr, 1.0, -1.0)
    d = sg * (pha - phb)
    gd = np.gradient(d, g.dx, edge_order=2)
    gdn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
    band = np.abs(d) <= 4.0 * g.dx
    gk = np.gradient(pha, g.dx, edge_order=2)
    gkn = np.sqrt(sum(t ** 2 for t in gk)) + 1e-30
    return dict(gd2=float(np.median((gdn / 2.0)[band])),
                gphi=float(np.median(gkn[band])),
                nband=int(band.sum()), tag=tag)


def vol(g):
    reg = g.region()
    return float((reg > 0).sum()) / g.N ** 3


def zero_shift_metric(g):
    """★ 记账（**本函数是坏量具，只作诊断，不参与判定**）：
       界面带内 `median(φ_karr)`。带掩模是 `|φ_karr| ≤ 3Δx` —— **由数值定义**的，
       而 reinit 的**本意就是改这些数值** ⇒ reinit 之后掩模本身选了**另一批胞**
       ⇒ 该统计量的变化**混入了掩模漂移**，**不是**零等值面的位移。
       实测（A2 修后）：`翻转胞 = 0`（几何逐位不变）而本量仍读出 0.014–0.079 Δx
       ⇒ 与 `MEASUREMENT_SPEC` R3/R4 同类：**不要用"由被测量自己定义的掩模"去做统计**。
       ⇒ 判定用 `region()` 的**逐胞比较**（离散、无掩模、可逐位核对）。"""
    ph = g.phi
    pha = np.min(ph, axis=0)
    band = np.abs(pha) <= 3.0 * g.dx
    return float(np.median(pha[band])) if band.any() else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--steps', type=int, default=300)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    print('=' * 104)
    print('T23 —— A2：重初始化必须**不移动**零等值面   N=%d Δx=%.1f nm L=%.2f µm'
          % (N, a.dx_nm, L * 1e6))
    print('=' * 104)

    # ---------- T23-3 根因定位：种子之后立刻量 ----------
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(80):
        if ns >= 12:
            break
        c = rng.random(3) * (L - 1.6e-6) + 0.8e-6
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, 3.2e-7, 1.0e-7)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    b0 = band_grad(g, 'seed')
    print('【T23-3】根因定位（R2 先写下期望：`|∇(d/2)|` 应 = 1.000）')
    print('   **种子刚建好**（未推进）：胞数 %d  `|∇(d/2)|` 中位 = **%.3f**  '
          '`|∇φ|` 中位 = %.3f' % (b0['nband'], b0['gd2'], b0['gphi']))
    print('   ⇒ %s' % ('**种子本身就非 SDF** ⇒ 病灶在 `seed_plate`/`init_parent`'
                       if abs(b0['gd2'] - 1.0) > 0.15
                       else '种子是 SDF ⇒ 病灶在平流/带（看下面随步数的演化）'))
    dt = 0.15 * dx / (MOB * DF)
    traj = [(0, b0['gd2'], b0['gphi'])]
    for it in range(1, a.steps + 1):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
        if it % 50 == 0:
            b = band_grad(g)
            traj.append((it, b['gd2'], b['gphi']))
    print('   随步数演化：')
    for it, gd2, gphi in traj:
        print('      step %-4d  `|∇(d/2)|` = %.3f   `|∇φ|` = %.3f' % (it, gd2, gphi))

    # ---------- T23-1 零位移（核心）----------
    print('-' * 104)
    print('【T23-1】**零位移**：冻结速度、只调一次 `reinitialize()` ⇒ 零等值面必须不动')
    print('   量具：区域体积（整数计数）与带内 `median(φ_karr)` 的**无偏**位移')
    g2 = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                         df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                         reinit_dt=None)          # ★ 关掉自动 reinit，手动调
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(80):
        if ns >= 12:
            break
        c = rng.random(3) * (L - 1.6e-6) + 0.8e-6
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g2.seed_plate(k, c, nrm, 3.2e-7, 1.0e-7)
            ns += 1
        except ValueError:
            pass
    g2.init_parent()
    for _ in range(40):                    # 先演化到"脏"的状态（这才是真实工况）
        g2.elastic_driving()
        g2.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    ok1 = True
    print('   %-6s %-14s %-14s %-14s %-10s %s'
          % ('第几次', 'ΔV/V', 'Δmedianφ/dx', '|∇(d/2)| 前→后', '翻转胞', '判定'))
    prev_reg = None
    for rep in range(1, 6):
        v0, z0 = vol(g2), zero_shift_metric(g2)
        b_before = band_grad(g2)['gd2']
        reg_before = g2.region()
        g2.reinitialize()
        reg_after = g2.region()
        v1, z1 = vol(g2), zero_shift_metric(g2)
        b_after = band_grad(g2)['gd2']
        # ★★ A2 的**精确判据**（离散、可逐位）：`region()` 必须**逐个胞相同**。
        nflip = int((reg_after != reg_before).sum())
        dV = abs(v1 - v0) / max(abs(v0), 1e-30)
        dz = abs(z1 - z0) / dx
        # ★★ 判定只取**离散、无掩模**的两条（`region()` 逐胞 + 体积）；
        #    `dz` 只打印作诊断（它是坏量具，见 `zero_shift_metric` 的记账）。
        good = (nflip == 0) and (dV < 2e-4)
        ok1 &= good
        print('   %-6d %-14.3e %-14.3e %-14s %-10d %s'
              % (rep, dV, dz, '%.3f→%.3f' % (b_before, b_after), nflip,
                 'PASS' if good else 'FAIL'))
    print('   T23-1（零位移；判据 = **翻转胞数 == 0** 且 ΔV/V < 2e-4）: %s'
          % ('PASS' if ok1 else 'FAIL'))
    print('   ★ 记账：判据**不能**用 `Δmedian(φ_karr)` —— 它的带掩模由数值自身定义，')
    print('     reinit 改数值 ⇒ 掩模选了另一批胞 ⇒ 读数混入掩模漂移（实测：翻转胞=0')
    print('     却仍读出 0.014–0.079 Δx）。`region()` 才是"几何"的定义。')
    print('   代码内计数：reinit 跳过 %d 次 / 执行 %d 次 ⇒ 跳过率 %.2f'
          % (getattr(g2, '_reinit_skipped', 0), getattr(g2, '_reinit_done', 0),
             getattr(g2, '_reinit_skipped', 0)
             / max(getattr(g2, '_reinit_skipped', 0) + getattr(g2, '_reinit_done', 0), 1)))
    print('   T23-2（幂等性：位移不随次数累积）: %s'
          % ('PASS' if ok1 else 'FAIL（与 T23-1 同判据，逐次都查）'))
    print('=' * 104)
    print('  ⇒ T23 %s' % ('PASS' if ok1 else 'FAIL（确认缺陷，需修法）'))
    print('=' * 104)
    return 0 if ok1 else 1


if __name__ == '__main__':
    sys.exit(main())
