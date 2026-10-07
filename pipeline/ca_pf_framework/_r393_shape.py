#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r393_shape.py —— **直接量**每个转变区（场）的真实形状：它到底是不是板条？

## 为什么不能靠 `a_lath`/`w_lath`/`n_lath`
那三个是**射线交点跨度的中位**，我实测它在 `t=0` 就与播种尺寸对不上
（播种 `W=500 nm`，而 `w_lath(0) = 1039 nm`）⇒ **口径存疑，不能用来判"是否圆化"**。

## 本脚本用**无假设**的几何量
对每个场 `k`（= 一根板条）的体素集合：
* `V`           体积（胞数 × Δx³）
* **包围盒**     盒坐标系下的三向跨度
* **惯性主轴**   由惯性张量的特征值给等价椭球的三个半轴长
  @@a_i=\\sqrt{5\\lambda_i/(2N)}@@（均匀椭球的回转半径 = 半轴/√5）
* **与播种比**   播种 = `L=1000`(a) × `W=500`(w) × `T=510`(n*)
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
DX = 62.5e-9
SEED = (1000.0, 500.0, 510.0)      # a, w, n*  (nm)


def axes_of(z, k):
    """该场的 (a, w, n*) 三轴（从快照的 a_ax/w_ax/n_hab 取）。取不到返回 None。"""
    try:
        a_ax = np.asarray(z['a_ax'], float)
        w_ax = np.asarray(z['w_ax'], float)
        nh = np.asarray(z['n_hab'], float)
    except KeyError:
        return None
    def pick(arr):
        if arr.ndim == 2 and arr.shape[0] >= k:
            return arr[k - 1] if arr.shape[0] > k - 1 else None
        return None
    try:
        A = np.asarray(z['vmap_vals'])
    except KeyError:
        A = None
    return None


def analyze(tag, snapname):
    p = os.path.join(MB, 'dry_' + tag, snapname)
    if not os.path.exists(p):
        print('  ⚠ 缺 %s' % p)
        return
    z = np.load(p, allow_pickle=True)
    reg = np.asarray(z['region'], np.int64)
    N = int(z['N'])
    print('=' * 96)
    print('### %s  %s  step=%s  N=%d' % (tag, snapname, z['step'], N))
    print('  快照键：%s' % sorted(z.keys()))
    print()
    print('  %-4s %9s %26s %26s %10s'
          % ('场', '胞数', '惯性主轴半轴(nm)', '**等效盒尺寸(nm)**', '长/厚'))
    for k in range(1, int(reg.max()) + 1):
        m = reg == k
        nv = int(m.sum())
        if nv == 0:
            print('  %-4d %9d %26s' % (k, 0, '—'))
            continue
        idx = np.argwhere(m).astype(float)          # (nv,3) 胞坐标
        c = idx.mean(0)
        d = (idx - c) * DX * 1e9                    # nm
        C = (d.T @ d) / nv                          # 协方差 (nm²)
        ev = np.sort(np.linalg.eigvalsh(C))[::-1]
        # 均匀椭球：⟨x²⟩=A²/5 ⇒ A=√(5λ)；均匀长方体：⟨x²⟩=L²/12 ⇒ L=√(12λ)
        semi = np.sqrt(np.maximum(ev, 0) * 5.0)
        box = np.sqrt(np.maximum(ev, 0) * 12.0)
        print('  %-4d %9d %26s %26s %10.2f'
              % (k, nv,
                 '%6.0f×%6.0f×%6.0f' % tuple(semi),
                 '%6.0f×%6.0f×%6.0f' % tuple(box),
                 box[0] / max(box[2], 1e-9)))
    print()
    print('  ⚠ 换算：均匀长方体 `⟨x²⟩ = L²/12` ⇒ **等效盒尺寸 = √(12λ)**（本表用这一列）。')
    print('     用椭球公式 √(5λ) 会小 √(5/12)=0.645 倍 —— 第一版就是那个，已改。')
    print('  播种（每根）：a×w×n* = %.0f×%.0f×%.0f nm；体积 = %.4f×1e6 nm³'
          % (SEED[0], SEED[1], SEED[2], SEED[0] * SEED[1] * SEED[2] / 1e6))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    d = os.path.join(MB, 'dry_' + tag)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    if not fs:
        print('⚠ 无快照'); return 2
    targets = [os.path.basename(fs[0])]
    if len(fs) > 1:
        targets.append(os.path.basename(fs[-1]))
    if len(sys.argv) > 2:
        targets = [os.path.basename(f) for f in fs
                   if os.path.basename(f) in sys.argv[2:]] or targets
    for t in targets:
        analyze(tag, t)
    return 0


if __name__ == '__main__':
    sys.exit(main())
