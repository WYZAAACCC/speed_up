#!/usr/bin/env python3
"""R50: cln11 的"块"结论必须**在两个口径下都成立**才算数。
  旧口径 nslab_n/nf3_col（r_col=300 nm 硬编码、min_run=2）
  新口径 nslab_n1/nf3_col1（自适应柱半径、min_run=1）+ 可见性守卫 r_col_nm/col_cover_min
⚠ 语义更正（自查）：`runs` 是**每段的长度（体素数）列表**，
  而**不是**"每根场被切成的段数"（`_bk_measure.py:835` `out['nslab_n'] = len(runs)`）。
  上一版我按名字猜语义，差点写出"cln11 是碎片化结构"的**错误结论**。
"""
import csv
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
rows = list(csv.DictReader(open('_exp/_bk_closed/dry_cln11/series.csv')))
print('  %-6s %-8s %-8s %-9s %-9s %-8s %-10s %-12s %s'
      % ('step', 'nslab_n', 'nslab_n1', 'nf3_col', 'nf3_col1', 'r_col_nm',
         'col_cover', 'runs_len_sum', 'runs'))
for i, r in enumerate(rows):
    if i % 4 and i != len(rows) - 1:
        continue
    rl = [int(x) for x in r.get('runs', '').split('/') if x]
    print('  %-6s %-8s %-8s %-9s %-9s %-8s %-10s %-12s %s'
          % (r['step'], r['nslab_n'], r.get('nslab_n1', ''), r['nf3_col'],
             r.get('nf3_col1', ''), r.get('r_col_nm', ''),
             r.get('col_cover_min', ''), sum(rl), r.get('runs', '')[:26]))
print()
last = rows[-1]
print('=== 末态判读')
print('  M=%s  在位场=%s' % (last['M'], last.get('nreg_used')))
print('  nslab_n=%s  nslab_n1=%s   (两者一致才好)' % (last['nslab_n'], last.get('nslab_n1')))
print('  nf3_col=%s  nf3_col1=%s' % (last['nf3_col'], last.get('nf3_col1')))
rl = [int(x) for x in last['runs'].split('/') if x]
print('  柱上段长（体素）=%s  ⇒ ×125nm = %s nm'
      % (rl, [x * 125 for x in rl]))
print('  段数 = %d，其中相邻同变体对 = %s' % (len(rl), last['nf3_col']))
print()
print('=== 全程序列：nslab_n / nf3_col 是否始终 nf3_col == nslab_n-1')
bad = [r['step'] for r in rows
       if r['nslab_n'] and r['nf3_col'] != str(int(r['nslab_n']) - 1)]
print('  违反 nf3_col == nslab_n-1 的步: %s' % (bad[:10] if bad else '无 ✅'))
