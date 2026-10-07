#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r86_r77_verdict.py —— **条件 ③ 的隔离判决**（判据已在 `_r77_iso.sh` 预先写死）。

## 判据（**先写死再看数**，原文见 `_r77_iso.sh` 头部）

| # | 判据 |
|---|---|
| **I-1** | 隔离有效性：单块臂 `nblk_sig == 1`；两块臂 `nblk_sig == 2` |
| **I-2** | **无影响**：块 0 的 `blk_span_nm`/`blk_alen_nm`/`blk_wlen_nm` 两臂逐步一致（< 1% 或 < 1Δx） |
| **I-3** | **有影响**：任一时间点差异 > 2% ⇒ 记录**首次偏离的步数** |
| **I-4** | 归因：`Δ(el=1)` 与 `Δ(el=0)` 的对比 |

## ⚠ 两个必须处理的口径陷阱

1. **块的排序是"体积降序"，不是"场号序"**
   （`_bk_measure.blocks()`：`sig.sort(key=lambda t: -t[1])`）
   ⇒ 两块臂的 `blk_span_nm` **第 0 个元素**可能是 V3 块，也可能不是。
   **必须按 `blk_vars` 选出变体 1 的那一块**再比（实测 R75：保面臂末态 `blk_vars='3/1'`，
   两臂顺序**是反的** —— 直接比第 0 个元素会得到"差异巨大"的**假结论**）。
2. **`blk_span_nm` 是"沿该块自己的 n\* 的跨度"**（不是盒轴）⇒ 与单块臂同口径 ✅。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')

TOL_ABS_DX = 1.0        # 1Δx
TOL_REL = 0.01          # 1%
FLAG_REL = 0.02         # 2% ⇒ 判"有影响"


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as f:
        rows = list(csv.DictReader(f))
    return rows


def nth(s, i):
    """`'3/3'` -> 第 i 个；越界 ⇒ None。"""
    t = [x for x in str(s or '').split('/') if x.strip()]
    try:
        return float(t[i])
    except (IndexError, ValueError):
        return None


def pick_var1(row, col):
    """按 `blk_vars` 选出**变体 1** 那一块的 `col`；找不到 ⇒ None。"""
    vs = [x for x in str(row.get('blk_vars', '') or '').split('/') if x.strip()]
    try:
        i = [int(float(v)) for v in vs].index(1)
    except ValueError:
        return None
    return nth(row.get(col, ''), i)


def series_of(rows, col):
    out = {}
    for r in rows:
        try:
            k = int(float(r['step']))
        except (KeyError, ValueError):
            continue
        v = pick_var1(r, col)
        if v is not None and np.isfinite(v):
            out[k] = v
    return out


def compare(lab_a, a, lab_b, b, dx_nm):
    print()
    print('=' * 104)
    print('### %s  vs  %s   （只比**变体 1 那个块**的几何）' % (lab_a, lab_b))
    print('=' * 104)
    verdict = {}
    for col in ('blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm'):
        sa, sb = series_of(a, col), series_of(b, col)
        ks = sorted(set(sa) & set(sb))
        if not ks:
            print('  %-14s （无共同步）' % col)
            continue
        rel, absd = [], []
        first_flag = None
        for k in ks:
            d = sa[k] - sb[k]
            m = max(abs(sa[k]), abs(sb[k]), 1e-9)
            rel.append(abs(d) / m)
            absd.append(abs(d) / dx_nm)
            if first_flag is None and (abs(d) / m > FLAG_REL
                                       and abs(d) / dx_nm > TOL_ABS_DX):
                first_flag = k
        print('  %-14s  末态 %s=%.0f  %s=%.0f  Δ=%+.1f nm（%+.2f%%）'
              '  最大|Δ|/Δx=%.2f  最大相对差=%.2f%%'
              % (col, lab_a, sa[ks[-1]], lab_b, sb[ks[-1]],
                 sa[ks[-1]] - sb[ks[-1]],
                 100 * (sa[ks[-1]] / max(sb[ks[-1]], 1e-9) - 1) if sb[ks[-1]] else float('nan'),
                 max(absd), 100 * max(rel)))
        print('              首次"有影响"步号（相对 >2%% 且 >1Δx）：%s'
              % ('**%d**' % first_flag if first_flag is not None else '无（全程一致）'))
        verdict[col] = first_flag
    return verdict


def main():
    need = ['dry_mo1fp10', 'dry_mb2fp10', 'dry_mo2el0', 'dry_mo1el0']
    data = {}
    for t in need:
        r = load(t)
        data[t] = r
        print('  %-14s %s' % (t, ('%d 行' % len(r)) if r else '**缺**'))
    if not all(data.values()):
        print('\n⚠ 臂未跑完，稍后再来')
        return 2

    # ---- I-1 隔离有效性 ----
    print()
    print('=' * 104)
    print('### I-1 隔离有效性（量具自证）')
    print('=' * 104)
    ok1 = True
    for t, want in (('dry_mo1fp10', 1), ('dry_mb2fp10', 2),
                    ('dry_mo1el0', 1), ('dry_mo2el0', 2)):
        nb = data[t][-1].get('nblk_sig', '')
        ok = (str(nb) == str(want))
        ok1 &= ok
        print('  %-14s nblk_sig=%-4s 期望 %d  ⇒ %s' % (t, nb, want, 'PASS' if ok else '**FAIL**'))
    print('  ⇒ **%s**' % ('PASS' if ok1 else 'FAIL'))

    dx = 62.5
    va = compare('mo1fp10(单块)', data['dry_mo1fp10'],
                 'mb2fp10(两块)', data['dry_mb2fp10'], dx)
    vb = compare('mo1el0(单块,el=0)', data['dry_mo1el0'],
                 'mo2el0(两块,el=0)', data['dry_mo2el0'], dx)

    # ---- I-4 归因 ----
    print()
    print('=' * 104)
    print('### I-4 机制归因')
    print('=' * 104)
    for col in ('blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm'):
        fa, fb = va.get(col), vb.get(col)
        print('  %-14s el=1 首次偏离步=%-6s   el=0 首次偏离步=%-6s  ⇒ %s'
              % (col, fa if fa is not None else '无',
                 fb if fb is not None else '无',
                 ('**耦合随弹性消失 ⇒ 是弹性的**' if (fa is not None and fb is None)
                  else ('两者都无 ⇒ 无影响' if (fa is None and fb is None)
                        else ('两者都有 ⇒ 耦合不只是弹性的' if (fa is not None and fb is not None)
                              else 'el=1 无偏离而 el=0 有 ⇒ 反常，需查')))))
    print()
    print('  ⇒ 另注意：`el=0` 会**改变块本身的演化**（弹性驱动力是总驱动力的一部分）')
    print('     ⇒ 该对比只在"两块 vs 单块"的**差**上做归因，**不**跨 el 档比绝对值。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
