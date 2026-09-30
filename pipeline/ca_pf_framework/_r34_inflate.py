#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r34_inflate.py —— **P1-23 的零成本复核**：包围盒口径把"长大"放大多少倍？

## 问题
R38 实测 MB-1 两臂：**包围盒**口径的 a 跨度是**核心**（最大连通分量）口径的
**2.21× / 2.51×**。而全项目多处引用的"实测长大速率"（`BLOCK_DERIVATION §9.5` 的
15.5 nm/步、C-3 步数下界）**都是包围盒口径**。
⇒ 若这个放大倍数**普遍成立**，那些设计约束就要整体重估。

## 本脚本（**只吃 `region`，不需要 φ，不跑新仿真**）
对一批**已跑完的归档臂**，在**最后一个快照**上同时算：
  `bbox`  = 该变体**全部胞**沿其长轴 a 的 ptp（= `blocks()` 的旧口径）
  `core`  = 该变体**最大连通分量**沿 a 的 ptp（碎片免疫）
  `ncomp` = 连通分量数
⇒ 报 `bbox/core` 的**倍数**与分量数。

判据（先写死）：
  * 若倍数在**多数臂**上都 ≳1.5 ⇒ P1-23 **成立**（包围盒口径系统性高估）；
  * 若倍数多在 1.0–1.2 ⇒ P1-23 **不成立**（MB-1 是特例）。

用法：  python3 _r34_inflate.py            # 用内置的臂清单
        python3 _r34_inflate.py _exp/_bk_closed/dry_cl1b ...
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from _r33_remeasure import variant_axes                         # noqa: E402

DEFAULT = [
    '_exp/_bk_closed/dry_cl1b', '_exp/_bk_closed/dry_cln2',
    '_exp/_bk_closed/dry_cl1gb', '_exp/_bk_mb/dry_mb1',
    '_exp/_bk_mb/dry_mb1s', '_exp/_bk_eng/dry_def3',
]


def one(d):
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        return None
    z = np.load(snaps[-1])
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    rows = []
    for v in sorted(set(vm.values())):
        ks = [k for k, vv in vm.items() if vv == v]
        m = np.zeros(reg.shape, bool)
        for k in ks:
            m |= (reg == k)
        if int(m.sum()) < 50:
            continue
        lab, nlab = BM._label_periodic(m)
        sizes = np.bincount(lab.ravel(), minlength=nlab + 1)[1:]
        big = int(np.argmax(sizes)) + 1
        mb = (lab == big)
        _, a_ax, _ = variant_axes(v)
        ii = np.arange(reg.shape[0]) * dx
        pa = (a_ax[0] * ii[:, None, None] + a_ax[1] * ii[None, :, None]
              + a_ax[2] * ii[None, None, :])
        bbox = float(np.ptp(pa[m])) * 1e9
        core = float(np.ptp(pa[mb])) * 1e9
        # ★ R40：**核心**有没有碰到盒面（vs 旧的"任一胞碰壁"口径）
        N = reg.shape[0]
        wall_any = bool(any(np.take(m, 0, axis=ax).any()
                            or np.take(m, N - 1, axis=ax).any() for ax in (0, 1, 2)))
        wall_core = bool(any(np.take(mb, 0, axis=ax).any()
                             or np.take(mb, N - 1, axis=ax).any() for ax in (0, 1, 2)))
        rows.append((v, bbox, core, nlab, int(m.sum()), int(sizes[big - 1]),
                     int(wall_any), int(wall_core)))
    return (os.path.basename(d), int(z['step']), rows)


def main():
    dirs = sys.argv[1:] or DEFAULT
    print('★ 包围盒口径 vs **核心**口径（只吃 region；最后一个快照）')
    print('  %-22s %-6s %-4s %-11s %-11s %-8s %-9s %s'
          % ('臂', 'step', '变体', 'bbox a 跨度', 'core a 跨度', '倍数', '分量数',
             '触壁 任一/核心'))
    mults = []
    n_any = n_core = n_tot2 = 0
    for d in dirs:
        if not os.path.isdir(d):
            print('  %-22s （不存在）' % os.path.basename(d))
            continue
        r = one(d)
        if r is None:
            print('  %-22s （无快照）' % os.path.basename(d))
            continue
        name, step, rows = r
        for v, bbox, core, nlab, ntot, ncore, wa, wc in rows:
            mult = (bbox / core) if core > 1e-9 else float('nan')
            mults.append(mult)
            n_tot2 += 1
            n_any += int(bool(wa))
            n_core += int(bool(wc))
            print('  %-22s %-6d %-4d %-11.0f %-11.0f %-8.2f %-9s %d/%d'
                  % (name, step, v, bbox, core, mult,
                     '%d（占 %d/%d 胞）' % (nlab, ncore, ntot), wa, wc))
    if mults:
        m = np.array([x for x in mults if np.isfinite(x)])
        print('\n⇒ 共 %d 个（臂,变体）样本：倍数 中位 **%.2f**、最小 %.2f、最大 %.2f'
              % (m.size, np.median(m), m.min(), m.max()))
        print('   ≥1.5 的占 %d/%d（%.0f%%）⇒ %s'
              % (int((m >= 1.5).sum()), m.size, 100.0 * (m >= 1.5).mean(),
                 '**P1-23 成立**（包围盒口径系统性高估）' if (m >= 1.5).mean() > 0.5
                 else 'P1-23 不成立（MB-1 是特例）'))
        print('\n★ **撞壁判据的两套口径**：旧"任一胞碰壁" ⟹ **%d/%d**；'
              '新"**核心**碰壁" ⟹ **%d/%d**'
              % (n_any, n_tot2, n_core, n_tot2))
        if n_any > n_core:
            print('   ⇒ ⚠⚠ **%d 个样本的"撞壁"是孤儿造成的** ⇒ '
                  '一切以 `box_touch` 为前提的判决都要重判（P1-22 的后果）。'
                  % (n_any - n_core))


if __name__ == '__main__':
    main()
