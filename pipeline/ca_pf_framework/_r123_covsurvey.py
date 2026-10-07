#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r123_covsurvey.py —— **`cov(t=0)` 到底由什么决定？**（跨全部已产出的扫描臂做相关）

## 为什么要做

`_r121` 实测：`t1N96L800`（L=800/W=600/**T=635**）的 `cov(t=0) = **0.635**`，
而 R75（L=1600/W=700/**T=635**）是 **1.079**。
⇒ **T=635 本身不是充分条件** —— 我上一轮"`T` 的格点相位是关键"的说法**不成立**（至少不完整）。

⇒ 把**所有**已产出的六块/多块臂的 `cov(t=0)` 与它们的 (N, L, W, T, gap, 块数, 每块根数)
并列，**用数据找规律**，而不是继续猜。

⚠ 本脚本**只报相关，不建因果**：臂之间的差异往往是**多因素**的，
下一轮要做的才是**受控**的单变量扫描。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
    print('=' * 122)
    print('_r123 —— `cov(t=0)` 全库普查（只报相关，不建因果）')
    print('=' * 122)
    rows = []
    for d in sorted(glob.glob(os.path.join(MB, 'dry_*'))):
        mj = os.path.join(d, 'meta.json')
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'snap_(\d+)', q).group(1)))
        if not (os.path.exists(mj) and fs):
            continue
        try:
            meta = json.load(open(mj))
            ea = meta.get('exp_args', {}) or {}
            z = np.load(fs[0])
            c = BM.snapshot_coverage(z)
        except Exception:
            continue
        bf = c.get('beta_frac', {}) or {}
        rows.append(dict(
            tag=os.path.basename(d)[4:], N=meta.get('N'),
            L=ea.get('plate_L'), W=ea.get('plate_W'), T=ea.get('plate_T'),
            gap=ea.get('block_gap_nm'),
            nb=len([x for x in str(ea.get('laths', '')).split(',') if x.strip()]),
            cov=c.get('cov', float('nan')),
            mb=max(bf.values()) if bf else float('nan'),
            nf3=len(bf)))
    rows = [r for r in rows if np.isfinite(r['cov'])]
    rows.sort(key=lambda r: -r['cov'])
    print('  %-14s %-5s %-7s %-6s %-6s %-7s %-5s %-9s %-8s %s'
          % ('tag', 'N', 'L', 'W', 'T', 'gap', '场数', 'cov(0)', 'maxβ(0)', '判定'))
    for r in rows:
        good = (r['cov'] >= 0.85 and r['mb'] <= 0.25)
        print('  %-14s %-5s %-7s %-6s %-6s %-7s %-5s %-9.3f %-8.2f %s'
              % (r['tag'], r['N'], r['L'], r['W'], r['T'], r['gap'], r['nb'],
                 r['cov'], r['mb'], '✅' if good else ''))
    print()
    # 按 T 分组看
    print('  ---- 按 `--plate-T` 分组（看"T 决定 cov"这条假设成不成立）----')
    from collections import defaultdict
    g = defaultdict(list)
    for r in rows:
        g[r['T']].append(r)
    for T in sorted(g, key=lambda x: (x is None, x)):
        arr = g[T]
        print('     T=%-7s n=%-3d cov: %s' % (T, len(arr),
              '  '.join('%.3f' % a['cov'] for a in arr[:8])))
    print()
    print('  ---- 按 `--plate-L` 分组 ----')
    g2 = defaultdict(list)
    for r in rows:
        g2[r['L']].append(r)
    for L in sorted(g2, key=lambda x: (x is None, x)):
        arr = g2[L]
        print('     L=%-7s n=%-3d cov: %s' % (L, len(arr),
              '  '.join('%.3f' % a['cov'] for a in arr[:8])))
    print()
    print('  ⚠ **只报相关**：各臂在 N/L/W/T/gap/场数 上**同时不同** ⇒ 不能据此定因果。')
    print('     下一轮应按"一次只改一个"重扫（受控），并把 `cov(t=0) ≥ 0.85`')
    print('     与 `nf2(t=0) == 0` **同时**作为放行判据（`§99` 规程⑧）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
