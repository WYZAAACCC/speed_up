#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r520_paramverdict.py —— 「短跑定参数」的**预登记判据求值**（P1–P6）。

判据原文见 `_r520_paramrun.sh` 文件头，此处**原样实现，不放宽**。
对照基准：归档 `abA`（`nfsv_nofield = 9`、`n_athermal_ev = 13`、`n_target_final = 23`、
`blk_nprof` 空列）。

★ 读数口径（`#92` 的教训）：`--nuc-law athermal` 的事件行是 **`形核 @ step`**。
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = '_exp/_bk_mb'
# ★ 2026-10-04：口径改成**可传参**（原来写死 `dry_r520param`）。
#   用法：`python _r520_paramverdict.py [tag] [log]`
#     默认（不传）⇒ 仍是 `dry_r520param` / `_w2_r520_param.log` ⇒ **行为不变**。
TAG = (sys.argv[1] if len(sys.argv) > 1 else 'dry_r520param')
_LOG = (sys.argv[2] if len(sys.argv) > 2 else '_w2_r520_param.log')
REF = dict(nfsv_nofield=9, n_ath=13, n_target=23, ratio=13.0 / 23.0)


def load_csv():
    p = os.path.join(ROOT, TAG, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        rows = [ln.rstrip('\n') for ln in fh if ln.strip()]
    if len(rows) < 2:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {}
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        for k, i in ix.items():
            out.setdefault(k, []).append(c[i])
    return out


def main():
    lg = _LOG
    txt = open(lg, errors='replace').read() if os.path.exists(lg) else ''
    csv = load_csv()
    nuc = None
    p = os.path.join(ROOT, TAG, 'nuc_dbg.json')
    if os.path.exists(p):
        with open(p) as fh:
            nuc = json.load(fh)

    print('=' * 92)
    print('R520  「短跑定参数」判据（P1–P6）')
    print('=' * 92)
    n_ath = len(re.findall(r'形核\*?\*? @ step', txt))
    n_tb = txt.count('Traceback')
    has_csv = csv is not None and len(csv.get('step', [])) > 0
    last_step = int(float(csv['step'][-1])) if has_csv else None
    print('  CSV 行数 = %s ；末步 = %s ；事件行 = %d ；Traceback = %d'
          % (len(csv['step']) if has_csv else 0, last_step, n_ath, n_tb))
    if nuc:
        for k in ('n_athermal_ev', 'n_target_final', 'n_events_by_mode'):
            print('  nuc_dbg.%-20s = %s' % (k, nuc.get(k)))
        dbg = nuc.get('dbg') or {}
        for k in ('nfsv_nofield', 'fresh_blocked', 'nfsv_ok', 'attach_ok', 'ok'):
            if k in dbg:
                print('  nuc_dbg.dbg.%-16s = %s' % (k, dbg[k]))
    print()

    # ---- P1 ----
    p1 = (n_tb == 0) and has_csv
    print('  P1 不崩：Traceback=%d，CSV 行数=%s ⇒ **%s**'
          % (n_tb, len(csv['step']) if has_csv else 0,
             '✅ PASS' if p1 else '❌ FAIL'))

    # ---- P2 ----
    nf = (nuc or {}).get('dbg', {}).get('nfsv_nofield')
    p2 = (nf is not None) and (nf <= 3)
    print('  P2 变体饱和解开：`nfsv_nofield` = %s（abA = %d，判据 ≤ 3）⇒ **%s**'
          % (nf, REF['nfsv_nofield'], '✅ PASS' if p2 else '❌ FAIL'))

    # ---- P3 ----
    na = (nuc or {}).get('n_athermal_ev', n_ath)
    nt = (nuc or {}).get('n_target_final')
    ratio = (float(na) / float(nt)) if nt else float('nan')
    p3 = (nt is not None) and (ratio >= 0.70)
    print('  P3 事件数接近目标：%s / %s = **%.3f**（abA = %.3f，判据 ≥ 0.70）⇒ **%s**'
          % (na, nt, ratio, REF['ratio'], '✅ PASS' if p3 else '❌ FAIL'))

    # ---- P4 / P6 ----
    bn = csv.get('blk_nprof', [''])[-1] if has_csv else ''
    vals = [float(x) for x in str(bn).split('/') if x.strip() not in ('', 'nan')]
    has_gt1 = any(v > 1 for v in vals)
    multi = len(vals) >= 2
    p4 = bool(has_gt1 and multi)
    p6 = (len(vals) > 0)          # abA 是空列 ⇒ 本跑非空即"不同"
    print('  P4 C3（块内多根 + 多块）：末态 `blk_nprof` = %s ⇒ 有 >1？%s；≥2 块？%s ⇒ **%s**'
          % (vals, '✅' if has_gt1 else '❌', '✅' if multi else '❌',
             '✅ PASS' if p4 else '❌ FAIL'))
    print('  P6 负对照（本跑必须与 abA 的空列不同）：条目数 = %d ⇒ **%s**'
          % (len(vals), '✅ PASS（`--multi-block` 生效）' if p6 else '❌ FAIL'))

    # ---- P5 ----
    nf2 = csv.get('nf2', [None])[-1] if has_csv else None
    try:
        nf2v = float(nf2)
    except (TypeError, ValueError):
        nf2v = float('nan')
    p5 = nf2v > 0
    print('  P5 C4（块间接触）：末态 `nf2` = %s ⇒ **%s**'
          % (nf2, '✅ PASS' if p5 else '❌ FAIL'))

    print()
    print('=' * 92)
    print('★ 汇总： P1=%s P2=%s P3=%s P4=%s P5=%s P6=%s'
          % tuple('PASS' if x else 'FAIL' for x in (p1, p2, p3, p4, p5, p6)))
    if all((p1, p2, p3, p4, p5, p6)):
        print('★ ⇒ **五约束闭环的经验证据成立**：椭球 + α_KM=0.011 + 给足场数'
              ' ⇒ 变体饱和解开、块内多根堆叠、块间接触都出现。')
    else:
        print('★ ⇒ **未全部通过**，照实记，不得宣称闭环成立。')
    print('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
