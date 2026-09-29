#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_gapw.py —— R30：`_r1_exp.gap_w_nm` 的**汇总权重**问题在归档数据上的证据。

`_r1_exp.py:296-307` 把 `Lc/Wc/Tc/align_deg/...` 一律限制在**显著分量**
（≥1% 胞，`_sigc`），而 `:317-320` 的 `gap_w_nm` 用的是**全部分量**（`comps`，
门槛只有 8 胞 ⇒ 含碎屑液滴）。⇒ 「板条间距」在只剩 1 根主板条时仍会报一个数，
那个数实际是"主板条 ↔ 碎屑"的距离。
"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
print('=' * 118)
print('R30：`gap_w_nm`（全部分量）vs `nsig`（显著分量）在归档 `_exp/*/series.csv` 上的对照')
print('=' * 118)
print('%-26s %-7s %-8s %-8s %-8s %-11s %s'
      % ('算例', '总行数', 'nsig<=1行', '仍报gap', 'nc中位', 'gap中位(nm)', '判读'))
print('-' * 118)
for d in sorted(glob.glob(os.path.join(HERE, '_exp', '*', ''))):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p, newline='', encoding='utf-8')))
    if not rows or 'nsig' not in rows[0]:
        continue

    def g(r, k):
        try:
            return float(r.get(k, ''))
        except (TypeError, ValueError):
            return float('nan')
    low = [r for r in rows if g(r, 'nsig') == g(r, 'nsig') and g(r, 'nsig') <= 1]
    still = [r for r in low if g(r, 'gap_w_nm') == g(r, 'gap_w_nm')]
    if not still:
        continue
    ncs = sorted(g(r, 'nc') for r in rows if g(r, 'nc') == g(r, 'nc'))
    gws = sorted(g(r, 'gap_w_nm') for r in still)
    print('%-26s %-7d %-8d %-8d %-8.0f %-11.1f %s'
          % (os.path.relpath(d, HERE), len(rows), len(low), len(still),
             ncs[len(ncs) // 2], gws[len(gws) // 2],
             '⚠ 只有 1 个显著分量时仍报"间距"'))
    print('      例（nsig<=1 且 gap 非空的前 3 行）：'
          + '  '.join('nc=%s nsig=%s gap=%.1fnm' % (r.get('nc'), r.get('nsig'),
                                                    g(r, 'gap_w_nm'))
                      for r in still[:3]))
print('-' * 118)
print('⇒ 记账：`gap_w_nm` 的**权重是"全部 ≥8 胞分量"**，而同一函数里 `Lc/Wc/Tc/align_*`')
print('   的权重是"≥1% 胞的显著分量"。碎屑液滴的个数随构型/时间变 ⇒ 这个"间距"没有稳定含义。')
sys.exit(0)
