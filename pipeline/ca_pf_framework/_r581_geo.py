#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_geo.py --- ★★★★★★ **C2 的量**：板条三维几何（`n_lath`/`w_lath`/`a_lath`）+ 长宽比

## goal 判据 (5)-② 逐字
> 「单根板条形核与生长正确：**三维几何量、长宽比落在物理区间**
>   （**有文献/解析对照，不许只报数**）」

## 口径（先把"物理区间"写下来，再看数）
| 量 | 物理预期（Ti-64 的 α′ 板条，**待与文献核对**） | 出处 |
|---|---|---|
| **宽 `a_lath`** | **~0.1–0.5 µm** | **【待核】** |
| **厚 `n_lath`** | **~0.05–0.3 µm**（**板条厚度**） | **【待核】** |
| **长 `w_lath`** | **~1–10 µm**（**可横穿晶粒**） | **【待核】** |
| **长/厚** | **≫10**（**板条形状**） | **【待核】** |
| **种子尺寸（CLI 给的）** | **L=1000 / W=500 / T=510 nm** | **`--plate-L/-W/-T`** |

⚠ **本脚本先只**报数**（**并与种子尺寸、以及"N8：孤立单根没有有限厚度"那条对**）**
—— **"物理区间"的文献值必须单独核**（**不许拿本脚本的输出当"文献对照"**）。
"""
import csv
import os
import sys

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
TAGS = sys.argv[2:] or ['BK6', 'BN1']
COLS = ['n_lath', 'w_lath', 'a_lath']


def main():
    for tag in TAGS:
        p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('  %-5s 无数据' % tag)
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        k = list(rows[0].keys())[0]
        print('=' * 92)
        print('臂 %s：板条几何（%d 行）' % (tag, len(rows)))
        print('=' * 92)
        print('  %-6s %-11s %-11s %-11s %-9s %-9s' %
              ('step', 'n_lath(nm)', 'w_lath(nm)', 'a_lath(nm)', 'w/n', 'a/n'))
        vals = {c: [] for c in COLS}
        for r in rows:
            out = []
            for c in COLS:
                v = (r.get(c, '') or '').strip()
                try:
                    f = float(v)
                except Exception:
                    f = float('nan')
                out.append(f)
                if f == f and f > 0:
                    vals[c].append(f)
            n, w, a = out
            r1 = (w / n) if (n == n and n > 0 and w == w) else float('nan')
            r2 = (a / n) if (n == n and n > 0 and a == a) else float('nan')
            print('  %-6s %-11.6g %-11.6g %-11.6g %-9.4g %-9.4g'
                  % (r[k], n, w, a, r1, r2))
        print()
        for c in COLS:
            arr = np.array(vals[c], float)
            if arr.size:
                print('  %-9s 非零 %3d 行；中位 %-10.6g 最小 %-10.6g 最大 %-10.6g'
                      % (c, arr.size, np.median(arr), arr.min(), arr.max()))
        print()
    print('=' * 92)
    print('★ 判读：')
    print(' · **`n_lath` 是中位厚度、`w_lath`/`a_lath` 是另两个方向**（口径见 `_bk_exp.py` 的 `_med`）')
    print(' · **要与**物理区间**对** —— 而物理区间**必须另找文献/解析**，不许拿本表当选它')
    print(' · **`w/n`（长/厚）** 是板条形状的判据量')
    print('=' * 92)


if __name__ == '__main__':
    main()
