#!/usr/bin/env python3
"""R50: cln11 的体积轨迹（**读原始浮点，不做字符串截断**）。
⚠ 自查：上一版用 `str(v)[:12]` 打印 ⇒ 把 `1.976e-16` 截成 `1.9762109375`
   ⇒ **凭空造出一个"Vt 从 7.4 掉到 1.0"的假塌陷**。这是第 6 次同类（截断/单位）错，
   必须记账。本版一律 `float()` 读、按 `%.6e` 打印，并**自洽核对**：
   `Vt ≤ V0`（转变体积不能超过盒子）+ `V0` 应与 meta 的盒子尺寸一致。
"""
import csv
import json
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = '_exp/_bk_closed/dry_cln11'
m = json.load(open(os.path.join(D, 'meta.json')))
L = m['plate']['L']
N = m['N']
print('meta: N=%s  plate L=%.1f nm  → Δx=%.2f nm' % (N, L, L / N))
print('盒子体积 = (%.1f nm)³ = %.6e m³' % (L, (L * 1e-9) ** 3))
rows = list(csv.DictReader(open(os.path.join(D, 'series.csv'))))
print('行数 =', len(rows))
print()
print('  %-6s %-14s %-14s %-8s %-7s %-7s %s'
      % ('step', 'V0 (m³)', 'Vt (m³)', 'Vt/V0', 'nslab', 'nf3col', 'Σvols/Vt'))
for r in rows[::4] + [rows[-1]]:
    v0 = float(r['V0'])
    vt = float(r['Vt'])
    vols = [float(x) for x in r['vols'].split('/') if x]
    s = sum(vols)
    print('  %-6s %-14.6e %-14.6e %-8.4f %-7s %-7s %s'
          % (r['step'], v0, vt, (vt / v0 if v0 else float('nan')),
             r['nslab_n'], r['nf3_col'],
             ('%.4f' % (s / vt)) if vt else '-'))
print()
print('=== 单调性 / 塌陷检查（用原始浮点）')
worst = None
prev = None
for r in rows:
    vt = float(r['Vt'])
    if prev is not None and prev > 0:
        rel = (vt - prev) / prev
        if worst is None or rel < worst[1]:
            worst = (r['step'], rel)
    prev = vt
print('  单步最大相对下降: step %s  %+.2f%%' % worst if worst else '  (无)')
print('  末值 Vt = %.6e m³  (V0 = %.6e m³) ⇒ Vt/V0 = %.4f'
      % (float(rows[-1]['Vt']), float(rows[-1]['V0']),
         float(rows[-1]['Vt']) / float(rows[-1]['V0'])))
