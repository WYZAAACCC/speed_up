#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r34_corelen.py —— **碎片免疫**的核心长度：mb1 阴性结果的根因诊断。

## 为什么要它（`R30_AUDIT_LEDGER.md` P1-19）
MB-1 的判据用 `blocks()` 的 `blk_alen_nm`（= 该块**全部胞**沿自身长轴 a 的 ptp）。
实测 `mb1s` 的 `nc`（连通分量数）到 **12–36** ⇒ **ptp 会被远处的 1–2 胞孤儿撑大**，
于是"减速/平台"可能只是**包围盒被孤儿污染**，不是块真的停住。

## 口径（先写死）
对每个变体 v：
1. 该变体的掩模 → `_label_periodic`（6-连通、**周期**）；
2. 取**最大**的连通分量（= 主板条/主块）；
3. 报该分量的（a 跨度, n* 跨度, 体积, 分量总数, ≥32 胞的显著分量数）。
⇒ 与 `blk_alen_nm` 的差 = **孤儿/碎片的贡献**（两者一起看就知道口径有没有被污染）。

用法：  python3 _r34_corelen.py _exp/_bk_mb/dry_mb1s --variant 1
        python3 _r34_corelen.py _exp/_bk_mb/dry_mb1  --variant 1
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from _r33_remeasure import variant_axes                         # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    d = sys.argv[1]
    v = int(sys.argv[sys.argv.index('--variant') + 1]) if '--variant' in sys.argv else 1
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        raise SystemExit('✗ 没有快照')
    print('目录 %s；%d 个快照；被诊断的变体 = V%d' % (d, len(snaps), v))
    print('  %-6s %-8s %-11s %-11s %-11s %-9s %s'
          % ('step', '分量数', '核心 a 跨度', '核心 w 跨度', '核心 n*跨度', '核心体积',
             '全体胞 a 跨度（blocks 旧口径）'))
    for s in snaps:
        z = np.load(s)
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        vm = {int(k): int(kk) for k, kk in zip(z['vmap_keys'], z['vmap_vals'])}
        ks = [k for k, vv in vm.items() if vv == v]
        if not ks:
            continue
        m = np.zeros(reg.shape, bool)
        for k in ks:
            m |= (reg == k)
        if not m.any():
            continue
        lab, nlab = BM._label_periodic(m)
        sizes = [int((lab == i).sum()) for i in range(1, nlab + 1)]
        order = np.argsort(sizes)[::-1]
        big = order[0] + 1
        mb = (lab == big)
        n_ax, a_ax, w_ax = variant_axes(v)
        ii = np.arange(reg.shape[0]) * dx
        rel = [ii[:, None, None], ii[None, :, None], ii[None, None, :]]
        pa = a_ax[0] * rel[0] + a_ax[1] * rel[1] + a_ax[2] * rel[2]
        pw = w_ax[0] * rel[0] + w_ax[1] * rel[1] + w_ax[2] * rel[2]
        pn = n_ax[0] * rel[0] + n_ax[1] * rel[1] + n_ax[2] * rel[2]
        al_core = float(np.ptp(pa[mb])) * 1e9
        wl_core = float(np.ptp(pw[mb])) * 1e9
        sp_core = float(np.ptp(pn[mb])) * 1e9
        al_all = float(np.ptp(pa[m])) * 1e9
        nsig = sum(1 for x in sizes if x >= 32)
        print('  %-6d %-8d %-11.0f %-11.0f %-11.0f %-9d %.0f（%d 显著）'
              % (int(z['step']), nlab, al_core, wl_core, sp_core, sizes[order[0]],
                 al_all, nsig))


if __name__ == '__main__':
    main()
