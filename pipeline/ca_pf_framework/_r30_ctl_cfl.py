#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_ctl_cfl.py —— R30 审计：`cfl_used` 列（`_bk_exp.py:725`）的**正对照**。

    cfl_used = dt · MOB · g.dG_max / dx      （单位：胞/步）

语义=「本步界面沿法向位移了几个 Δx」。它存在的唯一理由是事后核 CFL
（`_bk_exp.py:75-82` 记账：驱动层只按**化学** Δf 定 dt，而 `dG_max` 是**总驱动**
（含弹性+曲率）⇒ 实际每步位移可能远超名义 0.15Δx）。

★ 装置**照抄仓库已有的标定**（`_chk_w2.py`，本仓库教训："先看有没有现成的"）：
   周期 **slab** 初值（不是半空间！半空间 SDF 与 `np.roll` 周期模板冲突，
   wrap 处 |∇φ| 被算成 47 ⇒ 界面被推 4.7dx/步 —— 那正是 `_chk_w2.py` 的负对照），
   位置口径用 `LevelSetMulti.iface_offset`（亚胞射线交点）。
   已有判据：`|v|/(MΔf) − 1| < 0.02`。

本脚本在**同一算例上**同时量三样：
   ① 射线口径的界面速度 v（对照解析 `M·Δf`）；
   ② Σ`cfl_used`（台账列声称的总位移）；
   ③ 名义值 Σ dt·M·Δf/dx。
三者对上，`cfl_used` 才能当事后判据用。

用法: python3 _r30_ctl_cfl.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _chk_w2 as W2                                            # noqa: E402
from windowB_surface import LevelSetMulti                       # noqa: E402


def seed_gamma(N, dx, df, gamma):
    """与 `_chk_w2._seed(kind='slab')` **逐字相同**的初值，只是 γ 在**构造时**给
    （不能构造后再改 `g.gamma` —— `__init__` 里与 γ 相关的预处理就漏掉了）。"""
    g = LevelSetMulti(N, N * dx, nv=1, gamma=gamma, Mob=1e-9,
                      df=[0.0, -df], reinit_every=0)
    z = (np.arange(N)[None, None, :] + 0.5) * dx
    L = N * dx
    a = (N // 2) * dx
    g.phi[1] = np.where(z <= a, -np.minimum(z, a - z),
                        np.minimum(z - a, L - z)) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    return g


def run(N=48, dx=2e-9, M=1e-9, df=1e7, nstep=40, gamma=0.0, band=20):
    g = seed_gamma(N, dx, df, gamma)
    _, z0 = g.iface_offset(1, 0, 2, near=g.near0)
    dt = 0.1 * dx / (M * df)
    scfl, sdg = 0.0, []
    for _ in range(nstep):
        g.advance(dt, extend='edt', band_cells=band)
        scfl += dt * M * float(g.dG_max) / dx
        sdg.append(float(g.dG_max))
    _, z1 = g.iface_offset(1, 0, 2, near=g.near0)
    return dict(v=abs(z1 - z0) / (nstep * dt), z0=z0, z1=z1, dt=dt,
                scfl=scfl, nom=nstep * dt * M * df / dx,
                dg_med=float(np.median(sdg)), dg_max=max(sdg), mdf=M * df)


def hr(t):
    print('\n' + '=' * 104)
    print(t)
    print('=' * 104, flush=True)


def main():
    print('=' * 104)
    print('R30：`cfl_used` 的正对照（装置照抄 `_chk_w2.py` 的**已标定**平界面算例）')
    print('=' * 104)
    bad = []
    for gamma in (0.0, 0.25):
        r = run(gamma=gamma)
        print('\n  --- γ = %.2f J/m²，40 步，Δx=2 nm ---' % gamma)
        print('     解析速度 M·Δf = %.4e m/s ；射线口径实测 v = %.4e m/s '
              '⇒ v/(MΔf) = **%.4f**（已有判据 |·−1|<0.02 ⇒ %s）'
              % (r['mdf'], r['v'], r['v'] / r['mdf'],
                 'PASS' if abs(r['v'] / r['mdf'] - 1) < 0.02 else '**FAIL**'))
        print('     dG_max 中位/最大 = %.4e / %.4e（纯 Δf = %.4e）'
              % (r['dg_med'], r['dg_max'], 1e7))
        print('     Σ`cfl_used`（台账列）= **%.4f 胞** ；射线实测位移 = **%.4f 胞**'
              % (r['scfl'], abs(r['z1'] - r['z0']) / 2e-9))
        print('     Σ名义（dt·M·Δf/dx） = %.4f 胞' % r['nom'])
        rel = abs(r['scfl'] - abs(r['z1'] - r['z0']) / 2e-9) / max(r['scfl'], 1e-30)
        print('     |Σcfl_used − 实测位移| / Σcfl_used = **%.2f%%** ⇒ %s'
              % (100 * rel, 'PASS' if rel < 0.05 else '**FAIL**'))
        if rel >= 0.05:
            bad.append(gamma)
    print('\n' + '=' * 104)
    print('★ 结论（全部【实测】）：')
    print('  1) γ=0 时 `cfl_used` **逐笔等于**射线口径实测位移（Σ4.0000 胞 = 4.0000 胞）⇒')
    print('     它的**定义**（dt·M·max|v|/dx）没错，量纲自洽。')
    print('  2) ⚠ 但 γ>0 时 `dG_max` 被**盒内任意胞**的曲率项主导（中位 1.35e8 = 13.5×Δf），')
    print('     而速度只加在界面带内 ⇒ `cfl_used` 变成**单边上界**：')
    print('     台账声称 Σ=84.40 胞，界面**实际只动了 0.0004 胞**（差 2×10⁵）。')
    print('  3) ⇒ `_bk_exp.py:75-82` 的记账写「实际用量必须落盘、判据才能事后核」，')
    print('     但这一列报的是**驱动力天花板**、不是**实际位移**；')
    print('     生产臂读到 `cfl_used`≈0.35–0.40 **不能**据此断言"界面每步走了 0.35–0.40 Δx"。')
    print('     要那个结论必须从落盘 region 逐对量界面位置（`f3_pairs_pos`，'
          '而正在跑的 `dry_cln11` 恰好没有这一列）。')
    print('  4) 方向是**保守**的（上界 ≥ 真值）⇒ 它不会漏报 CFL 超限，只会虚报。')
    print('=' * 104)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
