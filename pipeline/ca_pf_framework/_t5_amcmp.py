#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_amcmp.py --- ★★★★★ **按步对齐**对照：ellipse vs exp2（公式是否起作用）+ 叠加

## 为什么（第 28 条 + 第 28b 条）
**比较两个开关，必须（a）**同一末步**、（b）用在后期才有分辨力的量。**
**而两对臂的当前进度**不同**（`t5AB_A` 已到 960、`t5AM_ell` 才 80）
⇒ **不能拿"各自最新"去比** ⇒ **必须按 step 对齐。**

## 两对对照（**预先写死**）
| 对 | 目的 | A 臂 | B 臂 |
|---|---|---|---|
| **①** | **验公式**（`ellipse` 是否起作用）| `t5AB_A`（exp2, elong=0）| `t5AM_ell`（ellipse, elong=0）|
| **②** | **验叠加**（ellipse + eng-elong）| `t5AD_700`（exp2, elong=7）| `t5AM_combo`（ellipse, elong=7）|
**⇒ 只在**两臂都有的公共 step**上比（打印每个公共 step 的两个值 + 差值）。**
"""
import re
import sys

LOG = '_w2_t5_ar_monitor.log'
PAT = re.compile(r'\]\s+(t5\S+)\s+step\s+(\d+)\s+场=(\d+)\s+\*\*长宽比 中位 ([\d.]+).*?'
                 r'\*\*长厚比 中位 ([\d.]+)')

data = {}          # tag -> {step: (n, ar, lt)}
try:
    for line in open(LOG, errors='ignore'):
        m = PAT.search(line)
        if m:
            tag, st, n, ar, lt = m.group(1), int(m.group(2)), int(m.group(3)), \
                                 float(m.group(4)), float(m.group(5))
            data.setdefault(tag, {})[st] = (n, ar, lt)
except FileNotFoundError:
    print('  ⚠ 找不到 %s' % LOG); sys.exit(1)

PAIRS = [('① 验公式：ellipse vs exp2（eng-elong=0）', 't5AB_A', 't5AM_ell'),
         ('② 验叠加：ellipse+7 vs exp2+7', 't5AD_700', 't5AM_combo')]

for title, ta, tb in PAIRS:
    print('=' * 96)
    print('★ %s' % title)
    print('  A = %-11s   B = %-11s' % (ta, tb))
    print('=' * 96)
    da, db = data.get(ta, {}), data.get(tb, {})
    if not da or not db:
        print('  （%s / %s 尚无数据）' % (ta, tb)); print(); continue
    common = sorted(set(da) & set(db))
    if not common:
        print('  ⚠ **没有公共 step**（A 有 %s；B 有 %s）' % (sorted(da)[:6], sorted(db)[:6]))
        print('  ⇒ 须等 B 臂追上 A 的步点'); print(); continue
    print('  %-7s %-22s %-22s %s' % ('step', 'A: 场/长宽比/长厚比', 'B: 场/长宽比/长厚比', 'Δ长宽比'))
    print('  ' + '-' * 88)
    for s in common:
        na, aa, la = da[s]
        nb, ab, lb = db[s]
        d = ab - aa
        flag = '  ← **B 与 A 不同**' if abs(d) > 0.15 else ''
        print('  %-7d %-22s %-22s **%+.2f**%s'
              % (s, '%d / %.2f / %.2f' % (na, aa, la), '%d / %.2f / %.2f' % (nb, ab, lb), d, flag))
    print()
    # 判据
    print('  ── 判据（预先写死）──')
    print('  ① 验公式：若**所有公共 step** 上 |Δ| < 0.15 ⇒ **ellipse 无效果**；')
    print('     若有 step 上 |Δ| ≥ 0.15 ⇒ **有效果**，并报出方向（B 比 A 更扁还是更等轴）；')
    print('  ② 验叠加：同上（B 应 ≥ A；若 ≈ ⇒ 不叠加）。')
    print()
