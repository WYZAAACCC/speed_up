#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_newfield.py --- ★★★★★ 那些"新场"到底是**新形核**还是**region 突然变大**？

## 用户的问题（**这正是要回答的**）
> "它们从一出生就不扁（0.71-1.56）这个是怎么回事？"

## 我发现的**反常信号**（必须先处理）
1. **PCA 第一主轴按定义最长 ⇒ 长宽比应 ≥ 1**，而实测有 **0.71/0.73/0.94/0.98/0.99**
   ⇒ **形状是**非凸**的**（第一主成分的最大方差方向 ≠ 最大跨度方向）；
2. **那些"新场"**一出现就有 4.2-5.0 µm 长**，而**种子盘只有 1.0 µm**
   ⇒ **它们**不像"刚形核的核"**，更像**已有场的 region 突然变大**。

## 本脚本（**用已有数据**）
对每个场，报它在**每个快照**里的：
* **体素数**（判"是不是刚形核"：新核 ≈ 1000 体素 = 0.25 µm³）；
* 长/宽/厚/长宽比；
**⇒ 若某场"首次出现"时体素就远大于 1000 ⇒ **不是新形核**，而是 region 变大。**
**⇒ 并与引擎的**形核公告**（`_w2_t5_short_t5N276.log`）交叉核对：该场是**何时**被公告的。**
"""
import glob
import re
import sys
import numpy as np

DX = 62.5
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276'
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
if not snaps:
    print('  （无快照）'); sys.exit(0)


def measure(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    out = {}
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
        out[k] = (idx.shape[0], L, W, T, L / max(W, 1e-9))
    return out


data = {int(P.split('snap_')[1].replace('.npz', '')): measure(P) for P in snaps}
steps = sorted(data)

# 引擎形核公告：场号 → 首次公告的 step
ann = {}
try:
    for line in open('_w2_t5_short_%s.log' % TAG, errors='ignore'):
        if 'athermal 形核' in line:
            m = re.search(r'@ step (\d+)', line)
            f = re.search(r'场 (\d+)', line)
            if m and f:
                k = int(f.group(1))
                ann.setdefault(k, int(m.group(1)))
except FileNotFoundError:
    pass

print('=' * 100)
print('★ %s：新场的身份核查（体素数判"是否刚形核"）' % TAG)
print('=' * 100)
print('  种子盘参考：1000×500×510 nm = 2.55e8 nm³ ÷ (62.5 nm)³ = **1044 体素**（0.255 µm³）')
print()
print('  %-5s %-9s %-9s %-8s %-8s %-8s %-8s %s'
      % ('场', '首现step', '首现体素', '首现长', '首现宽', '首现厚', '首现宽比', '引擎公告step'))
first = {}
for s in steps:
    for k in data[s]:
        first.setdefault(k, s)
for k in sorted(first):
    s0 = first[k]
    n, L, W, T, ar = data[s0][k]
    print('  %-5d %-9d %-9d %-8.3f %-8.3f %-8.3f %-8.2f %s'
          % (k, s0, n, L, W, T, ar, ann.get(k, '（未公告）')))
print()
print('  ── 判据（**预先写死**）──')
print('  * 若"首现体素" ≈ 1000 且"引擎公告step" ≈ 首现step ⇒ **确实是刚形核**;')
print('  * 若"首现体素" ≫ 1000（如 3000+）⇒ **不是新形核，而是已有场的 region 变大**;')
print('  * 若 `引擎公告step` **晚于**首现step ⇒ **该场在"被公告"之前就已存在于 region** ⇒ 同理。')
