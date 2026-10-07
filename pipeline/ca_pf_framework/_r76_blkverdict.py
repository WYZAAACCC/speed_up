#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r76_blkverdict.py —— **R76：多块构型的判据口径复核（不跑仿真，只重读原始数据）**

## 为什么需要这个

R75 的判决行用的是**全局** `nslab_n`（沿**单一** n*、以**全体板条并集质心**为轴的柱剖面）。
在多块构型里这个口径**结构性地不成立**，两处独立原因：

  1. **轴心**：`column_profile` 的柱心 = `allowed`（= **两个块的全部场**）的质心
     ⇒ 恰落在**两块之间的空隙**里（R75 几何：块心 y=1.75/4.25 µm ⇒ 并集质心 y=3.0 µm）。
  2. **轴向**：柱轴只用 `laths[0]` 的 n*（`_bk_exp.py:413`）⇒ 块 1（镜面变体）的
     堆叠轴与之不同，投影必然弥散。

`_bk_measure.blocks()` 里**已有**逐块口径（R31 加的，`blk_nlath`/`blk_nprof`/`blk_nruns`），
但 R75 的判据没吃它。本脚本**只重读 F 盘上的原始 CSV**，把三种口径并排，
回答一个问题：**R75 的 `nslab_n=1` 是物理失败，还是量具口径错？**

## 三种口径（必须区分清楚）

| 列 | 定义 | 多块下是否有效 | 退化风险 |
|---|---|---|---|
| `nslab_n` | 全局柱、并集质心、`laths[0]` 的 n* | ❌ **无效** | — |
| `blk_nlath` | 该块连通分量**覆盖了几个场** | ✅ 有效 | **退化**：场只要有一个胞在分量里就计数 ⇒ 层并成一片也照样报 3 |
| `blk_nprof` | 逐块、沿**该块自己的 n***投影分箱后**众数里出现过几个不同场** | ✅ 有效 | 弱：一个场只要当过**一个箱**的众数就计数 |
| `blk_nruns` | 同上，但数**连续段** | ✅ 有效 | **多读**：分箱众数抖动会把一段劈成两段（实测 `mb1s`：真值 3 → 5~6） |

⇒ **判据应当看 `blk_nprof`**（几何的、且对分箱噪声免疫），
   `blk_nlath` 作**上界**、`blk_nruns` 作**诊断**。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')

COLS = ['step', 'Vt', 'nslab_n', 'nf3_col', 'runs',
        'blk_laths', 'blk_nlath', 'blk_nprof', 'blk_nruns', 'blk_vars',
        'nblk_sig', 'blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm',
        'box_touch_core', 'nf2', 'f_flat', 'r_selfac', 'E_el_J']
# 判据阈值（**先写死**，与 BLOCK_SELFAC.md §8 的 W-1..W-4 同族）
F_FLAT_MIN = 0.08


def read(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return rows


def fnum(r, c):
    v = r.get(c, '')
    try:
        return float(v)
    except (TypeError, ValueError):
        return float('nan')


def per_block_nums(s):
    """`'3/3'` -> `[3, 3]`；`''` -> `[]`。"""
    s = (s or '').strip()
    if not s:
        return []
    out = []
    for t in s.split('/'):
        t = t.strip()
        if not t:
            continue
        try:
            out.append(int(float(t)))
        except ValueError:
            out.append(-1)
    return out


def report(tag):
    p = os.path.join(MB, 'dry_%s' % tag, 'series.csv')
    if not os.path.exists(p):
        print('  %-10s （无 series.csv）' % tag)
        return None
    rows = read(p)
    hdr = rows[0]
    if 'blk_nprof' not in hdr:
        print('  %-10s ⚠ 无 `blk_nprof` 列（该算例早于 R31 量具）' % tag)
        return None
    print('=' * 108)
    print('### %s   （%d 行，step %s → %s）' % (tag, len(rows),
                                               rows[0]['step'], rows[-1]['step']))
    print('  ' + ' '.join('%-11s' % c for c in COLS[:6]))
    for r in rows[::max(1, len(rows) // 6)][:7]:
        print('  ' + ' '.join('%-11s' % str(r.get(c, ''))[:11] for c in COLS[:6]))
    print()
    print('  ---- **逐块口径**（R31 量具，沿**每块自己的 n***）----')
    print('  %-6s %-9s %-9s %-9s %-9s %-9s %s'
          % ('step', 'nblk_sig', 'blk_vars', 'nlath', 'nprof', 'nruns', 'span_nm'))
    for r in rows[::max(1, len(rows) // 8)][:9] + [rows[-1]]:
        print('  %-6s %-9s %-9s %-9s %-9s %-9s %s'
              % (r['step'], r.get('nblk_sig', ''), r.get('blk_vars', ''),
                 r.get('blk_nlath', ''), r.get('blk_nprof', ''),
                 r.get('blk_nruns', ''), r.get('blk_span_nm', '')))
    # ---- 终态判读 ----
    last = rows[-1]
    nprof = per_block_nums(last.get('blk_nprof'))
    nlath = per_block_nums(last.get('blk_nlath'))
    nrun = per_block_nums(last.get('blk_nruns'))
    nblk = int(fnum(last, 'nblk_sig'))
    nf2 = fnum(last, 'nf2')
    nf2_0 = fnum(rows[0], 'nf2')
    ff = fnum(last, 'f_flat')
    touch = max(fnum(r, 'box_touch_core') for r in rows)
    print()
    print('  ---- 判读 ----')
    print('  nblk_sig            = %d   （应为 2）' % nblk)
    print('  blk_nlath  （上界） = %s' % nlath)
    print('  blk_nprof  （**主**）= %s   ← 逐块沿自己 n* 的柱里出现过的场数' % nprof)
    print('  blk_nruns  （诊断） = %s' % nrun)
    print('  nslab_n    （无效） = %s' % last.get('nslab_n'))
    print('  nf2   %s → %s' % (nf2_0, nf2))
    print('  f_flat 终态 = %.4f  （判据 >= %.2f）' % (ff, F_FLAT_MIN))
    print('  box_touch_core 全程 max = %s' % touch)
    ok_nb = (nblk == 2)
    ok_3 = all(x == 3 for x in nprof) and len(nprof) == 2
    ok_ff = (ff >= F_FLAT_MIN)
    print('  [B-1 两块初始分离]  nf2(t=0) = %s  ⇒ %s'
          % (nf2_0, 'PASS' if nf2_0 == 0 else 'FAIL'))
    print('  [B-2 两块相互作用]  nf2 增 = %s  ⇒ %s'
          % (nf2 > nf2_0, 'PASS' if nf2 > nf2_0 else 'FAIL'))
    print('  [B-3 保面]          f_flat = %.4f  ⇒ %s'
          % (ff, 'PASS' if ok_ff else 'FAIL'))
    print('  [B-4 不撞壁]        max = %s  ⇒ %s'
          % (touch, 'PASS' if touch == 0 else 'FAIL'))
    print('  [① 板条可分辨 ×2块] blk_nprof = %s  ⇒ %s'
          % (nprof, 'PASS' if ok_3 else 'FAIL'))
    print('  [② 各块 3 根]       nblk_sig = %d  ⇒ %s'
          % (nblk, 'PASS' if ok_nb else 'FAIL'))
    return dict(tag=tag, nblk=nblk, nprof=nprof, nlath=nlath, nrun=nrun,
                nf2=nf2, nf2_0=nf2_0, ff=ff, touch=touch)


def main():
    tags = sys.argv[1:] or ['mb2fp10', 'mb2fp0']
    res = {}
    for t in tags:
        r = report(t)
        if r:
            res[t] = r
    if len(res) == 2:
        a, b = (res.get(t) for t in tags[:2])
        print()
        print('=' * 108)
        print('### 对照（保面 vs 不保面）')
        print('  %-22s %-14s %-14s' % ('量', tags[0], tags[1]))
        for k, lab in (('nblk', 'nblk_sig'), ('nprof', 'blk_nprof'),
                       ('nlath', 'blk_nlath'), ('nrun', 'blk_nruns'),
                       ('nf2', 'nf2 终态'), ('ff', 'f_flat 终态')):
            if a is None or b is None:
                continue
            print('  %-22s %-14s %-14s' % (lab, a[k], b[k]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
