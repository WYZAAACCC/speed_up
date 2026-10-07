#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r325_edvtrend.py —— `saSet2EDV`（**跑满 400 步**）的完整趋势摘要。

`§156` 用的是这条臂的**早期**读段（step 20–160）。现在跑满了 ⇒ 可以看**全程**。
判据：
* **T-1** `vol_cv` 是否**单调上升**？给出首/末、升的步占比、以及分段均值。
* **T-2** `ed` 极差/标准差是否同步上升？
* **T-3** **相关性**：`vol_cv` 与 `ed` 极差的 Pearson/Spearman。
* **T-4** 与 `_r322` 的 200 步实验**同窗对比**（step ≤200）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'diag_edv.json')


def main():
    print('=' * 100)
    print('_r325 —— `saSet2EDV` 全程趋势（400 步）')
    print('=' * 100)
    if not os.path.exists(P):
        print('  ⚠ 无 diag_edv.json'); return 2
    d = json.load(open(P))
    rec = d['rec']
    st = np.array([r['step'] for r in rec], float)
    cv = np.array([r.get('vol_cv', np.nan) for r in rec], float)
    sp = np.array([r.get('med_spread', np.nan) for r in rec], float)
    sd = np.array([r.get('med_std', np.nan) for r in rec], float)
    m = np.isfinite(cv)
    print('  记录 %d 条（step %d … %d）；`vol_cv` 有限 %d 条'
          % (len(rec), st[0], st[-1], m.sum()))
    print()
    print('  ## **T-1/T-2** 分段均值（每 40 步一段）')
    print('     %-12s %-14s %-14s %s' % ('step 段', '`vol_cv`', '`ed` 极差', '`ed` 标准差'))
    for a in range(0, 400, 40):
        mm = (st >= a) & (st < a + 40) & m
        if mm.sum() == 0:
            continue
        print('     %-12s %-14.4f %-14.4e %.4e'
              % ('%d–%d' % (a, a + 40), cv[mm].mean(), sp[mm].mean(), sd[mm].mean()))
    n = m.sum()
    up = int((np.diff(cv[m]) > 0).sum())
    print()
    print('  ## 汇总')
    print('     `vol_cv`：首 **%.4f** → 末 **%.4f**（**%.2f×**）；上升步占比 **%.1f%%**'
          % (cv[m][0], cv[m][-1], cv[m][-1] / cv[m][0], 100 * up / max(len(cv[m]) - 1, 1)))
    print('     `ed` 极差：首 **%.4e** → 末 **%.4e**（**%.2f×**）'
          % (sp[m][0], sp[m][-1], sp[m][-1] / sp[m][0]))
    print('     `ed` 标准差：首 **%.4e** → 末 **%.4e**（**%.2f×**）'
          % (sd[m][0], sd[m][-1], sd[m][-1] / sd[m][0]))
    # 相关性
    def pear(a, b):
        mm = np.isfinite(a) & np.isfinite(b)
        if mm.sum() < 3:
            return float('nan')
        return float(np.corrcoef(a[mm], b[mm])[0, 1])
    print()
    print('  ## **T-3** 相关性（全 400 步）')
    print('     `vol_cv` vs `ed` 极差：Pearson = **%.3f**' % pear(cv, sp))
    print('     `vol_cv` vs `ed` 标准差：Pearson = **%.3f**' % pear(cv, sd))
    # 分段
    print()
    print('  ## **T-4** 分窗看（与 `_r322` 的 200 步实验同窗）')
    for lo, hi in ((0, 100), (100, 200), (200, 300), (300, 401)):
        mm = (st >= lo) & (st < hi) & m
        if mm.sum() < 2:
            continue
        print('     step %-9s `vol_cv` %.4f → %.4f（**%.2f×**）；`ed` 极差 %.3e → %.3e（**%.2f×**）'
              % ('%d–%d' % (lo, hi - 1), cv[mm][0], cv[mm][-1],
                 cv[mm][-1] / cv[mm][0], sp[mm][0], sp[mm][-1], sp[mm][-1] / sp[mm][0]))
    print()
    print('  ⚠ 记账：本臂**带 `--facet-proj 10`**；`§162` 已证投影会**推高** `vol_cv`')
    print('     ⇒ 本表的增长**不能**直接读成"物理上的竞争性生长"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
