#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30：打印某个 series.csv 的 dt / cfl_used / f3 列（含 dG_max 反解）。"""
import os
import sys
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

MOB = 1.0e-9
path = sys.argv[1]
dx = float(sys.argv[2]) if len(sys.argv) > 2 else 125.0e-9
DF = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5e8

rows = list(csv.DictReader(open(path)))
print('%-8s %-12s %-12s %-10s %-12s %-10s %-10s %-8s %-8s' %
      ('step', 'dt_s', 'cfl_used', 'dGmax/DF', 'f3_pos_dx', 'f3_area', 'nf3', 'nslab', 'psi'))
for r in rows:
    try:
        dt = float(r['dt']); cfl = float(r['cfl_used'])
        dgm = cfl * dx / (dt * MOB) if dt > 0 else float('nan')
    except Exception:
        dt = cfl = dgm = float('nan')
    print('%-8s %-12.4e %-12.4g %-10.4g %-12s %-10s %-10s %-8s %-8s' %
          (r['step'], dt, cfl, dgm / DF, r.get('f3_pos_dx', ''),
           r.get('f3_area_m2', ''), r.get('nf3', ''), r.get('nslab_n', ''),
           r.get('psi_mean', '')))
