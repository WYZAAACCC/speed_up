"""_bkr_csv.py —— 读 R1 归档算例的 series.csv，量 regflip / nreinit / dG_max / t_s 等记账量。"""
import os
import sys
import csv

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for case in ('e4_lath6', 'e5_equi6', 'e6_mid6', 'e7d_pair34'):
    p = os.path.join(HERE, '_exp', case, 'series.csv')
    if not os.path.exists(p):
        continue
    with open(p) as f:
        rows = list(csv.DictReader(f))
    print('=' * 70)
    print('%s : %d 行' % (case, len(rows)))

    def col(name):
        out = []
        for r in rows:
            v = (r.get(name) or '').strip()
            try:
                out.append(float(v))
            except ValueError:
                out.append(np.nan)
        return np.array(out)

    for name in ('step', 't_s', 'dt', 'dG_max', 'nreinit', 'nskip', 'regflip',
                 'ncell', 'nsig', 'nc', 'ncomp', 'adv_wall', 'reinit_wall', 'reinit_pairs'):
        a = col(name)
        fin = np.isfinite(a)
        if fin.sum() == 0:
            print('  %-12s : 全为空/NaN' % name)
        else:
            print('  %-12s : n=%3d  首=%s  末=%s  非零数=%d'
                  % (name, int(fin.sum()), a[fin][0], a[fin][-1], int(np.count_nonzero(a[fin]))))
    a = col('t_s')
    if np.isfinite(a).sum() > 1:
        d = np.diff(a[np.isfinite(a)])
        print('  ⇒ t_s 增量: %.4e s/记录（记录间隔 %s 步）' % (d[0], col('step')[1] - col('step')[0]))
