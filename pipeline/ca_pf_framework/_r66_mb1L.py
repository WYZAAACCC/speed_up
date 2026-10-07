#!/usr/bin/env python3
"""R66: `mb1L`（6000 步，2 块 × 3 根，gap 5000 nm）的 **P-SA-2 arrest 判据**读数。

判据（`BLOCK_SELFAC.md` §7.1 P-SA-2）：**块在遇到邻居后停止**
⇒ `a_lath(t)` 出现**平台**，而母相仍在（`Vt`/`nf2` 仍在变）。
"""
import csv
import math
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = '_exp/_bk_mb/dry_mb1L'
rows = list(csv.DictReader(open(os.path.join(D, 'series.csv'))))
print('臂 %s  行数 %d  末 step=%s' % (D, len(rows), rows[-1]['step']))


def f(r, k):
    try:
        v = float(r.get(k, ''))
        return v if math.isfinite(v) else float('nan')
    except (TypeError, ValueError):
        return float('nan')


cs = [c for c in ('step', 'a_lath', 'w_lath', 'n_lath', 'Vt', 'nf2', 'nf3',
                  'nslab_n', 'nslab_nu', 'box_touch', 'box_touch_core')
      if c in rows[0]]
print()
print('  ' + ' '.join('%-12s' % c for c in cs))
for i, r in enumerate(rows):
    if i % max(1, len(rows) // 12) and i != len(rows) - 1:
        continue
    out = []
    for c in cs:
        v = r.get(c, '')
        if c.endswith('_lath'):
            v = '%.0f' % (f(r, c) * 1e9)      # 米 → nm
        out.append(str(v)[:12])
    print('  ' + ' '.join('%-12s' % x for x in out))
print()
print('=== P-SA-2 判据（`a_lath` 是否平台化）')
xs = [int(r['step']) for r in rows]
ys = [f(r, 'a_lath') * 1e9 for r in rows]
good = [(x, y) for x, y in zip(xs, ys) if math.isfinite(y) and y > 0]
if len(good) >= 6:
    n = len(good)
    seg = n // 3
    for i in range(3):
        a, b = good[i * seg], good[min((i + 1) * seg, n - 1)]
        if b[0] != a[0]:
            print('  段 %d：step %-5d→%-5d  %+.4f nm/步  (%.0f → %.0f nm)'
                  % (i + 1, a[0], b[0], (b[1] - a[1]) / (b[0] - a[0]), a[1], b[1]))
    print('  **末段速率 / 首段速率 = %.3f**'
          % (((good[-1][1] - good[2 * seg][1]) / (good[-1][0] - good[2 * seg][0]))
             / ((good[seg][1] - good[0][1]) / (good[seg][0] - good[0][0]))
             if good[seg][0] != good[0][0] else float('nan')))
vt = [f(r, 'Vt') for r in rows]
print('  `Vt`：%.3e → %.3e m³（母相 / 体积仍在变 ⇒ 若 a_lath 平台而 Vt 仍增，支持 arrest）'
      % (vt[0], vt[-1]))
