#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_traj.py <absdf> <nstep> [N] --- 打印 f(t) 轨迹（verbose），用于诊断是否到平台。
   ★ 不同 |df| 必须用**同一个 nstep**（dt 由 suggest_dt 按总驱动定，与 |df| 几乎无关
     => 同 nstep = 同总时间，才是同一时刻的比较）。"""
import sys
import numpy as np
import windowB_surface as W
absdf = float(sys.argv[1])
ns = int(sys.argv[2]) if len(sys.argv) > 2 else 300
N = int(sys.argv[3]) if len(sys.argv) > 3 else 32
print('#### absdf=%.2fe8 nstep=%d N=%d' % (absdf, ns, N), flush=True)
out = W.M2_twelve_variants(N=N, nstep=ns, df=absdf * 1e8, probe=0, quiet=False)
print('#### FINAL f_trans=%.6f band=%d ok=%d' % (out['f_trans'], out['band'], out['band_ok']), flush=True)
