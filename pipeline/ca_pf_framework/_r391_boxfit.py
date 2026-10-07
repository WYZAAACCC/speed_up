#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r391_boxfit.py —— 回答「7 µm 盒子装得下多个块吗？板条会长出盒子吗？」

## 口径
* `series.csv` 里有 `box_touch`（**任一**已转变胞落在盒面）与
  `box_touch_core`（只看**最大连通分量**是否碰壁 —— 后者更严，见 `_bk_measure.py:994-1012`）。
* 还有 `n_lath` / `w_lath` / `a_lath`（沿 n*/w/a 的板条尺度）⇒ 与盒棱 7 µm 比。
* `Vt` 与 `f = Vt/盒体积`。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
BOX_NM = 7000.0
BOX_UM3 = 343.0


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def g(r, k, d=float('nan')):
    try:
        v = r.get(k, '')
        return float(v) if v not in ('', None) else d
    except (TypeError, ValueError):
        return d


def main():
    tags = sys.argv[1:] or ['saSet2', 'goodA_400']
    for tag in tags:
        R = rows(tag)
        if not R:
            print('%-14s ⚠ 无 series.csv' % tag)
            continue
        print('=' * 88)
        print('### %s  共 %d 行；盒子棱 %.0f nm、体积 %.0f µm³'
              % (tag, len(R), BOX_NM, BOX_UM3))
        keys = [k for k in ('step', 'Vt', 'n_lath', 'w_lath', 'a_lath',
                            'box_touch', 'box_touch_core', 'f3_pos_dx')
                if k in R[0]]
        print('  列: %s' % keys)
        print()
        print('  %-6s %10s %8s %10s %10s %10s %10s %10s'
              % ('step', 'Vt(µm³)', 'f(%)', 'n_lath', 'w_lath', 'a_lath',
                 '撞壁', '核心撞壁'))
        sel = R[::max(len(R) // 10, 1)]
        if R[-1] not in sel:
            sel = sel + [R[-1]]
        for r in sel:
            vt = g(r, 'Vt')
            print('  %-6s %10.4f %8.3f %10.1f %10.1f %10.1f %10s %10s'
                  % (g(r, 'step'), vt, 100 * vt / BOX_UM3,
                     g(r, 'n_lath') * 1e9, g(r, 'w_lath') * 1e9,
                     g(r, 'a_lath') * 1e9,
                     r.get('box_touch', '?'), r.get('box_touch_core', '?')))
        # 汇总
        bt = [r.get('box_touch') for r in R]
        bc = [r.get('box_touch_core') for r in R]
        print()
        print('  **撞壁统计**：`box_touch=1` 的行数 = %d / %d；'
              '`box_touch_core=1` 的行数 = %d / %d'
              % (sum(1 for x in bt if str(x) in ('1', 'True')),
                 len(bt),
                 sum(1 for x in bc if str(x) in ('1', 'True')), len(bc)))
        an = np.array([g(r, 'a_lath') * 1e9 for r in R if np.isfinite(g(r, 'a_lath'))])
        nn = np.array([g(r, 'n_lath') * 1e9 for r in R if np.isfinite(g(r, 'n_lath'))])
        wn = np.array([g(r, 'w_lath') * 1e9 for r in R if np.isfinite(g(r, 'w_lath'))])
        if an.size:
            print('  `a_lath`（最长方向）范围 = %.0f … %.0f nm ⇒ 占盒棱 %.0f%%'
                  % (an.min(), an.max(), 100 * an.max() / BOX_NM))
        if nn.size:
            print('  `n_lath`（沿 n*，即"厚度"方向）范围 = %.0f … %.0f nm'
                  % (nn.min(), nn.max()))
        if wn.size:
            print('  `w_lath` 范围 = %.0f … %.0f nm' % (wn.min(), wn.max()))
        vtl = g(R[-1], 'Vt')
        print('  末态 `Vt` = %.4f µm³ ⇒ 占盒子 **%.2f%%**' % (vtl, 100 * vtl / BOX_UM3))


if __name__ == '__main__':
    sys.exit(main())
