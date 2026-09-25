#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_morph.py --- 末态组织的**几何测定 + 文献比对**（读 results_boxB_N080_dx250nm_final.npz）。

测定维度：
  M1 变体体积分数 + 存活变体数         vs 文献：LPBF Ti64 沉积态通常 1-5 个变体主导（Burgers 12 选）
  M2 连通性：每个变体是几块？           vs 物理：一个变体畴应为**一整块**（碎片=数值伪影/形核过多）
  M3 界面密度 S_v 与板片厚 t=2f/S_v     vs 文献：alpha' 板条宽 0.1-2 um（另一套 0.25-0.9 um）
  M4 每个变体畴的长径比（惯性张量半轴） vs 文献：板条/集束长径比 ~10-30（板条级）
  M5 界面**配对面积矩阵** + "相容对"富集 vs 文献：自协调 => 相容变体对显著占优
  M6 界面法向 vs **晶格相容（rank-1 / 最小弹性能）法向**的夹角，随机对照
                                        vs 文献：界面沿 {334}_beta 型惯习/孪生面 => 夹角小
"""
import numpy as np
from scipy import ndimage as ndi

from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants

d = np.load('results_boxB_N080_dx250nm_final.npz')
reg = d['reg']
N = int(d['N'])
dx = float(d['dx'])
V = (N * dx) ** 3
print('=== 末态组织几何测定 ===  N=%d  dx=%.3f um  L=%.1f um  f=%.4f'
      % (N, dx * 1e6, N * dx * 1e6, float(d['f'])))
nv = 12
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()

# ---------- M1 体积分数 ----------
cnt = np.bincount(reg.ravel(), minlength=13).astype(float)
vt = cnt[1:]
alive = [v + 1 for v in range(nv) if vt[v] > 0]
print('\n[M1] 变体体积分数（占全盒）: %s' % ['V%d:%.4f' % (v, cnt[v] / (N ** 3)) for v in alive])
print('     母相 %.4f ; **存活变体 %d / 12**' % (cnt[0] / N ** 3, len(alive)))
print('     文献: LPBF Ti64 沉积态 alpha\' 内常见 1-5 个变体主导【未核实·需检索】；随机形核 12 个则应 ~12 个')

# ---------- M2 连通性 ----------
print('\n[M2] 连通块数（26 邻域）:')
clu = {}
for v in alive:
    lab, n = ndi.label(reg == v, structure=np.ones((3, 3, 3)))
    sz = np.bincount(lab.ravel())[1:]
    clu[v] = (n, int(sz.max()), int((sz > 20).sum()))
for v in alive:
    print('     V%-2d 块数=%3d  最大块=%-7d  >20胞的块=%d' % (v, clu[v][0], clu[v][1], clu[v][2]))

# ---------- M3 界面密度 -> 板片厚 ----------
bonds = 0
for ax in range(3):
    bonds += int((reg != np.roll(reg, -1, axis=ax)).sum())
Sv = bonds * dx ** 2 / V                      # 面积/体积（格点键测度）
f = 1.0 - cnt[0] / N ** 3
print('\n[M3] S_v(格点键测度) = %.4e 1/m  => 板片厚 t = 2f/S_v = %.3f um'
      % (Sv, 2 * f / Sv * 1e6))
print('     文献: alpha\' 板条宽 0.25-0.9 um（另一套 0.1-2 um）; 板条长 1-20 um; 片层间距 ~1 um')
print('     ⚠ 本配置 12 个晶核 / (20um)^3 => 对应**集束/变体群尺度(5-50 um)**，不是板条尺度')

# ---------- M4 各变体畴的长径比 ----------
print('\n[M4] 各变体畴的惯性张量半轴比（长:短；越大越像片/针状）:')
X, Y, Z = np.meshgrid(*(np.arange(N) for _ in range(3)), indexing='ij')
for v in alive:
    m = (reg == v)
    n = int(m.sum())
    if n < 50:
        print('     V%-2d 胞数太少(%d)' % (v, n))
        continue
    p = np.stack([X[m], Y[m], Z[m]], 1).astype(float)
    p -= p.mean(0)
    ev = np.linalg.eigvalsh(np.cov(p.T))
    ev = np.sort(np.clip(ev, 1e-30, None))[::-1]
    print('     V%-2d 胞数=%-7d 半轴比 (长:中:短) = 1 : %.2f : %.2f   => 长:短 = %.1f'
          % (v, n, (ev[1] / ev[0]) ** .5, (ev[2] / ev[0]) ** .5, (ev[0] / ev[2]) ** .5))
print('     文献: 板条 长:宽 ~10-30（板条级）；集束/群 ~1-3（块状）')

# ---------- M5 界面配对面积 ----------
pair = {}
for ax in range(3):
    a = reg
    b = np.roll(reg, -1, axis=ax)
    sel = (a != b)
    ka, kb = a[sel], b[sel]
    for x, y in zip(ka.ravel(), kb.ravel()):
        if x == 0 or y == 0:
            continue
        k = (min(x, y), max(x, y))
        pair[k] = pair.get(k, 0) + 1
tot = sum(pair.values())
print('\n[M5] 界面配对（非母相界面）总面积份额 top-8:')
for k, v in sorted(pair.items(), key=lambda t: -t[1])[:8]:
    print('     V%d-V%-2d  %6.2f%%' % (k[0], k[1], 100.0 * v / tot))

# ---------- M6 界面法向 vs 晶格相容法向 ----------
print('\n[M6] 界面法向 vs 各配对的**最小弹性能法向**（rank-1 相容）:')
rng = np.random.default_rng(0)
ns = rng.normal(size=(600, 3))
ns /= np.linalg.norm(ns, axis=1)[:, None]
ncomp = {}
for k in range(1, nv + 1):
    for l in range(k + 1, nv + 1):
        de = eps0[k - 1] - eps0[l - 1]
        best, bn = None, None
        for n in ns:
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', de, _lam_full(C, n), de))
            if best is None or val < best:
                best, bn = val, n
        ncomp[(k, l)] = bn
# 用"平滑指示场"的梯度当界面法向（与模型内部同一做法）
angs, angs_rnd = [], []
for k, v in pair.items():
    if v < 30:
        continue
    chi = ndi.gaussian_filter((reg == k[0]).astype(float), 1.5)
    g = np.array(np.gradient(chi, dx))
    bnd = (chi > 0.2) & (chi < 0.8)
    nn = np.moveaxis(g, 0, -1)[bnd]
    nrm = np.linalg.norm(nn, axis=1)
    nn = nn[nrm > 1e-30] / nrm[nrm > 1e-30][:, None]
    if nn.shape[0] == 0:
        continue
    c = np.abs(nn @ ncomp[k])
    angs.append(np.degrees(np.arccos(np.clip(c, 0, 1))))
    angs_rnd.append(np.degrees(np.arccos(np.clip(np.abs(ns @ ncomp[k]), 0, 1))))
angs = np.concatenate(angs) if angs else np.array([np.nan])
angs_rnd = np.concatenate(angs_rnd) if angs_rnd else np.array([np.nan])
print('     实测界面法向与相容法向夹角: 中位 %.1f deg (n=%d)' % (np.median(angs), angs.size))
print('     随机法向对照             : 中位 %.1f deg' % np.median(angs_rnd))
print('     文献: 板条/孪晶界面沿 {334}_beta 型惯习面 => 与相容法向夹角应显著小于随机')
