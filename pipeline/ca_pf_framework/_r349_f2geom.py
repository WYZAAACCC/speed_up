#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r349_f2geom.py —— ★★★ **决定性**：变体-变体界面到底存不存在？两个基给出相反答案吗？

## 由来

`windowB_surface.py:3442` 的 R231 记账原话：
> 「`karr>0` 时 `larr` 到底取什么值？实测 `(karr>0)&(larr>0)` **恒为 0**」

而 `_r280` 的两个臂（`saSet2P0`/`saSet2F2P0`）日志里 **F2 胞数 = 0**（每一步），
`_stats` 在 `n<20` 时返回 `dict(name=..., n=n)`（`:3396-3399`）⇒ **打印的 `n` 是真计数**。

**但 `_bk_measure` 在 `region` 基上一直报得到 F2 面**（`§142.1`：F2 占界面面积 8.7%）。

**⇒ 两个基给出相反答案 ⇒ 哪一个描述物理用到的那个配对？**

## 两个基（**必须先分清**）

| 基 | 定义 | 谁在用 |
|---|---|---|
| **`region` 基** | `region` 图上 6-邻域区域号不同者 = 界面胞 | `_bk_measure`（面积/F1F2F3 统计）、所有离线测量 |
| **`(karr,larr)` 基** | `argsort(phi)[0]` 与 `[1]` = **赢家**与**亚军**场 | **`advance()`**（`:3013`）—— 速度律、`facet_nref`、`stk`、`edl` **全部**用它 |

**若 `region` 基有 F2 而 `(karr,larr)` 基恒无**，则：
* 物理里 **F2 的 γ 表从不被查**（⇒ `--f2-pair-gamma` 无效，R165/`_r280` 的前提作废）；
* `facet_nref` 里 **`ncmp[k,l]` 分支从不触发**（⇒ T9 的修法**空转**）⇒ **Q-15 的直接答案**；
* `Δed = ed_k − ed_0`（**变体 vs 母相**）而不是变体 vs 变体。

## 判据（**先写死**）

* **V-0 正对照（合成）**：造一个**已知**的三区域构型（两个不同变体 + 母相，
  用 `init_parent` 的约定 φ_0 = −min(φ_{k≥1})），检查
  ① `(karr>0)&(larr>0)` 是否为 0；② `region` 基的几何变体-变体面数是否 > 0。
  ⇒ **两个基的分歧必须在合成例上先复现出来**，否则本脚本的输出无意义。
* **V-1 真实归档**：同一张快照上同时算两个基的 F1/F2/F3 胞数。
* **V-2 结论**：`region` 基 F2 > 0 而 `(karr,larr)` 基 F2 = 0 ⇒ **物理用错了配对**。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


# --------------------------------------------------------------------------- #
def build_three_region(nreg=3, N=40, dx=6.25e-8, R=8.0, sep=9.5):
    """合成：两个球（不同变体 k=1,2）+ 母相（φ_0 = −min，`init_parent` 的约定）。"""
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    phi = np.full((nreg, N, N, N), 1e3)
    c = 0.5 * N * dx
    for k, off in ((1, -sep * dx / 2), (2, +sep * dx / 2)):
        cen = np.array([c + off, c, c])
        phi[k] = np.linalg.norm(X - cen, axis=-1) - R * dx
    for j in range(nreg):
        for k in range(1, nreg):
            if j != k:
                phi[j] = np.maximum(phi[j], -(np.linalg.norm(
                    X - np.array([c + (-sep * dx / 2 if k == 1 else sep * dx / 2), c, c]),
                    axis=-1) - R * dx))
    phi[0] = -np.min(phi[1:], axis=0)          # ★ init_parent 的约定
    return phi


def argmin2(phi):
    o = np.argsort(phi, axis=0)
    return o[0], o[1]


def region_of(phi):
    return np.argmin(phi, axis=0).astype(np.int64)


def geom_counts(reg, var):
    """`region` 基：6-邻域跨界面计数，按**变体身份**分类。
    返回 (n_f1, n_f2, n_f3) —— 一条**有向**边计数（与 `_bk_measure` 同精神）。"""
    n1 = n2 = n3 = 0
    for ax in range(3):
        a, b = reg, np.roll(reg, -1, axis=ax)
        sel = a != b
        if not sel.any():
            continue
        va = var[np.clip(a[sel], 0, len(var) - 1)]
        vb = var[np.clip(b[sel], 0, len(var) - 1)]
        both_v = (va > 0) & (vb > 0)
        n1 += int((~(both_v)).sum())                 # 至少一侧是母相 ⇒ F1
        n2 += int((both_v & (va != vb)).sum())       # 两侧都是变体且**异变体** ⇒ F2
        n3 += int((both_v & (va == vb)).sum())       # 同变体 ⇒ F3
    return n1, n2, n3


def pair_counts(karr, larr, var):
    """`(karr,larr)` 基：跨界面处赢家/亚军的变体身份分类（这是 **advance** 用的基）。"""
    ka, la = karr, larr
    sel = ka != la
    va = var[np.clip(ka[sel], 0, len(var) - 1)]
    vb = var[np.clip(la[sel], 0, len(var) - 1)]
    both_v = (va > 0) & (vb > 0)
    return (int((~both_v).sum()),
            int((both_v & (va != vb)).sum()),
            int((both_v & (va == vb)).sum()),
            int(sel.sum()))


def main():
    print('=' * 108)
    print('_r349 —— 变体-变体界面：`region` 基 vs `(karr,larr)` 基（advance 用的那个）')
    print('=' * 108)

    # ---------------- V-0 合成正对照 ----------------
    print()
    print('  ## **V-0 合成正对照**（两个不同变体的球 + 母相）')
    phi = build_three_region()
    reg = region_of(phi)
    var = np.array([-1, 1, 2])               # 场 0 = 母相；场 1→V1；场 2→V2
    ka, la = argmin2(phi)
    print('     场体积（胞）: ', [int((reg == k).sum()) for k in range(3)])
    n_kpos = int((ka > 0).sum())
    n_both = int(((ka > 0) & (la > 0)).sum())
    print('     `karr>0` 胞数 = %d ；其中 `larr>0` 的 = **%d**（%.3f%%）'
          % (n_kpos, n_both, 100.0 * n_both / max(n_kpos, 1)))
    print('     `region` 基几何计数 F1/F2/F3 = %s' % (geom_counts(reg, var),))
    print('     `(karr,larr)` 基计数 F1/F2/F3 = %s'
          % (pair_counts(ka, la, var)[:3],))
    g1, g2, g3 = geom_counts(reg, var)
    print('     ⇒ 合成例上 `region` 基有 F2 = **%d** 条；`(karr,larr)` 基 F2 = **%d** 条'
          % (g2, pair_counts(ka, la, var)[1]))
    if g2 == 0:
        print('     ❌ 合成例自己就没有 F2 ⇒ 本对照**不能**验证分歧（两球分开了？）')
    else:
        print('     ✅ 合成例有 F2（几何上）⇒ 可以检验两个基是否分歧')

    # ---------------- V-1 真实归档 ----------------
    print()
    print('  ## **V-1 真实归档**（同一张快照上同时算两个基）')
    arms = sys.argv[1:] or ['saSet2', 'saSet2F2']
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
        if not fs:
            print('     %-12s ⚠ 无快照' % arm)
            continue
        for f in (fs[0], fs[-1]):
            z = np.load(f, allow_pickle=True)
            reg = np.asarray(z['region'], np.int64)
            vk = np.asarray(z['vmap_keys'], np.int64)
            vv = np.asarray(z['vmap_vals'], np.int64)
            nreg = int(reg.max()) + 1
            var = np.full(max(nreg, int(vk.max()) + 1), -1, np.int64)
            var[vk] = vv
            f1, f2, f3 = geom_counts(reg, var)
            print('     %-12s step=%-5s nreg=%-3d | **`region` 基** F1=%-8d F2=%-8d F3=%-8d'
                  % (arm, z['step'], nreg, f1, f2, f3))
            print('     %-12s              | **`(karr,larr)` 基 = advance 用** '
                  '⇒ 见日志（`saSet2F2P0` 实测 F2 胞数 = **0**）' % '')
    print()
    print('  ⚠ 记账：`(karr,larr)` 基**无法**从 `band_*` 稀疏 φ 忠实重建')
    print('     （带外填 `+inf` 会改变亚军场，见 `§168.1`）⇒ 本脚本对它只引用**运行期实测**')
    print('     （`saSet2F2P0` 日志的 F2 胞数 = 0 与 `:3442` 的 R231 记账）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
