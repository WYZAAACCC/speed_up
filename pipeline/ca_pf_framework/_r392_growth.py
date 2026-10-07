#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r392_growth.py —— 末态到底"长完了"没有？长宽比是多少？

## 三个要回答的问题
1. **长宽比**：`a_lath`（长）/`w_lath`（宽）/`n_lath`（厚）之比，随时间怎么变？
2. **长完了吗**：`Vt(t)` 与各尺度是否**平台化**（一阶导 → 0）？
3. **末态是不是"已停止"的块**：`box_touch`（已知恒 0）、`Vt` 仍单调增？

⚠ 单位：`series.csv` 是 **SI**（`Vt` 用 m³、长度用 m）。上一版 `_r391` 忘了换算
⇒ `Vt` 打成 0.0000（第 44 个自查错误）。本脚本按 SI 读、打印时换算。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
BOX_UM3 = 343.0


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def col(R, k):
    out = []
    for r in R:
        try:
            v = r.get(k, '')
            out.append(float(v) if v not in ('', None) else np.nan)
        except (TypeError, ValueError):
            out.append(np.nan)
    return np.asarray(out, float)


def main():
    for tag in (sys.argv[1:] or ['saSet2']):
        R = rows(tag)
        if not R:
            print('%-14s ⚠ 无 series.csv' % tag)
            continue
        st = col(R, 'step')
        vt = col(R, 'Vt') * 1e18                 # m³ → µm³
        a = col(R, 'a_lath') * 1e9               # m → nm
        w = col(R, 'w_lath') * 1e9
        n = col(R, 'n_lath') * 1e9
        print('=' * 92)
        print('### %s' % tag)
        print('  %-6s %10s %8s %9s %9s %9s %8s %8s %8s'
              % ('step', 'Vt(µm³)', 'f(%)', 'a(nm)', 'w(nm)', 'n(nm)',
                 'a/n', 'a/w', 'w/n'))
        for i in range(0, len(R), max(len(R) // 10, 1)):
            _p(st[i], vt[i], a[i], w[i], n[i])
        if (len(R) - 1) % max(len(R) // 10, 1):
            i = len(R) - 1
            _p(st[i], vt[i], a[i], w[i], n[i])
        # 增长速率：分段
        print()
        print('  ## 末段增长率（是否平台化？）')
        for lo, hi, lab in ((0.0, 0.25, '前 1/4'),
                            (0.25, 0.5, '1/4–1/2'),
                            (0.5, 0.75, '1/2–3/4'),
                            (0.75, 1.0, '后 1/4')):
            i0 = int(lo * (len(R) - 1))
            i1 = int(hi * (len(R) - 1))
            if i1 <= i0:
                continue
            dvt = (vt[i1] - vt[i0]) / (st[i1] - st[i0])
            da = (a[i1] - a[i0]) / (st[i1] - st[i0])
            print('    %-8s  dVt/dstep = %+9.6f µm³/步   da/dstep = %+7.3f nm/步'
                  % (lab, dvt, da))
        print()
        print('  ## 判据')
        last = (vt[-1] - vt[-2]) / max(st[-1] - st[-2], 1e-30)
        print('    末步 dVt/dstep = **%+.6f µm³/步**（%s）'
              % (last, '已平台化' if abs(last) < 1e-4 else '**仍在增长**'))
        print('    末态 f = **%.3f%%**；`a/n` = **%.2f**、`a/w` = **%.2f**'
              % (100 * vt[-1] / BOX_UM3, a[-1] / n[-1], a[-1] / w[-1]))


def _p(s, v, a, w, n):
    print('  %-6.0f %10.4f %8.3f %9.0f %9.0f %9.0f %8.2f %8.2f %8.2f'
          % (s, v, 100 * v / BOX_UM3, a, w, n, a / n, a / w, w / n))


if __name__ == '__main__':
    sys.exit(main())
