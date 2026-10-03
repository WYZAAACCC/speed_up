#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_whyB.py --- ★★★★★ 问题 B 的两个子问题
   ① 老场为什么退化？  ② 新形核为什么不是板条状？

## 设计（**把长/宽/厚分开**，而不是只看比值）
种子参考（`closure.json` 逐字）：`plate L/W/T = [2400, 640, 250] nm`
  ⇒ 体积 = 2400×640×250 nm³ = 3.84e8 nm³ ÷ (62.5)³ = **1573 胞**
  ⇒ **长宽比 3.75** · **长厚比 9.6**

### ① 老场退化：逐场跟踪 (L, W, T, 宽比, 厚比) 随 step
判据：
* **L 缩 / W 涨** ⇒ 被**侧向吃掉**（面内竞争）;
* **T 涨** ⇒ **厚度钉扎失效**;
* **L 与 W 同步涨** ⇒ **各向同性长大**（失去拉长优势）。

### ② 新形核：测每个场**首现快照**的 (体积, L, W, T, 宽比)
判据：
* **体积 ≈ 1573 胞** 但**宽比 ≈1.4** ⇒ **种子被切割/未按 `elong` 播种**（播种缺陷）;
* **体积 ≪ 1573 胞**（如 <300）⇒ **那不是核，是 `argmin` 碎片**;
* **体积 > 1573 胞** ⇒ 它**已经长过**，测到的是生长后的形状。
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
VOX = DX ** 3
SEED_VOX = 2400 * 640 * 250 / VOX          # ≈1573
S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'


def meas(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    out = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        m = (reg == k)
        n = int(m.sum())
        if n < 10:
            continue
        lab, _ = ndimage.label(m, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        big = (lab == (int(np.argmax(sz)) + 1))
        idx = np.argwhere(big).astype(np.float64)
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX
        T = (float((c @ nh).max() - (c @ nh).min() + 1) * DX) if nh is not None \
            else float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX
        out[k] = dict(n=int(big.sum()), ntot=n, L=L, W=W, T=T,
                      ar=L / max(W, 1e-9), lt=L / max(T, 1e-9),
                      nfrag=int((sz >= 30).sum()), frac=float(sz.max() / n))
    return out


snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
data = {}
for P in snaps:
    st = int(P.split('snap_')[1].replace('.npz', ''))
    data[st] = meas(P)
steps = sorted(data)
first = {}
for st in steps:
    for k in data[st]:
        first.setdefault(k, st)

print('=' * 104)
print('★ %s：问题 B 的两个子问题（种子参考：**%d 胞** · 长宽比 **3.75** · 长厚比 **9.6**）'
      % (TAG, int(SEED_VOX)))
print('=' * 104)

# ── ① 老场逐场跟踪（只取最大分量，单位 nm）──
print('\n① 老场（首现 ≤ 200）的逐场演化：**L / W / T 分开看**')
print('  %-5s %-7s %s' % ('场', '首现', 'step → (L, W, T, 宽比, 厚比)'))
for k in sorted(first):
    if first[k] > 200:
        continue
    seq = [(st, data[st][k]) for st in steps if k in data[st]]
    if len(seq) < 3:
        continue
    print('  %-5d %-7d' % (k, first[k]))
    for st, d in seq[:3] + seq[-3:]:
        print('        step %-6d L=%6.0f W=%6.0f T=%6.0f  **宽比 %5.2f  厚比 %5.2f**  (%d 胞)'
              % (st, d['L'], d['W'], d['T'], d['ar'], d['lt'], d['n']))
    d0, d1 = seq[0][1], seq[-1][1]
    print('        ⇒ **ΔL=%+.0f nm  ΔW=%+.0f nm  ΔT=%+.0f nm**  ｜ 宽比 %+.2f'
          % (d1['L'] - d0['L'], d1['W'] - d0['W'], d1['T'] - d0['T'], d1['ar'] - d0['ar']))
    print()

# ── ② 新场的"出生几何"──
print('\n② 新场（首现 > 200）的**出生几何**（首现快照上，最大分量）')
print('  %-5s %-7s %-8s %-8s %-8s %-8s %-8s %-7s %s'
      % ('场', '首现', '体素', 'L(nm)', 'W(nm)', 'T(nm)', '宽比', '碎片数', '判读'))
for k in sorted(first):
    if first[k] <= 200:
        continue
    d = data[first[k]][k]
    if d['n'] >= SEED_VOX * 1.3:
        v = '**已长过**（>种子 1.3×）'
    elif d['n'] >= SEED_VOX * 0.6:
        v = ('**≈种子体积但宽比低 ⇒ 播种缺陷嫌疑**' if d['ar'] < 2.5 else '≈种子 ✓')
    else:
        v = '**远小于种子 ⇒ 可能是碎片**'
    print('  %-5d %-7d %-8d %-8.0f %-8.0f %-8.0f %-8.2f %-7d %s'
          % (k, first[k], d['n'], d['L'], d['W'], d['T'], d['ar'], d['nfrag'], v))
print()
print('  ── 判据 ──')
print('  * 若新场**体积 ≈ 种子而宽比 ≈1.4** ⇒ **种子未按 `elong` 播种 / 被切割**（播种缺陷）;')
print('  * 若新场**体积远小于种子** ⇒ **那不是核**，是 `argmin` 的碎片 ⇒ 问题在归属而非形核。')
