#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b_scan2.py <absdf/1e8> <t_end_s> [N] --- 在**同一物理时刻**量 f。
   列: N,df,t_end,k_used,t_total,f_trans,band,band_ok,secs
   ★ 记账：必须按 t_end 而不是 nstep —— 每步位移被 CFL 钉在 ~0.15dx，dt ∝ 1/dG_max，
     所以同一 nstep ≠ 同一时刻（低驱动 dt 更大 => 虚假领先）。"""
import sys, time, os, numpy as np
a = float(sys.argv[1]); te = float(sys.argv[2]); N = int(sys.argv[3]) if len(sys.argv) > 3 else 32
import windowB_surface as W
t0 = time.time()
out = W.M2_twelve_variants(N=N, t_end=te, df=+a * 1e8, quiet=True)
secs = time.time() - t0
f = '_t21b_scan3.csv'
if not os.path.exists(f):
    open(f, 'w').write('N,df,t_end,k_used,t_total,f_trans,band,band_ok,secs' + chr(10))
row = '%d,%.6e,%.3e,%d,%.3e,%.6f,%d,%d,%.1f' % (N, a*1e8, te, out['k_used'], out['t_total'], out['f_trans'], out['band'], int(out['band_ok']), secs)
open(f, 'a').write(row + chr(10))
print(row, flush=True)
