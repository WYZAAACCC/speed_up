#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r121_scan3read.py —— R120 双判据扫描判读。

判据（`§99` 新增规程⑧）：
  **块间** `nf2(t=0) == 0`；**块内** `cov(t=0) ≥ 0.85` 且每对 β 占比 ≤ 0.25。
参照（已实测的合格基线）：R75 `dry_mb2fp10` → `cov(t=0) = 1.079`、β = 0.15；
                              R77 `dry_mo1fp10` → `cov(t=0) = 0.958`、β = 0.15。
"""
from __future__ import annotations

import csv
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
TAGS = ['t1N96L800', 't1N96L1000', 't1N112L1000', 't1N112L800',
        't2N128L1600', 't2N128L1200', 't3N128L1000', 't3N112L1200']


def r(x, n=1):
    return ('%.*f' % (n, x)) if isinstance(x, float) and np.isfinite(x) else str(x)


def main():
    print('=' * 116)
    print('_r121 —— R120 双判据判读（块间 `nf2(t=0)==0`；块内 `cov(t=0)>=0.85`）')
    print('=' * 116)
    print('  %-13s %-5s %-6s %-6s %-6s %-6s %-9s %-8s %-9s %s'
          % ('tag', 'N', 'L', 'W', 'T', 'gap', 'nf2(t=0)', 'cov(0)',
             'maxβ(0)', '判定'))
    ok = []
    for t in TAGS:
        d = os.path.join(MB, 'dry_' + t)
        p = os.path.join(d, 'series.csv')
        mj = os.path.join(d, 'meta.json')
        if not os.path.exists(mj):
            print('  %-13s （未跑）' % t)
            continue
        meta = json.load(open(mj))
        ea = meta.get('exp_args', {}) or {}
        nf2, cov, mb = None, None, None
        if os.path.exists(p):
            rows = list(csv.DictReader(open(p)))
            try:
                nf2 = int(float(rows[0].get('nf2')))
            except (TypeError, ValueError):
                nf2 = None
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'snap_(\d+)', q).group(1)))
        if fs:
            try:
                c = BM.snapshot_coverage(np.load(fs[0]))
                cov = c.get('cov', float('nan'))
                bf = c.get('beta_frac', {}) or {}
                mb = max(bf.values()) if bf else float('nan')
            except Exception as e:
                print('     ⚠ cov 失败：%s' % str(e)[:60])
        good = (nf2 == 0 and cov is not None and np.isfinite(cov)
                and cov >= 0.85 and mb is not None and np.isfinite(mb)
                and mb <= 0.25)
        if good:
            ok.append((t, ea.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                       ea.get('plate_T'), ea.get('block_gap_nm')))
        print('  %-13s %-5s %-6s %-6s %-6s %-6s %-9s %-8s %-9s %s'
              % (t, meta.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                 ea.get('plate_T'), ea.get('block_gap_nm'), nf2,
                 r(cov, 3) if cov is not None else '?',
                 r(mb, 2) if mb is not None else '?',
                 '✅ **双判据通过**' if good else '❌'))
    print()
    if ok:
        print('  ⇒ **合格构型（%d 个）：**' % len(ok))
        for t, N, L, W, T, g in ok:
            print('     %-13s N=%s L=%s W=%s T=%s gap=%s' % (t, N, L, W, T, g))
        print('     ⇒ 用它的参数跑自协调三臂。')
    else:
        print('  ⇒ ⚠ 本批没有双判据全过的 ⇒ 下一轮按"块内差多少"调 T（格点相位）与 gap。')
    print()
    print('  参照基线：R75 `dry_mb2fp10` cov(t=0)=**1.079** β=0.15；'
          'R77 `dry_mo1fp10` cov(t=0)=**0.958** β=0.15')
    print('  不合格例：R110（L=600/W=350/**T=510**）cov(t=0)=**0.527** β=0.26–0.33')
    return 0


if __name__ == '__main__':
    sys.exit(main())
