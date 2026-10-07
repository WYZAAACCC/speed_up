#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r482_refillverdict.py —— 任务(2) ③ 的**预登记判据求值**。

判据原文见 `_r482_refillsmoke.sh` 的文件头（V1/V2/V3），此处**原样实现，不放宽**。

读数口径（**不猜**）：
* **形核事件数**：`_w2_r482_*.log` 里 `★★ **引擎形核**` 的行数
  （`_bk_exp.py` 每有一次事件就打一行）。
* **`nreg_used`**：`series.csv` 的对应列（在用场数），交叉核对。
* **`n(T_end)`**：直接向 `windowB_closure.alpha_km_n_lath` 要，**不自己算**。
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


def count_events(log):
    """★ 自查错误 #92（2026-10-01）：**这个函数的字符串选错了。**
    它数的是 `引擎形核` —— 那是 **`--arm eng`（cadence）路径**的打印串；
    而 `_r482` 跑的是 `--nuc-law athermal`，打的是 **`形核 @ step`**。
    ⇒ **两条臂都被数成 0**，据此得出的 V1/V2 判决与"F1 死锁"**均已撤销**
    （正确重数见 `_r494_r482recount.py`：A 臂 5 个事件、B 臂 6 个）。
    本函数已修正为 `形核 @ step`，**但本文件的历史结论不再作为依据**。"""
    if not os.path.exists(log):
        return None
    n = 0
    with open(log, errors='replace') as fh:
        for ln in fh:
            if '形核 @ step' in ln:
                n += 1
    return n


def last_event_step(log):
    if not os.path.exists(log):
        return None
    last = None
    with open(log, errors='replace') as fh:
        for ln in fh:
            m = re.search(r'形核\*?\*? @ step (\d+)', ln)
            if m:
                last = int(m.group(1))
    return last


def csv_series(tag):
    rows = read_rows(os.path.join(ROOT, tag, 'series.csv'))
    if not rows:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {k: [] for k in ('step', 'nreg_used', 't_s')}
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
    with open(os.path.join(ROOT, 'dry_r482A', 'meta.json')) as fh:
        mA = json.load(fh)
    with open(os.path.join(ROOT, 'dry_r482B', 'meta.json')) as fh:
        mB = json.load(fh)
    eA, eB = mA.get('exp_args') or {}, mB.get('exp_args') or {}
    alpha = float(eA.get('alpha_km', CL.ALPHA_KM_REF))
    T_end = float(eA.get('T_end', 298.0))
    nv = int(eA.get('nv', 0))
    q = float(eA.get('cool_rate', 0.0))
    n_law = int(CL.n_lath_int(T_end, alpha))
    steps = int(eA.get('steps', 0))

    # ★★ 自查发现的错误 #88（判据设计错，留痕）：
    #   第一版把上限写成 `cap = min(n(T_end), nv)`。**但步数预算也会限事件数** ——
    #   1200 步、冷速 2.3524e6、dt≈7.6e-8 ⇒ 只降 ≈215 K（849→634 K）
    #   ⇒ `n(634 K) ≈ 10`，而 `n(T_end=298) = 24` ⇒ **用 24 当上限，两条臂都够不到
    #   0.9×24 = 21.6 ⇒ V2 会"因为预算不够"而假 FAIL**，与本任务无关。
    #   ⇒ 正确口径：上限取 **本次跑实际到达的温度** 所对应的 `n`
    #     （由 CSV 的 `t_s` 反推 T，再向 `windowB_closure` 要 n）。
    sA0 = csv_series('dry_r482A')
    T_reached = float('nan')
    if sA0 is not None and len(sA0['step']) and q > 0:
        t_fin = float(sA0['t_s'][-1])
        # T = T_start − q·t_s；T_start 由 serise 起点（t_s=0）时的 df 反推太绕，
        # 直接用 `T_start_of_clock(alpha)`（与驱动同一函数）
        T_start = float(CL.T_start_of_clock(alpha))
        T_reached = max(T_start - q * t_fin, T_end)
    n_reached = int(CL.n_lath_int(T_reached, alpha)) if T_reached == T_reached else n_law
    cap = min(n_reached, nv)

    print('=' * 84)
    print('R482  位点持续可用 —— 判决')
    print('=' * 84)
    print('  α_KM = %.6g /K   q = %.4e K/s   T_end = %.1f K   nv = %d'
          % (alpha, q, T_end, nv))
    print('  ★ 本次跑**实际到达**的温度 T = **%.1f K** ⇒ 导出的 n(T) = **%d**'
          % (T_reached, n_reached))
    print('  ⇒ 上限 min(n(T_到达), nv) = **%d**   （⚠ 不是 n(T_end)=%d —— 见脚本头 #88）'
          % (cap, n_law))
    print('  预算步数 = %d' % steps)
    print()

    # ---- V3 对照有效性 ----
    keys = ('alpha_km', 'T_end', 'nv', 'steps', 'cool_rate', 'nuc_init',
            'nuc_fresh_every', 'laths', 'nuc_sites_refill')
    diff = [(k, eA.get(k), eB.get(k)) for k in keys if eA.get(k) != eB.get(k)]
    v3 = (diff == [('nuc_sites_refill', 0, 1)] or
          (len(diff) == 1 and diff[0][0] == 'nuc_sites_refill'))
    print('  ── V3 对照有效性（两臂只应差 `nuc_sites_refill`）──')
    for k, a, b in diff:
        print('     差异：%s : A=%r  B=%r' % (k, a, b))
    print('     ⇒ **%s**' % ('✅ PASS（只是那一个开关）' if v3 else '❌ FAIL（不止一个差异！）'))
    print()

    evA, evB = count_events('_w2_r482_r482A.log'), count_events('_w2_r482_r482B.log')
    sA, sB = csv_series('dry_r482A'), csv_series('dry_r482B')
    lA, lB = last_event_step('_w2_r482_r482A.log'), last_event_step('_w2_r482_r482B.log')

    print('  ── 读数 ──')
    for nm, ev, last, s in (('A（refill=0）', evA, lA, sA), ('B（refill=1）', evB, lB, sB)):
        if s is None:
            print('     %s：**没有 CSV**' % nm)
            continue
        print('     %-14s 事件数=%-4s 末次事件 step=%-6s  nreg_used(末)=%.0f  nreg_used(max)=%.0f'
              % (nm, ev, last, s['nreg_used'][-1], s['nreg_used'].max()))
    print()

    # ---- V1 病灶存在 ----
    v1 = None
    if evA is not None:
        v1 = evA < 0.9 * cap
        print('  ── V1 病灶存在（负对照）──')
        print('     A 臂事件数 = %d，上限 = %d ⇒ %s'
              % (evA, cap, '✅ PASS（确实提前停了 ⇒ 病灶存在）' if v1
                 else '❌ FAIL（A 臂也跑到上限 ⇒ **病灶不存在，本任务无必要**）'))
    # ---- V2 修复有效 ----
    v2 = None
    if evA is not None and evB is not None:
        v2 = (evB > evA) and (evB >= 0.9 * cap)
        print('  ── V2 修复有效 ──')
        print('     B 臂事件数 = %d vs A 臂 %d ⇒ %s；B ≥ 0.9×上限(%d)=%d ？ %s'
              % (evB, evA, '更多' if evB > evA else '**没有更多**',
                 cap, int(0.9 * cap), '是' if evB >= 0.9 * cap else '否'))
        print('     ⇒ **%s**' % ('✅ PASS' if v2 else '❌ FAIL'))
    print()
    print('=' * 84)
    print('★ 汇总： V1=%s  V2=%s  V3=%s'
          % ({True: 'PASS', False: 'FAIL', None: '未取证'}[v1],
             {True: 'PASS', False: 'FAIL', None: '未取证'}[v2],
             {True: 'PASS', False: 'FAIL'}[v3]))
    print('★ （V4 默认路径不变 = 由 `_r30_regress.sh` 另跑把关）')
    print('=' * 84)
    return 0


if __name__ == '__main__':
    sys.exit(main())
