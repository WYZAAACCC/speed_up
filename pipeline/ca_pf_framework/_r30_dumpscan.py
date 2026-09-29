#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：全 `_exp/` 只读普查 —— 每个算例目录里 snap_*.npz 的 key 集合、
份数、step 间隔、体积，以及 series.csv 的列/行数。
**新增文件，不改任何已有文件。**
用法: python3 _r30_dumpscan.py  [--root _exp]
"""
import os
import sys
import glob
import csv
import json
import argparse

import numpy as np


def snapkeys(p):
    try:
        z = np.load(p, allow_pickle=False)
    except Exception as e:                                  # noqa: BLE001
        return None, repr(e)
    ks = sorted(z.files)
    z.close()
    return ks, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp')
    ap.add_argument('--out', default='/tmp/r30_dumpscan.json')
    a = ap.parse_args()

    rows = []
    for dirpath, _dirs, files in os.walk(a.root):
        snaps = sorted(f for f in files if f.startswith('snap_')
                       and f.endswith('.npz'))
        if not snaps:
            continue
        rec = dict(dir=dirpath, nsnap=len(snaps))
        steps = []
        keysets = {}
        tot = 0
        for f in snaps:
            p = os.path.join(dirpath, f)
            st = os.stat(p)
            tot += st.st_size
            ks, err = snapkeys(p)
            if ks is None:
                rec.setdefault('errors', []).append('%s: %s' % (f, err))
                continue
            keysets.setdefault(tuple(ks), 0)
            keysets[tuple(ks)] += 1
            try:
                stp = int(np.load(p, allow_pickle=False)['step'])
                steps.append(stp)
            except Exception:                               # noqa: BLE001
                steps.append(None)
        rec['bytes'] = tot
        rec['keysets'] = [dict(keys=list(k), n=v) for k, v in keysets.items()]
        rec['steps'] = steps
        if len(steps) >= 2 and all(s is not None for s in steps):
            rec['dstep'] = [b - a2 for a2, b in zip(steps[:-1], steps[1:])]
        # ---- series.csv ----
        sc = os.path.join(dirpath, 'series.csv')
        if os.path.exists(sc):
            try:
                with open(sc, newline='') as fh:
                    r = list(csv.reader(fh))
                rec['csv_cols'] = r[0]
                rec['csv_rows'] = len(r) - 1
                if len(r) > 1:
                    ix = {c: i for i, c in enumerate(r[0])}
                    rec['csv_first_step'] = r[1][0]
                    rec['csv_last_step'] = r[-1][0]
                    rec['csv_last_nslab'] = (r[-1][ix['nslab_n']]
                                             if 'nslab_n' in ix else None)
                    rec['csv_last_nf3'] = (r[-1][ix['nf3']]
                                           if 'nf3' in ix else None)
            except Exception as e:                          # noqa: BLE001
                rec['csv_error'] = repr(e)
        rec['other'] = sorted(f for f in files
                              if not f.startswith('snap_'))
        rows.append(rec)

    # 汇总：哪些算例存了 'phi'
    withphi = [r['dir'] for r in rows
               if any('phi' in k['keys'] for k in r['keysets'])]
    allkeys = {}
    for r in rows:
        for k in r['keysets']:
            for kk in k['keys']:
                allkeys[kk] = allkeys.get(kk, 0) + 1
    summary = dict(n_case_with_snap=len(rows),
                   all_keys_seen=allkeys,
                   cases_with_phi_in_snap=withphi,
                   total_bytes=sum(r['bytes'] for r in rows))
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(dict(summary=summary, cases=rows), fh,
                  ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(' -> %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
