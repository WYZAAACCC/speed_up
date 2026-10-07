#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r113_contact.py —— **接触到底从哪一步开始？**（决定 §95 的说法对不对）

## 为什么必须查

`§95` 写的是：「**首次偏离在 step 240**，而两块初始相距 2.5 µm、`t=0` 异变体接触面 = 0
⇒ 偏离发生时两块**还没有接触** ⇒ 耦合是**穿过母相**传递的」。

**这句话有一个我没有验证的环节**：`nf2(t=0) = 0` **不等于** `nf2(240) = 0`。
R75 的日志里 step 240 明明写着 `nf2 = 13`（**已经接触了**）。
⇒ 我把"起点分离"当成了"偏离时仍分离"。**必须查 `nf2` 第一次 > 0 的步号。**

## 判据

* `nf2` 首次 > 0 的步号 `s_c`；
* `_r112` 的"未接触窗口"是 `nf2 == 0` 的步 —— 它在 `s_c` 处结束；
* 块 0 几何的首次偏离步 `s_d`；
* **若 `s_d > s_c`** ⇒ 偏离**发生在接触之后** ⇒ `§95` 的"穿过母相"说法**不成立**，
  差异可以用**几何碰撞**解释（那就不是"耦合"，是"撞上了"）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


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
    rows = list(csv.DictReader(open(p)))
    out = {}
    for r in rows:
        try:
            st = int(float(r['step']))
        except (KeyError, ValueError):
            continue
        out[st] = dict(
            nf2=float(r.get('nf2', 'nan') or 'nan'),
            span=pick_var1(r, 'blk_span_nm'),
            alen=pick_var1(r, 'blk_alen_nm'),
            wlen=pick_var1(r, 'blk_wlen_nm'),
            V0=float(r.get('V0', 'nan') or 'nan'),
            Vt=float(r.get('Vt', 'nan') or 'nan'))
    return out


def main():
    print('=' * 104)
    print('_r113 —— 接触起始步 vs 几何偏离起始步')
    print('=' * 104)
    arms = ['dry_mo1fp10', 'dry_mb2fp10']
    D = {}
    for t in arms:
        if not os.path.exists(os.path.join(MB, t, 'series.csv')):
            print('  %-14s （无数据）' % t)
            continue
        D[t] = load(t)
    if len(D) < 2:
        return 1
    a, b = D['dry_mo1fp10'], D['dry_mb2fp10']
    ks = sorted(set(a) & set(b))
    # 接触起始
    for t, d in (('dry_mo1fp10', a), ('dry_mb2fp10', b)):
        ks2 = sorted(d)
        first = next((k for k in ks2 if d[k]['nf2'] > 0), None)
        print('  %-14s `nf2` 首次 > 0 的步 = **%s**' % (t, first))
    sc = next((k for k in sorted(b) if b[k]['nf2'] > 0), None)
    print()
    print('  两块臂的接触起始步 `s_c` = **%s**' % sc)
    print()
    print('  %-7s %-10s %-12s %-12s %-11s %-11s %-11s'
          % ('step', 'nf2(两块)', 'span 单块', 'span 两块', 'Δspan', 'Δalen', 'Δwlen'))
    sd = None
    for k in ks:
        if k > (sc or 0) + 260:
            break
        ds = a[k]['span'] - b[k]['span']
        da = a[k]['alen'] - b[k]['alen']
        dw = a[k]['wlen'] - b[k]['wlen']
        mark = ''
        if sd is None and (abs(ds) > 0.02 * max(abs(b[k]['span']), 1) and abs(ds) > 62.5):
            sd = k
            mark = '  ← **首次偏离（>2% 且 >1Δx）**'
        if (sc is not None and k == sc) or mark or k % 60 == 0:
            print('  %-7d %-10.0f %-12.1f %-12.1f %+-11.1f %+-11.1f %+-11.1f%s'
                  % (k, b[k]['nf2'], a[k]['span'], b[k]['span'], ds, da, dw, mark))
    print()
    print('  ⇒ 几何首次偏离步 `s_d` = **%s**；接触起始步 `s_c` = **%s**' % (sd, sc))
    if sd is None:
        print('     ⚠ 没找到偏离 ⇒ 两臂全程一致')
    elif sc is not None and sd > sc:
        print('     ⚠⚠ **`s_d > s_c`（偏离在接触之后）** ⇒ `§95` 的"穿过母相耦合"')
        print('         **说法不成立** —— 差异可以用**几何碰撞**解释。')
    elif sc is not None and sd <= sc:
        print('     ✅ **`s_d ≤ s_c`（偏离不晚于接触）** ⇒ `§95` 的"穿过母相"')
        print('         说法在**这一步号口径下**成立（⚠ 仍受 step 分辨率限制：')
        print('         `--every 20` ⇒ `s_c` 与 `s_d` 都可能被量化到 ±20 步）')
    print()
    print('  ---- `V0` / `Vt` 原始值（`V0` 在 `_r112` 里读成 0.0000，核实一下）----')
    for t, d in (('dry_mo1fp10', a), ('dry_mb2fp10', b)):
        ks2 = sorted(d)
        print('  %-14s %s' % (t, '  '.join('step%d:V0=%.6g,Vt=%.4g'
                                           % (k, d[k]['V0'], d[k]['Vt'])
                                           for k in ks2[::max(1, len(ks2) // 4)])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
