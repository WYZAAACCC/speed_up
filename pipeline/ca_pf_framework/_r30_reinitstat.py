#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_reinitstat.py —— R30 审计：`reinitialize()` 的**跳过判据统计域**是否被污染。

## 可疑点（读代码得到，file:line）

`windowB_surface.py::LevelSetMulti.reinitialize(mode='pair')`：

  * line 3746-3747：`d2 = 0.5*(phi[k] - phi[l])`；`near = np.abs(d2) <= band_cells*dx`
  * line 3784-3786：`_med = median(|grad d2| [near])`   ← **只在 `near` 上取中位**
  * line 3802：`if (not force) and abs(_med - 1.0) <= skip_tol: continue`  ← **跳过判据**
  * line 3816-3820：`if abs(_med - 1.0) > 0.5: warn(...)`
  * line 3826：`is_kl = ((karr==k)&(larr==l)) | ((karr==l)&(larr==k))`  ← **回写掩模**

⚠ **`is_kl` 是在 `_med` 之后才算的** ⇒ `_med` 统计的是**整个 `near` 带**，
**而不是"这一对 (k,l) 真正相邻的那些胞"**。

## 为什么这会真的发生（读 `seed_plate`）

`seed_plate`（line 2047-2055）对新播的场 k 做
`phi[k] = min(phi[k], sdf)`，同时**对其它每一个场 j** 做 `phi[j] = max(phi[j], -sdf)`。
⇒ 在新核盘**内部**，`-sdf > 0` ⇒ 所有别的场都被抬到 `≥ -sdf`；
若某两个场 i,j 在盘内的旧值都足够负，则两者**都被钉到 `-sdf`** ⇒ **φ_i ≡ φ_j**（盘内）
⇒ `d2 ≡ 0` 覆盖**整个新盘** ⇒ 只要 (i,j) 同时在别处相邻（⇒ 进 `pairs`），
`near` 就被新盘主导 ⇒ `_med → 0`。

## 本脚本要证明什么

P-1（正对照，证明检查有分辨力）：造一个**干净**的两片状态 ⇒ `_med(near)` ≈ 1 且
    `_med(near & is_kl)` ≈ 1，两者一致 ⇒ 判据在这种状态下没问题。
P-2（病灶）：再用 `seed_plate` 播第三片（于是前两场的 φ 在新盘内被一起钉到 `-sdf`）
    ⇒ `_med(near)` 被拉到 ≈0，而 `_med(near & is_kl)` 仍然 ≈1
    ⇒ **两者分家 ⇒ 跳过判据看错了对象**。
P-3：直接调 `g.reinitialize()`，读引擎**自己**记的 `_reinit_last_med` 与
    `_reinit_skipped`/`_reinit_done`，确认它真的按（被污染的）`_med` 做决定。

跑法：  python3 _r30_reinitstat.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF                         # noqa: E402

N, DX = 48, 62.5e-9
L = N * DX


def build(nlat=3):
    lt = WL.LathTable([1] * nlat, omegas=WL.default_omega(nlat, 5.0,
                                                          axis=np.array([1.0, 0, 0])),
                      eps0_var=EPS0, npref_var=NPF, gamma0=0.25)
    g = W.LevelSetMulti(N, L, C=C, eps0=lt.eps0, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [1.5e8] * nlat, workers=1, reinit_every=0)
    g.lath = lt
    return g


def stat(g, k, l, band_cells=20):
    """复刻 reinitialize() 里的 _med 计算，但分开报两个口径。"""
    d2 = 0.5 * (g.phi[k] - g.phi[l])
    near = np.abs(d2) <= band_cells * g.dx
    if not near.any():
        return None
    gd = np.gradient(d2, g.dx, edge_order=2)
    gdn = np.sqrt(sum(x ** 2 for x in gd))
    order = np.argsort(g.phi, axis=0)
    ka, la = order[0], order[1]
    is_kl = ((ka == k) & (la == l)) | ((ka == l) & (la == k))
    m_all = float(np.median(gdn[near]))
    m_int = float(np.median(gdn[near & is_kl])) if (near & is_kl).any() else float('nan')
    return dict(near=int(near.sum()), inter=int((near & is_kl).sum()),
                m_all=m_all, m_int=m_int, d2_disk=int((np.abs(d2) < 1e-12).sum()))


def main():
    n_hab = np.array([0.0, 0.0, 1.0])
    a_ax = np.array([1.0, 0.0, 0.0])
    w_ax = np.cross(n_hab, a_ax)

    # ---------------- P-1 干净状态：两片沿 n* 堆叠、不重叠 ----------------
    g = build(3)
    g.init_parent()
    t = 250e-9
    g.seed_plate(1, np.array([L / 2, L / 2, L / 2 - 1.5 * t]), n_hab, 600e-9, t,
                 elong=1.0, along=a_ax, flat_end=True)
    g.seed_plate(2, np.array([L / 2, L / 2, L / 2 + 1.5 * t]), n_hab, 600e-9, t,
                 elong=1.0, along=a_ax, flat_end=True)
    s = stat(g, 1, 2)
    print('=' * 78)
    print('P-1 干净状态（两片不重叠；第三场从未播种）')
    print('   near=%d  near∩is_kl=%d  d2≡0 的胞=%d' % (s['near'], s['inter'], s['d2_disk']))
    print('   _med(near)=%.4f   _med(near∩is_kl)=%.4f   ⇒ 差值 %.2e'
          % (s['m_all'], s['m_int'], abs(s['m_all'] - s['m_int'])))

    # ---------------- P-2 病灶：再播第三片，且它与场 1、2 都重叠 ----------------
    g2 = build(3)
    g2.init_parent()
    g2.seed_plate(1, np.array([L / 2, L / 2, L / 2 - 1.5 * t]), n_hab, 600e-9, t,
                  elong=1.0, along=a_ax, flat_end=True)
    g2.seed_plate(2, np.array([L / 2, L / 2, L / 2 + 1.5 * t]), n_hab, 600e-9, t,
                  elong=1.0, along=a_ax, flat_end=True)
    before = stat(g2, 1, 2)
    # 第三片播在**场地中央**、与 1/2 都咬入 ⇒ 盘内所有别的场被一起钉到 -sdf
    g2.seed_plate(3, np.array([L / 2, L / 2, L / 2]), n_hab, 900e-9, 3.5 * t,
                  elong=1.0, along=a_ax, flat_end=True)
    after = stat(g2, 1, 2)
    print('\nP-2 播下第三片（大而居中）之后，**同一对 (1,2)** 的统计：')
    print('   %-14s %-10s %-12s %-16s %-16s' % ('', 'near', 'near∩is_kl', '_med(near)',
                                                '_med(near∩is_kl)'))
    for tag, s2 in (('播之前', before), ('播之后', after)):
        print('   %-14s %-10d %-12d %-16.4f %-16.4f'
              % (tag, s2['near'], s2['inter'], s2['m_all'], s2['m_int']))
    ok = (abs(before['m_all'] - 1.0) < 0.5) and (after['m_all'] < 0.5) \
        and (abs(after['m_int'] - 1.0) < 0.5)
    print('   ⇒ 病灶成立？ %s（播之后 `_med(near)` 掉到 %.3f，而真界面口径仍是 %.3f）'
          % ('✅ 是' if ok else '❌ 否', after['m_all'], after['m_int']))

    # ---------------- P-3 直接问引擎自己 ----------------
    print('\nP-3 直接调 `g2.reinitialize()`，读引擎自己的记账：')
    for tag, gg in (('干净 g', g), ('病灶 g2', g2)):
        gg._reinit_done = 0
        gg._reinit_skipped = 0
        for _ in range(4):
            gg.reinitialize()
        print('   %-9s _reinit_last_med=%.4f  done=%d  skipped=%d'
              % (tag, float(getattr(gg, '_reinit_last_med', float('nan'))),
                 gg._reinit_done, gg._reinit_skipped))
    print('\n⚠ 结论口径：若 P-2/P-3 成立，则 `_med` 的**统计域**与它要服务的判据'
          '（"带内 |∇d2| 是否已经够 SDF"）**不是同一个域** —— '
          '回写掩模是对的（`is_kl`），但**跳过判据与告警看错了对象**。')


if __name__ == '__main__':
    main()
