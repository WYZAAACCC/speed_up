#!/usr/bin/env python3
"""R50: **P1-28 的量级** —— `nf3_col == nslab_n−1` 在"全部场同变体"的臂上是**恒真**的。
判据：若一条臂的所有场变体都相同，则该式**无论几何如何**都成立 ⇒ 它**没有分辨力**。
⇒ 这些臂上"形成了 M−1 张 F3 界面"**不得**被当作独立佐证。
"""
import csv
import glob
import json
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
print('  %-14s %-22s %-9s %-9s %-9s %s'
      % ('臂', 'laths/vmap', '同变体?', '末nslab', '末nf3col', 'nf3_col==nslab-1?'))
for root in ('_exp/_bk_mb', '_exp/_bk_closed', '_exp/_bk_eng'):
    for d in sorted(glob.glob(root + '/*/')):
        mp = os.path.join(d, 'meta.json')
        cs = os.path.join(d, 'series.csv')
        if not (os.path.exists(mp) and os.path.exists(cs)):
            continue
        m = json.load(open(mp))
        la = m.get('laths')
        if not la:
            continue
        uniq = sorted(set(int(x) for x in la))
        rows = list(csv.DictReader(open(cs)))
        if not rows:
            continue
        last = rows[-1]
        try:
            ns, nf = int(last['nslab_n']), int(last['nf3_col'])
        except (KeyError, ValueError):
            continue
        # 全程是否恒满足
        allsat = all((int(r['nf3_col']) == int(r['nslab_n']) - 1)
                     for r in rows if r.get('nslab_n') not in (None, '', '0'))
        print('  %-14s %-22s %-9s %-9s %-9s %s'
              % (os.path.basename(d.rstrip('/')),
                 str(la)[:22], ('**是**' if len(uniq) == 1 else '否(%d)' % len(uniq)),
                 ns, nf,
                 ('恒真 ⚠' if allsat and len(uniq) == 1 else
                  ('成立' if allsat else '有不成立步'))))
print()
print('★ 结论：标记"恒真 ⚠"的臂上，V-1 的第 2 条**没有分辨力**；')
print('  该臂的"块形成"只能由 `nslab_n == M` 与 `f3_area > 0` 承担。')
