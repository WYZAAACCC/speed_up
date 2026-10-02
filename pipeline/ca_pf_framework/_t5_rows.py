#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_rows.py --- ★ 查**哪些行真正带块表**（防止把"最大值所在的行"记错成"末行"）

## 为什么要查（本 goal 第 8 次口径风险）
`_bk_exp.py` 里块表只在 `_pair_now = (it % pair_every == 0)` 时算。
我先后读过 `nf3 max = 1039`（末步 200）与 `nf3 max = 1675`（末步 220/260）——
**若两者来自**同一行**，那 §55 的"step 200→220 增长 +61%"就是**归因错误**。**
"""
import csv
import sys

for t in (sys.argv[1:] or ['t5H3']):
    p = '_exp/_bk_t5/dry_%s/series.csv' % t
    r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    print('=' * 88)
    print('  %s：%d 行' % (t, len(r)))
    print('  %-7s %-13s %-9s %-9s %-9s %-9s %s'
          % ('step', 'Vt', 'nf3', 'nf3_col', 'nblk_sig', 'n_var_sig', 'nslab_n'))
    print('  ' + '-' * 80)
    for x in r:
        def g(k):
            return (x.get(k) or '').strip()
        print('  %-7s %-13s %-9s %-9s %-9s %-9s %s'
              % (x['step'], g('Vt')[:13], g('nf3')[:9] or '（空）',
                 g('nf3_col')[:9] or '（空）', g('nblk_sig')[:9] or '（空）',
                 g('n_var_sig')[:9] or '（空）', g('nslab_n')[:4]))
    pop = [int(x['step']) for x in r if (x.get('nf3') or '').strip()]
    print()
    print('  ★ **带块表的步**（nf3 非空）：%s' % pop)
    print('  ★ 判定：块表只在 %s 的倍数步 ⇒ 我的"step 200→220"说法**%s**'
          % ('lcm(--every, --pair-every)',
             '成立' if (220 in pop) else '**不成立（归因错误！）**'))
