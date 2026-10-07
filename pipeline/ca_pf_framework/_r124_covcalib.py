#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r124_covcalib.py —— **给 `cov` 做长度基线标定**（把 `§100` 的三难解开）。

## 问题（`§100`）

`cov(t=0)` 随 `--plate-L` **单调上升**（L=450 ⇒ 0.44；L=1600 ⇒ ~1.08），
所以 `cov ≥ 0.85` **不能跨 `L` 一刀切** —— 否则所有短板条构型被**误杀**，
而"6 块 + 长板条"在 6–7 µm 盒里**放不下**（`nf2(t=0) > 0`）⇒ 三难。

## 本脚本

对每个 `L`，取**该 `L` 下、且 `nf2(t=0) == 0`（块间真分离）**的臂里 `cov(t=0)` 的
**最大值**作为该 `L` 的**清洁种子基线** `cov_base(L)`（"短板条能做到的最好"），
再算归一化指标

    @@\mathrm{cov\_norm}=\mathrm{cov}(t{=}0)/\mathrm{cov\_base}(L)@@

判据改为 **`cov_norm ≥ 0.95`**（即"与该 `L` 下最好的种子相比，损失不超过 5%"）。

⇒ 这样**短 `L` 的构型不再被误杀**，而真正**播坏了的**（比如同一 `L` 下 β 占比异常高的）
仍会被抓出来。

⚠ 记账：`cov_base(L)` 是**经验基线**（来自本库已有臂），不是解析值；
点数少的 `L` 档（1–3 个）基线**不牢**，要报出来。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
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
            nf2 = None
            p = os.path.join(d, 'series.csv')
            if os.path.exists(p):
                rs = list(csv.DictReader(open(p)))
                nf2 = int(float(rs[0].get('nf2')))
        except Exception:
            continue
        bf = c.get('beta_frac', {}) or {}
        rows.append(dict(tag=os.path.basename(d)[4:], L=ea.get('plate_L'),
                         T=ea.get('plate_T'), W=ea.get('plate_W'),
                         N=meta.get('N'), gap=ea.get('block_gap_nm'),
                         nl=len([x for x in str(ea.get('laths', '')).split(',')
                                 if x.strip()]),
                         cov=c.get('cov', float('nan')),
                         mb=max(bf.values()) if bf else float('nan'),
                         nf2=nf2))
    rows = [r for r in rows if np.isfinite(r['cov']) and r['L']]
    base = {}
    for r in rows:
        if r['nf2'] == 0:                     # 只看**块间真分离**的臂
            base.setdefault(r['L'], []).append(r['cov'])
    print('=' * 108)
    print('_r124 —— `cov` 的长度基线标定（基线只取 `nf2(t=0)==0` 的臂）')
    print('=' * 108)
    print('  %-8s %-6s %-10s %-10s %s' % ('L(nm)', 'n(清洁)', 'cov_base', 'cov 范围', '备注'))
    for L in sorted(base):
        v = sorted(base[L])
        print('  %-8s %-6d %-10.3f %-10s %s'
              % (L, len(v), max(v), '%.3f–%.3f' % (min(v), max(v)),
                 '⚠ 点数少，基线不牢' if len(v) < 3 else ''))
    print()
    print('  ---- 用 `cov_norm = cov / cov_base(L)` 重判（阈值 0.95）----')
    print('  %-14s %-7s %-7s %-7s %-9s %-9s %-8s %s'
          % ('tag', 'L', 'T', 'nf2(0)', 'cov(0)', 'cov_base', 'cov_norm', '判定'))
    ok = []
    for r in sorted(rows, key=lambda x: (x['L'], -x['cov'])):
        b = max(base.get(r['L'], [float('nan')]))
        cn = r['cov'] / b if b == b and b > 0 else float('nan')
        good = (r['nf2'] == 0 and np.isfinite(cn) and cn >= 0.95
                and r['mb'] <= 0.25)
        if good:
            ok.append(r)
        print('  %-14s %-7s %-7s %-9s %-9.3f %-9.3f %-8.3f %s'
              % (r['tag'], r['L'], r['T'], r['nf2'], r['cov'], b, cn,
                 '✅ **合格**' if good else ''))
    print()
    print('  ⇒ **用新口径合格的臂（%d 个）**：' % len(ok))
    for r in ok:
        print('     %-14s N=%-4s L=%-6s W=%-6s T=%-6s gap=%-7s 场数=%d  '
              'cov=%.3f cov_norm=%.3f maxβ=%.2f'
              % (r['tag'], r['N'], r['L'], r['W'], r['T'], r['gap'], r['nl'],
                 r['cov'], r['cov'] / max(base[r['L']]), r['mb']))
    print()
    print('  ⚠ `cov_base(L)` 是**经验**基线（本库已有臂），点数少的档不牢；')
    print('     要把它变成**量具**的一部分，需在**受控单变量**下重扫 `L`（下一轮）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
