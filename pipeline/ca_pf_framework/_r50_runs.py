#!/usr/bin/env python3
"""R50: cln11 的柱剖面细查 —— `nslab_n`/`nf3_col` 是不是被碎片骗了？
⚠ 自查：上一步我只看 `nslab_n`/`nf3_col` 就准备写"干净的 1→10 阶梯"。
   但运行日志里 `runs=9/7/5/3/1/1/4/6/8/9`（**每根场沿柱被切成的段数**）
   与 `nc=0..549`（**549 个分量**）都在说"这是碎的不是整的"。
   ⇒ 先把 `runs`/`col_cover_min`/`ncomp*` 一起看完再下结论。
"""
import csv
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
rows = list(csv.DictReader(open('_exp/_bk_closed/dry_cln11/series.csv')))
cols = ['step', 'nslab_n', 'nf3_col', 'runs', 'r_col_nm', 'col_cover_min',
        'ncomp_min', 'ncomp_max', 'ncompbig_max', 'box_touch', 'Vt']
cols = [c for c in cols if c in rows[0]]
print('  ' + ' '.join('%-13s' % c for c in cols))
for i, r in enumerate(rows):
    if i % 4 == 0 or i == len(rows) - 1:
        print('  ' + ' '.join('%-13s' % str(r.get(c, ''))[:13] for c in cols))
print()
print('=== 判读')
r0, rl = rows[0], rows[-1]
print('  首末 nslab_n: %s → %s   (M=%s)' % (r0['nslab_n'], rl['nslab_n'], rl['M']))
print('  首末 nf3_col: %s → %s' % (r0['nf3_col'], rl['nf3_col']))
print('  首末 runs   : %s → %s' % (r0['runs'], rl['runs']))
print('  首末 显著分量: %s → %s' % (r0['ncompbig_max'], rl['ncompbig_max']))
print('  首末 分量上限: %s → %s' % (r0['ncomp_max'], rl['ncomp_max']))
print('  首末 柱覆盖最小: %s → %s' % (r0.get('col_cover_min'), rl.get('col_cover_min')))
nruns = [len([x for x in r['runs'].split('/') if x]) for r in rows]
print('  runs 字段个数（=在位场数）: %d → %d' % (nruns[0], nruns[-1]))
tot = []
for r in rows:
    tot.append(sum(int(x) for x in r['runs'].split('/') if x))
print('  runs 总和（=柱上被穿越的总段数）: %d → %d' % (tot[0], tot[-1]))
print()
print('  ⚠ 若 "runs 总和" 远大于 "在位场数"，说明**每根场在柱上被切成多段**')
print('     ⇒ 那**不是**"M 根完整板条堆叠"，而是**碎片化结构**。')
