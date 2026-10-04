#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_bigpiece.py --- 量「最发育的单片」的长/宽/厚（修正解码版）。

## 为什么不能读 CSV 的 `n_lath`/`w_lath`/`a_lath`
`_bk_measure.py:176` 已写明 `n_%d` 是**沿 `n*` 的包围盒跨度**，会被**碎片**撑大
（R595 实测出 `5944 nm > 5 µm 盒` 的不可能值）。⇒ 要真尺寸只能**逐连通分量做 PCA**。

## 解码（照 `_t5_split3d2.py:33-48`，**不是我自创**）
快照是**带内胞稀疏存储**：`band_idx`（展平索引）+ `band_val`（带符号距离 φ）+ `band_fld`（场号）
物理相 = `band_fld == k AND band_val < 0`
⚠ **口径记账**：只存"带内"胞 ⇒ `cells` 数是**带内胞数**，不是体积；
但 **PCA 极差给的是外包尺寸**（壳也包住实体）⇒ 长/宽/厚**有效**，体积需另核。
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DX = 62.5e-9
S26 = ndimage.generate_binary_structure(3, 3)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "t5N276F"
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 2240
    p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (tag, step))
    if not os.path.exists(p):
        print("无快照 %s" % p)
        return 1
    with np.load(p, allow_pickle=False) as z:
        N = int(np.asarray(z["N"]))
        bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
        bv = np.asarray(z["band_val"]).ravel()
        bf = np.asarray(z["band_fld"]).ravel()
    print("══ %s step=%d  N=%d  L=%.3f µm  dx=%.1f nm ══"
          % (tag, step, N, N * DX * 1e6, DX * 1e9))
    print("  带内胞总数 = %d（占盒 %.2f%%）" % (bi.size, 100.0 * bi.size / N ** 3))
    print("  φ<0 的带内胞 = %d（占盒 %.2f%%）"
          % ((bv < 0).sum(), 100.0 * (bv < 0).sum() / N ** 3))

    rows = []
    for k in np.unique(bf[bv < 0]):
        # ★ 必须排除 **场 0 = 母相 β**（`field 0 = parent`）——
        #   第一版没排除，结果"最发育的单片"取到了母相（328797 胞）。
        if int(k) == 0:
            continue
        sel = (bf == k) & (bv < 0)
        if sel.sum() < 20:
            continue
        idx = bi[sel]
        g = np.zeros((N, N, N), bool)
        g[idx // (N * N), (idx // N) % N, idx % N] = True
        lab, nc = ndimage.label(g, structure=S26)
        if nc == 0:
            continue
        sz = np.bincount(lab.ravel())[1:]
        big = int(np.argmax(sz)) + 1
        cc = np.argwhere(lab == big).astype(float)
        c0 = cc - cc.mean(0)
        _, _, vt = np.linalg.svd(c0, full_matrices=False)
        ext = np.array([(c0 @ vt[i]).max() - (c0 @ vt[i]).min() + 1.0 for i in range(3)])
        o = np.argsort(ext)[::-1]
        rows.append((int(k), int(sz[big - 1]), ext[o], nc, int(sel.sum())))

    rows.sort(key=lambda r: -r[1])
    print()
    print("  ── 按「最大单片带内胞数」排序前 8 ──")
    print("  %-5s %-8s %-8s %-8s %-8s %-7s %-7s %-6s"
          % ("场", "单片胞", "长nm", "宽nm", "厚nm", "长/宽", "长/厚", "碎片"))
    for k, nc_, e, ncomp, tot in rows[:8]:
        print("  %-5d %-8d %-8.0f %-8.0f %-8.0f %-7.2f %-7.2f %-6d"
              % (k, nc_, e[0] * DX * 1e9, e[1] * DX * 1e9, e[2] * DX * 1e9,
                 e[0] / max(e[1], 1e-9), e[0] / max(e[2], 1e-9), ncomp))
    if rows:
        k, nc_, e, ncomp, tot = rows[0]
        print()
        print("  ★★ **最发育的单片**：场 %d，单片带内胞 %d，该场碎片数 %d（全场带内胞 %d）"
              % (k, nc_, ncomp, tot))
        print("      （PCA 极差，单位 nm；1 胞 = %.1f nm）" % (DX * 1e9))
        print("      **长 = %.0f nm**（%.3f µm）" % (e[0] * DX * 1e9, e[0] * DX * 1e6))
        print("      **宽 = %.0f nm**（%.3f µm）" % (e[1] * DX * 1e9, e[1] * DX * 1e6))
        print("      **厚 = %.0f nm**（%.3f µm）" % (e[2] * DX * 1e9, e[2] * DX * 1e6))
        print("      **长/宽 = %.2f**   **长/厚 = %.2f**   **宽/厚 = %.2f**"
              % (e[0] / max(e[1], 1e-9), e[0] / max(e[2], 1e-9), e[1] / max(e[2], 1e-9)))
        print("      设计播种值：`--plate-L/W/T = 1000/500/510 nm`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
