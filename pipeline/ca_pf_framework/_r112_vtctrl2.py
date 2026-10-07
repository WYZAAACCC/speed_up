#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r112_vtctrl2.py —— `_r111` 的**更正版**：用**同一步号**、并**切出"未接触"窗口**。

## `_r111` 错在哪（**又一个"轴不是同一个量"**）

我拿 `Vt` 当横轴做"同 Vt 比较"。但：
* 单块臂：`Vt` ≈ **块 0 自己的体积**；
* 两块臂：`Vt` = **块 0 + 块 1**（播种时就约 2 倍）。
⇒ "同一个 `Vt`"在两臂里对应**块 0 只有一半大** ⇒ 表里出现"两块 span 随 Vt **下降**"
（1901→639）这种**非物理**的读法 —— 那是插值在两臂各自的**不同历史段**之间穿行。
⇒ **`_r111` 的分辨结论（+1704 nm / 60.9%）作废。**

## 正确做法

1. **横轴用 `step`**（两臂同步推进的**同一个钟**）；
2. **切出"两块未接触"的窗口**（`nf2 == 0`）—— 那一段只有**穿过母相**的耦合，
   没有几何撞上 ⇒ 这是"**相互影响**"最干净的证据窗口；
3. 在窗口内比"变体 1 那个块"的 `blk_span_nm` / `blk_alen_nm` / `blk_wlen_nm`；
4. 顺带报 β 分数 `V0/(N·Δx)³`（母相消耗）—— §95 第五节列的"第二通道"假设要用它。

⚠ **块按 `blk_vars` 选，不按位置**（`blocks()` 按**体积降序**排，两臂顺序可能是反的）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = [('dry_mo1fp10', '单块 V1×3'),
        ('dry_mb2fp10', '两块 V1×3+V3×3')]
COLS = ['blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm']


def pick_var1(row, col):
    vs = [x for x in str(row.get('blk_vars', '') or '').split('/') if x.strip()]
    t = [x for x in str(row.get(col, '') or '').split('/') if x.strip()]
    try:
        i = [int(float(v)) for v in vs].index(1)
        return float(t[i])
    except (ValueError, IndexError):
        return float('nan')


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {c: {} for c in COLS}
    out['nf2'], out['V0'], out['Vt'] = {}, {}, {}
    for r in rows:
        try:
            st = int(float(r['step']))
        except (KeyError, ValueError):
            continue
        for c in COLS:
            out[c][st] = pick_var1(r, c)
        for c in ('nf2', 'V0', 'Vt'):
            try:
                out[c][st] = float(r.get(c, 'nan'))
            except (TypeError, ValueError):
                out[c][st] = float('nan')
    return out


def main():
    print('=' * 108)
    print('_r112 —— 同 step 比较 + "未接触"窗口（`_r111` 的更正版）')
    print('=' * 108)
    D = {}
    for t, lab in ARMS:
        d = load(t)
        if d is None:
            print('  %-14s （无数据）' % t)
            continue
        D[t] = d
        ks = sorted(d['nf2'])
        nz = [k for k in ks if d['nf2'][k] == 0]
        print('  %-14s %-18s step %d→%d；**`nf2 == 0` 的步：%s**'
              % (t, lab, ks[0], ks[-1],
                 ('0…%d（%d 个采样点）' % (max(nz), len(nz))) if nz else '无'))
    if len(D) < 2:
        return 1
    a, b = D['dry_mo1fp10'], D['dry_mb2fp10']
    ks = sorted(set(a['nf2']) & set(b['nf2']))
    clean = [k for k in ks if a['nf2'][k] == 0 and b['nf2'][k] == 0]
    print()
    print('  **两臂 `nf2` 都为 0 的步（"未接触"窗口）：%s**'
          % (('%d…%d，共 %d 点' % (min(clean), max(clean), len(clean)))
             if clean else '**无**'))
    for c in COLS:
        print()
        print('  ### %s' % c)
        if not clean:
            print('     ⚠ 没有共同未接触步 ⇒ 本量无法在"纯体耦合"窗口里比')
            continue
        print('     %-8s %-13s %-13s %-11s %-9s %s'
              % ('step', '单块', '两块', 'Δ(nm)', 'Δ/Δx', 'Δ%'))
        ds = []
        for k in clean[::max(1, len(clean) // 8)] + [clean[-1]]:
            sa, sb = a[c][k], b[c][k]
            d = sa - sb
            ds.append(d)
            print('     %-8d %-13.1f %-13.1f %+-11.1f %+-9.2f %+.2f%%'
                  % (k, sa, sb, d, d / 62.5, 100 * d / max(abs(sb), 1e-9)))
        ds = np.array([a[c][k] - b[c][k] for k in clean])
        print('     ⇒ 窗口内 Δ = 单块 − 两块：**mean %+.1f nm、min %+.1f、max %+.1f**'
              % (ds.mean(), ds.min(), ds.max()))
        if np.all(ds > 0) or np.all(ds < 0):
            print('        **符号全程一致** ⇒ 未接触期间差异已存在（穿过母相的耦合）✅')
        else:
            print('        ⚠ 符号不一致 ⇒ 未接触窗口内差异**不稳定**')
    # ---- β 分数 ----
    print()
    print('  ### β（母相）分数 `V0 / 盒体积`（§95 第五节的"第二通道"要用的量）')
    for t, lab in ARMS:
        if t not in D:
            continue
        d = D[t]
        ks = sorted(d['V0'])
        print('     %-14s %s' % (t, '  '.join(
            'step%d:%.4f' % (k, d['V0'][k]) for k in ks[::max(1, len(ks) // 5)])))
    print()
    print('     ⚠ `V0` 是**体积分数**（无量纲，`measure_state` 里已按盒体积归一）')
    print('        ⇒ 可跨臂比；但它只说明"母相消耗程度"，**不**直接证明是耦合通道。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
