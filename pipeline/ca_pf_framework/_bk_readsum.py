#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_readsum.py —— 把一个/多个算例目录的**末态摘要**读出来对照（只读，不改任何东西）。

为什么要单独一个文件：本仓库反复踩过「从目录列举取文件，默认顺序不可依赖」的坑
（AGENTS.md §3.9 / 教训 25）。这里一律用 `csv.DictReader` 读指定的 `series.csv`，
并且快照只按 `snap_*.npz` 的**字典序最后**取（文件名是 5 位零填充 ⇒ 字典序 = 时间序）。
"""
import csv
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def summarise(d):
    p = os.path.join(_HERE, d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    if not rows:
        return None
    meta = {}
    mp = os.path.join(_HERE, d, 'meta.json')
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding='utf-8'))
    f, l = rows[0], rows[-1]

    def fx(k):
        try:
            return float(l[k])
        except (KeyError, ValueError):
            return float('nan')
    snaps = sorted(x for x in os.listdir(os.path.join(_HERE, d))
                   if x.startswith('snap_') and x.endswith('.npz'))
    return dict(dir=d, npts=len(rows), step0=f.get('step'), stepN=l.get('step'),
                t_s=fx('t_s'), Vt0=fx('Vt'), VtN=fx('Vt'),
                nslab0=f.get('nslab_n'), nslabN=l.get('nslab_n'),
                nf3_0=f.get('nf3_col'), nf3N=l.get('nf3_col'),
                runs=l.get('runs'), ncompbig=l.get('ncompbig_max'),
                f3area=fx('f3_area_m2'), touch=l.get('box_touch'),
                ths=l.get('ths'), plate=(meta.get('plate') or {}),
                dx=meta.get('dx_nm'), steps=meta.get('steps'),
                beta_h=meta.get('beta_h'), nv=meta.get('nv'),
                last_snap=(snaps[-1] if snaps else None))


def main(argv):
    for d in (argv[1:] or ['_exp/_bk_closed/dry_cl1']):
        s = summarise(d)
        if s is None:
            print('%-34s （无 series.csv）' % d)
            continue
        print('--- %s' % s['dir'])
        print('    测点=%-3d step %s→%s  t_s=%.4e' % (s['npts'], s['step0'],
                                                     s['stepN'], s['t_s']))
        print('    Vt %.4f → **%.4f** µm³      nslab %s → **%s**   nf3col %s → %s'
              % (s['Vt0'] * 1e18, s['VtN'] * 1e18, s['nslab0'], s['nslabN'],
                 s['nf3_0'], s['nf3N']))
        print('    runs=%-16s ncompbig_max=%s  F3面积=%.4f µm²  壁=%s'
              % (s['runs'], s['ncompbig'], s['f3area'] * 1e12, s['touch']))
        print('    plate=%s nm  dx=%s nm  steps=%s  β_h=%s  nv=%s  末快照=%s'
              % (s['plate'], s['dx'], s['steps'], s['beta_h'], s['nv'],
                 s['last_snap']))
        print('    原始 ths（含孤儿，仅供参考）=%s' % s['ths'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
