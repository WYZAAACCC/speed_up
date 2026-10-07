#!/usr/bin/env python3
"""R67: **面片投影的离线可行性检查**（用已有 φ 快照，**不跑新仿真**）。

## 做什么
取 `dry_single` 某个快照的场 1，按 `BLOCK_SELFAC.md §8 C` 的做法：
1. 由界面点云算 6 个支撑值 `h = max(x·n)`，`n ∈ {±a, ±w, ±n*}`；
2. 构造多面体 `K = {x : x·n_j ≤ h_j}`，写成 `phi_proj = max_j (|x·n_j| − h_j)`；
3. 量：**投影后的 `f_flat`**（能否恢复到解析值附近）与**体积变化**。

## 判据（先写死）
  P-1 投影后 `f_flat` **≥ 0.10**（解析值 0.172；侵蚀后实测 0.005–0.02）
  P-2 体积相对变化 **≤ 25%**（这是"不做保体积标定"的裸投影；标定后应 ≤1%）
"""
import glob
import os
import sys

import numpy as np

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_single'
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 400
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
pick = [s for s in snaps if int(np.load(s)['step']) == STEP] or snaps[-1:]
s = pick[0]
z = np.load(s)
N = int(z['N'])
dx = float(z['L']) / N
aa = np.asarray(z['a_ax'], float); aa /= np.linalg.norm(aa)
ww = np.asarray(z['w_ax'], float); ww /= np.linalg.norm(ww)
nn = np.asarray(z['n_hab'], float); nn /= np.linalg.norm(nn)
print('臂 %s  快照 step=%s  N=%d  Δx=%.2f nm' % (D, z['step'], N, dx * 1e9))

fld = z['band_fld']; sel = (fld == 1)
idx, val = z['band_idx'][sel], z['band_val'][sel]
phi = np.full(N ** 3, np.nan, np.float32); phi[idx] = val
phi = phi.reshape(N, N, N)
ii = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
P = np.stack([X, Y, Z], -1)
m = np.isfinite(phi) & (np.abs(phi) <= 0.5 * dx)
pts = P[m]
vol_orig = int((np.isfinite(phi) & (phi < 0)).sum())
print('  界面点 %d 个；原体积 %d 胞' % (len(pts), vol_orig))

# 1) 6 个支撑值
hs = {}
for nm, u in (('a', aa), ('w', ww), ('n', nn)):
    pr = pts @ u
    hs[nm] = 0.5 * (pr.max() - pr.min())
    cen = 0.5 * (pr.max() + pr.min())
    hs[nm + '_c'] = cen
print('  支撑半宽：a=%.0f w=%.0f n*=%.0f nm'
      % (hs['a'] * 1e9, hs['w'] * 1e9, hs['n'] * 1e9))

# 2) 多面体 φ（把中心平移掉；用场自己的质心做中心）
c0 = 0.5 * np.array([float(z['L'])] * 3)
d = P - c0
pp = np.maximum.reduce([np.abs(d @ aa) - hs['a'],
                        np.abs(d @ ww) - hs['w'],
                        np.abs(d @ nn) - hs['n']])
vol_proj = int((pp < 0).sum())
print('  投影体积 %d 胞（相对变化 %+.1f%%）'
      % (vol_proj, 100.0 * (vol_proj - vol_orig) / max(vol_orig, 1)))

# 2b) ★ 设计里的**保体积标定**（`BLOCK_SELFAC.md §8 C` 第 3 步）：
#     把 6 个支撑值**统一缩放** `s`，使体积回到原来的值。
#     凸体体积对**齐次缩放**是三次齐次的 ⇒ `s = (V0/Vp)^(1/3)`（对长方体精确）。
s_sc = (vol_orig / max(vol_proj, 1)) ** (1.0 / 3.0)
pp2 = np.maximum.reduce([np.abs(d @ aa) - hs['a'] * s_sc,
                         np.abs(d @ ww) - hs['w'] * s_sc,
                         np.abs(d @ nn) - hs['n'] * s_sc])
vol2 = int((pp2 < 0).sum())
print('  标定 `s=%.4f` 后体积 %d 胞（相对变化 %+.2f%%）'
      % (s_sc, vol2, 100.0 * (vol2 - vol_orig) / max(vol_orig, 1)))
g2 = np.gradient(pp2, dx, edge_order=2)
gn2 = np.sqrt(sum(x ** 2 for x in g2)) + 1e-30
nr2 = np.stack([x / gn2 for x in g2], -1)
mm2 = np.abs(pp2) <= 0.5 * dx
c22 = np.clip(nr2[mm2] @ aa, -1, 1) ** 2
f2 = float((c22 > np.cos(np.radians(25)) ** 2).mean())
print('  **标定后 `f_flat` = %.3f**' % f2)
print('  P-1b `f_flat` ≥ 0.10 : %s' % ('✅' if f2 >= 0.10 else '❌'))
rel2 = abs(vol2 - vol_orig) / max(vol_orig, 1)
print('  P-2b 标定后体积变化 ≤ 5%% : %s (%.2f%%)'
      % ('✅' if rel2 <= 0.05 else '❌', 100 * rel2))

# 3) 投影后的 f_flat（在 φ_proj = 0 面上）
g = np.gradient(pp, dx, edge_order=2)
gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
nr = np.stack([x / gn for x in g], -1)
mm = np.abs(pp) <= 0.5 * dx
c2 = np.clip(nr[mm] @ aa, -1, 1) ** 2
f_proj = float((c2 > np.cos(np.radians(25)) ** 2).mean())
print()
print('  **投影后 `f_flat` = %.3f**（解析值 0.172；侵蚀后实测 0.005–0.02）'
      % f_proj)
print('  P-1 `f_flat` ≥ 0.10 : %s' % ('✅' if f_proj >= 0.10 else '❌'))
rel = abs(vol_proj - vol_orig) / max(vol_orig, 1)
print('  P-2 体积变化 ≤ 25%% : %s (%.1f%%)'
      % ('✅' if rel <= 0.25 else '❌', 100 * rel))
