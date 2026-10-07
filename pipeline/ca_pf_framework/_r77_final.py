#!/usr/bin/env python3
"""R77: R75 多块测试的**终态**判定（严格遵循 §84 的三条硬规程）。

规程：① 数字一律 float() 读 + %.6e 打印（不用 [:N] 截断）；
     ② 跨量比值先看定义（广延 vs 强度）；
     ③ 只读 600 步终态，不读中途值。
"""
import csv
import math
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')


def fnum(r, k):
    try:
        v = float(r.get(k, ''))
        return v if math.isfinite(v) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


print('=== R75 多块测试（2 块 × 3 根、gap 2500、N=96/Δx=62.5）终态')
rows = {}
for t in ('mb2fp0', 'mb2fp10'):
    p = '_exp/_bk_mb/dry_%s/series.csv' % t
    rows[t] = list(csv.DictReader(open(p))) if os.path.exists(p) else []
print('  %-9s %-6s %-8s %-9s %-14s %-14s %-9s %s'
      % ('臂', 'step', 'nslab_n', 'nf3_col', 'nf2(末)', 'nf2单调增', 'core', 'Vt (m³)'))
for t, rr in rows.items():
    if not rr:
        print('  %-9s （无）' % t)
        continue
    last = rr[-1]
    nf = [fnum(r, 'nf2') for r in rr]
    nf = [v for v in nf if math.isfinite(v)]
    mono = all(b >= a for a, b in zip(nf, nf[1:])) if nf else None
    print('  %-9s %-6s %-8s %-9s %-14.6e %-14s %-9s %.6e'
          % (t, last['step'], last['nslab_n'], last['nf3_col'],
             nf[-1] if nf else float('nan'), mono,
             last.get('box_touch_core'), fnum(last, 'Vt')))
print()
print('=== 强度量（可直接对照）')
for t, rr in rows.items():
    if not rr:
        continue
    last = rr[-1]
    print('  %-9s r_selfac = %.6e   （强度量，可直接比）' % (t, fnum(last, 'r_selfac')))
    e, v = fnum(last, 'E_el_J'), fnum(last, 'Vt')
    if v:
        print('  %-9s E_el_J/Vt = %.6e J/m³  （密度；E_el 是广延量）' % (t, e / v))
