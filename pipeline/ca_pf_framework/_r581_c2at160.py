#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c2at160.py --- ★★★★★★★★ **在真实 10 µm 尺度上量 C2 的形状**（已校准量具）

## 为什么
之前 C2 的结论只在 **N=64（4 µm）** 上得到。而全库扫描发现**四条 N=160（10 µm）臂各跑到 600 步**，
**每条带 4 个快照（0/200/400/600）** ⇒ **共 16 个快照** ⇒ **可以在真实尺度上量**。

## 量具（**已用已知答案校准**，见 R187）
| 口径 | 校准结果（种子真值 1000×500×510 nm） | 判定 |
|---|---|---|
| **`t_wf`**（`_bk_measure.wide_face_thickness`，仓库正式量具） | **559.6 nm（+9.7%）** | **✅ 用** |
| **PCA 主轴最长**（×1.73 均匀分布修正） | **1002 nm（+0.2%）** | **✅ 用** |
| **长/厚 = PCA 最长 / `t_wf`** | — | **判据量** |
| ~~S/V 反解 `2/T`~~ | **136 nm（−73%）** | **❌ 弃用** |

## 怎么调 `t_wf`（**R187 的教训**）
快照**没有**整场 `phi`，但带**逐场**的界面带：`band_idx`/`band_val`/`band_fld`。
`band_val` 是**该场自己**的 φ ⇒ **必须按 `band_fld == k` 拆出逐场 φ**，再调量具（它要 (N,N,N) 单场）。
"""
import csv
import json
import os
import sys
import time

import numpy as np

FR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FR)
import _bk_measure as BM

ARMS = [('p2_b3', [0, 200, 400, 600]),
        ('p2_b5', [0, 200, 400, 600]),
        ('p2_b5ov', [0, 200, 400, 600]),
        ('p2_b5ps', [0, 200, 400, 600])]
ROOT = '_exp/_bk_p2'
OUT = '_r581_wfout/c2at160'


def measure(snap):
    z = np.load(snap)
    N = int(z['N'])
    L = float(z['L'])
    dx = L / N
    n_hab = np.asarray(z['n_hab'], float)
    idx = np.asarray(z['band_idx']).ravel().astype(np.int64)
    val = np.asarray(z['band_val']).ravel().astype(np.float64)
    fld = np.asarray(z['band_fld']).ravel().astype(np.int32)
    reg = np.asarray(z['region'])
    vmap = {}
    if 'vmap_keys' in z.files:
        vmap = dict(zip([int(x) for x in np.asarray(z['vmap_keys']).ravel()],
                        [int(x) for x in np.asarray(z['vmap_vals']).ravel()]))
    ks = sorted(set(int(x) for x in np.unique(reg)) - {0})
    rows = []
    for k in ks:
        mk = (reg == k)
        nvox = int(mk.sum())
        if nvox < 20:
            continue
        sel = (fld == k)
        nband = int(sel.sum())
        t = None
        nwf = None
        if nband >= 50:
            p = np.full(N ** 3, np.nan)
            p[idx[sel]] = val[sel]
            try:
                d = BM.wide_face_thickness(p.reshape((N, N, N)), dx, n_hab, k)
                if d:
                    t = float(d['t_wf'])
                    nwf = d.get('n_wf')
            except Exception:
                t = None
            del p
        # PCA（×1.73 修正 ⇒ 全长）
        ik = np.argwhere(mk).astype(float)
        c = ik - ik.mean(axis=0)
        ev = np.sqrt(np.maximum(np.linalg.eigvalsh(c.T @ c / max(len(c) - 1, 1)), 0))
        ext = ev * 2.0 * 1.73 * dx          # 三根主轴的全长（m）
        pca_long = float(ext.max())
        pca_min = float(ext.min())
        # S/V（**只作参考，已被校准否掉**）
        faces = 0
        for ax in range(3):
            faces += int(np.abs(np.diff(mk.astype(np.int8), axis=ax)).sum())
        t_sv = 2.0 / max(faces / max(nvox, 1), 1e-9) * dx
        rows.append(dict(k=k, var=vmap.get(k, '?'), nvox=nvox, nband=nband,
                         t_wf=t, n_wf=nwf, pca_long=pca_long, pca_min=pca_min,
                         t_sv=t_sv, aspect=(pca_long / t) if t else None))
    return rows, N, L, dx


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = []
    print('=' * 108)
    print('★ C2 在**真实 10 µm 尺度**上：四条 N=160 臂 × 4 个快照点（已校准量具）')
    print('=' * 108)
    for arm, steps in ARMS:
        for st in steps:
            snap = os.path.join(ROOT, 'dry_%s' % arm, 'snap_%05d.npz' % st)
            if not os.path.exists(snap):
                print('  %-9s step %-5d （缺快照）' % (arm, st))
                continue
            t0 = time.time()
            rows, N, L, dx = measure(snap)
            dt = time.time() - t0
            if not rows:
                print('  %-9s step %-5d 无场' % (arm, st))
                continue
            ts = np.array([r['t_wf'] for r in rows if r['t_wf']], float)
            asp = np.array([r['aspect'] for r in rows if r['aspect']], float)
            pl = np.array([r['pca_long'] for r in rows], float)
            summary.append(dict(arm=arm, step=st, nfield=len(rows), nt=len(ts),
                                t_wf=np.median(ts) if len(ts) else None,
                                aspect=np.median(asp) if len(asp) else None,
                                asp_max=asp.max() if len(asp) else None,
                                pca_long=np.median(pl), dt=dt, dx=dx))
            print('  %-9s step %-5d  场 %-4d  `t_wf` 可测 %-3d  中位 t_wf=%-8s  '
                  'PCA长中位=%-7.0f nm  **长/厚中位=%-6s**  最好=%-6s  (%.0f s)'
                  % (arm, st, len(rows), len(ts),
                     ('%.0f nm' % np.median(ts)) if len(ts) else '**None**',
                     np.median(pl) * 1e9,
                     ('%.2f' % np.median(asp)) if len(asp) else '—',
                     ('%.2f' % asp.max()) if len(asp) else '—', dt))
            with open(os.path.join(OUT, '%s_%05d.tsv' % (arm, st)), 'w',
                      encoding='utf-8') as f:
                f.write('k\tvar\tnvox\tnband\tt_wf_nm\tn_wf\tpca_long_nm\tpca_min_nm\t'
                        't_sv_nm\taspect\n')
                for r in rows:
                    f.write('%d\t%s\t%d\t%d\t%s\t%s\t%.1f\t%.1f\t%.1f\t%s\n'
                            % (r['k'], r['var'], r['nvox'], r['nband'],
                               ('%.1f' % (r['t_wf'] * 1e9)) if r['t_wf'] else 'None',
                               r['n_wf'] if r['n_wf'] else '',
                               r['pca_long'] * 1e9, r['pca_min'] * 1e9, r['t_sv'] * 1e9,
                               ('%.3f' % r['aspect']) if r['aspect'] else 'None'))
    print()
    print('=' * 108)
    print('  ── **汇总（按臂）**──')
    print('  %-9s %-7s %-8s %-11s %-11s %-11s %-9s %s' %
          ('臂', 'step', '场数', 't_wf中位(nm)', 'PCA长中位(nm)', '长/厚中位', '最好长/厚', 'Δx(nm)'))
    print('  ' + '-' * 100)
    for s in summary:
        print('  %-9s %-7d %-8d %-11s %-11.0f %-11s %-9s %.2f' %
              (s['arm'], s['step'], s['nfield'],
               ('%.0f' % (s['t_wf'] * 1e9)) if s['t_wf'] else 'None',
               s['pca_long'] * 1e9,
               ('%.2f' % s['aspect']) if s['aspect'] else '—',
               ('%.2f' % s['asp_max']) if s['asp_max'] else '—', s['dx'] * 1e9))
    print()
    # 与 N=64 的对照
    print('  ── ★ 与 **N=64（4 µm）** 的对照（R187 的 `BK6`/`BK7`，step 250）──')
    print('     `BK6`：`t_wf` **947 nm**、PCA 长 **2744 nm**、**长/厚 2.56**（最好 14.56）')
    print('     `BK7`：`t_wf` **942 nm**、PCA 长 **2640 nm**、**长/厚 2.97**（最好  9.43）')
    print()
    with open(os.path.join(OUT, 'SUMMARY.csv'), 'w', encoding='utf-8') as f:
        f.write('arm,step,nfield,nt_measurable,t_wf_nm,aspect_med,aspect_max,'
                'pca_long_nm,dx_nm\n')
        for s in summary:
            f.write('%s,%d,%d,%d,%s,%s,%s,%.1f,%.4f\n'
                    % (s['arm'], s['step'], s['nfield'], s['nt'],
                       ('%.1f' % (s['t_wf'] * 1e9)) if s['t_wf'] else '',
                       ('%.3f' % s['aspect']) if s['aspect'] else '',
                       ('%.3f' % s['asp_max']) if s['asp_max'] else '',
                       s['pca_long'] * 1e9, s['dx'] * 1e9))
    print('  （逐场明细 + SUMMARY.csv 已落盘 %s/）' % OUT)
    print('=' * 108)


if __name__ == '__main__':
    main()
