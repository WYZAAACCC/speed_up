#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r47_rates.py —— **用「面间距」金标准口径重报长大速率**（R47 / 阶段计划第 2 步）。

## 为什么（`R30_AUDIT_LEDGER.md` §17）
包围盒口径把面间距的增长**放大 2.5–2.8×**（`a` 与 `w` 两方向都验过），
而全项目的"实测长大速率"（`BLOCK_DERIVATION §9.5` 的 **15.5 nm/步**、C-3 步数下界、
"盒子该多大"）**用的都是包围盒口径** ⇒ 必须用金标准重报。

## 口径
对每个场、每个面族（tip/side/wide），由**落盘的带内稀疏 φ** 算面间距（与
`_bk_measure.face_separations` **同一套**），再对 (step, sep) 做最小二乘 ⇒ **nm/步**。

⚠ **只对带 `band_*` 的快照有效**（R30 之前跑的归档臂**没有 φ** ⇒ 本工具会明确报
"无法重报"，**不**回退到包围盒口径 —— 回退会掩盖问题）。

用法：  python3 _r47_rates.py _exp/_bk_mb/dry_mb1s [--fields 1,2,3]
        python3 _r47_rates.py --scan          # 扫描 _exp 下所有带 φ 的臂
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from _r33_remeasure import variant_axes                         # noqa: E402
from _r33_thickdiag import load_phi                             # noqa: E402


def rates_for(d, fields=None):
    snaps = [s for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
             if 'band_idx' in np.load(s).files]
    if len(snaps) < 3:
        return None
    z0 = np.load(snaps[0])
    vm = {int(a): int(b) for a, b in zip(z0['vmap_keys'], z0['vmap_vals'])}
    ks = fields or sorted(vm)
    ax = {}
    for v in sorted(set(vm.values())):
        n, a, w = variant_axes(v)
        ax[v] = dict(tip=a, side=w, wide=n)
    seq = {k: {t: ([], []) for t in ('tip', 'side', 'wide')} for k in ks}
    for s in snaps:
        z = np.load(s)
        N = int(z['N'])
        dx = float(z['L']) / N
        nreg = len(z['vmap_keys']) + 1
        phi = load_phi(z, nreg, N)
        st = int(z['step'])
        for k in ks:
            if k >= nreg or not np.isfinite(phi[k]).any():
                continue
            d = BM.face_separations(phi, dx, ax[vm[k]], k)
            for t, v in d.items():
                seq[k][t][0].append(st)
                seq[k][t][1].append(v * 1e9)
    return seq


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    dirs = sys.argv[1:]
    if dirs and dirs[0] == '--scan':
        dirs = sorted({os.path.dirname(p) for p in
                       glob.glob('_exp/**/snap_*.npz', recursive=True)})
    for d in dirs:
        r = rates_for(d)
        print('=' * 92)
        print('臂 %s' % d)
        if r is None:
            print('   ⚠ **无法重报**：带 `band_*` 的快照 < 3 个（R30 之前跑的归档臂没有 φ）')
            continue
        print('  %-5s %-6s %-11s %-11s %-11s %s'
              % ('场', '面族', '首值 nm', '末值 nm', 'Δ nm', '**速率 nm/步**'))
        for k in sorted(r):
            for t in ('tip', 'side', 'wide'):
                xs, ys = r[k][t]
                if len(xs) < 3:
                    continue
                sl = float(np.polyfit(np.array(xs, float), np.array(ys, float), 1)[0])
                print('  %-5d %-6s %-11.0f %-11.0f %-11.0f %+.4f'
                      % (k, t, ys[0], ys[-1], ys[-1] - ys[0], sl))
    print('\n★ 预登记判据：**「长大速率」一律用本口径**；包围盒口径（`n_lath`/`blk_alen_nm`）')
    print('  与逐胞中位 `dG` **都不得**用作速率读数（前者放大 2.5–2.8×，后者不预测面运动）。')


if __name__ == '__main__':
    main()
