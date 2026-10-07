#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r184_inert_cmp.py —— **W-1 闭环**：新代码 + λ=0 是否与归档**逐位相同**？

## 预登记判据（原文在 `_r179_inert.sh` 头部，**读数据前写死**）

* **I-1** 新跑 `dry_saSet2INERT`（新代码 / λ=0 / 120 步）与归档 `dry_saSet2`
  在**共同步**（0,20,…,120）上，**每一列都逐位相同**（`repr(float)` 完全一致）
  ⇒ 代码改动对 λ=0 路径**完全惰性** ⇒ R165 是合法单变量对照。
* **I-2** 若有差：**先看量级**
  * 相对差 ≤ `1e-12` ⇒ 只是**求和次序**（`§92` 的 T3 gather 那类），**可接受**；
  * 相对差 O(1) ⇒ **真混杂 ⇒ R165 的判决作废**，必须重跑对照。
* **I-3** 时间步与几何必须一致（`step` 列一致、行数足够）—— 否则比的是两件事。

## 为什么要比"每一列"而不是只比 Vt

`§116` 的教训：**55/97 列会变、21 列不变** ⇒ 只盯 `Vt` 会漏掉大部分影响。
反过来，**惰性也必须逐列证**，不能只证 `Vt` 没变。
"""
from __future__ import annotations

import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
NEW, OLD = 'saSet2INERT', 'saSet2'

# 这些列是**运行期元数据**（时间戳/耗时），不参与逐位判据
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None, p
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f)), p


def as_f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    print('=' * 108)
    print('_r184 —— W-1 惰性闭环：新代码+λ=0（`%s`）vs 归档（`%s`）' % (NEW, OLD))
    print('=' * 108)
    rn, pn = rows(NEW)
    ro, po = rows(OLD)
    if rn is None:
        print('  ❌ 新跑的结果不存在：%s' % pn)
        return 2
    if ro is None:
        print('  ❌ 归档不存在：%s' % po)
        return 2
    print('  新跑：%s  （%d 行）' % (os.path.basename(pn), len(rn)))
    print('  归档：%s  （%d 行）' % (os.path.basename(po), len(ro)))
    sn = {r.get('step'): r for r in rn}
    so = {r.get('step'): r for r in ro}
    common = sorted(set(sn) & set(so), key=lambda x: int(x) if x and x.isdigit() else -1)
    print('  共同步（%d 个）：%s' % (len(common), common))
    if len(common) < 2:
        print('  ❌ **I-3 失败**：共同步不足 2 个 ⇒ 没法比')
        return 2
    cols = [c for c in rn[0] if c in ro[0] and c not in SKIP]
    print('  可比列：%d 个' % len(cols))
    print()
    exact = 0
    maxrel = 0.0
    worst = None
    nonnum = []
    diffs = []
    for c in cols:
        n_ex = 0
        worst_c = (0.0, None)
        for s in common:
            a, b = sn[s].get(c), so[s].get(c)
            fa, fb = as_f(a), as_f(b)
            if fa is None or fb is None:
                if (a or '') != (b or ''):
                    nonnum.append((c, s, a, b))
                else:
                    n_ex += 1
                continue
            if repr(fa) == repr(fb):
                n_ex += 1
                continue
            den = max(abs(fa), abs(fb), 1e-300)
            rel = abs(fa - fb) / den
            if rel > worst_c[0]:
                worst_c = (rel, 'step=%s 新=%r 旧=%r' % (s, fa, fb))
            if rel > maxrel:
                maxrel, worst = rel, (c, s, fa, fb)
        if n_ex == len(common):
            exact += 1
        else:
            diffs.append((c, n_ex, len(common), worst_c))
    print('  ## **I-1**：逐位相同的列 = **%d / %d**' % (exact, len(cols)))
    if diffs:
        print()
        print('  ## 有差异的列（%d 个）' % len(diffs))
        print('     %-26s %-12s %s' % ('列', '逐位相同', '最大相对差 / 例'))
        for (c, n_ex, tot, wc) in sorted(diffs, key=lambda d: -d[3][0]):
            print('     %-26s %-12s %.3e  %s'
                  % (c, '%d/%d' % (n_ex, tot), wc[0], wc[1]))
    if nonnum:
        print()
        print('  ## 非数值列的不一致（%d 处，前 5）' % len(nonnum))
        for t in nonnum[:5]:
            print('     %s step=%s 新=%r 旧=%r' % t)
    print()
    print('=' * 108)
    print('  ## 判定')
    print('=' * 108)
    print('     最大相对差（全表）= **%.3e**' % maxrel)
    if worst:
        print('     出处：列 `%s`，step=%s，新=%r 旧=%r' % worst)
    if not diffs and not nonnum:
        print('     ⇒ ✅ **I-1 通过**：**%d 列全部逐位相同**'
              ' ⇒ 新代码对 λ=0 路径**完全惰性**' % len(cols))
        print('     ⇒ **R165 是合法单变量对照**，可以读 `_r171` 的判决。')
        return 0
    if maxrel <= 1e-12:
        print('     ⇒ ⚠ **I-2 可接受**：有差异但最大相对差 %.3e ≤ 1e-12'
              ' ⇒ 属**求和次序**（`§92` T3 gather 那类），非物理差异。' % maxrel)
        print('     ⇒ R165 的判决**仍然可读**，但须记账"非逐位"。')
        return 0
    print('     ⇒ ❌ **I-2 真混杂**：最大相对差 %.3e 远超 1e-12'
          ' ⇒ 代码改动**改变了 λ=0 的物理** ⇒ **R165 的判决作废**，须重跑对照。'
          % maxrel)
    return 1


if __name__ == '__main__':
    sys.exit(main())
