#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_same_step.py --- ★★★★ **同 step 的逐列对照**（S4/N13 的判决）。

## 为什么要这个
`_r581_athstep.py` 只比"形核事件"；而**真正的物理量**（`Vt`/`nslab_n`/`nf3_col`/`F3面`/`nf2`）
在 `series.csv` 里逐行都有 ⇒ **必须在**同 step**上逐列比**，才是公平判决。

## ⚠ 口径（P30 的雷）
`series.csv` 的 **`Vt` 是 SI（m³）** ⇒ 本量具**统一乘 1e18** 报 µm³。
"""
import os
import sys

import numpy as np

ROOT = '_exp/_bk_p2'
# 只比这些列（其余列口径各异，先不混）
KEYS = ['Vt', 'nslab_n', 'nf3_col', 'nf2', 'M', 'nreg_used', 'nc_max', 'nc_sig',
        'box_touch', 'finite']


def load(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        cols = fh.readline().strip().split(',')
    dd = np.genfromtxt(p, delimiter=',', names=True)
    return cols, dd


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b5ov', 'p2_b5ps']
    print('=' * 104)
    print('同 step 逐列对照（S4/N13 判决；`Vt` 已 ×1e18 报 µm³ —— P30）')
    print('=' * 104)
    data = {}
    for t in tags:
        r = load(t)
        if r is None:
            print('  %-9s ❌ 无 series.csv' % t); continue
        cols, dd = r
        st = np.atleast_1d(dd['step']).astype(int)
        data[t] = (cols, dd, st)
        print('  %-9s 行=%-4d step %d → %d' % (t, len(st), st[0], st[-1]))
    if not data:
        return
    # 共同 step
    common = None
    for t, (_, _, st) in data.items():
        s = set(int(x) for x in st)
        common = s if common is None else (common & s)
    common = sorted(common or [])
    print()
    print('  共同 step：%d 个（%s … %s）' % (len(common), common[0] if common else '—',
                                            common[-1] if common else '—'))
    if not common:
        print('  ⇒ **没有共同 step ⇒ 不可比**（如实登记）'); return
    # 逐列逐 step
    for k in KEYS:
        if not all(k in d[1].dtype.names for d in data.values()):
            continue
        print()
        print('  ── `%s`%s ──' % (k, '（已 ×1e18 ⇒ µm³）' if k == 'Vt' else ''))
        hdr = '    %-7s' % 'step' + ''.join('%14s' % t for t in data) + '   末值对照'
        print(hdr)
        for s in common:
            row = '    %-7d' % s
            vals = {}
            for t, (_, dd, st) in data.items():
                i = int(np.argmin(np.abs(st - s)))
                v = float(np.atleast_1d(dd[k])[i])
                if k == 'Vt':
                    v *= 1e18
                vals[t] = v
                row += '%14.5g' % v
            # 末值对照（各臂自己最后一行）
            ends = {}
            for t, (_, dd, st) in data.items():
                v = float(np.atleast_1d(dd[k])[-1])
                if k == 'Vt':
                    v *= 1e18
                ends[t] = v
            row += '   ' + ' '.join('%s末=%.5g' % (t.replace('p2_', ''), ends[t])
                                    for t in data)
            print(row)
    print()
    print('=' * 104)
    print('★ 判读（**预先写死**）')
    print('  · **只在共同 step 上比**；末值对照仅供方向参考（各臂 step 不同 ⇒ 不是判决）')
    print('  · 若 `p2_b5ov` 在每个共同 step 上都与 `p2_b5` **逐位相同** ⇒ S4 不动这些量')
    print('  · 若 `p2_b5ps` 在某个 step 上分道 ⇒ N13 动了')
    print('=' * 104)


if __name__ == '__main__':
    main()
