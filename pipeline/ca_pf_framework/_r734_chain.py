#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r734_chain.py —— **把 `R631 §7.2` 的"冲销链"逐环量出来**（离线、只读归档快照）。

## 要回答的问题（用户最终关心的）
> **为什么"没开 `facet_proj`"的板条长厚比卡在 ~3，而设计是 33？**

`R631 §7.2` 给了一条**定性**链：
```
形状各向异性 = M(n) --[重初始化磨角]--> --[平流角平均]--> 残值 ≲ 2
```
本脚本把它**逐环量化**，判据是：**每个环节的"各向异性传递率"**。

## 三环与各自的口径（**写死**）
| 环 | 量 | 口径 |
|---|---|---|
| **① `M(n)` 本征** | `M_tip/M_wide` 的设计值 | `exp(β_h)`；**这是设计意图，不是测量** |
| **② 实测法向分布上的 `M(n)`** | `M_eff(tip)/M_eff(wide)` | 在快照界面上按 `n·n*` 分档求 `M(n)/M0`（`R719` 口径） |
| **③ 实际形状** | `λ = PCA 主轴比` | `R666 §1.1` 的最可信口径 |

## ★ 关键判据（**先登记，可 FAIL**）
| # | 判据 | 含义 |
|---|---|---|
| **Q-1** | 若 ② ≫ 1 而 ③ ≈ 1 ⇒ **瓶颈在几何/运动学**（法向给足了各向异性，形状没兑现） | — |
| **Q-2** | 若 ② ≈ 1 ⇒ **瓶颈在 `M(n)` 的输入**（法向分布已经把各向异性抹平） | — |
| **Q-3** | **各环的传递率** = 下一环 / 上一环；报告哪一环跌得最多 | — |

⚠ 记账：`β` 用**硬编码**（快照不落盘，`R719 §1.1` 的 G-3 缺口）；只读 `box_touch=0` 的步（`R720 §1`）。

## 用法
    python3 _r734_chain.py <root> <tag> --steps 100 200
"""
import argparse
import csv
import os
import sys

import numpy as np

BETA_H_DEFAULT, BETA_W_DEFAULT = 6.477, 2.3
COS25 = float(np.cos(np.radians(25.0)))      # `R30 §56` 的 f_flat 口径；此处用于 tip 档


def series(p):
    with open(p, newline='') as f:
        return {int(r['step']): r for r in csv.DictReader(f) if r.get('step')}


def measure(sp):
    with np.load(sp, allow_pickle=False) as z:
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        ii = (np.arange(N) + 0.5) * dx
        P = np.stack(np.meshgrid(ii, ii, ii, indexing='ij'), -1).reshape(-1, 3)
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
        nref = np.asarray(z['n_hab'], float)
        wref = np.asarray(z['w_ax'], float)
        a_ax = np.asarray(z['a_ax'], float)
    nref = nref / (np.linalg.norm(nref) + 1e-300)
    wref = wref / (np.linalg.norm(wref) + 1e-300)
    a_ax = a_ax / (np.linalg.norm(a_ax) + 1e-300)
    nif = 0
    mt_num = ms_num = mw_num = 0.0
    nt = ns = nw = 0
    pca = 0.0
    # 各界面的**面积加权**累计
    for k in sorted(int(v) for v in np.unique(fld) if v > 0):
        m = (fld == k)
        g = np.full(N ** 3, 1e3)
        g[idx[m]] = val[m]
        if int((g < 0).sum()) < 200:
            continue
        gr = np.gradient(g.reshape(N, N, N), dx, edge_order=2)
        gn = np.sqrt(sum(x ** 2 for x in gr)) + 1e-300
        iface = (np.abs(g) <= 0.5 * dx).reshape(N ** 3)
        ni = int(iface.sum())
        if ni < 50:
            continue
        _n = np.stack([x / gn for x in gr], -1).reshape(N ** 3, 3)[iface]
        nif += ni
        c2b = np.clip((_n @ nref) ** 2, 0, 1)
        c2w = np.clip((_n @ wref) ** 2, 0, 1)
        mm = np.exp(-BETA_H_DEFAULT * c2b - BETA_W_DEFAULT * c2w)
        # ⚠⚠ **量具更正（2026-10-08，本脚本第一版实测抓出）**：
        #   第一版把 `wide` 档也定义成 `c2b ≥ 0.90` —— 与 `tip` 档**同一个条件**
        #   ⇒ `M_tip == M_wide` **恒成立** ⇒ 比值恒为 1 ⇒ 报出"传递率 0.0015"**是假的**。
        #   正解（引擎的口径，`windowB_surface.py:5251-5272`）：
        #     `tip`  = **端面**：`|n·a| ≥ cos25°`（`a` = 长轴）且 `c2b` 小
        #     `wide` = **宽面**：法向接近 `n*` ⇒ `c2b ≥ 0.90`
        #   ⇒ **`wide` 用 `c2b ≥ 0.90`；`tip` 改用 `a` 轴判据**（否则两者恒等）。
        tip_mask = np.clip((_n @ a_ax) ** 2, 0, 1) >= COS25 ** 2
        if tip_mask.any():
            mt_num += float(mm[tip_mask].mean()) * int(tip_mask.sum())
            nt += int(tip_mask.sum())
        if (c2w >= 0.90).any():
            ms_num += float(mm[c2w >= 0.90].mean()) * int((c2w >= 0.90).sum())
            ns += int((c2w >= 0.90).sum())
        if (c2b >= 0.90).any():
            mw_num += float(mm[c2b >= 0.90].mean()) * int((c2b >= 0.90).sum())
            nw += int((c2b >= 0.90).sum())
        # 形状
        pts = P[g < 0]
        cen = pts - pts.mean(0)
        _, V = np.linalg.eigh(cen.T @ cen / max(len(cen), 1))
        pr = cen @ V
        sp = np.sort(pr.max(0) - pr.min(0))[::-1]
        pca = max(pca, float(sp[0] / max(sp[2], 1e-30)))
    M_tip = mt_num / nt if nt else float('nan')
    M_side = ms_num / ns if ns else float('nan')
    M_wide = mw_num / nw if nw else float('nan')
    # ②：实测法向分布下的有效比
    ratio_eff = M_tip / M_wide if (M_wide == M_wide and M_wide > 0) else float('nan')
    return dict(nif=nif, M_tip=M_tip, M_side=M_side, M_wide=M_wide,
                ratio_eff=ratio_eff, pca=pca,
                f_tip=(nt / nif if nif else float('nan')),
                f_wide=(nw / nif if nif else float('nan')),
                f_side=(ns / nif if nif else float('nan')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('tag')
    ap.add_argument('--steps', type=int, nargs='*', default=[100, 200])
    a = ap.parse_args()
    d = os.path.join(a.root, 'dry_%s' % a.tag)
    S = series(os.path.join(d, 'series.csv'))
    print('=' * 104)
    print('冲销链逐环量化：%s（`R631 §7.2` 的定量版）' % a.tag)
    print('=' * 104)
    print('  设计环 ① `M_tip/M_wide` = exp(β_h) = %.1f（**设计意图**）'
          % np.exp(BETA_H_DEFAULT))
    print()
    print('  %-6s %8s %10s %10s %10s %12s %10s %8s %8s %8s'
          % ('step', 'box', '界面胞', 'M_tip', 'M_wide', '②实测比', '③PCA',
             'f_tip', 'f_wide', 'f_side'))
    rows = []
    for st in a.steps:
        sp = os.path.join(d, 'snap_%05d.npz' % st)
        if not os.path.exists(sp):
            print('  %-6d  ⚠ 无快照' % st)
            continue
        bt = str(S.get(st, {}).get('box_touch', '?'))
        r = measure(sp)
        rows.append((st, bt, r))
        print('  %-6d %8s %10d %10.3e %10.3e %12.2f %10.3f %8.4f %8.4f %8.4f'
              % (st, bt, r['nif'], r['M_tip'], r['M_wide'], r['ratio_eff'],
                 r['pca'], r['f_tip'], r['f_wide'], r['f_side']))
    print()
    print('  ★ `f_tip` = **端面胞占全部界面胞的比例**（`|n·a| ≥ cos25°`）')
    print('    ⇒ 这是"`M(n)` 对了但形状没动"的**候选解释**：')
    print('      若 `f_tip` 很小 ⇒ **高迁移率只作用在很小一部分界面上** ⇒')
    print('      宏观伸长被其余 95% 的慢界面**稀释**（`[推理]`，本表给证据）')
    print()
    if not rows:
        print('  ⚪ 无数据')
        return 0
    print('  ## 判据')
    for st, bt, r in rows:
        if bt != '0':
            print('    step %d：⚪ **不适用**（`box_touch=%s`，`R720 §1`）' % (st, bt))
            continue
        e1 = np.exp(BETA_H_DEFAULT)
        e2 = r['ratio_eff']
        e3 = r['pca']
        print('    step %d：① %.1f → ② %.2f（传递率 **%.4f**）→ ③ PCA %.3f'
              % (st, e1, e2, e2 / e1, e3))
        if e2 > 50 and e3 < 5:
            print('         ⇒ **Q-1 成立**：法向给了各向异性（② ≫ 1），'
                  '但形状没兑现（③ 小）⇒ **瓶颈在几何/运动学**，不在 `M(n)` 的输入')
        elif e2 < 5:
            print('         ⇒ **Q-2 成立**：`M(n)` 的输入把各向异性抹平了（② ≈ 1）')
        else:
            print('         ⇒ 介于两者之间，需并读 ③')
    return 0


if __name__ == '__main__':
    sys.exit(main())
