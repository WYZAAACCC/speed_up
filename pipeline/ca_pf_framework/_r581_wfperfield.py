#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_wfperfield.py --- ★★★★★★★ **修正版：按 `band_fld` 拆成**逐场的 φ**，再调正式量具

## 上一版错在哪（R187 的教训）
`band_val` 是**逐场的 φ**（到**该场自己**界面的符号距离）。证据：
```
idx=923 ⇒ 2 条记录：val=[-3.68e-07, +3.68e-07]；fld=[0, 181]
```
⇒ **同一个胞在 `fld=0`（母相）眼里是"内"、在 `fld=181` 眼里是"外"**。
而 `(fld, idx)` 组合 = 552988 / 552988 ⇒ **完全唯一** ⇒ **快照就是按"每场一条"存的**。

**⇒ 所以正确调法是**逐场**构造 `φ_k`（只在**该场的带胞**上有值，其余 NaN），
再 `wide_face_thickness(φ_k, dx, n_hab, k)`** —— 这正合它 docstring 说的「(N,N,N) **单场**」。

⚠ 上一版把 18 个场混成一个全局 φ ⇒ `own = isfinite(p)` 覆盖全盒 ⇒ 18 个场给出**同一个数**。
"""
import os
import sys

import numpy as np

FR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FR)
import _bk_measure as BM


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk/dry_BK6/snap_00250.npz'
    dx = float(sys.argv[2]) if len(sys.argv) > 2 else 62.5e-9
    z = np.load(snap)
    N = int(z['N'])
    bc = int(z['band_cells'])
    n_hab = np.asarray(z['n_hab'], float)
    idx = np.asarray(z['band_idx']).ravel().astype(np.int64)
    val = np.asarray(z['band_val']).ravel().astype(np.float64)
    fld = np.asarray(z['band_fld']).ravel().astype(np.int32)
    reg = np.asarray(z['region'])
    outdir = '_r581_wfout'
    os.makedirs(outdir, exist_ok=True)
    tag = os.path.basename(os.path.dirname(snap)) + '_' + os.path.basename(snap)[:-4]

    print('=' * 104)
    print('★ 修正版：**逐场** φ ⇒ 仓库正式量具 `wide_face_thickness`')
    print('  快照 %s' % snap)
    print('=' * 104)
    print('  N=%d  Δx=%.2f nm  band_cells=%d（带半宽 %.0f nm）  band 记录 %d 条'
          % (N, dx * 1e9, bc, bc * dx * 1e9, idx.size))

    ks = sorted(set(int(x) for x in np.unique(reg)) - {0})
    print()
    print('  %-6s %-7s %-8s %-11s %-12s %-12s %-12s %-9s %s' %
          ('场', '变体', '胞数', '带胞数', 't_wf(nm)', 'PCA长(nm)', 'S/V厚(nm)', '长/厚', '判读'))
    print('  ' + '-' * 100)
    rows = []
    for k in ks:
        mk = (reg == k)
        nvox = int(mk.sum())
        if nvox < 20:
            continue
        # ★ 逐场 φ
        sel = (fld == k)
        if int(sel.sum()) < 50:
            print('  %-6d %-7s %-8d %-11d %s' % (k, '?', nvox, int(sel.sum()),
                                                 '⚠ 带记录太少 ⇒ 不可测'))
            continue
        p = np.full(N ** 3, np.nan)
        p[idx[sel]] = val[sel]
        phi_k = p.reshape((N, N, N))
        try:
            d = BM.wide_face_thickness(phi_k, dx, n_hab, k)
        except Exception as e:
            d = None
        t = float(d['t_wf']) * 1e9 if d else None
        nwf = d.get('n_wf') if d else None
        # PCA 最长（×1.73 均匀分布修正）
        ik = np.argwhere(mk).astype(float)
        c = ik - ik.mean(axis=0)
        ev = np.sqrt(np.maximum(np.linalg.eigvalsh(c.T @ c / max(len(c) - 1, 1)), 0))
        pca_long = float(ev.max() * 2.0 * 1.73 * dx * 1e9)
        # S/V 反解厚度（薄板 S/V ≈ 2/T）
        faces = 0
        for ax in range(3):
            faces += int(np.abs(np.diff(mk.astype(np.int8), axis=ax)).sum())
        t_sv = 2.0 / max(faces / max(nvox, 1), 1e-9) * dx * 1e9
        ratio = (pca_long / t) if (t and t > 0) else float('nan')
        rows.append((k, nvox, int(sel.sum()), t, pca_long, t_sv, ratio, nwf))
        print('  %-6d %-7s %-8d %-11d %-12s %-12.0f %-12.0f %-9s %s' %
              (k, '?', nvox, int(sel.sum()), ('%.1f' % t) if t else '**None**',
               pca_long, t_sv, ('%.2f' % ratio) if ratio == ratio else '—',
               ('✅ 薄板' if ratio >= 5 else ('⚠ 中等' if ratio >= 2 else '❌ 近等轴'))
               if ratio == ratio else '⚠ 不可测'))
    print()
    if rows:
        ts = np.array([r[3] for r in rows if r[3]], float)
        ps = np.array([r[4] for r in rows], float)
        ss = np.array([r[5] for r in rows], float)
        rs = np.array([r[6] for r in rows if r[6] == r[6]], float)
        ns = np.array([r[7] for r in rows if r[7]], float)
        print('  ── 汇总（中位；`t_wf` 可测 %d/%d 场）──' % (len(ts), len(rows)))
        if len(ts):
            print('  ★ **`t_wf`（正式量具）中位 = %.1f nm**；范围 %.1f–%.1f nm'
                  % (np.median(ts), ts.min(), ts.max()))
            print('     ★ 它是**逐场变化**的（不再是一个常数）%s'
                  % ('✅' if ts.std() > 1.0 else '❌ 仍是常数'))
            print('     宽面胞数 n_wf 中位 = %.0f' % np.median(ns))
        print('    PCA 最长 中位 = %.0f nm' % np.median(ps))
        print('    S/V 反解厚 中位 = %.0f nm' % np.median(ss))
        if len(rs):
            print('  ★ **长/厚（PCA/t_wf）中位 = %.2f**（范围 %.2f–%.2f）'
                  % (np.median(rs), rs.min(), rs.max()))
            print('    ⇒ %s' % ('✅ **是板条**' if np.median(rs) >= 5 else
                                ('⚠ 中等（2–5）' if np.median(rs) >= 2 else '❌ 近等轴')))
        # ★ 三口径一致性
        if len(ts):
            print('  ★ **三口径交叉**：t_wf=%.0f / S/V=%.0f nm ⇒ 比值 %.2f %s'
                  % (np.median(ts), np.median(ss), np.median(ts) / max(np.median(ss), 1e-9),
                     '✅ 一致（<2×）' if np.median(ts) / max(np.median(ss), 1e-9) < 2.0
                     else '⚠ 差得多 ⇒ 要查'))
        np.savetxt(os.path.join(outdir, tag + '_perfield.tsv'),
                   np.array([[r[0], r[1], r[2], r[3] or np.nan, r[4], r[5], r[6], r[7] or np.nan]
                             for r in rows]),
                   delimiter='\t', fmt='%.6g',
                   header='k\tnvox\tnband\tt_wf_nm\tpca_long_nm\tsv_thick_nm\tratio\tn_wf')
        print('    （已落盘 %s/%s_perfield.tsv）' % (outdir, tag))
    print('=' * 104)


if __name__ == '__main__':
    main()
