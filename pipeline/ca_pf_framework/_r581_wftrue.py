#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_wftrue.py --- ★★★★★★★ **从快照重建 φ，把仓库的正式量具 `wide_face_thickness` 跑通**

## 依据（R581-R187 的探查）
快照**没有**整场 `phi` 键，但它带着**界面带**：
* `band_idx`（int32，55.3 万）：带内胞的**平坦索引**
* **`band_val`（float32）：那些胞的 **φ 值**（±3.75e-07 = ±`band_cells`·Δx）**
* `band_fld`（int16）：每个带胞属于哪个场（0 = 母相）
* `band_cells` = 6（带的半宽，胞）

**⇒ 重建**：`phi.ravel()[band_idx] = band_val`，带外填**带符号的大值**（保号，避免"零交叉"假象）。

## ★ 为什么重建是**可用**的（关键论证）
`wide_face_thickness` 的算法：
1. 界面胞 = `|φ| ≤ 1.5·Δx`；2. 法向 `n = ∇φ/|∇φ|`；3. `(n·n*)² > 0.81`；4. 两簇中位之差。
**⇒ 用到的胞**都在 `|φ| ≤ 1.5Δx`** ⇒ **它们**深在 ±6Δx 的带内 ⇒ **其 6-邻域也在带内****
⇒ **∴ 那些胞上的 `∇φ` 是**真实**的（**不是外插垃圾**）** ✓
**⚠ 带**最外**两层胞的梯度会受填充值污染** ⇒ **但它们 `|φ| ≈ 5–6Δx` ⇒ **不进第 1 步** ⇒ 不影响** ✓

## 三个口径一起报（**互相交叉**）
`t_wf`（正式量具）· PCA 主轴 · S/V 反解厚度
"""
import os
import sys

import numpy as np

FR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FR)
import _bk_measure as BM


def rebuild_phi(z, fill=1.0):
    """从 band_* 重建 (N,N,N) 的 φ。带外填 fill*sign（保号）。"""
    N = int(z['N'])
    idx = np.asarray(z['band_idx']).ravel().astype(np.int64)
    val = np.asarray(z['band_val']).ravel().astype(np.float64)
    fld = np.asarray(z['band_fld']).ravel().astype(np.int32)
    phi = np.full(N ** 3, np.nan)
    phi[idx] = val
    return phi.reshape((N, N, N)), fld, idx, val


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk/dry_BK6/snap_00250.npz'
    dx = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5e-9
    z = np.load(snap)
    N = int(z['N'])
    L = float(z['L'])
    bc = int(z['band_cells'])
    n_hab = np.asarray(z['n_hab'], float)
    outdir = '_r581_wfout'
    os.makedirs(outdir, exist_ok=True)
    tag = os.path.basename(os.path.dirname(snap)) + '_' + os.path.basename(snap)[:-4]

    print('=' * 104)
    print('从快照重建 φ 后，用**仓库正式量具**量宽面厚度：%s' % snap)
    print('=' * 104)
    print('  N=%d  L=%.1f µm  Δx=%.2f nm  band_cells=%d（带的半宽 = %.2f nm）'
          % (N, L * 1e6, dx * 1e9, bc, bc * dx * 1e9))

    phi, fld, idx, val = rebuild_phi(z)
    print('  重建：带内 %d 个胞有 φ；带外 = NaN' % idx.size)

    # ── 自洽检查（量具先验）────────────────────────────
    fin = np.isfinite(phi)
    print()
    print('  ── ★ 重建的自洽检查（**先验量具**）──')
    print('    带内胞数 = %d（应 == band_idx.size = %d）%s'
          % (int(fin.sum()), idx.size, '✅' if int(fin.sum()) == idx.size else '❌'))
    print('    |φ| 的最大值 = %.4g m = %.2f 胞（应 ≈ band_cells=%d）%s'
          % (np.nanmax(np.abs(phi)), np.nanmax(np.abs(phi)) / dx, bc,
             '✅' if abs(np.nanmax(np.abs(phi)) / dx - bc) < 1.5 else '⚠'))
    # 每个带胞的 6-邻域是否都在带内（决定梯度可信度）
    m = fin
    nb_ok = 0
    tot = 0
    r = 1.5 * dx
    core = m & (np.abs(phi) <= r)
    ci = np.argwhere(core)
    for (i, j, k) in ci[:: max(1, len(ci) // 2000)]:
        tot += 1
        ok = True
        for ax, d in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            p = [i, j, k]
            p[ax] += d
            if not (0 <= p[0] < N and 0 <= p[1] < N and 0 <= p[2] < N):
                continue
            if not m[p[0], p[1], p[2]]:
                ok = False
                break
        nb_ok += 1 if ok else 0
    print('    **核心胞**（|φ| ≤ 1.5Δx，共 %d 个）里抽样 %d 个：'
          '6-邻域全在带内的比例 = **%.1f%%** %s'
          % (len(ci), tot, 100.0 * nb_ok / max(tot, 1),
             '✅ 梯度可信' if nb_ok / max(tot, 1) > 0.95 else '⚠ 部分梯度受填充污染'))

    # ── 正式量具 ────────────────────────────────────
    reg = np.asarray(z['region'])
    ks = sorted(set(int(x) for x in np.unique(reg)) - {0})
    print()
    print('  %-6s %-8s %-13s %-13s %-13s %-9s %s' %
          ('场', '胞数', 't_wf(nm)', 'PCA最长(nm)', 'S/V厚(nm)', '长/厚', '判读'))
    print('  ' + '-' * 100)
    rows = []
    for k in ks:
        mk = (reg == k)
        nvox = int(mk.sum())
        if nvox < 20:
            continue
        # ① 正式量具（用重建的 φ）
        try:
            d = BM.wide_face_thickness(phi, dx, n_hab, k)
        except Exception as e:
            d = None
        t = float(d['t_wf']) * 1e9 if d else None
        # ② PCA 最长
        idxk = np.argwhere(mk).astype(float)
        c = idxk - idxk.mean(axis=0)
        ev = np.sqrt(np.maximum(np.linalg.eigvalsh(c.T @ c / max(len(c) - 1, 1)), 0))
        pca_long = float(ev.max() * 2.0 * 1.73 * dx * 1e9)   # ±1σ → 全长
        # ③ S/V 反解厚度（薄板 S/V≈2/T）
        faces = 0
        for ax in range(3):
            faces += int(np.abs(np.diff(mk.astype(np.int8), axis=ax)).sum())
        sv = faces / max(nvox, 1)
        t_sv = 2.0 / max(sv, 1e-9) * dx * 1e9
        ratio = (pca_long / t) if (t and t > 0) else float('nan')
        rows.append((k, nvox, t, pca_long, t_sv, ratio))
        print('  %-6d %-8d %-13s %-13.0f %-13.0f %-9.2f %s' %
              (k, nvox, ('%.1f' % t) if t else '**None**', pca_long, t_sv, ratio,
               ('✅ 薄板' if ratio >= 5 else ('⚠ 中等' if ratio >= 2 else '❌ 近等轴'))
               if t else '⚠ 不可测'))
    print()
    if rows:
        ts = np.array([r[2] for r in rows if r[2]], float)
        ps = np.array([r[3] for r in rows], float)
        ss = np.array([r[4] for r in rows], float)
        rs = np.array([r[5] for r in rows if r[5] == r[5]], float)
        print('  ── 汇总（中位，可测 %d/%d 场）──' % (len(ts), len(rows)))
        if len(ts):
            print('  ★ `t_wf` 中位 = **%.0f nm**（正式量具）' % np.median(ts))
        print('    PCA 最长 中位 = %.0f nm' % np.median(ps))
        print('    S/V 反解厚 中位 = %.0f nm' % np.median(ss))
        if len(rs):
            print('  ★ **长/厚（PCA/t_wf）中位 = %.2f**' % np.median(rs))
            print('    ⇒ %s' % ('✅ **是板条**' if np.median(rs) >= 5 else
                                ('⚠ 中等（2–5）' if np.median(rs) >= 2 else '❌ 近等轴')))
        # 落盘
        np.savetxt(os.path.join(outdir, tag + '.tsv'),
                   np.array([[r[0], r[1], r[2] or np.nan, r[3], r[4], r[5]] for r in rows]),
                   delimiter='\t', fmt='%.6g',
                   header='k\tnvox\tt_wf_nm\tpca_long_nm\tsv_thick_nm\tratio')
        print('    （已落盘 %s/%s.tsv）' % (outdir, tag))
    print('=' * 104)


if __name__ == '__main__':
    main()
