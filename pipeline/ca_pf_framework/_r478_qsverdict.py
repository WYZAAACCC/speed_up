#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r478_qsverdict.py —— 准静态钟（1B）的**预登记判据求值**。

判据原文见 `_r478_qssmoke.sh` 的文件头（Q1/Q2/Q3），此处**原样实现，不放宽**。

⚠ 记账：`--qs-dT 0` ⇒ 用 `1/α_KM`。本脚本**直接向 `windowB_closure` 要** α_KM 与
`T_start_of_clock`，不自己算，避免与驱动两套口径。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                # noqa: E402
import windowB_km as KM                                     # noqa: E402
from _r463_reinitcount import read_rows                      # noqa: E402

ROOT = '_exp/_bk_mb'


def load(tag):
    p = os.path.join(ROOT, tag, 'series.csv')
    rows = read_rows(p)
    if not rows:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {k: [] for k in ('step', 't_s', 'dt')}
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
    with open(os.path.join(ROOT, 'dry_qsA', 'meta.json')) as fh:
        m = json.load(fh)
    ea = m.get('exp_args') or {}
    alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
    q = float(ea.get('cool_rate', 0.0))
    T_end = float(ea.get('T_end', 298.0))
    Ts_arg = float(ea.get('T_start', 0.0))
    T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))
    dT = 1.0 / alpha
    n_stage_expect = (T_start - T_end) / dT

    print('=' * 84)
    print('R478  准静态钟判决')
    print('=' * 84)
    print('  α_KM = %.6g /K   T_start = %.2f K   T_end = %.1f K   q = %.4e K/s'
          % (alpha, T_start, T_end, q))
    print('  ΔT = 1/α_KM = **%.3f K**  ⇒ 预期档数 = (T_start−T_end)/ΔT = **%.1f**'
          % (dT, n_stage_expect))
    print()

    ok = {}
    for tag in ('dry_qsA', 'dry_qsB'):
        d = load(tag)
        if d is None:
            print('✗ %s 没数据' % tag)
            ok[tag] = None
            continue
        ts, dts, steps = d['t_s'], d['dt'], d['step']
        print('  ── %s ──  行 %d  step %.0f→%.0f' % (tag, len(ts), steps[0], steps[-1]))
        # Q1：t_s 是否由温度决定
        T_now = T_start - q * ts
        mono = bool(np.all(np.diff(ts) >= -1e-18))
        print('     Q1 t_s 单调？ %s ；末 t_s = %.4e s ⇒ 反推末温 T = **%.1f K**'
              % ('✅' if mono else '❌', ts[-1], T_now[-1]))
        # Q2：档数。用"温度平台数"近似 —— 直接看 dt 的变化次数（每档 dt 固定 ⇒ 平台）
        nplate = 1 + int((np.abs(np.diff(dts)) > 1e-18).sum()) if len(dts) > 1 else 1
        print('     Q2 dt 的平台数（≈ 档数）= **%d**（预期 %.1f，判据 ±2）'
              % (nplate, n_stage_expect))
        q2 = abs(nplate - n_stage_expect) <= 2
        print('        ⇒ **%s**' % ('✅ PASS' if q2 else '❌ FAIL'))
        # 每档平均步数
        print('     ⇒ 每档平均弛豫步数 = %.1f（总 %d 步 / %d 档）'
              % (len(ts) / max(nplate, 1), len(ts), nplate))
        ok[tag] = dict(Q1=mono, Q2=q2, nplate=nplate, n=len(ts),
                       t_end=float(ts[-1]), T_end_reached=float(T_now[-1]))
        print()

    # Q3：负对照 —— tol=1e-12 且 max_relax=5 ⇒ 步数应 ≈ 档数×5
    a, b = ok.get('dry_qsA'), ok.get('dry_qsB')
    if a and b:
        print('  ── Q3 负对照（--qs-tol 1e-12 --qs-max-relax 5）──')
        print('     qsA（正常 tol）步数 = %d' % a['n'])
        print('     qsB（极严 tol）步数 = %d' % b['n'])
        # qsB 应当在**更少的档数**内用掉同样/更少的步数？不 —— 它每档只给 5 步，
        # 所以要覆盖同样多的档需要 档数×5 步。若 qsB 的步数 ≈ 档数×5 ⇒ 判据在跑。
        expect_b = b['nplate'] * 5
        hit = abs(b['n'] - expect_b) <= max(3, 0.2 * expect_b)
        print('     qsB 档数 = %d ⇒ 若每档撞上限 5，预期步数 ≈ %d；实测 %d'
              % (b['nplate'], expect_b, b['n']))
        print('     ⇒ 每档平均步数 = **%.2f**（撞上限应 ≈5.0；若远小于 5 ⇒ 判据没在跑）'
              % (b['n'] / max(b['nplate'], 1)))
        q3 = hit
        print('     ⇒ **%s**' % ('✅ PASS（收敛判据确实在被求值）' if q3
                                 else '❌ FAIL（判据可能没生效）'))
    else:
        q3 = None
        print('  Q3：数据不全，跳过（**未取证**）')

    print()
    print('=' * 84)
    print('★ 汇总： Q1=%s  Q2=%s  Q3=%s'
          % ('PASS' if (a and a['Q1']) else 'FAIL/NA',
             'PASS' if (a and a['Q2']) else 'FAIL/NA',
             'PASS' if q3 else ('FAIL' if q3 is False else '未取证')))
    print('=' * 84)
    return 0


if __name__ == '__main__':
    sys.exit(main())
