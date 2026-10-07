#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r353_larr_ident.py —— ★★★ E-2 结案：**几何 F2 界面上的亚军 `larr` 到底是谁？**

## 为什么这个测量是**精确**的（不是近似）

`_r352` 已确立：在界面胞上 `φ_b`（几何邻居的场）**总是存下来的**（83.8% 明为负，其余也很小）。
而 `_sparse_band` 只丢 `|φ| > BΔx` 的胞 ⇒ 任何 `|φ_j| > BΔx` 的场都**不可能**是亚军
（因为亚军 ≤ `φ_b` ≤ BΔx）。**⇒ 用稀疏 φ 重建的亚军与引擎的 `larr` 一致** ✓
（这正是 `§168.1` 里对 `argmin` 不可靠的那个坑的**反面**：那里错在"把没存的当 +inf"，
这里被比较的场上界恰好保证它一定存下来了。）

## 要回答

`region` 基几何上明明有 **1922** 条 F2 面，`advance` 的 `(karr,larr)` 基却报 **F2 ≡ 0**。
`_r352` 已否掉"母相场抢走亚军"（F2 上 `φ_0 < φ_b` 只占 11.2%）。
**⇒ 那亚军究竟是谁？**

**候选**：同变体的**复制场**（每根板条一个场；同变体板条的场近乎相同）
⇒ `var(larr) == var(karr)` ⇒ 被 `_samev` 判成 **F3**。

## 判据（**先写死**）

* **X-0 自证**：重建的 `argmin`（13 场）必须 = 归档 `region`。**不过则全体作废。**
* **X-1**：F2 胞上 `larr == 0` 的占比（`_r352` 预测：低）。
* **X-2 ★**：F2 胞上 **`var(larr) == var(karr)`**（即被判成 F3）的占比。
  **高 ⇒ 假设成立**：几何上的**块-块（异变体）界面被当成同变体低角界面处理**。
* **X-3 对照**：F3 胞上 `var(larr) == var(karr)` 的占比（应当也高，那本来就是同变体）。
* **X-4**：F2 胞上 `var(larr) == var(b)`（**认对了**几何邻居）的占比。
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


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def main():
    print('=' * 104)
    print('_r353 —— E-2 结案：几何 F2 界面上的亚军是谁？')
    print('=' * 104)
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    snap = sys.argv[2] if len(sys.argv) > 2 else ''
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    f = os.path.join(d, snap) if snap else fs[-1]
    z = np.load(f, allow_pickle=True)
    N = int(z['N'])
    reg = np.asarray(z['region'], np.int64)
    vk = np.asarray(z['vmap_keys'], np.int64)
    vv = np.asarray(z['vmap_vals'], np.int64)
    nf = int(z['band_fld'].max()) + 1
    var = np.full(nf, -1, np.int64)
    var[vk] = vv
    p = rebuild(z)
    fin = np.isfinite(p)
    print('  arm=%s 快照=%s step=%s N=%d nf=%d' % (arm, os.path.basename(f), z['step'], N, nf))

    full = np.where(fin, p, np.inf)
    order = np.argsort(full, axis=0)
    krec = order[0]
    lrec = order[1]

    # X-0 自证 —— ★ 必须**限定在"归档 winner 自己的场存下来了"的胞上**：
    #   重建把没存的场填 `+inf` ⇒ 若 winner 的场没存，重建必然选错（`§168.1`）。
    #   全盒口径因此**本来就不该**是 1.0（第一版写成全盒，实测 0.9676 ⇒ 判据写错了，
    #   不是数据坏了）。限定后应 ≈ 1.0（`§168.2` 的 `hard=0` 就是这个意思）。
    m_ok = fin[reg, np.arange(N)[:, None, None],
               np.arange(N)[None, :, None], np.arange(N)[None, None, :]]
    x0_all = float((krec == reg).mean())
    x0 = float((krec == reg)[m_ok].mean()) if m_ok.any() else float('nan')
    print('  **X-0 自证**  全盒 = %.4f（⚠ 全盒口径**不该**是 1.0，见下）；'
          '限定在"winner 的场存下来了"的 %d 胞上 = **%.4f** %s'
          % (x0_all, int(m_ok.sum()), x0,
             '✅' if x0 > 0.999 else '❌ 作废'))
    if not (x0 > 0.999):
        print('  ⇒ ❌ 自证不过 ⇒ 本脚本其余输出全部作废（硬规则 ④/⑯）。')
        return 2

    # 分类界面
    cls = {'F2': [], 'F3': []}
    for ax in range(3):
        b = np.roll(reg, -1, axis=ax)
        I0 = np.where(reg != b)
        A0 = reg[I0]
        B0 = b[I0]
        va = var[np.clip(A0, 0, nf - 1)]
        vb = var[np.clip(B0, 0, nf - 1)]
        both = (va > 0) & (vb > 0)
        for kk, m in (('F2', both & (va != vb)), ('F3', both & (va == vb))):
            if m.any():
                cls[kk].append(((I0[0][m], I0[1][m], I0[2][m]), A0[m], B0[m]))
    print()
    print('  %-4s %7s %10s %10s %12s %12s %12s' %
          ('类', '胞数', 'larr==0', 'larr==k', 'var(l)==var(k)',
           'var(l)==var(b)', 'var(l) 其它'))
    for kk in ('F2', 'F3'):
        if not cls[kk]:
            print('  %-4s （无胞）' % kk)
            continue
        I = tuple(np.concatenate([c[0][j] for c in cls[kk]]) for j in range(3))
        A0 = np.concatenate([c[1] for c in cls[kk]])
        B0 = np.concatenate([c[2] for c in cls[kk]])
        n = A0.size
        l = lrec[I]
        vk_ = var[np.clip(A0, 0, nf - 1)]
        vl = var[np.clip(l, 0, nf - 1)]
        vb_ = var[np.clip(B0, 0, nf - 1)]
        same = vl == vk_
        eqb = vl == vb_
        other = (~same) & (~eqb) & (l != 0)
        print('  %-4s %7d %9.1f%% %9.1f%% %11.1f%% %11.1f%% %11.1f%%'
              % (kk, n, 100.0 * float((l == 0).mean()),
                 100.0 * float((l == A0).mean()),
                 100.0 * float(same.mean()),
                 100.0 * float(eqb.mean()),
                 100.0 * float(other.mean())))
    # 末态 top 配对
    print()
    print('  ## F2 胞上 `(var(karr) → var(larr))` 的 top 组合')
    if cls['F2']:
        I = tuple(np.concatenate([c[0][j] for c in cls['F2']]) for j in range(3))
        A0 = np.concatenate([c[1] for c in cls['F2']])
        l = lrec[I]
        vk_ = var[np.clip(A0, 0, nf - 1)]
        vl = var[np.clip(l, 0, nf - 1)]
        d_ = {}
        for a_, b_ in zip(vk_.tolist(), vl.tolist()):
            d_[(a_, b_)] = d_.get((a_, b_), 0) + 1
        for kk2, c in sorted(d_.items(), key=lambda x: -x[1])[:8]:
            print('     var(karr)=%2d → var(larr)=%2d : %d' % (kk2[0], kk2[1], c))
    print()
    print('  ## 判据')
    print('  * **X-2 ★**：F2 上 `var(larr)==var(karr)` 高 ⇒ **块-块（异变体）界面被当成同变体处理**')
    print('  * **X-4**：F2 上 `var(larr)==var(b)`（认对邻居）低 ⇒ 配对**没有**指向几何邻居')
    print()
    print('  ⚠ 记账：重建亚军在**界面胞**上与引擎 `larr` 一致（理由见文件头注）；')
    print('     但**非界面胞**不保证（那里 `φ_b` 未必存下来）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
