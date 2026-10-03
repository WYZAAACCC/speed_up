#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_lathlen.py --- ★★★ 量**真实板条长度**（主轴 PCA）+ **它是否随时间长大**

## 为什么要换量具（§206 的教训）
我先前量的是**包围盒跨度沿 `a_ax`**，得到 910–1227 nm —— **而那与种子 `plate_L=1000 nm` 逐数吻合**
⇒ **无法区分"长出来的"与"种子"**。
**⇒ 本工具改为：**
1. **用 PCA 求该场的**主轴**（最大主成分）⇒ 沿主轴量长度（**这才是"板条长度"的定义**）；
2. **同时报三个方向（沿主轴 / 沿 `a_ax` / 垂直主轴）**，避免轴选错；
3. ★ **跨快照追踪同一根** ⇒ 报**长度随步数的变化** ⇒ **这才是"生长"的直接证据**。
"""
import glob
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5H3'
DX = 62.5
snaps = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % TAG))
print('=' * 92)
print('★ 真实板条长度（主轴 PCA）+ 跨时间变化   TAG=%s' % TAG)
print('=' * 92)

def measure(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    out = {}
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        # PCA：最大主成分 = 长轴
        try:
            w, v = np.linalg.eigh(c.T @ c)
        except Exception:
            continue
        ax = v[:, -1]                       # 长轴方向（单位向量）
        proj = c @ ax                        # 沿长轴的坐标
        L = float(proj.max() - proj.min() + 1) * DX / 1000.0     # µm
        # 垂直方向的最大跨度（宽度：用第二大主成分）
        ax2 = v[:, -2]
        W = float((c @ ax2).max() - (c @ ax2).min() + 1) * DX / 1000.0
        out[k] = dict(n=idx.shape[0], L=L, W=W)
    return out

res = {}
for P in snaps:
    st = int(P.split('snap_')[1].replace('.npz', ''))
    try:
        res[st] = measure(P)
    except Exception as e:
        print('  ⚠ step %d 读失败: %s' % (st, e))

if not res:
    print('  ⚠ 没有可用快照'); sys.exit(1)

last = max(res)
print('  ── 最新快照 step %d：各场的主轴长度（µm）──' % last)
ms = res[last]
print('  %-5s %8s %10s %10s' % ('场', '体素', '主轴长度', '次轴宽度'))
for k in sorted(ms):
    print('  %-5d %8d %10.3f %10.3f' % (k, ms[k]['n'], ms[k]['L'], ms[k]['W']))
Ls = [v['L'] for v in ms.values()]
print()
print('  **主轴长度统计：中位 %.3f µm   范围 [%.3f, %.3f]   （%d 个场）**'
      % (float(np.median(Ls)), min(Ls), max(Ls), len(Ls)))
print('  ★ 种子 `plate_L` = **1.000 µm** ⇒ 若中位 ≈ 1.0 ⇒ **就是种子尺寸，没长大**；')
print('    若显著 > 1.0 ⇒ **确实长长了**。')

print()
print('  ── ★ 跨时间追踪（同一场在不同 step 的主轴长度，µm）──')
steps = sorted(res)
keys = sorted(set().union(*[set(res[s]) for s in steps]))
hdr = [s for s in steps if s in (steps[0], steps[len(steps)//4], steps[len(steps)//2],
                                 steps[3*len(steps)//4], steps[-1])]
print('  %-5s %s' % ('场', '  '.join('%7d' % s for s in hdr)))
for k in keys[:14]:
    row = []
    for s in hdr:
        v = res[s].get(k)
        row.append('%7.3f' % v['L'] if v else '      —')
    print('  %-5d %s' % (k, '  '.join(row)))
print()
print('  ── 判读（**预先写死**）──')
print('  若各场长度在各 step 上**基本不变（≈1.0 µm）** ⇒ **板条没有长大，只是种子**；')
print('  若随时间**单调增大** ⇒ **确实在生长**（则先前的"未生长"判断需更正）。')
