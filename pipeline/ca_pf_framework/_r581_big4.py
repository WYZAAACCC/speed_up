#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_big4.py --- ★★★★★★★ **那四条 N=160 大仿真**：配置 + 终态读数"""
import csv
import glob
import json
import os
import sys

TAGS = sys.argv[1:] or ['p2_b3', 'p2_b5', 'p2_b5ov', 'p2_b5ps']
KEYS = ['Vt', 'nslab_n', 'nslab_n1', 'nf3', 'nf2', 'n_var_sig', 'n_habit',
        'blk_nsp', 'r_selfac', 'nslab_nu', 'box_touch', 'f_var']


def main():
    for t in TAGS:
        ds = glob.glob('_exp/**/dry_%s' % t, recursive=True)
        if not ds:
            print('  %-10s 找不到目录' % t)
            continue
        d = ds[0]
        print('=' * 106)
        print('臂 %s   （%s）' % (t, d))
        print('=' * 106)
        mp = os.path.join(d, 'meta.json')
        if os.path.exists(mp):
            try:
                m = json.load(open(mp, encoding='utf-8', errors='replace'))
                show = {k: m[k] for k in ('N', 'stage', 'steps', 'dx_nm', 'every', 'arm',
                                          'beta_h', 'df_start', 'DF') if k in m}
                print('  meta：%s' % json.dumps(show, ensure_ascii=False)[:200])
            except Exception as e:
                print('  meta 读不出：%s' % e)
        p = os.path.join(d, 'series.csv')
        if not os.path.exists(p):
            print('  （没有 series.csv）')
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        k = list(rows[0].keys())[0]
        have = [c for c in KEYS if c in rows[0]]
        print('  行数 %d；末步 %s' % (len(rows), rows[-1][k]))
        print('  时间：首 t_s=%s  末 t_s=%s' % (rows[0].get('t_s'), rows[-1].get('t_s')))
        print()
        print('  %-7s %s' % ('step', ' '.join('%-11s' % c[:11] for c in have)))
        show = [r for r in rows if r[k] in ('0',)]
        show += [r for r in rows if r[k].isdigit() and int(r[k]) % 100 == 0]
        show += [rows[-1]]
        seen = set()
        for r in show:
            if r[k] in seen:
                continue
            seen.add(r[k])
            vals = []
            for c in have:
                v = (r.get(c, '') or '').strip()
                try:
                    vals.append('%-11.6g' % float(v))
                except Exception:
                    vals.append('%-11s' % v[:11])
            print('  %-7s %s' % (r[k], ' '.join(vals)))
        snaps = sorted(os.path.basename(x) for x in glob.glob(os.path.join(d, 'snap_*.npz')))
        print()
        print('  快照 %d 个：%s' % (len(snaps), ', '.join(snaps[:10])))
        print()


if __name__ == '__main__':
    main()
