#!/usr/bin/env python3
"""R53: **机理核对** —— `M(n)` 与 `dG(n)` 是不是反相关（§38 的假设）。

若 `M(n)` 给尖端 9 倍优势，而实测 `v_a/v_w` 只有 1.24–1.48，
则必然有 `dG(tip)/dG(side) ≈ 1.24/9 ≈ 0.14` 量级的反向补偿。
本脚本直接用**已落盘**的列核对，不跑新仿真。
"""
import csv
import math
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
B_H, B_W = 6.477, 2.3
# 各面族"标称法向"的 M/M0（用变体 1 的 n*/w/a；a·n* = -0.127）
MREL = {
    'tip':  math.exp(-B_H * 0.127 ** 2 - B_W * 0.0),      # a 方向
    'side': math.exp(-B_H * 0.0 - B_W * 1.0),             # w 方向
    'wide': math.exp(-B_H * 1.0 - B_W * 0.0),             # n* 方向（惯习面法向）
}
for arm in ('dry_mb1s62', 'dry_mb1s'):
    p = '_exp/_bk_mb/%s/series.csv' % arm
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p)))
    def g(r, k):
        try:
            v = float(r.get(k, ''))
            return v if math.isfinite(v) else float('nan')
        except (TypeError, ValueError):
            return float('nan')
    # 取中段（500–1500）逐行平均，避开 t=0 的瞬态
    seg = [r for r in rows if 500 <= int(r['step']) <= 1500]
    print('=== %s   取 step 500–1500 共 %d 行' % (arm, len(seg)))
    print('  %-7s %-10s %-13s %-13s %-13s %s'
          % ('面族', 'M/M0', 'dG 中位', '|v|·dt (nm/步)', 'dG/M 归一', 'n 胞'))
    base = None
    vals = {}
    for tag in ('tip', 'side', 'wide'):
        dg = [g(r, 'dG_%s' % tag) for r in seg]
        dg = [x for x in dg if math.isfinite(x)]
        vv = [g(r, 'v_%s_nabs' % tag) for r in seg]
        vv = [x for x in vv if math.isfinite(x)]
        nn = [g(r, 'n_%s' % tag) for r in seg]
        nn = [x for x in nn if math.isfinite(x)]
        if not dg:
            print('  %-7s （缺列）' % tag)
            continue
        dgm = sum(dg) / len(dg)
        vvm = sum(vv) / len(vv) if vv else float('nan')
        vals[tag] = (MREL[tag], dgm, vvm)
        print('  %-7s %-10.4f %-13.4e %-13.4f %-13.4e %s'
              % (tag, MREL[tag], dgm, vvm, dgm / MREL[tag],
                 ('%.0f' % (sum(nn) / len(nn))) if nn else '-'))
    if 'tip' in vals and 'side' in vals:
        mt, dt_, vt = vals['tip']
        ms, ds_, vs = vals['side']
        print()
        print('  **`M(tip)/M(side)` = %.2f 倍**（设计：尖端该快这么多）' % (mt / ms))
        print('  **`dG(tip)/dG(side)` = %.3f 倍**（实测的驱动比）' % (dt_ / ds_))
        print('  **乘积 `v(tip)/v(side)` = %.2f 倍**（实测的面速度比）' % (vt / vs))
        print('  ⇒ 若 `dG` 比 < 1 且 `M` 比 ≫ 1 ⇒ **两者反相关、互相抵消**'
              if dt_ / ds_ < 1 else '  ⇒ `dG` 同向 ⇒ 不抵消')
    print()
