#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_obs.py --- ★★★★★ 「三件事」的**持续观测器**（用户逐字要求全程观测）

## 用户要观测的三件事 → 对应的量（**含量具出处与已知偏差**）
| # | 观测对象 | 用什么量 | 量具出处 / 已知问题 |
|---|---|---|---|
| **①** | **单根板条生长（三维几何量、长宽比）** | `nslab_n`（板条数）、`vols`（逐根体积）、`blk_alen_nm`/`blk_wlen_nm`（面内长/宽）、**`t_wf − Δx`**（厚度）| ⚠ **不能用 `ths`/`n_lath`**（包围盒跨度，非厚度）；⚠ **`t_wf` 有恒定 +1Δx 偏差** ⇒ 必须减 |
| **②** | **多根是否正确堆叠成块、块内低角晶界** | `nblk_sig`（显著块数）、`blk_laths`（每块板条根数）、`nf3`/`f3_area_m2`（**F3 = 低角晶界**）、`nf3_col`/`runs` | 逐行非空率 99.7%（已验）|
| **③** | **块与块是否相互影响** | **`nf2`/`f2_area_m2`（F2 = 异变体界面 = "块相遇"的签名）**、`n_var_sig`、`f_var`、`r_selfac` | `nf2` 是 R31 新增量具 ⇒ **abA 里最大 1009** |

## 判据⑤⑥ 的指示量
* **⑤ 填满盒子**：`Vt / V0`（转变分数）、`box_touch`（**是否碰到盒面**）、`f1_area`（母相剩余）
* **⑥ 涌现自协调**：`r_selfac`（**实测自协调残差**；单变体=1.0、多变体协同⇒下降）、`f_var`（变体分布）
"""
import csv
import glob
import os
import sys

COLS = ['step', 'Vt', 'nslab_n', 'nslab_n1', 'nf3', 'nf3_col', 'nf2', 'nblk_sig',
        'blk_laths', 'f_var', 'n_var_sig', 'r_selfac', 'box_touch', 'box_touch_core',
        'blk_alen_nm', 'blk_wlen_nm', 'ths']


def show(tag, path, tailn=10):
    if not os.path.exists(path):
        print('  %-7s ⚠ 没有 series.csv' % tag)
        return
    rows = list(csv.DictReader(open(path, encoding='utf-8', errors='replace')))
    if not rows:
        print('  %-7s ⚠ 空' % tag)
        return
    r0, rl = rows[0], rows[-1]
    print('  ── %s：%d 行，step %s → %s ──' % (tag, len(rows), r0.get('step'), rl.get('step')))

    def f(r, k):
        v = (r.get(k) or '').strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return v
    v0, vl = f(r0, 'Vt'), f(rl, 'Vt')
    if isinstance(v0, float) and isinstance(vl, float) and v0:
        print('     ⑤ 填充分数 Vt/V0 = %.4f%% → **%.4f%%**' % (100 * v0 / 3.0679e-16,
                                                              100 * vl / 3.0679e-16))
    for k in COLS:
        a, b = f(r0, k), f(rl, k)
        if a is None and b is None:
            continue
        print('     %-14s %s → %s' % (k, str(a)[:30], str(b)[:30]))
    # ★ 逐行看趋势（末 tailn 行）
    print('     ── 末 %d 行的关键趋势 ──' % tailn)
    hdr = ['step', 'Vt', 'nslab_n', 'nblk_sig', 'nf3', 'nf2', 'r_selfac', 'box_touch']
    print('        ' + ' '.join('%-11s' % h[:11] for h in hdr))
    for r in rows[-tailn:]:
        print('        ' + ' '.join('%-11s' % ((r.get(h) or '')[:11]) for h in hdr))


def main():
    print('=' * 100)
    print('实验(5) 「三件事」观测  %s' % __import__('time').strftime('%F %T'))
    print('=' * 100)
    any_ = False
    for tag in sys.argv[1:] or ['t5L62', 't5L0']:
        for base in ('_exp/_bk_t5/dry_%s' % tag,):
            p = os.path.join(base, 'series.csv')
            if os.path.exists(p):
                any_ = True
                show(tag, p)
                ck = os.path.join(base, 'ckpt')
                if os.path.isdir(ck):
                    fs = sorted(os.listdir(ck))
                    print('     ckpt: %d 个 %s' % (len(fs), fs[:4]))
                sn = sorted(glob.glob(os.path.join(base, 'snap_*.npz')))
                if sn:
                    print('     snap: %d 个（末 %s，%.1f MB）'
                          % (len(sn), os.path.basename(sn[-1]),
                             os.path.getsize(sn[-1]) / 1048576.0))
    if not any_:
        print('  ⚠ 两臂都还没有 series.csv ⇒ 仍在构造期')
    print('=' * 100)


if __name__ == '__main__':
    main()
