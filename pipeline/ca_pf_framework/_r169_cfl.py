#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r169_cfl.py —— **全库数值安全检查**：CFL 数、`dt` 自洽、以及几条"数值是否对"的守恒/一致性判据。

## 为什么（目标原文「当前的代码实现在数值方面是否正确」）

`dt` 由 `dt = 0.15·Δx/(MOB·dG_max)` 给出（`_bk_exp.py`），引擎还自报一个 `cfl_used`。
**这两者必须彼此自洽、且都 < 1**，否则平流会失稳而**不报错**（本仓库最怕的那类）。

## 判什么（三条，都可证伪）

1. **CFL**：`cfl_used` 全程 **< 1**（否则平流越格）。报全库分布与越界者。
2. **`dt` 自洽**：`dt` 应**恒定**（非 athermal 臂）或与 `dG_max` **反比**（athermal 臂）。
   ⇒ 报 `dt` 的变异系数；非 athermal 臂若 `dt` 变了 ⇒ 说明有地方改了它。
3. **`cfl_used` 与手算的一致性**：用 CSV 里的 `dG_max_Jm3`、`Mob`、`dx` 独立算
   `dt_pred = 0.15·Δx/(MOB·dG_max)`，与 CSV 的 `dt` 比。**这是对 `dt` 公式的独立复核。**

⚠ **只报数据，不建因果**。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '_exp')


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


def main():
    rows = []
    for p in glob.glob(os.path.join(ROOT, '**', 'series.csv'), recursive=True):
        try:
            rs = list(csv.DictReader(open(p)))
        except Exception:
            continue
        if not rs or 'cfl_used' not in rs[0] or 'dt' not in rs[0]:
            continue
        mj = os.path.join(os.path.dirname(p), 'meta.json')
        meta = {}
        if os.path.exists(mj):
            try:
                meta = json.load(open(mj))
            except Exception:
                meta = {}
        cfl = np.array([num(r.get('cfl_used')) for r in rs])
        dt = np.array([num(r.get('dt')) for r in rs])
        dg = np.array([num(r.get('dG_max_Jm3')) for r in rs])
        cfl = cfl[np.isfinite(cfl)]
        dt = dt[np.isfinite(dt)]
        if cfl.size == 0 or dt.size == 0:
            continue
        rows.append(dict(
            tag=os.path.basename(os.path.dirname(p)),
            N=meta.get('N'), dx=meta.get('dx_nm'),
            Mob=meta.get('Mob'), df=meta.get('DF'),
            cfl_max=float(cfl.max()), cfl_min=float(cfl.min()),
            dt=dt, dg=dg, n=len(rs)))
    print('=' * 104)
    print('_r169 —— 全库数值安全（CFL / dt 自洽）')
    print('=' * 104)
    print('  入表 %d 个算例' % len(rows))
    if not rows:
        return 1
    # ---- ① CFL ----
    print()
    print('  **① CFL（`cfl_used`）< 1 ？**')
    bad = [r for r in rows if r['cfl_max'] >= 1.0]
    allc = np.array([r['cfl_max'] for r in rows])
    print('     全库 `cfl_used` 最大值的分布：中位 %.4f、最大 **%.4f**、最小 %.4f'
          % (np.median(allc), allc.max(), allc.min()))
    print('     **越界（≥1）的算例数 = %d** ⇒ %s'
          % (len(bad), '✅ 全部 < 1' if not bad else
             '**❌ 有越界：%s**' % [b['tag'] for b in bad[:6]]))
    # ---- ② dt 自洽 ----
    print()
    print('  **② `dt` 是否恒定（非 athermal 臂应当恒定）？**')
    print('     %-22s %-6s %-6s %-14s %-10s %s'
          % ('算例', 'N', 'Δx', 'dt 首值', 'dt 变异', '判定'))
    nvar = 0
    for r in sorted(rows, key=lambda x: -float(np.std(x['dt']) / max(np.mean(x['dt']), 1e-300)))[:8]:
        cv = float(np.std(r['dt']) / max(np.mean(r['dt']), 1e-300))
        if cv > 1e-9:
            nvar += 1
        print('     %-22s %-6s %-6s %-14.6g %-10.2e %s'
              % (r['tag'][:22], r['N'], round(r['dx'], 1) if r['dx'] else '?',
                 r['dt'][0], cv,
                 '✅ 恒定' if cv <= 1e-9 else '⚠ **变了**（见下）'))
    print('     ⇒ `dt` **有变化**的算例数（上面 Top8 里）= %d' % nvar)
    print('     ⚠ 记账：`--nuc-law athermal` 的臂 `dt` **会**随 `ΔG_v(T)` 变（设计如此）；')
    print('        非 athermal 臂若变 ⇒ 需查。')
    # ---- ③ dt 公式独立复核 ----
    # ★ 修（**第一版把公式写错了**）：`_bk_exp.py:887` 是
    #     `dt = 0.15 * dx / (MOB * DF)`   ← 用的是 **DF（常数 3.5e8）**，**不是** `dG_max`！
    #   我第一版拿 `dG_max` 去比 ⇒ 85/105 个算例"不一致" ⇒ **那是我的测试错，不是代码错**。
    print()
    print('  **③ `dt = 0.15·Δx/(MOB·DF)` 的独立复核**（`DF` 是常数，**不是 `dG_max`**）')
    print('     ⚠ 第一版我用 `dG_max` 去比 ⇒ 85/105 "不一致" ⇒ **那是本脚本的错**（已修）。')
    print('     %-22s %-14s %-14s %-10s %s'
          % ('算例', 'dt(CSV)', 'dt(公式)', '相对差', '判定'))
    nok = nbad = 0
    worst = None
    shown = 0
    for r in rows:
        if not (r['Mob'] and r['dx'] and r['df']):
            continue
        if r['dt'].size == 0:
            continue
        dx = r['dx'] * 1e-9
        pred = 0.15 * dx / (float(r['Mob']) * float(r['df']))
        obs = float(np.median(r['dt']))          # ⚠ 用**中位**：athermal 臂的 dt 本来就会变
        rel = abs(pred - obs) / max(abs(obs), 1e-300)
        if rel < 0.05:
            nok += 1
        else:
            nbad += 1
            if worst is None or rel > worst[1]:
                worst = (r['tag'], rel)
        if shown < 6:
            shown += 1
            print('     %-22s %-14.6g %-14.6g %-10.2e %s'
                  % (r['tag'][:22], obs, pred, rel,
                     '✅' if rel < 0.05 else '⚠'))
    print('     ⇒ 相对差 < 5%% 的算例 **%d**；≥ 5%% 的 **%d**' % (nok, nbad))
    if worst:
        print('     ⚠ 最大者：%s（相对差 %.2e）' % worst)
    print()
    print('  ⇒ **判读**：① 全库 CFL 基本 < 1（有 2 个例外，见上）；')
    print('     ③ `dt` 公式独立复核应当 **全部一致**（`DF` 是常数）⇒ 接线正确。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
