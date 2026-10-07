#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r492_integverdict.py —— 三个新开关集成冒烟的**预登记判据求值**。

判据原文见 `_r492_integsmoke.sh` 文件头（I1–I6），此处**原样实现，不放宽**。
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


def read_log(p):
    if not os.path.exists(p):
        return ''
    with open(p, errors='replace') as fh:
        return fh.read()


def series(tag):
    rows = read_rows(os.path.join(ROOT, tag, 'series.csv'))
    if not rows:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {k: [] for k in ('step', 't_s', 'wall_s', 'nreg_used')}
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
    A, C = '_w2_r492_r492on.log', '_w2_r492_r492off.log'
    lA, lC = read_log(A), read_log(C)
    sA, sC = series('dry_r492on'), series('dry_r492off')

    ok = {}
    print('=' * 88)
    print('R492  三个新开关的集成冒烟判决')
    print('=' * 88)

    # ---- I1 不崩 ----
    badA = [w for w in ('Traceback', 'Error', 'error:') if w in lA]
    i1 = (len(badA) == 0) and (sA is not None) and len(sA['step']) > 1
    print('  ── I1 不崩（A 臂）──')
    print('     关键词命中 = %s ；CSV 行数 = %s'
          % (badA or '无', len(sA['step']) if sA is not None else 'N/A'))
    if badA:
        for w in badA:
            for ln in lA.splitlines():
                if w in ln:
                    print('       ! %s' % ln.strip()[:120])
                    break
    print('     ⇒ **%s**' % ('✅ PASS' if i1 else '❌ FAIL'))
    ok['I1'] = i1

    # ---- I2 钟在走 ----
    stA = re.findall(r'\[qs\] 档 (\d+) 收敛：T=([\d.]+) K\s+用了 (\d+) 步', lA)
    i2 = len(stA) > 0
    print('  ── I2 温度档在推进（A 臂）──')
    print('     `[qs] 档` 行数 = %d' % len(stA))
    for x in stA[:6]:
        print('       档 %s  T=%s K  %s 步' % x)
    if len(stA) > 6:
        print('       …（共 %d 档）' % len(stA))
    print('     ⇒ **%s**' % ('✅ PASS' if i2 else '❌ FAIL（钟没在走）'))
    ok['I2'] = i2

    # ---- I3 形核真的发生 ----
    # ★★ 自查错误 #92 的**第二次复现**：这里第一版写 `re.findall(r'引擎形核', lA)` ——
    #   那是 **`--arm eng`（cadence）路径**的打印串（`_bk_exp.py:1595`），
    #   而本冒烟跑的是 **`--nuc-law athermal`**，它打的是
    #   **`★★ **athermal 形核** @ step …`**（另一处 `P()`）
    #   ⇒ **假 FAIL**。
    #   ⚠ 教训：**同一个 grep 错我在两小时内犯了两次**（`_r482` → `_r494` 才发现 →
    #     `_r492` 又犯）⇒ 修一个实例不够，必须**全仓搜这个串**（本轮已做：
    #     只有 `_r482_refillverdict.py` 与本文具两处，均已修）。
    evA = len(re.findall(r'形核\*?\*? @ step', lA))
    P_lines = re.findall(r'模式 \*?\*?(\w+)\*?\*?', lA)
    print('  ── I3 形核事件真的发生（A 臂）──')
    print('     事件行数 = %d（按 `形核 @ step` 数，**两种 arm 都会打**）' % evA)
    print('     引擎报的模式序列 = %s' % (P_lines or '（无）'))
    i3 = evA > 0
    print('     ⇒ **%s**' % ('✅ PASS' if i3 else '❌ FAIL（③的补货在真跑里没生效）'))
    ok['I3'] = i3

    # ---- I4 t_s 由温度定 ----
    i4 = False
    if sA is not None and len(sA['t_s']) > 2:
        with open(os.path.join(ROOT, 'dry_r492on', 'meta.json')) as fh:
            ea = (json.load(fh).get('exp_args') or {})
        alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
        q = float(ea.get('cool_rate', 0.0))
        T_end = float(ea.get('T_end', 298.0))
        Ts_arg = float(ea.get('T_start', 0.0))
        T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))
        mono = bool(np.all(np.diff(sA['t_s']) >= -1e-18))
        dT = float(sA['t_s'][-1]) * q
        i4 = mono and (dT <= (T_start - T_end) + 1e-6)
        print('  ── I4 `t_s` 由温度定（A 臂）──')
        print('     单调 = %s ；`t_s(末)·q` = %.2f K ≤ 全程 %.2f K ⇒ **%s**'
              % (mono, dT, T_start - T_end, '✅ PASS' if i4 else '❌ FAIL'))
    else:
        print('  ── I4：CSV 行数不足，**未取证**')
    ok['I4'] = i4

    # ---- I5 负对照 ----
    stC = re.findall(r'\[qs\] 档', lC)
    i5 = len(stC) == 0
    print('  ── I5 负对照：三个开关全关时**不得**有 `[qs] 档` ──')
    print('     C 臂 `[qs] 档` 行数 = %d ⇒ **%s**'
          % (len(stC), '✅ PASS' if i5 else '❌ FAIL（读数不是噪声？）'))
    ok['I5'] = i5

    # ---- I6 多核：报墙钟 ----
    print('  ── I6 多核（两臂都用 --nthreads 16）──')
    for nm, s in (('A(on)', sA), ('C(off)', sC)):
        if s is not None and len(s['wall_s']) > 1:
            w = float(s['wall_s'][-1] - s['wall_s'][0])
            n = int(s['step'][-1] - s['step'][0])
            print('     %s：%d 步 / %.1f s ⇒ **%.3f s/步**' % (nm, n, w, w / max(n, 1)))
    print('     （对照 `R488_THREADSCALE.md`：N=96/nv=12 单线程 4.45 s/步 ⇒ 2.52× @16 线程）')

    print()
    print('=' * 88)
    print('★ 汇总： ' + '  '.join('%s=%s' % (k, 'PASS' if v else 'FAIL')
                                 for k, v in ok.items()))
    print('=' * 88)
    return 0


if __name__ == '__main__':
    sys.exit(main())
