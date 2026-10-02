#!/bin/bash
# _t5_blk_correct.sh --- ★ 纠正我自己的第二个量具错：只看末行就断言"全空"
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
$PY - <<'PYEOF'
import csv
from collections import Counter
p = '_exp/_bk_mb/dry_abA/series.csv'
rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
BLK = ['nblk_sig','blk_laths','blk_vars','n_var_sig','n_habit','f_var','r_selfac',
       'blk_nlath','blk_span_nm','blk_alen_nm','blk_wlen_nm','blk_nprof','blk_nruns']
print('=' * 92)
print('★ 纠正：abA 的块表列**逐行统计**（不是只看末行）')
print('=' * 92)
print('  总行数 = %d' % len(rows))
print()
print('  %-16s %8s %8s %8s   %s' % ('列','非空行','空行','非空率','不同取值数'))
print('  ' + '-' * 76)
for c in BLK:
    if c not in rows[0]:
        print('  %-16s （无此列）' % c); continue
    vals = [(r.get(c) or '').strip() for r in rows]
    nz = [v for v in vals if v != '']
    print('  %-16s %8d %8d %7.1f%%   %d'
          % (c, len(nz), len(vals)-len(nz), 100.0*len(nz)/len(vals), len(set(nz))))
print()
print('  ── nblk_sig 的取值分布（块数）──')
c = Counter((r.get('nblk_sig') or '').strip() for r in rows)
for v, n in sorted(c.items(), key=lambda x: (x[0] == '', x[0])):
    print('     %-6s %d 行' % (v if v else '(空)', n))
print()
print('  ── ★ 空行出现在哪些步（前 20 个）──')
es = [r['step'] for r in rows if not (r.get('nblk_sig') or '').strip()]
print('     空行 %d 个：%s%s' % (len(es), es[:20], ' …' if len(es) > 20 else ''))
print()
print('  ── ★ 末行（step %s）到底哪些列空 ──' % rows[-1]['step'])
last = rows[-1]
empt = [k for k, v in last.items() if (v or '').strip() == '']
print('     空列 %d 个：%s' % (len(empt), empt))
print()
print('  ── 对照：倒数第 2 行（step %s）──' % rows[-2]['step'])
print('     nblk_sig = %r  f_var = %r  r_selfac = %r'
      % (rows[-2].get('nblk_sig'), rows[-2].get('f_var'), rows[-2].get('r_selfac')))
print('=' * 92)
PYEOF
