#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ar.py --- ★★★ 长宽比（**三个方向都要**）+ 惯习轴对照 + 种子对照

## 为什么要三个方向（§206/§207 的教训）
板条是**扁的**：长 ≫ 宽 ≫ 厚。**只报两个方向算不出正确的长宽比**。
* 上次我只报了 PCA 第 1/2 主轴 ⇒ **缺厚度方向**；
* 而上一次（§84）我报的"长度"其实是**沿 `a_ax` 的包围盒跨度**，**不是板条长轴** ⇒ 两次都不完整。

## 本工具（**一次算全**）
对每个场：
1. **PCA 三主轴**的长度（`p1 ≥ p2 ≥ p3`）——**真实形状**；
2. **沿惯习轴** `a_ax` / `w_ax` / `n_hab` 的跨度 ——**物理标签方向**；
3. **长宽比**：`p1/p2`、`p1/p3`、`p2/p3`；
4. **与种子对照**：`plate_L/W/T` = 1000/500/510 nm。
"""
import glob
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5H3'
DX = 62.5
SEED = dict(L=1.000, W=0.500, T=0.510)      # µm（plate_L/W/T，引擎配置逐字）
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
P = snaps[-1]
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    a_ax = np.asarray(z['a_ax'], float) if 'a_ax' in z.files else None
    w_ax = np.asarray(z['w_ax'], float) if 'w_ax' in z.files else None
    n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None

print('=' * 104)
print('★ 长宽比（三方向）：%s   dx=%.1f nm   种子 plate_L/W/T = %.0f/%.0f/%.0f nm'
      % (P.split('/')[-1], DX, SEED['L']*1000, SEED['W']*1000, SEED['T']*1000))
print('=' * 104)
if a_ax is not None:
    print('  惯习轴: a_ax=%s  w_ax=%s  n_hab=%s'
          % (np.round(a_ax, 3), np.round(w_ax, 3), np.round(n_hab, 3)))
print()
print('  %-5s %7s | %-19s | %-19s | %s' %
      ('场', '体素', 'PCA p1/p2/p3 (µm)', '惯习 a/w/n (µm)', '长宽比 p1/p2  p1/p3'))
print('  ' + '-' * 96)

rows = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    idx = np.argwhere(reg == k).astype(np.float64)
    if idx.shape[0] < 8:
        continue
    c = idx - idx.mean(0)
    try:
        w, v = np.linalg.eigh(c.T @ c)
    except Exception:
        continue
    # 主轴从大到小
    order = np.argsort(w)[::-1]
    p = []
    for j in order:
        ax = v[:, j]
        pr = c @ ax
        p.append(float(pr.max() - pr.min() + 1) * DX / 1000.0)
    hab = []
    for ax in (a_ax, w_ax, n_hab):
        if ax is None:
            hab.append(np.nan); continue
        pr = c @ (ax / (np.linalg.norm(ax) + 1e-300))
        hab.append(float(pr.max() - pr.min() + 1) * DX / 1000.0)
    ar12 = p[0] / max(p[1], 1e-9)
    ar13 = p[0] / max(p[2], 1e-9)
    rows.append(dict(k=k, n=idx.shape[0], p=p, hab=hab, ar12=ar12, ar13=ar13))
    print('  %-5d %7d | %6.3f/%6.3f/%6.3f | %6.3f/%6.3f/%6.3f | %6.2f  %6.2f'
          % (k, idx.shape[0], p[0], p[1], p[2], hab[0], hab[1], hab[2], ar12, ar13))

print()
print('  ── 统计（%d 个场）──' % len(rows))
for name, key in (('p1（长）', 0), ('p2（宽）', 1), ('p3（厚）', 2)):
    v = np.array([r['p'][key] for r in rows])
    print('    %-10s 中位 %6.3f µm   范围 [%6.3f, %6.3f]' % (name, np.median(v), v.min(), v.max()))
a12 = np.array([r['ar12'] for r in rows]); a13 = np.array([r['ar13'] for r in rows])
print('    **长宽比 p1/p2**  中位 **%.2f**   范围 [%.2f, %.2f]' % (np.median(a12), a12.min(), a12.max()))
print('    **长厚比 p1/p3**  中位 **%.2f**   范围 [%.2f, %.2f]' % (np.median(a13), a13.min(), a13.max()))
print()
print('  ── 与**种子**对照（种子 L/W/T = 1.000/0.500/0.510 ⇒ 长宽比 2.0、长厚比 1.96）──')
print('    种子是"盘"（长=2×宽、厚≈宽）—— **不是**长板条。')
print('    ⇒ 若实测 long/thick 显著 > 2 ⇒ **确实长成了板条**；若 ≈2 ⇒ 仍是种子形状。')
print()
print('  ── 判读（**预先写死**）──')
med13 = float(np.median(a13))
if med13 > 3.0:
    print('    ✅ **长厚比中位 %.2f > 3** ⇒ **形貌已是"板条"**（种子只有 1.96）' % med13)
elif med13 > 2.0:
    print('    ⚠ 长厚比中位 %.2f ⇒ **比种子略扁，但还不到典型板条**' % med13)
else:
    print('    ❌ 长厚比中位 %.2f ⇒ **仍接近种子形状**' % med13)
