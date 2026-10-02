#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_wfthick.py --- ★★★★★★★ **用仓库**自己的正确量具**（`_bk_measure.wide_face_thickness`）交叉验证

## 为什么
R36 已经写好并登记了 `wide_face_thickness`（`t_wf` = 两张宽面之间的距离，由 φ 量）
—— 正是为了替代被证伪的"包围盒跨度"口径。
**⇒ 本轮直接调它，对 `snap_00250` 的每个场出 `t_wf`** ⇒ 与 PCA / S/V **三个独立口径**对比。

## 判据（**先写死**）
| 三口径 | 判决 |
|---|---|
| **S/V ≈ 2/t_wf**（**一致**） | **✅ 真厚度可信 ⇒ **是薄板**** |
| **t_wf ≪ 最长跨度** | **✅ 板条形状成立** |
| **t_wf ≈ 最长跨度** | **❌ 等轴 ⇒ C2 的否定成立** |
| **`t_wf` 返回 `None`（不可测）** | **⚠ 无法判定**（**不是"0"**） |
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bk_measure as BM


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk/dry_BK6/snap_00250.npz'
    dx = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5e-9
    print('=' * 100)
    print('仓库自己的量具 `wide_face_thickness`：%s（dx=%.1f nm）' % (snap, dx * 1e9))
    print('=' * 100)
    z = np.load(snap)
    reg = np.asarray(z['region'])
    n_hab = np.asarray(z['n_hab'], float)
    print('  n_hab = %s' % np.array2string(n_hab, precision=4))
    ks = sorted(set(int(x) for x in np.unique(reg)) - {0})
    print('  场数 %d' % len(ks))
    print()
    print('  %-6s %-9s %-13s %-13s %-11s %s' %
          ('场', '胞数', 't_wf(nm)', '最长跨度(nm)', '长/厚', '判读'))
    print('  ' + '-' * 92)
    res = []
    for k in ks:
        m = (reg == k)
        nvox = int(m.sum())
        if nvox < 20:
            continue
        idx = np.argwhere(m).astype(float)
        bb = (idx.max(axis=0) - idx.min(axis=0) + 1.0) * dx * 1e9
        longest = float(bb.max())
        # ★ 调仓库的量具（它要 (nreg,N,N,N) + k，或 3-D 单场）
        try:
            d = BM.wide_face_thickness(reg, dx, n_hab, k)
        except Exception as e:
            d = None
            print('    （场 %d 调用异常：%s）' % (k, e))
        if d is None:
            print('  %-6d %-9d %-13s %-13.0f %-11s %s' %
                  (k, nvox, '**None**', longest, '—', '⚠ 不可测（**不是 0**）'))
            continue
        t = float(d['t_wf']) * 1e9
        ratio = longest / max(t, 1e-9)
        res.append((k, nvox, t, longest, ratio))
        print('  %-6d %-9d %-13.1f %-13.0f %-11.2f %s' %
              (k, nvox, t, longest, ratio,
               '✅ 薄板' if ratio >= 5 else ('⚠ 中等' if ratio >= 2 else '❌ 近等轴')))
    print()
    if res:
        ts = np.array([r[2] for r in res])
        ls = np.array([r[3] for r in res])
        rs = np.array([r[4] for r in res])
        print('  ── 汇总（中位）──')
        print('  `t_wf` 中位 = **%.1f nm**；最长跨度中位 = %.0f nm；**长/厚 中位 = %.2f**'
              % (np.median(ts), np.median(ls), np.median(rs)))
        print('  ⇒ %s' % ('✅ **是板条**（长/厚 ≥5）' if np.median(rs) >= 5
                          else ('⚠ **中等**（2–5）' if np.median(rs) >= 2
                                else '❌ **近等轴**（<2）⇒ C2 的否定成立')))
    print()
    print('  ★ 与另两个口径对照（同一快照）：')
    print('   · **S/V 反解厚度 ≈ 1.70 胞 = 106 nm**（`_r581_trueshape.py`）')
    print('   · **PCA 最长 25.4 胞（×1.73 修正 ≈ 2748 nm）**')
    print('   ⇒ **若 `t_wf` ≈ 100 nm 且最长 ≈ 2–3 µm ⇒ 三口径一致 ⇒ 是板条**')
    print('=' * 100)


if __name__ == '__main__':
    main()
