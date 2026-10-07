#!/usr/bin/env python3
"""R51: **实测 t=0 播种几何** —— 直接量每根场的包围盒/质心/尺寸，判 P1-30 在哪一环。
不看日志、不推理：只从落盘的 `region` 量。
"""
import glob
import os
import sys

import numpy as np

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_b62r'
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
if not snaps:
    print('%s: 还没有快照' % D)
    raise SystemExit(1)
z = np.load(snaps[0])
reg = z['region']
N = int(z['N'])
L = float(z['L'])
dx = L / N
NM = 1e9                       # ⚠ 本脚本第一版**忘了把米换成 nm** ⇒ 所有读数打成 0
print('臂 %s  首快照 step=%s  N=%d  盒=%.0f nm  Δx=%.2f nm'
      % (D, z['step'], N, L * NM, dx * NM))
print('vmap:', dict(zip([int(x) for x in z['vmap_keys']],
                        [int(x) for x in z['vmap_vals']])))
print()
print('  %-4s %-8s %-24s %-24s %-24s %s'
      % ('场', '体素', '质心 (nm)', '包围盒 min (nm)', '包围盒 max (nm)', '尺寸 (nm)'))
cen = {}
bb = {}
for k in sorted({int(x) for x in np.unique(reg)} - {0}):
    m = (reg == k)
    n = int(m.sum())
    if n == 0:
        continue
    idx = np.argwhere(m)
    c = idx.mean(0) * dx * NM * NM
    lo = idx.min(0) * dx * NM
    hi = (idx.max(0) + 1) * dx * NM
    cen[k] = c
    bb[k] = (lo, hi)
    print('  %-4d %-8d %-24s %-24s %-24s %s'
          % (k, n, np.array2string(c, precision=0, suppress_small=True),
             np.array2string(lo, precision=0, suppress_small=True),
             np.array2string(hi, precision=0, suppress_small=True),
             np.array2string(hi - lo, precision=0, suppress_small=True)))
print()
# 按变体分块（vmap: 1,1,1,2,2,2 ⇒ 场 1-3 = 块A, 场 4-6 = 块B）
vm = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
blk = {}
for k, v in vm.items():
    blk.setdefault(v, []).append(k)
print('=== 每块的合并包围盒与质心')
bc = {}
for v, fids in sorted(blk.items()):
    m = np.isin(reg, [f for f in fids if f in cen])
    if not m.any():
        continue
    idx = np.argwhere(m)
    c = idx.mean(0) * dx * NM * NM
    lo, hi = idx.min(0)*dx*NM, (idx.max(0)+1)*dx*NM
    bc[v] = c
    print('  块 V%d（场 %s）：质心 %s  包围盒 %s … %s  尺寸 %s'
          % (v, fids, np.array2string(c, precision=0, suppress_small=True),
             np.array2string(lo, precision=0, suppress_small=True),
             np.array2string(hi, precision=0, suppress_small=True),
             np.array2string(hi - lo, precision=0, suppress_small=True)))
if len(bc) >= 2:
    vs = sorted(bc)
    d = np.linalg.norm(bc[vs[0]] - bc[vs[1]])
    print()
    print('  **实测两块质心距 = %.0f nm**' % d)
    print('  两块包围盒在各轴上是否重叠:')
    for a in range(3):
        ov = min(bb[max(blk[vs[0]])][1][a], bb[max(blk[vs[1]])][1][a]) - \
             max(bb[min(blk[vs[0]])][0][a], bb[min(blk[vs[1]])][0][a])
        print('     轴 %s : 重叠 %.0f nm' % ('xyz'[a], ov))
