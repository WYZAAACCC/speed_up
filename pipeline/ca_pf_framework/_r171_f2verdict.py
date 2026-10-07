#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r171_f2verdict.py —— **`§122/§123` 的受控对照判决**（`_r165`，λ=1 vs λ=0）。

## 对照（同几何、同变体集、同步数，**只差 `--f2-pair-gamma`**）

| λ=1 臂 | λ=0 对照（`§112`） | `G` | 含同 packet 对吗？ |
|---|---|---|---|
| `saSet2F2` | `saSet2` | `{1,2,3,4,7,8}` | **含 2 对**：(1,2)、(3,4) ⇒ **有便宜界面可用** |
| `saOddGF2` | `saOddG` | `{1,3,5,7,9,11}` | **一对都没有** |

## 预登记判据（原文在 `_r165_f2test.sh` 头部）

* **G-1** λ=0 的两臂应与 `§112` 的 `saSet2`/`saOddG` **逐位相同**（开关惰性）
* **G-2** λ=1 时 `saSet2` 的 `r_selfac` **趋势改变幅度** > `saOddG` 的（核心预测）
* **G-3** `nf2(t=0)=0`、`box_touch_core=0` 全程
* **G-4** 记录 `E_el/Vt`（`§118/§119` 强制：不得只报 `r`）

## ★ 额外记录（**受 `§128` 启发，作为"记录"而非硬判据**）

`§128` 实测：**无投影臂的 `E_el/Vt` 与界面面积密度 `A_int/Vt` 强相关（+0.95…+0.998）**
⇒ 那些臂里**弹性能≈界面能** ⇒ 那么"**有效界面能**"`E_el/A_int` 就是一个有意义的量。
⇒ **记录**：λ=1 是否**降低** `E_el/A_int`（同 packet 对便宜 ⇒ 有效界面能应降）。
⚠ 按 `§84` 规程②，**跨量比值必须先做正对照** —— 本项**只作记录**，**不作判据**。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
PAIRS = [('saSet2', 'saSet2F2', '{1,2,3,4,7,8}（**含 2 对同 packet**）'),
         ('saOddG', 'saOddGF2', '{1,3,5,7,9,11}（**不含**）')]


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {}
    for key in ('step', 'r_selfac', 'E_el_J', 'Vt', 'f3_area_m2', 'f2_area_m2',
                'nf2', 'box_touch_core'):
        v = []
        for r in rows:
            try:
                v.append(float(r.get(key, 'nan') or 'nan'))
            except (TypeError, ValueError):
                v.append(float('nan'))
        out[key] = np.array(v)
    out['ed'] = out['E_el_J'] / np.maximum(out['Vt'], 1e-300)          # E_el/Vt
    A = np.nan_to_num(out['f3_area_m2']) + np.nan_to_num(out['f2_area_m2'])
    out['ad'] = A / np.maximum(out['Vt'], 1e-300)                      # A_int/Vt
    out['eperA'] = np.where(A > 0, out['E_el_J'] / np.maximum(A, 1e-300), np.nan)
    out['_r0'] = rows[0].get('r_selfac')
    out['_nf20'] = rows[0].get('nf2')
    out['_nprof0'] = rows[0].get('blk_nprof')
    out['_nblk0'] = rows[0].get('nblk_sig')
    return out


def trend(x, y):
    m = np.isfinite(y) & np.isfinite(x)
    if m.sum() < 3:
        return float('nan')
    return float(np.polyfit(x[m], y[m], 1)[0])


def main():
    print('=' * 112)
    print('_r171 —— F2 配对面能的受控对照判决（λ=1 vs λ=0）')
    print('=' * 112)
    res = {}
    for t0, t1, lab in PAIRS:
        A, B = load(t0), load(t1)
        print()
        print('  ### %s' % lab)
        if A is None or B is None:
            print('     ⚠ 数据不全（%s=%s, %s=%s）'
                  % (t0, A is not None, t1, B is not None))
            continue
        res[t0] = (A, B)
        print('     %-12s %-9s %-11s %-11s %-13s %-13s %s'
              % ('臂', '步数', 'r(0)', 'r(末)', 'E_el/Vt(末)', 'E_el/A_int(末)',
                 '撞壁max'))
        for nm, D in (('%s(λ=0)' % t0, A), ('%s(λ=1)' % t1, B)):
            m = np.isfinite(D['r_selfac'])
            ea = D['eperA'][np.isfinite(D['eperA'])]
            print('     %-12s %-9d %-11.4f %-11.4f %-13.4g %-13.4g %.0f'
                  % (nm, int(m.sum()), D['r_selfac'][m][0], D['r_selfac'][m][-1],
                     np.nanmedian(D['ed'][D['ed'] > 0]),
                     np.median(ea) if ea.size else float('nan'),
                     np.nanmax(D['box_touch_core'])))
        tr0 = trend(A['step'], A['r_selfac']) * 100
        tr1 = trend(B['step'], B['r_selfac']) * 100
        print('     **r 趋势**：λ=0 %+.4f/100步 → λ=1 %+.4f/100步'
              '（**改变 %+.4f**，相对 %+.1f%%）'
              % (tr0, tr1, tr1 - tr0,
                 100 * (tr1 / tr0 - 1) if abs(tr0) > 1e-12 else float('nan')))
        e0 = np.nanmedian(A['ed'][A['ed'] > 0])
        e1 = np.nanmedian(B['ed'][B['ed'] > 0])
        print('     **E_el/Vt**：λ=0 %.4g → λ=1 %.4g（%+.1f%%）'
              % (e0, e1, 100 * (e1 / e0 - 1) if e0 else float('nan')))
        a0 = np.nanmedian(A['eperA'])
        a1 = np.nanmedian(B['eperA'])
        print('     **E_el/A_int（记录，非判据）**：λ=0 %.4g → λ=1 %.4g（%+.1f%%）'
              % (a0, a1, 100 * (a1 / a0 - 1) if a0 == a0 and a0 else float('nan')))
        ok = (str(A['_nf20']) == '0' and str(B['_nf20']) == '0'
              and np.nanmax(A['box_touch_core']) == 0
              and np.nanmax(B['box_touch_core']) == 0)
        print('     **G-3** `nf2(t=0)` = %s / %s；`blk_nprof(t=0)` = %s / %s；'
              '`nblk_sig(t=0)` = %s / %s ⇒ %s'
              % (A['_nf20'], B['_nf20'], A['_nprof0'], B['_nprof0'],
                 A['_nblk0'], B['_nblk0'], '✅' if ok else '❌'))
    # ---- 核心：G-2 ----
    print()
    print('=' * 112)
    print('  ## G-2 核心判据：**λ=1 对含同 packet 对的臂影响应更大**')
    print('=' * 112)
    ds = {}
    for t0, t1, lab in PAIRS:
        if t0 not in res:
            continue
        A, B = res[t0]
        tr0 = trend(A['step'], A['r_selfac']) * 100
        tr1 = trend(B['step'], B['r_selfac']) * 100
        ds[t0] = abs(tr1 - tr0)
        print('     %-10s |Δ趋势| = **%.4f**/100步' % (t0, ds[t0]))
    if len(ds) == 2:
        s = ds['saSet2']
        o = ds['saOddG']
        print()
        print('     `saSet2`（含 2 对同 packet）|Δ| = %.4f；`saOddG`（不含）|Δ| = %.4f'
              % (s, o))
        print('     ⇒ 比值 **%.2f×**' % (s / o if o > 1e-12 else float('inf')))
        if s > 2 * o:
            print('     ⇒ ✅ **G-2 成立**：影响**确实经"同 packet 便宜"起作用**')
        else:
            print('     ⇒ ⚠ **G-2 不成立**：影响不是（或不只是）经"同 packet 便宜"起作用的')
    print()
    print('  ⚠ **不预设"哪个对"**（`§122` 第五节）：本实验只测"补法有没有按预期起作用"，')
    print('     不判"促进 packet 好还是促进 6 变体自协调好"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
