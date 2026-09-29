#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_thick.py —— 用**剔孤儿的稳健厚度**量一个算例的**最新快照**（不跑仿真）。

为什么需要它：`series.csv` 的 `ths` 列读的是 `_bk_measure` 的原始 `n_%d`
（**包围尺寸**），会被 1–2 体素的孤立碎点污染 —— 本仓库已为此栽过四次
（V-2 基准、V-6 基准、V-8b、R-5）。长跑途中看到厚度跳一下，必须先分清
"板条真的增厚了"还是"冒出个碎点把包围盒撑大了"，否则会白等两小时。

用法：
    python3 _bk_thick.py _exp/_bk_closed/dry_cl1
    python3 _bk_thick.py _exp/_bk_closed/dry_cl1 --plate-t 510
"""
import argparse
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--plate-t', type=float, default=0.0,
                    help='0 = 从 meta.json 的 plate.T 取')
    a = ap.parse_args()
    import _bk_cmp as CMP
    for d in a.dirs:
        p = os.path.join(_HERE, d)
        snaps = sorted(glob.glob(os.path.join(p, 'snap_*.npz')))
        mp = os.path.join(p, 'meta.json')
        if not snaps or not os.path.exists(mp):
            print('%-34s （缺快照或 meta）' % d)
            continue
        meta = json.load(open(mp, encoding='utf-8'))
        _pl = meta.get('plate') or {}
        # ★ 靶必须是**物理**厚（`T_physical`），不是播种厚 `T` —— 与 V-8b 同口径。
        #   （播种厚里含"预补的被咬量"，拿它当靶等于自己跟自己比。）
        t0 = a.plate_t or float(_pl.get('T_physical') or _pl.get('T', 250.0))
        z = np.load(snaps[-1], allow_pickle=True)
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        nh = np.asarray(z['n_hab'], float)
        nv = int(meta.get('nv', 0))
        print('--- %s（末快照 %s，step=%s，t=%.0f nm，dx=%.2f nm）'
              % (d, os.path.basename(snaps[-1]), z['step'], t0, dx * 1e9))
        raw = []
        for k in range(1, nv + 1):
            if not (reg == k).any():
                continue
            nk = int((reg == k).sum())
            rth = CMP.robust_thickness(reg, dx, nh, k) * 1e9
            # 原始包围尺寸（与 `_bk_measure` 的 n_%d 同口径）
            idx = np.argwhere(reg == k).astype(float)
            pr = idx @ nh
            rawk = float(pr.max() - pr.min() + 1) * dx * 1e9
            raw.append(rawk)
            print('    场 %d：体素 %6d  原始包围 %7.1f nm  剔孤儿 %7.1f nm  与种子比 %+.1f%%'
                  % (k, nk, rawk, rth, 100.0 * (rth / t0 - 1.0)))
        print('    ⇒ 落在 [%.0f, %.0f] nm 内的场数 = %d / %d'
              % (0.8 * t0, 1.3 * t0,
                 sum(1 for k in range(1, nv + 1) if (reg == k).any()
                     and 0.8 * t0 <= CMP.robust_thickness(reg, dx, nh, k) * 1e9
                     <= 1.3 * t0),
                 sum(1 for k in range(1, nv + 1) if (reg == k).any())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
