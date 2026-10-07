#!/usr/bin/env python3
"""R50: **P1-29** —— `nslab_n` 也会**多读**（一根柱穿出一根板条再穿回来 ⇒ 多算一段）。
判据：真正的"柱里穿过几根板条"应是**去重后的场数** `len(set(runs))`，
      而不是段数 `len(runs)`。
   若 `len(runs)` 显著大于 `M` 而 `len(set(runs))` 接近 `M` ⇒ 确认是多读。
"""
import csv
import glob
import json
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
print('  %-14s %-6s %-10s %-10s %-10s %-10s %s'
      % ('臂', 'M', '末nslab', '去重场数', 'nslab/M', '去重/M', '判定'))
for root in ('_exp/_bk_mb', '_exp/_bk_closed', '_exp/_bk_eng'):
    for d in sorted(glob.glob(root + '/*/')):
        mp, cs = os.path.join(d, 'meta.json'), os.path.join(d, 'series.csv')
        if not (os.path.exists(mp) and os.path.exists(cs)):
            continue
        m = json.load(open(mp))
        la = m.get('laths')
        if not la:
            continue
        M = len(la)
        rows = list(csv.DictReader(open(cs)))
        if not rows:
            continue
        last = rows[-1]
        runs = [int(x) for x in last.get('runs', '').split('/') if x]
        if not runs:
            continue
        ns = len(runs)
        nu = len(set(runs))
        if ns > M:
            verdict = '**nslab 多读 %.2f×**' % (ns / M)
        elif ns == M:
            verdict = 'ok'
        else:
            verdict = 'nslab 少读'
        if nu == M and ns != M:
            verdict += '  ⇒ 去重后 == M ✅'
        print('  %-14s %-6s %-10s %-10s %-10.2f %-10.2f %s'
              % (os.path.basename(d.rstrip('/')), M, ns, nu, ns / M, nu / M, verdict))
print()
print('★ 若多数臂满足 `去重场数 == M` 而 `nslab_n > M`，则 V-1 的第 1 条')
print('  应改用**去重场数**（`len(set(runs))`），否则好块也会被判 FAIL。')
