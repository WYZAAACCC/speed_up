#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ardist.py --- ★★★★★ 长宽比的**分布**（不只中位）—— 回答"板条长宽比是否正常"

## 为什么（**由实测驱动的补充**）
用户目标写的是「**板条**长宽比要正常」⇒ **中位达标 ≠ 每根都达标**。
实测 `t5N276` step 400 的长宽比范围是 `[**0.74**, 7.28]`（中位 6.24）
⇒ **有一个场只有 0.74**（比等轴还"扁反了"）⇒ **必须看分布。**

## 口径（与既有量具一致，**已过两级对照**）
长 = PCA 第 1 主轴跨度 ；宽 = PCA 第 2 主轴跨度 ；厚 = 沿 `n_hab` 跨度
**⇒ 长宽比 = 长/宽 ；长厚比 = 长/厚**（µm）

## 输出
* 逐场表（长/宽/厚/两个比值）；
* **分布统计**：中位、均值、**< 3 / 3–5 / 5–20 / > 20 各多少场**（真实区间 5–20）；
* **同时报厚度 < 4 胞（250 nm）的场数**（§208：那档不可信）。
"""
import glob
import sys
import numpy as np

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not sn:
    print('  （%s 无快照）' % TAG); sys.exit(0)
P = sn[-1]
st = int(P.split('snap_')[1].replace('.npz', ''))
with np.load(P, allow_pickle=False) as z:
    reg = np.asarray(z['region']).astype(np.int32)
    nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None

rows = []
for k in sorted(int(x) for x in np.unique(reg) if x != 0):
    idx = np.argwhere(reg == k).astype(np.float64)
    if idx.shape[0] < 8:
        continue
    c = idx - idx.mean(0)
    w, v = np.linalg.eigh(c.T @ c)
    o = np.argsort(w)[::-1]
    L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
    W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
    if nh is not None:
        ax = nh / (np.linalg.norm(nh) + 1e-300)
        T = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
    else:
        T = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
    rows.append((k, idx.shape[0], L, W, T, L / max(W, 1e-9), L / max(T, 1e-9)))

print('=' * 96)
print('★ %s 长宽比**分布**（快照 step %d，%d 个场）' % (TAG, st, len(rows)))
print('=' * 96)
print('  %-5s %-7s %-8s %-8s %-8s %-9s %s' % ('场', '体素', '长', '宽', '厚', '长宽比', '长厚比'))
for k, n, L, W, T, ar, lt in rows:
    flag = '' if T >= 0.25 else '  ⚠厚<4胞'
    print('  %-5d %-7d %-8.3f %-8.3f %-8.3f %-9.2f %.2f%s' % (k, n, L, W, T, ar, lt, flag))

ar = np.array([r[5] for r in rows]); lt = np.array([r[6] for r in rows])
th = np.array([r[4] for r in rows])
print()
print('  ── 分布统计 ──')
print('  长宽比：中位 **%.2f** · 均值 %.2f · 范围 [%.2f, %.2f]'
      % (np.median(ar), ar.mean(), ar.min(), ar.max()))
print('  长厚比：中位 **%.2f** · 均值 %.2f · 范围 [%.2f, %.2f]'
      % (np.median(lt), lt.mean(), lt.min(), lt.max()))
print()
print('  ── 分档（**真实板条区间 = 5–20**）──')
for lo, hi, name in ((0, 3, '<3（**不像板条**）'), (3, 5, '3–5（偏钝）'),
                     (5, 20, '**5–20（真实区间）**'), (20, 1e9, '>20（过度拉长）')):
    m = (ar >= lo) & (ar < hi)
    print('    长宽比 %-22s **%d 个场**（%.0f%%）' % (name, m.sum(), 100.0 * m.sum() / len(ar)))
print()
print('  ⚠ 厚度 < 4 胞（250 nm）的场 = **%d 个**（§208：这档的长厚比不可信）'
      % int((th < 0.25).sum()))
