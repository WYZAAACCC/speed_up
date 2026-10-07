#!/usr/bin/env python3
"""_r430_vtdrop.py —— ★ **查 `§190.7` 的 `Vt` 下降**：用**已有落盘数据**先定位，再决定要不要深挖。

## 问题
A 臂（守 C-3）`Vt` 单调下降 50%，B 臂（burst）上升 4.5×。
两臂同起点、同 `α_KM`、同板条几何，**只差冷速与步数**。

## 候选解释（`§190.7` 已登记，均未验证）
1. 孤立板条在 `β_h` 钉扎下变薄（`_seed_next` 注释记过同类现象）；
2. athermal 的大 `dt`（`ΔG_v(T_1)` 最小 ⇒ 首段 `dt` 最大）；
3. **C-5（`β_h` 下界）在当前步数档下失去约束力**（日志打印 0.000 vs 归档 2.015）。

## 本脚本做什么（**只读**）
从两臂的 `series.csv` 把**引擎自己算的驱动力分解**读出来：
`dG_max_Jm3` / `dG_p999` / `dG_tip` / `dG_side` / `ed_tip` / `ed_side` / `df`（若有）。
判据：
  * 若 `dG_* ≈ df + ed < 0`（净驱动力为负）⇒ **解释 1/3 成立**（临界尺寸效应，
    起点 `T_1` 处 ΔG_v 最小 ⇒ 板条**亚稳**）⇒ 是**物理**，不是 bug。
  * 若 `dG_* > 0` 而 `Vt` 仍在降 ⇒ 另有机理，继续查。
"""
import csv
import os
import sys

import numpy as np

BASE = '_exp/_bk_mb'
# ⚠ 驱动把目录建成 `<out>/<arm>_<tag>` ⇒ 实际是 `dry_abA` / `dry_abB`。
ARMS = ['dry_abA', 'dry_abB']
WANT = ['step', 't_s', 'dt', 'Vt', 'nreg_used', 'nslab_n', 'nf3', 'nf2',
        'dG_max_Jm3', 'dG_p999', 'dG_ratio', 'dG_near_max',
        'ed_tip', 'ed_side', 'ed_wide', 'dG_tip', 'dG_side', 'dG_wide',
        'ed_tip_p90', 'ed_side_p90', 'dG_tip_p90', 'dG_side_p90',
        'dG_tip_max', 'dG_side_max', 'v_tip_nabs', 'v_side_nabs',
        'ths', 'vols', 'runs', 'box_touch', 'finite']


def P(s):
    print(s, flush=True)


P('=' * 100)
P('_r430 —— `Vt` 下降的定位（只读落盘数据）')
P('=' * 100)

for tag in ARMS:
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        P('\n[%s] ✗ 无 series.csv' % tag)
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    cols = [c for c in WANT if c in rows[0]]
    P('\n' + '#' * 100)
    P('# %s  （%d 行；可用列 %d/%d）' % (tag, len(rows), len(cols), len(WANT)))
    P('#' * 100)
    missing = [c for c in WANT if c not in rows[0]]
    if missing:
        P('  缺列：%s' % ', '.join(missing))
    show = [c for c in ('step', 'dt', 'Vt', 'nreg_used', 'nslab_n', 'nf3',
                        'dG_max_Jm3', 'dG_p999', 'dG_tip', 'dG_side',
                        'ed_tip', 'ed_side', 'dG_tip_p90') if c in cols]
    P('  %s' % ' | '.join('%-9s' % c[:9] for c in show))
    for r in rows:
        cells = []
        for c in show:
            v = r.get(c, '')
            try:
                f = float(v)
                if c == 'Vt':
                    cells.append('%-9.5f' % (f * 1e18))
                elif c in ('dt',):
                    cells.append('%-9.2e' % f)
                elif abs(f) >= 1e5:
                    cells.append('%-9.3e' % f)
                else:
                    cells.append('%-9.4g' % f)
            except (ValueError, TypeError):
                cells.append('%-9s' % (str(v)[:9]))
        P('  %s' % ' | '.join(cells))
    if 'Vt' in rows[0]:
        vt = np.array([float(r['Vt']) for r in rows])
        P('  ⇒ Vt: 首 %.5f → 末 %.5f µm³（%+.1f%%）'
          % (vt[0] * 1e18, vt[-1] * 1e18, 100 * (vt[-1] / vt[0] - 1)))
P('=' * 100)
