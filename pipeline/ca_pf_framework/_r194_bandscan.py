#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r194_bandscan.py —— 扫全库快照，查 `band_*`（带内稀疏 φ，P0-4 的产物）**在哪些臂里有**。

## 为什么要查

`§132.2`（P1-46）报"归档快照没有 φ ⇒ 无法离线重算法向/曲率类量"。
但复核时发现 `_bk_exp.py:296-325` 的 **`_sparse_band()`（R30 / **P0-4**）**
**已经**把**带内稀疏 φ** 写进快照（键 `band_idx` / `band_val` / `band_fld` / `band_cells`）。
⇒ **P1-46 必须分档说清**：
  * **有** `band_*` 的臂 ⇒ 能用**真实 φ 梯度**重算（比 `§132.5` 的 `region` 重建**准得多**）；
  * **没有**的臂（P0-4 之前跑的）⇒ 真的重算不了，只能用 `region` 重建的近似。

⇒ 本脚本给出**准确的清单**（不猜）。
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
WANT = ('band_idx', 'band_val', 'band_fld', 'band_cells')


def main():
    print('=' * 104)
    print('_r194 —— 扫全库快照：`band_*`（带内稀疏 φ）覆盖率')
    print('=' * 104)
    arms = sorted(d for d in os.listdir(MB)
                  if d.startswith('dry_') and os.path.isdir(os.path.join(MB, d)))
    print('  归档臂目录共 %d 个' % len(arms))
    have, miss, nophi = [], [], []
    rows = []
    for a in arms:
        fs = sorted(glob.glob(os.path.join(MB, a, 'snap_*.npz')))
        if not fs:
            continue
        last = max(fs, key=lambda f: int(
            (os.path.basename(f).split('_')[-1]).split('.')[0]))
        try:
            z = np.load(last, allow_pickle=True)
            ks = list(z.keys())
        except (OSError, ValueError) as e:
            rows.append((a, len(fs), '**读失败** %s' % e, ''))
            continue
        nb = sum(1 for k in WANT if k in ks)
        tag = ('**有** (%d/4)' % nb) if nb == 4 else (
            '部分 (%d/4)' % nb if nb else '**无**')
        size = os.path.getsize(last) / 1e6
        rows.append((a, len(fs), tag, '%.1f MB  keys=%s' % (size, ','.join(ks))))
        (have if nb == 4 else (miss if nb else nophi)).append(a)
    print()
    print('  ## 逐个臂（末快照）')
    for (a, n, tag, extra) in rows:
        print('     %-22s 快照 %-4d %-12s %s' % (a, n, tag, extra[:70]))
    print()
    print('=' * 104)
    print('  ## 汇总')
    print('=' * 104)
    print('     ✅ **有完整 `band_*`（能重算 φ 类量）= %d 个臂**' % len(have))
    for a in have:
        print('        %s' % a)
    print('     ⚠ 部分有 = %d 个' % len(miss))
    for a in miss:
        print('        %s' % a)
    print('     ❌ **完全没有 φ = %d 个臂**（P0-4 之前跑的 ⇒ `§132.2` 的 P1-46 对它们成立）'
          % len(nophi))
    print('        共 %d 个，前 20：%s' % (len(nophi), nophi[:20]))
    print()
    print('  ⇒ **结论**：P1-46 要按档说 —— ')
    print('     * 有 `band_*` 的臂：**能**用真实 φ 重算（`§132.5` 的 `region` 重建只是兜底）；')
    print('     * 没有的臂：**确实不能**，只能靠 `region` 近似或**重跑**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
