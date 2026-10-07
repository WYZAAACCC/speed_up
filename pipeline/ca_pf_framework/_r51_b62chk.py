#!/usr/bin/env python3
"""R51: 方案 B 的**初始接触检查** —— 两块在 t=0 不能接触（否则是"初始混杂"，读数不可用）。
判据（`BLOCK_SELFAC.md` §7.2 预登记）：t=0 的 `nf2` 必须为 0（异变体界面数）。
"""
import csv
import os
import sys

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
p = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_b62/series.csv'
if not os.path.exists(p):
    print('（还没写出 CSV）')
    raise SystemExit(1)
rows = list(csv.DictReader(open(p)))
print('行数 %d' % len(rows))
cs = [c for c in ('step', 'nslab_n', 'nf3_col', 'nf2', 'f2_area_m2', 'nf3',
                  'box_touch', 'Vt', 'M') if c in rows[0]]
print('  ' + ' '.join('%-12s' % c for c in cs))
for r in rows[:4]:
    print('  ' + ' '.join('%-12s' % str(r.get(c, ''))[:12] for c in cs))
print()
r0 = rows[0]
try:
    nf2_0 = float(r0.get('nf2', 'nan'))
except (TypeError, ValueError):
    nf2_0 = float('nan')
print('t=0 的 nf2 = %s' % r0.get('nf2', '(无此列)'))
if nf2_0 == 0:
    print('**PASS**：两块在 t=0 **不接触** ⇒ 不是初始混杂 ✅')
elif nf2_0 != nf2_0:
    print('⚠ 无法判定（缺列或非数）')
else:
    print('**FAIL**：t=0 就有 %g 个异变体界面 ⇒ **初始混杂**，P-SA-2 读数不可用 ❌' % nf2_0)
