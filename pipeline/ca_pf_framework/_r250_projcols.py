#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r250_projcols.py —— H-1 检验的**列级明细**：投影把哪些量的差异压掉了？

`_r249` 的结论需要落地：**分叉步数不变（94%）但最大相对差从 0.91 掉到 8.2e-04**。
⇒ 必须看清**是哪些列**、以及**末步**的差异分布，否则"压制 1100 倍"这句话没有内容。
"""
from __future__ import annotations

import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s', 'dt'}


def load(root, tag):
    p = os.path.join(HERE, root, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def col_diff(A, B, last_only=False):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    if last_only:
        common = common[-1:]
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    out = {}
    for c in cols:
        worst = 0.0
        for s in common:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                continue
            if fa != fa and fb != fb:
                continue
            if repr(fa) != repr(fb):
                worst = max(worst, abs(fa - fb) / max(abs(fa), abs(fb), 1e-300))
        out[c] = worst
    return out, common[-1] if common else None


def main():
    print('=' * 108)
    print('_r250 —— 投影效应的列级明细（端点相对差）')
    print('=' * 108)
    A0 = load('_exp/_bk_q17', 'qH'); B0 = load('_exp/_bk_q17', 'qC')
    A1 = load('_exp/_bk_q18', 'qHp'); B1 = load('_exp/_bk_q18', 'qCp')
    d0, s0 = col_diff(A0, B0, last_only=True)
    d1, s1 = col_diff(A1, B1, last_only=True)
    print('  端点步：无投影 step=%s ；有投影 step=%s' % (s0, s1))
    print()
    print('  ## 末步相对差 Top-12（按"无投影"排序）')
    print('     %-22s %-14s %-14s %s' % ('列', '无投影', '有投影', '压制倍数'))
    keys = sorted(d0, key=lambda c: -d0[c])[:12]
    for c in keys:
        r0, r1 = d0[c], d1[c]
        sup = (r0 / r1) if r1 > 0 else float('inf')
        print('     %-22s %-14.3e %-14.3e %s'
              % (c, r0, r1, ('%.0f×' % sup) if sup != float('inf') else '∞（压没了）'))
    n0 = sum(1 for c in d0 if d0[c] > 0)
    n1 = sum(1 for c in d1 if d1[c] > 0)
    print()
    print('  ## 汇总（末步）')
    print('     有差异的列数：无投影 **%d** ；有投影 **%d**' % (n0, n1))
    print('     最大相对差：无投影 **%.3e** ；有投影 **%.3e**'
          % (max(d0.values()), max(d1.values())))
    print()
    print('  ## ★ 关键形态量（形态是否真的被"钉住"）')
    for c in ('f3_area_m2', 'nf3', 'Vt', 'n_lath', 'a_lath', 'w_lath',
              'blk_span_nm', 'f3_pos_m', 'r_selfac'):
        if c in d0:
            print('     %-16s 无投影 %-12.3e 有投影 %-12.3e' % (c, d0[c], d1[c]))
    print()
    print('  ⚠ 记账：端点=末步（step %s），**不是** 400 步长跑的末态。' % s0)
    return 0


if __name__ == '__main__':
    sys.exit(main())
