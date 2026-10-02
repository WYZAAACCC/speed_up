#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_n1.py --- ★★★★★★ **用 R30 已经做好的**正确口径**（`nslab_n1`/`runs1`/`nf3_col1`）重报 C3**

## 为什么（R165 的发现）
`_bk_measure.py:834-854` 的 docstring **逐字**写着：
```
★★★ R30 修复（R30_AUDIT_LEDGER.md P0-1）：柱剖面原来有两种静默少读 …
  ① min_run=2 把"沿 n* 只占 1 个箱"的层整层丢掉
  ② r_col = 300 nm 硬编码 ⇒ 面内偏置 > 300 nm 的板条整个不可见，截面大的还会被切成两段
处置：nslab_n / runs / nf3_col —— **保持归档口径不变**（r_col=300nm、min_run=2）
     ★★ 新增 nslab_n1 / runs1 / nf3_col1 —— 用**自适应柱半径 + min_run=1**
     ★★ 新增 r_col_nm 与 col_cover_min / col_cover_<k> ⇒ **可见性守卫**
```
**⇒ ⇒ **∴ R149–R151 我报的"1-D 口径低报"，**根因早被 R30 查明，且正确口径**已经在 CSV 里****
（**`nslab_n1` / `runs1` / `nf3_col1` / `r_col_nm` / `col_cover_min`**）。

**★ 而 R149–R151 我用的是**归档口径 `nslab_n`**（**R30 故意保持不变的那个**）** ⇒ **用错了列**。**
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['E', 'F', 'G', 'L']
# 两个口径 + 守卫
COLS = ['nslab_n', 'nf3_col', 'nslab_n1', 'runs1', 'nf3_col1',
        'r_col_nm', 'col_cover_min', 'nslab_nu', 'nslab_nu1', 'nf3', 'nf2']


def main():
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
        if not os.path.exists(p):
            print('  %-4s （无 series.csv）' % t)
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        hdr = list(rows[0].keys())
        have = [c for c in COLS if c in hdr]
        miss = [c for c in COLS if c not in hdr]
        print('=' * 104)
        print('臂 %s：%d 行' % (t, len(rows)))
        print('=' * 104)
        if miss:
            print('  ⚠ CSV 里没有这些列：%s' % ', '.join(miss))
        print('  %-7s %s' % ('step', ' '.join('%-13s' % c for c in have)))
        print('  ' + '-' * 98)
        # 每 50 步 + 首末
        show = [r for r in rows if r[hdr[0]] in ('0', '5') or
                (r[hdr[0]].isdigit() and int(r[hdr[0]]) % 50 == 0) or r is rows[-1]]
        seen = set()
        for r in show + [rows[-1]]:
            k = r[hdr[0]]
            if k in seen:
                continue
            seen.add(k)
            vals = []
            for c in have:
                v = r.get(c, '')
                try:
                    f = float(v)
                    vals.append('%-13.6g' % f)
                except Exception:
                    vals.append('%-13s' % (str(v)[:13]))
            print('  %-7s %s' % (k, ' '.join(vals)))
        print()
    print('=' * 104)
    print('★ 判读：')
    print(' · `nslab_n`/`nf3_col` = **归档口径**（`r_col=300nm`、`min_run=2`）—— **R30 故意冻结的**')
    print(' · `nslab_n1`/`runs1`/`nf3_col1` = **自适应柱半径 + min_run=1** ⇒ **★ 这才是该用来判 C3 的**')
    print(' · `col_cover_min` = **可见性守卫**（最小覆盖率）⇒ **它小就说明有场看不见**')
    print(' · `r_col_nm` = 实际用的柱半径 ⇒ **≠300 就说明归档口径不适用**')
    print('=' * 104)


if __name__ == '__main__':
    main()
