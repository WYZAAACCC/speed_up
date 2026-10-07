#!/usr/bin/env python3
"""R51: **板条三轴尺寸的演化**（决定"板条还能不能算板条"+ 盒子/步数约束）。

⚠⚠ 自查（**第 7 次同类错**）：本脚本第一版用 `str(v)[:11]` 打印，
   而 `n_lath` 的单位是 **米**（`6.301451283263206e-07`）⇒ 截掉指数后读成 "6.301"，
   于是把 **630 nm** 当成了 **6.30 µm**（差 10000 倍）。
   ⇒ 我在 §28 刚写下"数值一律 `float()` 读、`%.6e` 打印"，**同轮就自己违反了**。
   本版：全部 `float()` 读、带单位打印。

## 口径（回定义行确认过，不按名字猜）
`_bk_measure.measure_state` 里
  `out['%s_%d' % (nm, k)] = _linear_extent(m, axes[nm], dx)[0]`，`nm ∈ {n,w,a}`；
`_linear_extent` 用 `_sub_coord(bb, dx)` ⇒ **单位 = `dx` 的单位 = 米**。
CSV 里的 `n_lath/w_lath/a_lath` 是**在位场的中位数**（`_med`，见 `_bk_exp.py:1123`）。
`ths` 是**逐场厚度（nm）**的斜杠串。
"""
import csv
import math
import os
import sys

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_closed/dry_cln11'
rows = list(csv.DictReader(open(os.path.join(D, 'series.csv'))))
print('臂 %s   行数 %d' % (D, len(rows)))


def fnum(r, k):
    try:
        v = float(r.get(k, ''))
        return v if math.isfinite(v) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


xs = [int(r['step']) for r in rows]
cols = {'厚度 n': 'n_lath', '宽度 w': 'w_lath', '长度 a': 'a_lath'}
print()
print('  %-6s %-14s %-14s %-14s %s'
      % ('step', '厚度 n (nm)', '宽度 w (nm)', '长度 a (nm)', 'L/W'))
for i, r in enumerate(rows):
    if i % 6 and i != len(rows) - 1:
        continue
    n, w, a = (fnum(r, v) * 1e9 for v in ('n_lath', 'w_lath', 'a_lath'))
    lw = (a / w) if w else float('nan')
    print('  %-6s %-14.1f %-14.1f %-14.1f %.2f' % (r['step'], n, w, a, lw))
print()
print('=== 全程线性速率（nm/步）与倍率')
for lab, key in cols.items():
    ys = [fnum(r, key) * 1e9 for r in rows]
    good = [(x, y) for x, y in zip(xs, ys) if math.isfinite(y) and y > 0]
    if len(good) < 3:
        print('  %-8s 数据不足' % lab)
        continue
    (x0, y0), (x1, y1) = good[0], good[-1]
    print('  %-8s %8.1f → %8.1f nm   **%+.4f nm/步**   倍率 %.2f×'
          % (lab, y0, y1, (y1 - y0) / (x1 - x0), y1 / y0))
print()
print('=== 长径比（板条的"板条性"）')
lw0 = fnum(rows[0], 'a_lath') / fnum(rows[0], 'w_lath')
lw1 = fnum(rows[-1], 'a_lath') / fnum(rows[-1], 'w_lath')
wt0 = fnum(rows[0], 'w_lath') / fnum(rows[0], 'n_lath')
wt1 = fnum(rows[-1], 'w_lath') / fnum(rows[-1], 'n_lath')
print('  L/W: %.2f → %.2f' % (lw0, lw1))
print('  W/T: %.2f → %.2f' % (wt0, wt1))
print('  ⇒ L/W 掉 %.0f%%；W/T 掉 %.0f%%'
      % (100 * (1 - lw1 / lw0), 100 * (1 - wt1 / wt0)))
print()
print('=== 盒子需求（末态最大单场跨度 vs 盒边长）')
mx = max(fnum(rows[-1], k) for k in ('n_lath', 'w_lath', 'a_lath')) * 1e9
print('  末态最大单场跨度 = %.0f nm = %.2f µm' % (mx, mx / 1000))
