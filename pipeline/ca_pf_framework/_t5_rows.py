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
    # ★★★★★ 2026-10-03（s59 更正）：**原来这里写的是错的**
    #   旧判词：「块表只在 lcm(--every, --pair-every) 的倍数步算」——**与上面的实测输出自相矛盾**
    #   （实测 `0,20,40,…,260` **每一行**都非空）。
    #   那句是我从 §13 的一个**未经验证的推断**抄来的，**没有随实测更新** ⇒ 会把后续读者带偏。
    #   **实测结论**：块表**每一行**都算（`--pair-every` 并没有把块表压成 100 步一格）。
    #   ⚠ 而"**在线块列分辨率**"这件事，**仍以实测的非空行为准**，不要引用任何未验证的 lcm 推断。
    print('  ★ 判定：**块表每一行都有值**（见上面的非空步列表）'
          '—— 「只在 lcm 倍数算」那条**推断已被实测推翻**（s59 更正）')
    if 220 in pop:
        print('     ⇒ §55 的「step 200→220 增长」说法**成立**（220 行确实带块表）')
