#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_arms4ans.py --- 四条 N=160 臂的**完整答问**（块 / 每块板条数 / 长宽比 / 是否还在长）

## 口径（**先写死**，来自 `_bk_measure.py:305-334` 的 R30 J-1）
* **块** = 同一个**变体**在 `region` 上 **6-连通**的一块
* **板条** = 块内的一个**场**（`vmap[k] = v`）⇒ `blk_laths` = 该块的**板条根数**
* `nblk_sig` = **显著**块数（≥ `min_vox` 体素）
* `n_var_sig` = 实测用到的**变体数**；`n_habit` = **惯习面种类数**
* `r_selfac` = 用**实测**体积分数算的自协调残差

## ⚠ 长宽比**不用** `blk_alen_nm`/`blk_wlen_nm`
`_bk_measure.py:210` 逐字：**「包围盒跨度（`n_lath`/`blk_alen_nm`）❌ 会（实测放大 2.5–2.8×）」**
⇒ 那是与 `n_lath` **同一类**伪影 ⇒ 长宽比只用本轮的 **`t_wf` + PCA**（已校准）。
"""
import csv
import json
import os
import sys

import numpy as np

ARMS = ['p2_b3', 'p2_b5', 'p2_b5ov', 'p2_b5ps']
ROOT = '_exp/_bk_p2'


def load(tag):
    d = os.path.join(ROOT, 'dry_' + tag)
    m = json.load(open(os.path.join(d, 'meta.json'), encoding='utf-8', errors='replace'))
    rows = list(csv.DictReader(open(os.path.join(d, 'series.csv'),
                                    encoding='utf-8', errors='replace')))
    return m, rows


def f(x, d=None):
    try:
        return float(x)
    except Exception:
        return d


def main():
    print('=' * 108)
    print('① 四条臂的**唯一区别**（把 `exp_args` 当 dict 读）')
    print('=' * 108)
    metas, rowsd = {}, {}
    for t in ARMS:
        metas[t], rowsd[t] = load(t)
    args = {}
    for t in ARMS:
        ea = metas[t].get('exp_args')
        if isinstance(ea, dict):
            args[t] = {k: ea[k] for k in ea}
        elif isinstance(ea, str):
            try:
                args[t] = json.loads(ea.replace("'", '"'))
            except Exception:
                args[t] = {}
        else:
            args[t] = {}
        if not args[t]:
            # 退回 meta 顶层
            args[t] = {k: v for k, v in metas[t].items() if not k.startswith('sha_')}
    keys = set()
    for a in args.values():
        keys |= set(a.keys())
    print('  `exp_args` 共 %d 个键；**取值不同**的：' % len(keys))
    print('  %-22s %s' % ('键', '  |  '.join('%-14s' % t for t in ARMS)))
    print('  ' + '-' * 104)
    ndiff = 0
    for k in sorted(keys):
        vals = [str(args[t].get(k, '—'))[:14] for t in ARMS]
        if len(set(vals)) > 1:
            ndiff += 1
            print('  **%-20s** %s' % (k[:20], '  |  '.join('%-14s' % v for v in vals)))
    print('  ⇒ **不同的键 %d 个**（其余 %d 个**逐字相同**）' % (ndiff, len(keys) - ndiff))
    print()
    print('=' * 108)
    print('② **块结构**（`--pair-every` 落盘的那些行；块 = 同变体的 6-连通区）')
    print('=' * 108)
    for t in ARMS:
        rows = rowsd[t]
        k = list(rows[0].keys())[0]
        pr = [r for r in rows if (r.get('blk_laths') or '').strip()]
        print('  ── **%s**（%d 个块表行）──' % (t, len(pr)))
        if not pr:
            print('     （没有块表行）')
            continue
        print('     %-6s %-9s %-9s %-24s %-24s %-8s %-8s %s' %
              ('step', '显著块', '变体数', '每块板条数(blk_laths)', '每块变体(blk_vars)',
               '惯习面', 'r_self', 'nslab_n/n1'))
        for r in pr:
            print('     %-6s %-9s %-9s %-24s %-24s %-8s %-8s %s/%s' %
                  (r[k], r.get('nblk_sig', '—'), r.get('n_var_sig', '—'),
                   r.get('blk_laths', '')[:24], r.get('blk_vars', '')[:24],
                   r.get('n_habit', '—'), (r.get('r_selfac') or '')[:6],
                   r.get('nslab_n', '—'), r.get('nslab_n1', '—')))
        last = pr[-1]
        bl = [int(x) for x in last['blk_laths'].split('/') if x]
        print('     ⇒ **末态：%d 个显著块，每块板条数 = %s（共 %d 根）**'
              % (int(f(last.get('nblk_sig'), 0)), bl, sum(bl)))
        print()
    print('=' * 108)
    print('③ **长宽比**（用已校准的 `t_wf` + PCA；**不用** `blk_*len_nm`）')
    print('=' * 108)
    sp = '_r581_wfout/c2at160/SUMMARY.csv'
    rr = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace')))
    print('  %-9s %-7s %-7s %-11s %-12s %-11s %-11s %s' %
          ('臂', 'step', '场数', 't_wf(nm)', 'PCA长(nm)', '长/厚中位', '最好长/厚', '（对照）blk_alen/wlen'))
    print('  ' + '-' * 100)
    for r in rr:
        blkref = ''
        rows = rowsd.get(r['arm'], [])
        k = list(rows[0].keys())[0] if rows else None
        for x in rows:
            if k and x[k] == r['step'] and (x.get('blk_alen_nm') or '').strip():
                blkref = '%s / %s' % (x['blk_alen_nm'][:14], x['blk_wlen_nm'][:14])
                break
        print('  %-9s %-7s %-7s %-11s %-12s %-11s %-11s %s' %
              (r['arm'], r['step'], r['nfield'], r['t_wf_nm'], r['pca_long_nm'],
               r['aspect_med'], r['aspect_max'], blkref))
    print()
    print('  ★ **读法**：`blk_alen/wlen` 是**包围盒跨度** ⇒ 比 `t_wf` 粗（**放大 2.5–2.8×**，见 `_bk_measure.py:210`）')
    print('     ⇒ **长宽比以 `长/厚中位`（PCA / `t_wf`）为准**')
    print()
    print('=' * 108)
    print('④ **生长是否还在继续**（`Vt` 的增量趋势）')
    print('=' * 108)
    print('  %-9s %-26s %-26s %s' % ('臂', 'Vt 末200步增量', '前段/后段增量', '判读'))
    print('  ' + '-' * 96)
    for t in ARMS:
        rows = rowsd[t]
        k = list(rows[0].keys())[0]
        vs = [(f(r[k]), f(r['Vt'])) for r in rows if f(r[k]) is not None and f(r['Vt'])]
        last = vs[-1][0]
        seg = [v for s, v in vs if s >= last - 200]
        half = len(seg) // 2
        r1 = (seg[half] - seg[0]) / seg[0] if half else 0
        r2 = (seg[-1] - seg[half]) / seg[half] if half else 0
        rel = (seg[-1] - seg[0]) / seg[0]
        if r2 > 0.02 and r2 >= 0.7 * max(r1, 1e-12):
            v = '**仍在长**（后段 ≥ 前段 70%）'
        elif r2 > 0.02:
            v = '**在减速**（后段 < 前段 70%）'
        elif r2 > 0:
            v = '**接近停**（后段 <2%）'
        else:
            v = '**已停滞/回落**（后段 ≤0）'
        print('  %-9s %-26s %-26s %s' %
              (t, '%+.3e（%+.2f%%）' % (seg[-1] - seg[0], rel * 100),
               '前 %+.2f%% / 后 %+.2f%%' % (r1 * 100, r2 * 100), v))
    print()
    print('  ── `Vt` 全程轨迹（每 100 步，m³）──')
    for t in ARMS:
        rows = rowsd[t]
        k = list(rows[0].keys())[0]
        pts = ['%.3g' % f(r['Vt']) for r in rows
               if f(r[k]) is not None and f(r[k]) % 100 == 0]
        print('  %-9s %s' % (t, ' → '.join(pts)))
    print()
    print('  ── 形核事件是否还在发生（`nf3` 与 `nlath` 趋势）──')
    for t in ARMS:
        rows = rowsd[t]
        k = list(rows[0].keys())[0]
        pts = ['%.0f' % f(r['nf3'], -1) for r in rows
               if f(r[k]) is not None and f(r[k]) % 200 == 0 and 'nf3' in r]
        print('  %-9s nf3: %s' % (t, ' → '.join(pts)))
    print('=' * 108)


if __name__ == '__main__':
    main()
