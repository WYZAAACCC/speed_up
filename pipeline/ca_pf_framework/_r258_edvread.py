#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r258_edvread.py —— 读 `saSet2EDV`（真实 R165 几何 + `--diag-edv`）的**逐变体 `ed`**。

## 为什么这条现在特别有价值（`§144` 之后）

`§144` 证明：**带 `--facet-proj 10` 时界面能对形态零影响**。
而 `saSet2EDV` 用的就是归档几何（**带投影**）
⇒ **在这个配置下，动力学**只剩下 `ed`**（`dG = 0 + Δed − 0`）
⇒ **它正好是"纯 `ed` 驱动"的理想实验**，用来回答条件③的核心问题。

## 要回答

* **Q-A** `ed` 是按**变体**组织，还是按**场/位置**组织？
  ⇒ 比"**变体内**离散"与"**变体间**离散"哪个大。
  （`_r239` 的小几何给出：**同变体的场差 23%** > 跨变体极差 1.01e8 ⇒ 像按场组织。）
* **Q-B** 随演化，跨变体的 `ed` 极差/标准差是**变大**（分化）还是**变小**（趋同）？
* **Q-C** 六变体的**体积**是否趋匀（`vol_cv` 下降）？—— "块间协调"的直接签名。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_exp', '_bk_mb', 'dry_saSet2EDV', 'diag_edv.json')


def main():
    print('=' * 108)
    print('_r258 —— `saSet2EDV` 逐变体 `ed`（真实 R165 几何，**带投影** ⇒ 纯 `ed` 驱动）')
    print('=' * 108)
    if not os.path.exists(P):
        print('  ⚠ `diag_edv.json` 还没落盘（进程可能仍在跑）')
        return 2
    d = json.load(open(P))
    rec = d.get('rec') or []
    print('  记录条数 = %d（每 `--every 20` 一条，落盘时为最新）' % d.get('n_rec', 0))
    if not rec:
        print('  ⚠ 无记录')
        return 2
    print()
    print('  ## 逐步的跨变体汇总')
    print('     %-6s %-8s %-14s %-14s %-12s %s'
          % ('step', '变体数', '`ed` 中位极差', '`ed` 中位标准差', '体积 CV', '备注'))
    for r in rec:
        print('     %-6s %-8s %-14.4e %-14.4e %-12.4f'
              % (r.get('step'), r.get('n_field'),
                 r.get('med_spread', float('nan')),
                 r.get('med_std', float('nan')),
                 r.get('vol_cv', float('nan'))))
    last = rec[-1]
    pf = last.get('per_field') or {}
    print()
    print('  ## 末条（step=%s）逐场明细' % last.get('step'))
    print('     %-6s %-8s %-12s %-15s %-15s %s'
          % ('场', '变体', '体积[µm³]', '`ed` 中位', '`ed` 均值', '10–90 分位'))
    for k in sorted(pf, key=lambda x: int(x)):
        v = pf[k]
        print('     %-6d V%-7d %-12.4f %-15.4e %-15.4e %+.3e … %+.3e'
              % (v['field'], v['variant'], v['vol_um3'], v['med'], v['mean'],
                 v['p10'], v['p90']))
    # ---- Q-A：变体内 vs 变体间 ----
    print()
    print('  ## **Q-A** `ed` 按**变体**还是按**场/位置**组织？')
    byv = {}
    for v in pf.values():
        byv.setdefault(v['variant'], []).append(v['med'])
    within, between = [], []
    for var, meds in sorted(byv.items()):
        if len(meds) > 1:
            within.append(max(meds) - min(meds))
        print('     变体 V%-3d：%d 个场，`ed` 中位 = %s（场内极差 %.3e）'
              % (var, len(meds), ['%.4e' % m for m in meds],
                 (max(meds) - min(meds)) if len(meds) > 1 else 0.0))
    allmed = np.array([v['med'] for v in pf.values()])
    print('     ⇒ **变体间**极差（所有场中位）= **%.4e**' % (allmed.max() - allmed.min()))
    if within:
        print('     ⇒ **变体内**极差（同变体不同场）最大 = **%.4e**，中位 = **%.4e**'
              % (max(within), float(np.median(within))))
        r = max(within) / (allmed.max() - allmed.min()) if allmed.max() > allmed.min() else float('nan')
        print('     ⇒ 比值（变体内最大 / 变体间）= **%.3f**'
              % r)
        if r > 0.5:
            print('     ⇒ ⇒ **`ed` 更像按"场/位置"组织，而不是按"变体"** '
                  '（同变体的两个场差得和不同变体一样多）')
        else:
            print('     ⇒ ⇒ **`ed` 主要按"变体"组织**（同变体的场彼此接近）')
    else:
        print('     ⇒ ⚠ 每个变体只有一个场 ⇒ 无法分离"变体内" ⇒ **不适用**')
    print()
    print('  ⚠ 记账：`ed` = `Σ_p e0v_eng[v,p]·σ_p + sext_e0[v]`（弹性自项）。')
    print('     本臂带 `--facet-proj 10` ⇒ 按 `§144`，动力学里界面能已被压制')
    print('     ⇒ **本读数近似"纯 `ed` 驱动"下的变体选择图景**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
