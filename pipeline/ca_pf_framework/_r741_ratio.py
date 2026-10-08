#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r741_ratio.py —— **比率检验**：哪些参数真正决定 `nf2 > 0`（消除样本量偏差）。

## 为什么要做
`_r741_cfgdiff.py` 的计数表**不能直接比**（`nf2>0` 组 141 个 vs `nf2=0` 组 560 个，
差 4 倍 ⇒ 任何取值在两组里都"看起来"前者少）。
⇒ 正解：对每个参数的每个取值，报 **`P(nf2>0 | 该取值)`**（该取值下正例的**比例**）。

## 判据
* **P(pos|v) 高**（≫ 全局基准 141/701 = 20.1%）⇒ 该取值**促进** F2 界面；
* **P(pos|v) ≈ 0** ⇒ 该取值**阻止** F2 界面；
* 报**全局基准**以便对照。
"""
import argparse
import csv
import json
import os
import sys

WANT = ['laths', 'nuc_init', 'nuc_shape', 'var_rule', 'nuc_iface_nucleation',
        'grow_stack', 'nuc_law', 'nuc_every', 'nuc_mode', 'eng_cadence',
        'nuc_supercrit', 'nuc_count_mode', 'per_field_axes',
        'plate_L', 'plate_W', 'plate_T', 'N', 'steps', 'facet_proj']
DEFAULT_ROOTS = ['/mnt/f/speed_up/_exp',
                 '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp']


def arm(dirpath):
    sp = os.path.join(dirpath, 'series.csv')
    mp = os.path.join(dirpath, 'meta.json')
    try:
        with open(sp, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
    except OSError:
        return None
    if not rows or 'nf2' not in rows[0]:
        return None
    vals = []
    for r in rows:
        try:
            vals.append(float(r['nf2']))
        except (TypeError, ValueError):
            pass
    if not vals:
        return None
    if not os.path.isfile(mp):
        return None
    try:
        with open(mp) as f:
            ar = (json.load(f).get('exp_args') or {})
    except (OSError, ValueError):
        return None
    return (max(vals) > 0, ar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--roots', nargs='*', default=DEFAULT_ROOTS)
    ap.add_argument('--minn', type=int, default=8,
                    help='某取值至少要有这么多样本才报（否则是小样本噪声）')
    a = ap.parse_args()
    recs = []
    for root in a.roots:
        if not os.path.isdir(root):
            continue
        for dp, _dn, fn in os.walk(root):
            if 'series.csv' not in fn:
                continue
            r = arm(dp)
            if r:
                recs.append(r)
    npos = sum(1 for p, _ in recs if p)
    base = 100.0 * npos / max(len(recs), 1)
    print('=' * 104)
    print('比率检验：P(nf2>0 | 参数取值)  —— 全局基准 = %d/%d = **%.1f%%**'
          % (npos, len(recs), base))
    print('=' * 104)
    print('  比值 `P/基准`：>1.5 促进 / <0.5 阻止 / 其余中性。**只列偏离的**。\n')
    for k in WANT:
        grp = {}
        for p, ar in recs:
            v = ar.get(k, '(缺失)')
            if isinstance(v, list):
                v = 'len=%d' % len(v)
            grp.setdefault(str(v), [0, 0])
            grp[str(v)][0] += 1
            if p:
                grp[str(v)][1] += 1
        rows = []
        for v, (n, np_) in grp.items():
            if n < a.minn:
                continue
            pp = 100.0 * np_ / n
            rows.append((pp / base if base else 0, v, n, np_, pp))
        rows.sort(reverse=True)
        dev = [r for r in rows if r[0] > 1.5 or r[0] < 0.5]
        if not dev:
            continue
        print('  %s' % k)
        for ratio, v, n, np_, pp in dev:
            tag = '★促进' if ratio > 1.5 else '⛔阻止'
            print('      %-16s n=%-4d pos=%-4d P=%5.1f%%  比值=%4.2f  %s'
                  % (v[:16], n, np_, pp, ratio, tag))
    return 0


if __name__ == '__main__':
    sys.exit(main())
