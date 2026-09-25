#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t21b8_run.py <alpha> <t_cool> <t_hold> <tag> [N]
  跑一次 B1 athermal（降温 + 可选保温），把轨迹写 _t21b8_<tag>.json。"""
import json
import sys
import time

import numpy as np

import windowB_km as K
from windowB_b1 import B1Athermal

alpha = float(sys.argv[1])
t_cool = float(sys.argv[2])
t_hold = float(sys.argv[3])
tag = sys.argv[4]
N = int(sys.argv[5]) if len(sys.argv) > 5 else 32
import os
T_END = float(os.environ.get("T21B_TEND", "350"))
dx = 1e-8
V = (N * dx) ** 3

# v0 由**模型自己的饱和分数**反解（数据：_t21b_scan3.csv，12 预置晶核、t=8e-6）
f_sat = None
try:
    for ln in open('_t21b_scan3.csv').read().strip().split(chr(10))[1:]:
        p = ln.split(',')
        if len(p) == 9 and abs(float(p[1]) - 0.8e8) < 1e-6 and float(p[2]) > 7e-6:
            f_sat = float(p[5])
except Exception:
    pass
if f_sat is None:
    f_sat = 0.9674
    print('   (warn) 用默认 f_sat=0.9674')
v0 = K.v0_from_saturation(f_sat, 12, V)
print('   f_sat=%.4f => v0=%.4e m3 (v0/V=%.3f)' % (f_sat, v0, v0 / V), flush=True)

t0 = time.time()
b = B1Athermal(N=N, dx=dx, alpha=alpha, v0=v0)
b.run(t_cool=t_cool, t_hold=t_hold, T_end=T_END)
secs = time.time() - t0
out = dict(alpha=alpha, t_cool=t_cool, t_hold=t_hold, N=N, v0=v0, f_sat=f_sat,
           k=b.k_used, secs=secs, **{k: list(map(float, vv)) for k, vv in b.hist.items()})
json.dump(out, open('_t21b8_%s.json' % tag, 'w'))
print('   %s: k=%d f_end=%.4f N_end=%d secs=%.1f' %
      (tag, b.k_used, b.hist['f'][-1], b.hist['n'][-1], secs), flush=True)
