#!/usr/bin/env python3
"""R68c: 把**已过自检**的算子用到**真实（已圆化）**的快照上 —— 判据 P-1b/P-2b。"""
import glob
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
from _r68_facet_op import facet_project_one  # noqa: E402

D = '_exp/_bk_mb/dry_single'
STEP = 400
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
pick = [s for s in snaps if int(np.load(s)['step']) == STEP] or snaps[-1:]
z = np.load(pick[0])
N = int(z['N'])
dx = float(z['L']) / N
aa = np.asarray(z['a_ax'], float)
ww = np.asarray(z['w_ax'], float)
nn = np.asarray(z['n_hab'], float)
fld = z['band_fld']
sel = (fld == 1)
idx, val = z['band_idx'][sel], z['band_val'][sel]
phi = np.full(N ** 3, np.nan, np.float32)
phi[idx] = val
phi = phi.reshape(N, N, N)
print('臂 %s step=%s  Δx=%.2f nm  原体积 %d 胞'
      % (D, z['step'], dx * 1e9, int((np.isfinite(phi) & (phi < 0)).sum())))


def fflat(p):
    g = np.gradient(p, dx, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    nr = np.stack([x / gn for x in g], -1)
    m = np.isfinite(p) & (np.abs(p) <= 0.5 * dx)
    c2 = np.clip(nr[m] @ (aa / np.linalg.norm(aa)), -1, 1) ** 2
    return float((c2 > np.cos(np.radians(25)) ** 2).mean())


print('  投影前 f_flat = %.3f' % fflat(phi))
ph, info = facet_project_one(phi, dx, (nn, aa, ww))
print('  info: v0=%d vp=%d s=%.4f v1=%d' % (info['v0'], info['vp'],
                                            info['s'], info['v1']))
print('  投影后 f_flat = %.3f   （解析值 0.172）' % fflat(ph))
rel = abs(info['v1'] - info['v0']) / max(info['v0'], 1)
print()
print('  P-1b f_flat ≥ 0.10     : %s (%.3f)'
      % ('✅' if fflat(ph) >= 0.10 else '❌', fflat(ph)))
print('  P-2b 体积变化 ≤ 5%%     : %s (%.2f%%)'
      % ('✅' if rel <= 0.05 else '❌', 100 * rel))
