#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_proj2.py --- D17 探针（单步级）：把 `proj` 路径的**每个中间量**逐胞量出来，
   与解析期望对照，定位"少数胞爆掉"的确切来源。"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from scipy.ndimage import distance_transform_edt                # noqa: E402
from T19_verify_proj import plane_setup                         # noqa: E402

DF, MOB = 2.0e8, 1.0e-9
EXACT = MOB * DF

N, dx = 60, 50e-9
L = N * dx
n_h = np.array([1.0, 2.0, 3.0]) / np.sqrt(14.0)
g, d0 = plane_setup(N, dx, n_h, L)
dt = 0.15 * dx / EXACT

ph = g.phi
karr = np.argmin(ph, axis=0)
larr = 1 - karr
pha = np.take_along_axis(ph, karr[None], 0)[0]
phb = np.take_along_axis(ph, larr[None], 0)[0]
sigma = np.where(karr < larr, 1.0, -1.0)

d = sigma * (pha - phb)
gd = np.gradient(d, dx, edge_order=2)
gn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
n_or = [t / gn for t in gd]

phiw = np.min(ph, axis=0)
iface = (np.abs(phiw) <= 2.0 * dx) & (np.abs(np.full(ph.shape[1:], EXACT)) > 0)
print('iface 胞数 = %d ; |phiw| min/p50 = %.4g / %.4g (= %.3f dx / %.3f dx)'
      % (iface.sum(), np.abs(phiw)[iface].min(), np.median(np.abs(phiw)[iface]),
         np.abs(phiw)[iface].min() / dx, np.median(np.abs(phiw)[iface]) / dx))
dist = distance_transform_edt(~iface)
ind = distance_transform_edt(~iface, return_distances=False, return_indices=True)
band = dist <= 20
print('band 胞数 = %d ; iface∩band = %d' % (band.sum(), (iface & band).sum()))

# v_canon（这里恒 = −0.2）
vcanon_field = sigma * (MOB * (np.where(karr == 1, DF, -DF)))
print('vcanon 唯一值 = %s   （应恒 = −0.2）'
      % np.unique(np.round(vcanon_field, 6))[:4])
v_at = np.where(iface, vcanon_field, 0.0)
coef = np.where(band, sigma * v_at[tuple(ind)], 0.0)
vc_ext = sigma * coef
print('coef 唯一值（band 内）= %s' % np.unique(np.round(coef[band], 6))[:4])
print('vc_ext 唯一值（band 内）= %s （应恒 = −0.2）'
      % np.unique(np.round(vc_ext[band], 6))[:4])

V = [vc_ext * n_or[i] for i in range(3)]
Vmag = np.sqrt(sum(t ** 2 for t in V))
print('|V|（band 内） p1/p50/p99/max = %.6f / %.6f / %.6f / %.6f （应恒 = 0.2）'
      % tuple(np.percentile(Vmag[band], [1, 50, 99]).tolist() + [Vmag[band].max()]))
print('  |V|≠0.2 的胞数 = %d / %d（%.4f%%）'
      % (int((np.abs(Vmag - EXACT) > 1e-9 * EXACT).sum()), band.sum(),
         100.0 * (np.abs(Vmag - EXACT) > 1e-9 * EXACT).sum() / max(band.sum(), 1)))
bad = band & (np.abs(Vmag - EXACT) > 1e-9 * EXACT)
if bad.any():
    pos = np.argwhere(bad)
    print('     这些胞：dist p50=%.1f  |phiw| p50=%.3f dx  |∇d| p50=%.3f'
          % (np.median(dist[bad]), np.median(np.abs(phiw)[bad]) / dx,
             np.median(gn[bad])))
    print('     位置 x∈[%d,%d] y∈[%d,%d] z∈[%d,%d]（盒 %d）'
          % (pos[:, 0].min(), pos[:, 0].max(), pos[:, 1].min(), pos[:, 1].max(),
             pos[:, 2].min(), pos[:, 2].max(), N))

# 手工做一步 proj 推进（对两个场）
Vcopy = [t.copy() for t in V]
new = {}
for k in (0, 1):
    vnk = coef * (np.where(karr == k, 1.0, 0.0) - np.where(larr == k, 1.0, 0.0))
    upd = dt * W.upwind_flux_vec(ph[k], Vcopy, dx, order=1)
    new[k] = ph[k] - np.where(np.abs(vnk) > 0, upd, 0.0)
    print('场 %d：vnk≠0 胞数 = %d ; |Δφ|/dx 在 band 内 p50/p99/max = %.4g / %.4g / %.4g'
          % (k, int((vnk != 0).sum()),
             np.median(np.abs(upd)[band]) / dx,
             np.percentile(np.abs(upd)[band], 99) / dx,
             np.abs(upd)[band].max() / dx))
# 精确解：φ_1 应平移 v t
phi1_ex = d0 - EXACT * dt
r1 = new[1] - phi1_ex
nz = np.abs(r1) > 1e-9 * dx
print('一步后 φ_1 残差：>1e-9dx 的胞数 = %d ; max = %.4g dx' % (nz.sum(), np.abs(r1).max() / dx))
if nz.any():
    pos = np.argwhere(nz)
    print('  位置 x∈[%d,%d] y∈[%d,%d] z∈[%d,%d] ; dist p50=%.1f ; |phiw| p50=%.3f dx'
          % (pos[:, 0].min(), pos[:, 0].max(), pos[:, 1].min(), pos[:, 1].max(),
             pos[:, 2].min(), pos[:, 2].max(),
             np.median(dist[nz]), np.median(np.abs(phiw)[nz]) / dx))
    print('  这些胞的 Vmag p50 = %.4g（应为 0.2）；vnk≠0 的比例 = %.4f'
          % (np.median(Vmag[nz]),
             float((np.abs(coef[nz]) > 0).mean())))
    # 是不是"一侧被推进、另一侧没有"？
    print('  karr 分布（这些胞）：karr=0 占 %.3f' % float((karr[nz] == 0).mean()))
