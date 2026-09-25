#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_scan.py --- 扫一个 (N, |df|, nstep) 点，量 f_eq，追加到 _t21b_scan.csv。

用法: _t21b_scan.py <absdf> <N> <nstep>       (absdf 用 1e8 J/m3 为单位，正数；内部取 -absdf)

★ 记账（关键，否则 f_eq 读错）：nstep 必须按 |df| 缩放，使**总物理时间相同**
    dt = cfl*dx/(M*|df|)  =>  T = nstep*dt ∝ nstep/|df|
    => 取 nstep = round(K * |df|/1e8) 时 T 与 |df| 无关。
  不同 |df| 用同一个 nstep 会让高驱动点"还没跑完"就记录 f ⇒ 假 f_eq。
列: N, df, nstep, T_total_s, f_trans, f0, band, band_ok, secs
"""
import sys
import time
import os

import numpy as np

absdf = float(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 32
ns = int(sys.argv[3]) if len(sys.argv) > 3 else 120
K = float(os.environ.get('T21B_K', '120'))
if len(sys.argv) <= 3:
    ns = max(60, int(round(K * absdf)))
df = -absdf * 1e8

import windowB_surface as W

t0 = time.time()
out = W.M2_twelve_variants(N=N, nstep=ns, df=df, quiet=True)
secs = time.time() - t0
v = np.asarray(out['v_abs'], float)
f0 = 1.0 - v[0] / v.sum()          # 末态母相 -> 这里只存 1-母相; f0 由 init 诊断给
import os as _os
if not _os.path.exists('_t21b_scan.csv'):
    with open('_t21b_scan.csv', 'w') as f:
        f.write('N,df,nstep,f_trans,band,band_ok,secs' + chr(10))
row = '%d,%.6e,%d,%.6f,%d,%d,%.1f' % (
    N, df, ns, out['f_trans'], out['band'], int(out['band_ok']), secs)
with open('_t21b_scan.csv', 'a') as f:
    f.write(row + chr(10))
print(row, flush=True)
