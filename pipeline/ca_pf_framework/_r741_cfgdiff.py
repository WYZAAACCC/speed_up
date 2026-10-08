#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r741_cfgdiff.py —— 对比"`nf2 > 0` 的臂"与"`nf2 == 0` 的臂"的**配置差异**。

## 为什么要做
`_r741_hunt_nf2.py` 全盘扫出 **141 个臂出现过 `nf2 > 0`**（最大 16140），
而 **560 个臂恒为 0** ⇒ **`R725` 的"F2 通道够不着"是**样本假象**（3 轮全落在 80% 的零臂里）。**
⇒ 本脚本从每个臂的 `meta.json` 的 `exp_args` 里取关键参数，找**判别哪个参数决定 `nf2`**。

## 输出
* 两组各自的**参数取值分布**（只看能造成差异的那些）；
* 结论：哪个开关是 `nf2 > 0` 的**必要条件**。
"""
import argparse
import csv
import json
import os
import sys

WANT = ['laths', 'nuc_init', 'nuc_shape', 'var_rule', 'nuc_iface_nucleation',
        'nfsv', 'stack_pick_dg', 'grow_stack', 'attach', 'nuc_law',
        'nuc_every', 'nuc_mode', 'eng_cadence', 'nuc_supercrit',
        'nuc_count_mode', 'per_field_axes', 'nuc_resample_ungated',
        'plate_L', 'plate_W', 'plate_T', 'N', 'steps', 'facet_proj',
        'rank1_swap', 'nuc_block_target', 'nuc_block_parallel',
        'nuc_sites_refill', 'nuc_periodic_seed', 'harden_f']

DEFAULT_ROOTS = [
    '/mnt/f/speed_up/_exp',
    '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp',
]


def arm_info(dirpath):
    """返回 (max_nf2 | None, args | None)。"""
    sp = os.path.join(dirpath, 'series.csv')
    mp = os.path.join(dirpath, 'meta.json')
    mx = None
    try:
        with open(sp, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
        if rows and 'nf2' in rows[0]:
            vals = []
            for r in rows:
                try:
                    vals.append(float(r['nf2']))
                except (TypeError, ValueError):
                    pass
            if vals:
                mx = max(vals)
    except OSError:
        return None, None
    args = None
    if os.path.isfile(mp):
        try:
            with open(mp) as f:
                m = json.load(f)
            args = m.get('exp_args') or None
        except (OSError, ValueError):
            pass
    return mx, args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--roots', nargs='*', default=DEFAULT_ROOTS)
    ap.add_argument('--topn', type=int, default=12)
    a = ap.parse_args()
    pos, zer = [], []
    for root in a.roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dn, fn in os.walk(root):
            if 'series.csv' not in fn:
                continue
            mx, args = arm_info(dirpath)
            if mx is None or args is None:
                continue
            rec = (mx, os.path.basename(dirpath), args)
            (pos if mx > 0 else zer).append(rec)
    print('=' * 104)
    print('配置对比：`nf2 > 0` 的臂 %d 个  vs  `nf2 == 0` 的臂 %d 个（有 meta.json 的）'
          % (len(pos), len(zer)))
    print('=' * 104)
    pos.sort(reverse=True)
    print('\n★ Top %d（`nf2` 最大）：' % a.topn)
    hdr = ['nf2', 'arm'] + WANT[:9]
    print('  ' + ' '.join('%-13s' % h for h in hdr))
    for mx, arm, ar in pos[:a.topn]:
        row = ['%-13g' % mx, '%-13s' % arm[:13]] + \
              ['%-13s' % str(ar.get(k, '·'))[:13] for k in WANT[:9]]
        print('  ' + ' '.join(row))

    def dist(group, key):
        d = {}
        for _mx, _arm, ar in group:
            if ar is None:
                continue
            v = ar.get(key, '(缺失)')
            if isinstance(v, list):
                v = 'len=%d' % len(v)
            d[str(v)] = d.get(str(v), 0) + 1
        return d

    print('\n' + '=' * 104)
    print('逐参数分布（只列两组**分布不同**的）')
    print('=' * 104)
    for k in WANT:
        dp, dz = dist(pos, k), dist(zer, k)
        if dp == dz:
            continue
        def top(d):
            return ', '.join('%s×%d' % (a_, b_) for a_, b_ in
                             sorted(d.items(), key=lambda x: -x[1])[:4])
        print('  %-24s' % k)
        print('      nf2>0 : %s' % top(dp))
        print('      nf2=0 : %s' % top(dz))
    return 0


if __name__ == '__main__':
    sys.exit(main())
