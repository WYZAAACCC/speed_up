#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_arms4qa.py --- 回答四个问题（全部从落盘数据读）
① 四条 N=160 臂的**唯一区别**是什么（从 `meta.json` 的 `exp_args` 逐字比）
② 各形成**多少块**、**每块几根马氏体**（看块级列有没有落盘）
③ 各臂的**长宽比**（用已落盘的 `_r581_wfout/c2at160/SUMMARY.csv`）
④ 生长**还在继续还是已结束**（`Vt` 的增量趋势）
"""
import csv
import glob
import json
import os
import sys

import numpy as np

ARMS = ['p2_b3', 'p2_b5', 'p2_b5ov', 'p2_b5ps']
ROOT = '_exp/_bk_p2'


def load(tag):
    d = os.path.join(ROOT, 'dry_' + tag)
    mp, sp = os.path.join(d, 'meta.json'), os.path.join(d, 'series.csv')
    m = json.load(open(mp, encoding='utf-8', errors='replace')) if os.path.exists(mp) else {}
    rows = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace'))) \
        if os.path.exists(sp) else []
    return d, m, rows


def main():
    print('=' * 106)
    print('① 四条 N=160（10 µm）臂的**唯一区别**')
    print('=' * 106)
    metas = {}
    for t in ARMS:
        d, m, rows = load(t)
        metas[t] = m
    # 找所有键，逐键比较
    keys = set()
    for m in metas.values():
        keys |= set(m.keys())
    diff = []
    for k in sorted(keys):
        vals = [str(metas[t].get(k, '（无）'))[:60] for t in ARMS]
        if len(set(vals)) > 1:
            diff.append((k, vals))
    print('  `meta.json` 共 %d 个键；**取值不同的键 = %d 个**：' % (len(keys), len(diff)))
    if diff:
        print('  %-18s %s' % ('键', '  |  '.join('%-16s' % t for t in ARMS)))
        print('  ' + '-' * 100)
        for k, vals in diff[:14]:
            print('  %-18s %s' % (k[:18], '  |  '.join('%-16s' % v[:16] for v in vals)))
    else:
        print('    （`meta.json` 里**没有**不同的键 ⇒ 区别在 `exp_args`（下一节））')
    print()
    print('  ── `exp_args`（命令行逐字）──')
    for t in ARMS:
        ea = metas[t].get('exp_args')
        if isinstance(ea, list):
            ea = ' '.join(str(x) for x in ea)
        s = str(ea)
        # 只显示可能不同的部分
        keep = [x for x in s.split() if any(w in x for w in
                ('nuc', 'block', 'laths', 'target', 'refill', 'init', 'every', 'steps'))]
        print('  %-9s %s' % (t, ' '.join(keep)[:150] if keep else s[:150]))
    print()
    print('  ── 逐条臂的**形核相关设置** ──')
    showk = ['nuc_block_target', 'nuc_init', 'nuc_sites_refill', 'nuc_law',
             'nuc_overlap_nm', 'nuc_shape', 'laths_n', 'every', 'steps', 'N']
    print('  %-9s %s' % ('臂', '  '.join('%-13s' % k[:13] for k in showk)))
    for t in ARMS:
        m = metas[t]
        print('  %-9s %s' % (t, '  '.join('%-13s' % str(m.get(k, '—'))[:13] for k in showk)))
    print()
    print('=' * 106)
    print('② 块结构：有哪些块级列**落了盘**')
    print('=' * 106)
    d, m, rows = load(ARMS[0])
    hdr = list(rows[0].keys())
    blk = [c for c in hdr if c.startswith('blk_') or c in
           ('r_selfac', 'n_habit', 'f_var', 'n_var_sig', 'nslab_n', 'nslab_n1',
            'nslab_nu', 'nslab_nu1', 'ncomp_max', 'ncompbig_max')]
    print('  `series.csv` 共 %d 列' % len(hdr))
    print('  与"块/变体"有关的列：%s' % (', '.join(blk) if blk else '**无**'))
    print()
    # 每个列在末行的取值 + 非空行数
    print('  %-16s %-9s %s' % ('列', '非空行', '末行取值'))
    print('  ' + '-' * 60)
    for c in blk:
        nz = sum(1 for r in rows if (r.get(c) or '').strip())
        print('  %-16s %-9d %s' % (c, nz, (rows[-1].get(c) or '（空）')[:60]))
    print()
    print('=' * 106)
    print('③ 每条臂的**长宽比**（已落盘，`_r581_wfout/c2at160/SUMMARY.csv`）')
    print('=' * 106)
    sp = '_r581_wfout/c2at160/SUMMARY.csv'
    if os.path.exists(sp):
        rr = list(csv.DictReader(open(sp, encoding='utf-8', errors='replace')))
        print('  %-9s %-7s %-9s %-11s %-11s %-11s %s' %
              ('臂', 'step', '场数', 't_wf(nm)', 'PCA长(nm)', '长/厚中位', '最好长/厚'))
        print('  ' + '-' * 84)
        for r in rr:
            if r['step'] in ('0', '600'):
                print('  %-9s %-7s %-9s %-11s %-11s %-11s %s' %
                      (r['arm'], r['step'], r['nfield'], r['t_wf_nm'],
                       r['pca_long_nm'], r['aspect_med'], r['aspect_max']))
    print()
    print('=' * 106)
    print('④ 生长**还在继续还是已结束**（`Vt` 的增量）')
    print('=' * 106)
    print('  %-9s %-30s %-30s %s' %
          ('臂', 'Vt 后 200 步的增量', '相对增量', '判读'))
    print('  ' + '-' * 92)
    for t in ARMS:
        d, m, rows = load(t)
        k = list(rows[0].keys())[0]
        vs = []
        for r in rows:
            try:
                vs.append((float(r[k]), float(r['Vt'])))
            except Exception:
                pass
        if not vs:
            print('  %-9s （无 Vt）' % t)
            continue
        last = vs[-1][0]
        seg = [v for s, v in vs if s >= last - 200]
        if len(seg) >= 2:
            d_abs = seg[-1] - seg[0]
            d_rel = d_abs / max(seg[0], 1e-30)
            # 后半段与前半段比
            half = len(seg) // 2
            r1 = (seg[half] - seg[0]) / max(seg[0], 1e-30) if half else 0
            r2 = (seg[-1] - seg[half]) / max(seg[half], 1e-30) if half else 0
            verdict = ('**仍在长**（后段增量 ≥ 前段 70%%）' if r2 >= 0.7 * max(r1, 1e-12)
                       else '**在减速**（后段 < 前段 70%）')
            print('  %-9s %-30s %-30s %s' %
                  (t, '%+.4e m³（%+.4g%%）' % (d_abs, d_rel * 100),
                   '前段 %+.3g%% / 后段 %+.3g%%' % (r1 * 100, r2 * 100), verdict))
    print()
    print('  ── Vt 的完整轨迹（每 100 步，m³）──')
    for t in ARMS:
        d, m, rows = load(t)
        k = list(rows[0].keys())[0]
        pts = []
        for r in rows:
            try:
                s = float(r[k])
                if s % 100 == 0 or s == 0:
                    pts.append('%.3g' % float(r['Vt']))
            except Exception:
                pass
        print('  %-9s %s' % (t, ' → '.join(pts)))
    print('=' * 106)


if __name__ == '__main__':
    main()
