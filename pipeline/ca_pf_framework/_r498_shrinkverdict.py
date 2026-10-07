#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r498_shrinkverdict.py —— `--qs-shrink-cap` 的**预登记判据求值**（E1–E4）。

判据原文见 `_r498_shrinksmoke.sh` 文件头，此处**原样实现，不放宽**。
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402
from _r463_reinitcount import read_rows                        # noqa: E402

ROOT = '_exp/_bk_mb'
ARMS = (('D', 'dry_r498D', 0), ('E', 'dry_r498E', 20), ('F', 'dry_r498F', 1))
TOL_VT = 0.10


def series(tag):
    rows = read_rows(os.path.join(ROOT, tag, 'series.csv'))
    if not rows:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    keys = ('step', 't_s', 'Vt', 'nreg_used', 'nslab_n', 'nf3_col', 'wall_s')
    out = {k: [] for k in keys if k in ix}
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            for k in out:
                out[k].append(float(c[ix[k]]))
        except ValueError:
            continue
    return {k: np.array(v) for k, v in out.items()}


def main():
    print('=' * 92)
    print('R498  `--qs-shrink-cap` A/B 等价性判决')
    print('=' * 92)
    data = {}
    for nm, tag, cap in ARMS:
        s = series(tag)
        lf = '_w2_r498_%s.log' % tag
        n_early = 0
        if os.path.exists(lf):
            with open(lf, errors='replace') as fh:
                n_early = sum(1 for ln in fh if '纯溶解早退' in ln)
        if s is None:
            print('  ✗ %s（%s）没有 CSV' % (nm, tag))
            continue
        with open(os.path.join(ROOT, tag, 'meta.json')) as fh:
            ea = (json.load(fh).get('exp_args') or {})
        alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
        q = float(ea.get('cool_rate', 0.0))
        T_end = float(ea.get('T_end', 298.0))
        Ts_arg = float(ea.get('T_start', 0.0))
        T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))
        T_fin = T_start - q * float(s['t_s'][-1])
        data[nm] = dict(s=s, T_fin=T_fin, T_end=T_end, n_early=n_early,
                        steps=int(s['step'][-1]), cap=cap,
                        nreg=int(s['nreg_used'][-1]),
                        nslab=float(s['nslab_n'][-1]),
                        Vt=float(s['Vt'][-1]),
                        wall=float(s['wall_s'][-1] - s['wall_s'][0]))
    print('  ── 各臂读数 ──')
    print('  臂  cap  步数   末温(K)  T_end  早退档数  nreg  nslab      Vt(m³)      用时(s)')
    for nm, _, cap in ARMS:
        d = data.get(nm)
        if not d:
            continue
        print('  %-3s %-4d %-6d %-8.1f %-7.1f %-9d %-5d %-6.0f %-12.4e %.0f'
              % (nm, cap, d['steps'], d['T_fin'], d['T_end'], d['n_early'],
                 d['nreg'], d['nslab'], d['Vt'], d['wall']))
    if 'D' not in data:
        print('✗ 参考臂 D 缺失 ⇒ 无法判决')
        return 2
    D = data['D']

    # ---- E1 都到终点 ----
    e1 = True
    for nm in ('D', 'E'):
        d = data.get(nm)
        if not d:
            e1 = False
            continue
        ok = abs(d['T_fin'] - d['T_end']) < 0.5
        e1 &= ok
        print('  E1 %s 末温 %.1f vs T_end %.1f ⇒ %s'
              % (nm, d['T_fin'], d['T_end'], '✅' if ok else '❌'))
    print('  ── E1 都到终点：**%s**' % ('✅ PASS' if e1 else '❌ FAIL'))

    # ---- E2 确实省了 ----
    E = data.get('E')
    e2 = False
    if E:
        r = E['steps'] / max(D['steps'], 1)
        e2 = r <= 0.6
        print('  ── E2 省步数：E/D = %d/%d = **%.3f**（判据 ≤ 0.60）⇒ **%s**'
              % (E['steps'], D['steps'], r, '✅ PASS' if e2 else '❌ FAIL'))

    # ---- E3 末态等价（核心） ----
    def cmp(a, b):
        """返回 (nreg同, nslab同, Vt相对差)"""
        if not a or not b:
            return None
        same_nreg = (a['nreg'] == b['nreg'])
        same_nslab = (abs(a['nslab'] - b['nslab']) < 0.5)
        rel = abs(a['Vt'] - b['Vt']) / max(abs(b['Vt']), 1e-300)
        return same_nreg, same_nslab, rel

    e3 = False
    c = cmp(E, D)
    if c:
        same_nreg, same_nslab, rel = c
        e3 = same_nreg and same_nslab and (rel <= TOL_VT)
        print('  ── E3 末态等价（E vs D）──')
        print('     nreg   %d vs %d ⇒ %s' % (E['nreg'], D['nreg'],
                                              '✅同' if same_nreg else '❌异'))
        print('     nslab  %.0f vs %.0f ⇒ %s' % (E['nslab'], D['nslab'],
                                                  '✅同' if same_nslab else '❌异'))
        print('     Vt     相对差 = **%.4f**（判据 ≤ %.2f）⇒ %s'
              % (rel, TOL_VT, '✅' if rel <= TOL_VT else '❌'))
        print('     ⇒ **%s**' % ('✅ PASS（末态等价）' if e3 else '❌ FAIL'))

    # ---- E4 负对照 ----
    e4 = None
    F = data.get('F')
    if F and c:
        cF = cmp(F, D)
        if cF:
            same_nreg, same_nslab, rel = cF
            differs = (not same_nreg) or (not same_nslab) or (rel > TOL_VT)
            e4 = differs
            print('  ── E4 负对照（F cap=1 过度激进 vs D）──')
            print('     nreg %d vs %d ；nslab %.0f vs %.0f ；Vt 相对差 %.4f'
                  % (F['nreg'], D['nreg'], F['nslab'], D['nslab'], rel))
            print('     ⇒ 判据（**必须**出现至少一项不一致）⇒ **%s**'
                  % ('✅ PASS（E3 有判别力）' if differs
                     else '❌ FAIL（E3 太松 ⇒ 它的 PASS 不算数）'))

    print()
    print('=' * 92)
    print('★ 汇总： E1=%s  E2=%s  E3=%s  E4=%s'
          % ('PASS' if e1 else 'FAIL', 'PASS' if e2 else 'FAIL',
             'PASS' if e3 else 'FAIL',
             {True: 'PASS', False: 'FAIL', None: '未取证'}[e4]))
    if e1 and e2 and e3 and e4:
        print('★ ⇒ **优化可用**：省步数且末态等价，负对照证明判据有判别力。')
    elif e4 is False:
        print('★ ⇒ **判据不可信**（E4 FAIL）⇒ 不得据此宣称等价。')
    else:
        print('★ ⇒ **未通过**，照实记，不得宣称优化可用。')
    print('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
