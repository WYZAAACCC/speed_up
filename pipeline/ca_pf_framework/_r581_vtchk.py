#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_vtchk.py --- 查我自己的 `Vt` 读数为什么是 0.0000（同一个症状出现两次了）。

## 症状
`_r581_cmpf3.py` 与 `_r581_mtest.sh` 都读 `series.csv` 的 `Vt` 列 ⇒ 都得到 **0.0000**，
而 R22/R23 从**快照**数出的非母相胞数明明是**上千**。
**⇒ 两次同一症状 ⇒ 先怀疑量具（P21/P13）。**

## 查三件事（不猜）
1. `series.csv` 的**表头**里到底有没有 `Vt`？列名叫什么？
2. `Vt` 列在**这一行**的**原始文本**是多少？
3. `Vt` 的单位/口径是什么（对照快照数出来的胞数）？
"""
import os
import sys

import numpy as np

ROOT = '_exp/_bk_p2'


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    print('=' * 88)
    print('查 `Vt` 读数：%s' % p)
    print('=' * 88)
    with open(p) as fh:
        head = fh.readline().strip()
    cols = head.split(',')
    print('  列数 = %d' % len(cols))
    print('  含 "Vt" 的列名：%s' % [c for c in cols if 'vt' in c.lower()])
    print('  前 12 个列名：%s' % cols[:12])
    print()
    # 原始文本行
    with open(p) as fh:
        fh.readline()
        rows = fh.readlines()
    st = [r.split(',')[0] for r in rows]
    try:
        i = int(np.argmin([abs(int(x) - step) for x in st if x.strip()]))
    except Exception:
        i = min(step, len(rows) - 1)
    print('  第 %d 行（step=%s）的**原始前 12 个字段**：' % (i + 1, st[i]))
    print('    %s' % rows[i].split(',')[:12])
    if 'Vt' in cols:
        j = cols.index('Vt')
        print('  `Vt` 是第 %d 列（0-based）⇒ 原始值 = %r' % (j, rows[i].split(',')[j]))
    # 用 genfromtxt 读一遍对照
    dd = np.genfromtxt(p, delimiter=',', names=True)
    print()
    print('  `np.genfromtxt` 读到的字段名（前 12）：%s' % list(dd.dtype.names)[:12])
    if 'Vt' in dd.dtype.names:
        v = np.atleast_1d(dd['Vt'])
        print('  `Vt` 数组：len=%d  前 5 = %s  非零个数 = %d'
              % (len(v), v[:5], int((v != 0).sum())))
    else:
        print('  ⚠ `Vt` **不在** genfromtxt 的字段里 ⇒ **列名对不上**（可能被重命名/去重）')
    # 与快照对账
    sp = os.path.join(ROOT, 'dry_' + tag, 'snap_%05d.npz' % step)
    if os.path.exists(sp):
        z = np.load(sp)
        reg = z['region']
        n = int((reg > 0).sum())
        L = float(z['L']); dx = L / reg.shape[0]
        print()
        print('  ── 从快照独立算（**自洽检查**）──')
        print('     `region>0` 胞数 = %d' % n)
        print('     Δx = %.4g m ⇒ 体积 = %.6f µm³' % (dx, n * dx ** 3 * 1e18))
    print('=' * 88)


if __name__ == '__main__':
    main()
