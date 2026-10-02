#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_trueshape.py --- ★★★★★★★ **用**真实的三维几何**量单根板条，而不是包围盒跨度**

## 为什么（R180 的量具口径错了）
`n_lath`/`w_lath`/`a_lath` 来自 `_bk_measure.py` 的 `n_%d`/`w_%d`/`a_%d`，
而 `wide_face_thickness` 的 docstring **逐字**说：
> `n_%d`（= `ths`，板条胞沿 `n*` 的**包围盒跨度**）**不是板条厚度**：
> 实测 `mb1s` 场 1 的包围跨度 624 → **2631 nm**，而由 φ 量出的两张宽面间距只有 780 → **732 nm**。
> ⇒ 包围跨度被**碎片**与 **`n*` 与真实板条法向的 7.3° 夹角**撑大。

## 本脚本怎么量（**三条互相独立**）
对快照里的**每个场** `k`：
1. **包围盒跨度**（= 我 R180 用的那个，做对照）；
2. **★ PCA 主轴跨度**（对胞坐标做协方差 ⇒ 三个特征方向上的**真实**展布）⇒ **对倾斜免疫**；
3. **★ 等效尺寸** = `(6V/π)^(1/3)`、`(V/(π/6·(L/W)·(T/W)))^…` ⇒ 用**体积**与**面数**交叉；
4. **★ 比表面积** ⇒ `S/V`：**板条**的 `S/V` ≈ `2/T`（T=厚度）⇒ 由 `S/V` 反解**等效厚度** ⇒ **对碎片/倾斜都不太敏感**。

⚠ **只读快照**（`region` / `phi` / `laths`），**不改引擎**。
"""
import os
import sys

import numpy as np


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk/dry_BK6/snap_00000.npz'
    if not os.path.exists(snap):
        # 退一步：找最新的快照
        d = os.path.dirname(snap)
        cand = sorted([f for f in os.listdir(d) if f.startswith('snap_')]) if os.path.isdir(d) else []
        if not cand:
            print('  ⚠ 没有快照：%s' % snap)
            return
        snap = os.path.join(d, cand[-1])
    print('=' * 100)
    print('真实三维几何：%s' % snap)
    print('=' * 100)
    z = np.load(snap)
    print('  键：%s' % ', '.join(z.files))
    reg = np.asarray(z['region']) if 'region' in z.files else None
    if reg is None:
        print('  ⚠ 快照里没有 region')
        return
    N = reg.shape[0]
    laths = np.asarray(z['laths']).ravel().tolist() if 'laths' in z.files else []
    vmap_k = np.asarray(z['vmap_keys']).ravel().tolist() if 'vmap_keys' in z.files else []
    vmap_v = np.asarray(z['vmap_vals']).ravel().tolist() if 'vmap_vals' in z.files else []
    vmap = dict(zip([int(x) for x in vmap_k], [int(x) for x in vmap_v]))
    print('  N=%d，变体映射 %d 项' % (N, len(vmap)))
    # 用胞数当体积（dx 未知 ⇒ 用"胞"当单位；相对量不受影响）
    ks = sorted(set(int(x) for x in np.unique(reg)) - {0})
    print('  场号（非零 region）：%d 个' % len(ks))
    print()
    print('  %-5s %-7s %-9s %-26s %-26s %s' %
          ('场', '变体', '胞数', '包围盒跨度(n*:w:a，胞)', 'PCA 主轴跨度(胞)', 'S/V(1/胞)'))
    print('  ' + '-' * 96)
    rows = []
    for k in ks:
        m = (reg == k)
        nvox = int(m.sum())
        if nvox < 5:
            continue
        idx = np.argwhere(m).astype(float)
        bb = idx.max(axis=0) - idx.min(axis=0) + 1.0
        c = idx - idx.mean(axis=0)
        cov = c.T @ c / max(len(c) - 1, 1)
        ev = np.linalg.eigvalsh(cov)
        ev = np.sqrt(np.maximum(ev, 0)) * 2.0      # 主轴上的 ±1σ 跨度（近似）
        # S/V：6-连通的面数
        faces = 0
        for ax in range(3):
            d = np.diff(m.astype(np.int8), axis=ax)
            faces += int(np.abs(d).sum())
        SV = faces / max(nvox, 1)
        rows.append((k, vmap.get(k, '?'), nvox, bb, ev, SV))
        print('  %-5d %-7s %-9d %-26s %-26s %-8.4f' %
              (k, vmap.get(k, '?'), nvox,
               '%.0f:%.0f:%.0f' % tuple(bb),
               '%.1f:%.1f:%.1f' % tuple(ev), SV))
    if not rows:
        print('  （没有 ≥5 胞的场）')
        return
    print()
    print('  ── 汇总（中位）──')
    bbs = np.array([r[3] for r in rows])
    evs = np.array([r[4] for r in rows])
    svs = np.array([r[5] for r in rows])
    print('  包围盒跨度 中位：%.1f : %.1f : %.1f（**长/短 = %.2f**）'
          % (np.median(bbs[:, 0]), np.median(bbs[:, 1]), np.median(bbs[:, 2]),
             np.median(bbs.max(axis=1) / np.maximum(bbs.min(axis=1), 1e-9))))
    print('  PCA 主轴   中位：%.1f : %.1f : %.1f（**长/短 = %.2f**）'
          % (np.median(evs[:, 0]), np.median(evs[:, 1]), np.median(evs[:, 2]),
             np.median(evs.max(axis=1) / np.maximum(evs.min(axis=1), 1e-9))))
    print('  S/V 中位：%.4f 1/胞 ⇒ 等效厚度 ≈ %.2f 胞（薄板 S/V≈2/T）'
          % (np.median(svs), 2.0 / max(np.median(svs), 1e-9)))
    print()
    print('  ★ 判读：')
    print('   · **PCA 长/短 ≫ 包围盒长/短** ⇒ **包围盒口径被倾斜/碎片撑大**（**R36 那条伪影**）')
    print('   · **S/V 反解的等效厚度 ≪ 最长跨度** ⇒ **它其实是**薄板****')
    print('   · **两者都 ≈1** ⇒ **真的是等轴**（**C2 的否定成立**）')
    print('=' * 100)


if __name__ == '__main__':
    main()
