#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r47_dxverdict.py —— **Δx 对照的判决**（`_r47_dx62.sh` 里预登记的 R-1/R-2/R-3）。

## 背景（`R30_AUDIT_LEDGER.md` §18）
`BLOCK_DERIVATION §9.5` 的盒子尺寸约束用的是 **15.5 nm/步**，而那是**包围盒口径**；
实测包围盒把面间距增长放大 **2.5–2.8×**。历史臂没有落盘 φ ⇒ 只能**新跑**一个带 φ 的
Δx=62.5 nm 臂（`mb1s62`）来替换它。

## 两臂（**只差 Δx**；⚠ 盒也随之减半 ⇒ 是"Δx + 盒"混合对照）
| 臂 | N | Δx | 盒 | `t/Δx` |
|---|---|---|---|---|
| `mb1s`   | 96 | 125 nm  | 12 µm | 5.08 |
| `mb1s62` | 96 | 62.5 nm | 6 µm  | 10.16 |

## 判据（**跑之前就写好**，见 `_r47_dx62.sh`）
* **R-1** 两臂三个面族的速率**量级**必须同阶（同物理）
* **R-2** `t/Δx` 从 5.08 升到 10.16 ⇒ 若速率**显著变化**，说明 `mb1s` 的速率受分辨率影响，**必须记账**
* **R-3** `wide` 是否仍为负（变薄）

用法：  python3 _r47_dxverdict.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from _r47_rates import rates_for                                # noqa: E402

ARMS = [('mb1s', '_exp/_bk_mb/dry_mb1s', 125.0),
        ('mb1s62', '_exp/_bk_mb/dry_mb1s62', 62.5)]


def med_rate(d, face):
    r = rates_for(d)
    if r is None:
        return None, 0
    vals = []
    for k in sorted(r):
        xs, ys = r[k][face]
        if len(xs) < 3:
            continue
        vals.append(float(np.polyfit(np.array(xs, float),
                                     np.array(ys, float), 1)[0]))
    return (float(np.median(vals)) if vals else None), len(vals)


def main():
    print('=' * 88)
    print('★ Δx 对照判决（金标准「面间距」口径；速率 nm/步，最小二乘）')
    print('  %-9s %-8s %-8s %-11s %-11s %-11s %s'
          % ('臂', 'Δx nm', '场数', 'tip', 'side', 'wide', '记账'))
    res = {}
    for tag, d, dx in ARMS:
        row = {}
        for f in ('tip', 'side', 'wide'):
            row[f], n = med_rate(d, f)
        res[tag] = row
        print('  %-9s %-8.1f %-8d %-11s %-11s %-11s %s'
              % (tag, dx, n,
                 ('%+.4f' % row['tip']) if row['tip'] is not None else '（不足）',
                 ('%+.4f' % row['side']) if row['side'] is not None else '（不足）',
                 ('%+.4f' % row['wide']) if row['wide'] is not None else '（不足）',
                 't/Δx=%.2f' % (635.0 / dx)))
    a, b = res['mb1s'], res['mb1s62']
    print('\n★ 判据')
    for f in ('tip', 'side', 'wide'):
        if a[f] is None or b[f] is None:
            print('  R-%-6s **数据不足 ⇒ 无法判定**（等 mb1s62 跑完）' % f)
            continue
        r = (b[f] / a[f]) if abs(a[f]) > 1e-9 else float('nan')
        same_order = (0.2 < abs(r) < 5.0) if np.isfinite(r) else False
        print('  %-5s mb1s=%+.4f  mb1s62=%+.4f  ⇒ 比 **%.2f×**  %s'
              % (f, a[f], b[f], r,
                 'R-1 同阶 ✅' if same_order else '⚠ R-2 **Δx 依赖显著**，必须记账'))
    if a.get('wide') is not None and b.get('wide') is not None:
        print('  R-3  `wide` 两臂是否都为负：mb1s=%s  mb1s62=%s ⇒ %s'
              % ('负' if a['wide'] < 0 else '**非负**',
                 '负' if b['wide'] < 0 else '**非负**',
                 '✅ 一致' if (a['wide'] < 0) == (b['wide'] < 0) else '❌ 不一致'))
    print('\n⚠ 记账：两臂同时改了 Δx 与盒尺寸（N 相同）⇒ 是混合对照。')
    print('   可接受的理由：该臂核心 ~2.9 µm ≪ 半盒（12/2=6 µm 与 6/2=3 µm）')
    print('   —— 但 62.5 nm 臂的余量只有 0.1 µm ⇒ **必须核对它有没有撞壁**'
          '（只看 `box_touch_core`）。')


if __name__ == '__main__':
    main()
