#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r503_blockverdict.py —— `--nuc-block-target` 的**预登记判据求值**（B1–B4）。

判据原文见 `_r503_blocksmoke.sh` 文件头与 `R502_BLOCKCOUNT.md §6`，**原样实现、不放宽**。

★ 读数口径（**这次先查清再写**，吸取 #92 的教训）：
  `--nuc-law athermal` 的事件行是 **`形核 @ step`**（`★★ **athermal 形核** @ step …`），
  **不是** `引擎形核`（那是 `--arm eng`/cadence 路径的串）。
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402

ROOT = '_exp/_bk_mb'
# 两条路径的串**都**认（并分别报，防止再犯 #92）
PAT_ATH = 'athermal 形核'
PAT_ENG = '引擎形核'


def counts(tag):
    lf = '_w2_r503_%s.log' % tag
    if not os.path.exists(lf):
        return None
    with open(lf, errors='replace') as fh:
        txt = fh.read()
    n_ath = len(re.findall(re.escape(PAT_ATH), txt))
    n_eng = len(re.findall(re.escape(PAT_ENG), txt))
    warn = ('超过几何上界' in txt)
    banner = [ln.strip() for ln in txt.splitlines()
              if ('块数口径' in ln or '总根数 = B' in ln or '几何上界' in ln)]
    return dict(n_ath=n_ath, n_eng=n_eng, warn=warn, banner=banner)


def csv_last(tag):
    p = os.path.join(ROOT, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        rows = [ln.rstrip('\n') for ln in fh if ln.strip()]
    if len(rows) < 2:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    last = rows[-1].split(',')
    try:
        return dict(step=int(last[ix['step']]),
                    nreg=int(last[ix['nreg_used']]),
                    nslab=float(last[ix['nslab_n']]))
    except (ValueError, KeyError):
        return None


def main():
    print('=' * 90)
    print('R503  `--nuc-block-target` 验收（B1–B4）')
    print('=' * 90)

    # 环境量：B_max 与 n(T_end)
    n_end = None
    T_end = 500.0
    alpha = 0.041739
    Af = 1000e-9 * 500e-9
    L_box = 48 * 62.5e-9
    Bmax = (L_box ** 2) / Af
    n_end = float(CL.alpha_km_n_lath(T_end, alpha))
    print('  环境：L_box=%.2f µm  A_f=%.4f µm²  ⇒ **B_max = %.1f**'
          % (L_box * 1e6, Af * 1e12, Bmax))
    print('        n(T_end=%.0f K) = **%.1f 根/块**' % (T_end, n_end))
    print()

    data = {}
    print('  臂       B   athermal事件  引擎型事件  nreg  nslab   超界告警')
    for tag, B in (('r503B0', 0), ('r503B1', 1), ('r503B8', 8), ('r503BIG', 100)):
        c = counts(tag)
        s = csv_last('dry_' + tag)
        data[tag] = dict(c=c, s=s, B=B)
        if c is None:
            print('  %-8s %-4d **无日志**' % (tag, B))
            continue
        print('  %-8s %-4d %-13d %-11d %-5s %-8s %s'
              % (tag, B, c['n_ath'], c['n_eng'],
                 s['nreg'] if s else '—', s['nslab'] if s else '—',
                 '⚠ 有' if c['warn'] else '无'))
    print()

    c0 = data['r503B0']['c']
    c1 = data['r503B1']['c']
    c8 = data['r503B8']['c']
    cB = data['r503BIG']['c']
    if not all((c0, c1, c8, cB)):
        print('✗ 有臂缺日志 ⇒ 无法完整判决')
        return 2

    # B1 默认惰性（同读数；逐位回归另跑）
    b1 = (c0['n_ath'] == c1['n_ath'])
    print('  ── B1 `B=0` 与 `B=1` 事件数相同（`B=1` 退化为旧路径）──')
    print('     %d vs %d ⇒ **%s**' % (c0['n_ath'], c1['n_ath'],
                                      '✅ PASS' if b1 else '❌ FAIL'))
    # B2 总量真放开
    b2 = c8['n_ath'] > c0['n_ath']
    print('  ── B2 `B=8` 的事件数 > `B=0` ──')
    print('     %d vs %d（上限 %.0f → %.0f）⇒ **%s**'
          % (c8['n_ath'], c0['n_ath'], n_end, min(8 * n_end, 48),
             '✅ PASS' if b2 else '❌ FAIL'))
    # B3 几何上界守卫（反向测）
    b3 = bool(cB['warn'])
    print('  ── B3 `B=100`（> B_max=%.1f）**必须**打超界告警 ──' % Bmax)
    print('     告警 = %s ⇒ **%s**' % ('有' if cB['warn'] else '**没有**',
                                       '✅ PASS' if b3 else '❌ FAIL（守卫失效）'))
    # B4 B=1 与 B=0 相同
    b4 = (c1['n_ath'] == c0['n_ath'])
    print('  ── B4 `B=1` 与 `B=0` 相同 ⇒ **%s**' % ('✅ PASS' if b4 else '❌ FAIL'))

    print()
    print('=' * 90)
    print('★ 汇总： B1(B=1≡B=0)=%s  B2(放开)=%s  B3(超界守卫)=%s  B4(B1≡B0)=%s'
          % ('PASS' if b1 else 'FAIL', 'PASS' if b2 else 'FAIL',
             'PASS' if b3 else 'FAIL', 'PASS' if b4 else 'FAIL'))
    if b2 and b3 and b1 and b4:
        print('★ ⇒ **`--nuc-block-target` 可用**（默认 0 = 旧口径逐位不变）。')
        print('   ⚠ 仍必须记账：**块的数目是输入、不是涌现**。')
    else:
        print('★ ⇒ **未通过全部判据**，照实记。')
    print('=' * 90)
    return 0


if __name__ == '__main__':
    sys.exit(main())
