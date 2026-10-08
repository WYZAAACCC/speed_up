#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r735_drive.py <root> <tag> ——— **驱动力按面的分解**（只读 `series.csv`，零算力）。

## 为什么测它（承 `R734` 的机理）
`R734` 实测：`M_tip/M_wide = 356–384`（速率比**给足了**），
但 `f_tip` 只有 **1.5–3.5%** ⇒ 宏观伸长被稀释。
⇒ **下一个问题**：**驱动力**在 tip / side / wide 三档上是否**帮倒忙**？

速度律（`windowB_surface.py:4857-4859`）：
```
v = M(n)·[ Δf + η·Δed − γ_eff·κ ]
```
⇒ 若 `dG_wide` **比 `dG_tip` 大**（或 `ed` 在宽面上更正），
则 `M` 的优势会被**驱使力的劣势抵消**一部分。

## `series.csv` 里现成的列（**不重新计算**）
`dG_tip` / `dG_side` / `dG_wide` / `dG_tip_p90` / `dG_side_p90` /
`ed_tip` / `ed_side` / `ed_wide` / `ed_obl` / `dG_obl` / `dG_max_Jm3` / `dG_ratio`

⚠ 记账：这些列的**分档口径由引擎给**（`_bk_exp.py` 的 `_ebf`），本脚本**只读不改**。
若引擎的口径与 `R734` 的 `|n·a|` 口径不同 ⇒ **两者不能直接相乘**，只能各自看趋势。

## 判据（**先登记，可 FAIL**）
| # | 判据 | 含义 |
|---|---|---|
| **D-1** | `dG_tip / dG_wide > 1` | 驱动力**在快方向上更大** ⇒ 与 `M(n)` 同向（好） |
| **D-2** | 若 `dG_tip / dG_wide < 1` | 驱动力**反号稀释** ⇒ 与 `M(n)` 对抗（这就能解释"给了 380× 却长不出去"） |

## 用法
    python3 _r735_drive.py _exp/_bk_block B2P_q0 B2P_pre
"""
import csv
import os
import sys


def main():
    root = sys.argv[1]
    tags = sys.argv[2:]
    print('=' * 104)
    print('驱动力按面的分解（只读 series.csv；root=%s）' % root)
    print('=' * 104)
    for t in tags:
        p = os.path.join(root, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('【%s】⚠ 无 series.csv' % t)
            continue
        with open(p, newline='') as f:
            rd = csv.DictReader(f)
            rows = [r for r in rd]
        if not rows:
            continue
        cols = ['step', 'box_touch', 'Vt', 'dG_tip', 'dG_side', 'dG_wide',
                'dG_obl', 'dG_max_Jm3', 'dG_ratio', 'ed_tip', 'ed_side', 'ed_wide']
        have = [c for c in cols if c in (rows[0].keys() if rows else [])]
        print('\n【%s】可用列：%s' % (t, ', '.join(have)))
        if 'dG_tip' not in have or 'dG_wide' not in have:
            print('   ⚠ 缺 `dG_tip`/`dG_wide` ⇒ **无法判定**（该臂可能没跑 `--pair-every`）')
            continue
        print('   %-6s %5s %12s %12s %12s %10s %10s'
              % ('step', 'box', 'dG_tip', 'dG_side', 'dG_wide', 'tip/wide', '判据'))

        def num(r, k):
            try:
                return float(r[k])
            except (KeyError, ValueError, TypeError):
                return float('nan')
        for r in rows:
            st = r.get('step', '?')
            bt = str(r.get('box_touch', '?'))
            dt, ds, dw = num(r, 'dG_tip'), num(r, 'dG_side'), num(r, 'dG_wide')
            ratio = dt / dw if (dw == dw and dw != 0) else float('nan')
            if ratio != ratio:
                judge = '⚪ 无法判定'
            elif ratio > 1:
                judge = '✅ D-1（与 M(n) 同向）'
            else:
                judge = '⛔ **D-2（与 M(n) 对抗！）**'
            print('   %-6s %5s %12.4g %12.4g %12.4g %10.3f  %s'
                  % (st, bt, dt, ds, dw, ratio, judge))
        # 汇总
        rr = [num(r, 'dG_tip') / num(r, 'dG_wide') for r in rows
              if num(r, 'dG_wide') == num(r, 'dG_wide') and num(r, 'dG_wide') != 0]
        if rr:
            print('   ⇒ `dG_tip/dG_wide` 的范围 [%.3f, %.3f]；中位 %.3f'
                  % (min(rr), max(rr), sorted(rr)[len(rr) // 2]))
    print()
    print('  ⚠ 记账：本表口径由**引擎**给（`_bk_exp.py` 的 `_ebf`），与 `R734` 的 `|n·a|`')
    print('     口径**可能不同** ⇒ 两者**不能直接相乘**，只能各自看趋势')
    return 0


if __name__ == '__main__':
    sys.exit(main())
