#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r134_swapread.py —— **选支受控对照（用户裁定 C）的判决**。

对照：`dry_mb2fp10`（`--rank1-swap none`，R75 已有） vs `dry_swapinv`（`invariant`），
**其余逐项相同**（N=96 / Δx=62.5 / 6 µm / `--laths 1,1,1,3,3,3` / gap 2500 /
L=1600 W=700 T=635 / `--facet-proj 10` / 600 步 / `--pair-every 20`）。

## 预登记判据（原文在 `_r132_swapcmp.sh` 头部）

| # | 判据 |
|---|---|
| **S-1** | 两臂 `cov(t=0) ≥ cov_base(1600)×0.95 = 1.025`（块内界面完整） |
| **S-2** | **形态学结论变不变**：`f_flat` 终态、`blk_span/alen/wlen` 的**增长方向**、`blk_nprof` |
| **S-3** | 两臂 `box_touch_core == 0` 全程 |

⚠ **块按 `blk_vars` 选变体 1**（`blocks()` 按**体积降序**排，两臂顺序可能相反）。
⚠ 只在**同 step** 比（两臂的钟相同、`dt` 逐位相同）。
"""
from __future__ import annotations

import csv
import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS_DEFAULT = [('dry_mb2fp10', '`none`（弹性能极小，对照）· N=96 v1'),
                ('dry_swapinv', '`invariant`（对调 n*/a）· N=96 v1')]


def arms_from_argv():
    """★ 与 `_r105` 同样的修：**不要把臂名写死**（否则会静默读错数据源）。
    用法：`_r134_swapread.py A=标签 B=标签`。"""
    if len(sys.argv) <= 1:
        return ARMS_DEFAULT
    out = []
    for s in sys.argv[1:]:
        t, lab = (s.split('=', 1) if '=' in s else (s, s))
        out.append((t.strip(), lab.strip()))
    return out


ARMS = []
COLS = ['blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm']


def pick_var1(row, col):
    vs = [x for x in str(row.get('blk_vars', '') or '').split('/') if x.strip()]
    t = [x for x in str(row.get(col, '') or '').split('/') if x.strip()]
    try:
        i = [int(float(v)) for v in vs].index(1)
        return float(t[i])
    except (ValueError, IndexError):
        return float('nan')


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {c: {} for c in COLS}
    for key in ('nf2', 'box_touch_core', 'Vt', 'r_selfac', 'E_el_J'):
        out[key] = {}
    out['_nblk'], out['_nprof'] = {}, {}
    for r in rows:
        try:
            st = int(float(r['step']))
        except (KeyError, ValueError):
            continue
        for c in COLS:
            out[c][st] = pick_var1(r, c)
        for key in ('nf2', 'box_touch_core', 'Vt', 'r_selfac', 'E_el_J'):
            try:
                out[key][st] = float(r.get(key, 'nan') or 'nan')
            except (TypeError, ValueError):
                out[key][st] = float('nan')
        try:
            out['_nblk'][st] = int(float(r.get('nblk_sig', 'nan') or 'nan'))
        except (TypeError, ValueError):
            out['_nblk'][st] = -1
        out['_nprof'][st] = r.get('blk_nprof', '')
    return out


def cov0(tag):
    fs = sorted(glob.glob(os.path.join(MB, tag, 'snap_*.npz')),
                key=lambda q: int(re.search(r'snap_(\d+)', q).group(1)))
    if not fs:
        return None
    try:
        c = BM.snapshot_coverage(np.load(fs[0]))
        bf = c.get('beta_frac', {}) or {}
        return c.get('cov', float('nan')), (max(bf.values()) if bf else float('nan'))
    except Exception:
        return None


def main():
    global ARMS
    ARMS = arms_from_argv()
    print('=' * 112)
    print('_r134 —— 选支受控对照判决（`none` vs `invariant`，其余逐项相同）')
    print('  **实际读的臂：%s**' % [a[0] for a in ARMS])
    print('=' * 112)
    D = {}
    for t, lab in ARMS:
        d = load(t)
        if d is None:
            print('  %-14s （无数据）' % t)
            continue
        D[t] = d
        ks = sorted(d['nf2'])
        cv = cov0(t)
        print('  %-14s %-28s 步 %d→%d  `cov(0)`=%s  `maxβ(0)`=%s'
              % (t, lab, ks[0], ks[-1],
                 ('%.3f' % cv[0]) if cv else '?',
                 ('%.2f' % cv[1]) if cv else '?'))
    if len(D) < 2:
        print('\n⚠ 对照臂未跑完，稍后再来')
        return 2
    a, b = D[ARMS[0][0]], D[ARMS[1][0]]
    # ---- S-1（用 `cov` 的**长度基线**判，`§100/§101`）----
    print()
    print('  **S-1 块内界面完整（`cov(0) ≥ cov_base(L)×0.95`）**')
    for t in (ARMS[0][0], ARMS[1][0]):
        cv = cov0(t)
        if not cv:
            print('     %-14s （无 step-0 快照）' % t)
            continue
        mj = os.path.join(MB, t, 'meta.json')
        _L = None
        if os.path.exists(mj):
            import json as _json
            _L = (_json.load(open(mj)).get('exp_args', {}) or {}).get('plate_L')
        _base, _n, _ex = (BM.cov_baseline(_L * 1e-9) if _L else (float('nan'), 0, False))
        _cn = (cv[0] / _base) if (_base == _base and _base > 0) else float('nan')
        print('     %-14s cov=%-8.3f  cov_base(L=%s)=%-6.3f  **cov_norm=%.3f** ⇒ %s'
              % (t, cv[0], _L, _base, _cn, '✅' if _cn >= 0.95 else '❌'))
    # ---- S-3 ----
    print()
    print('  **S-3 不撞壁（`box_touch_core == 0` 全程）**')
    for t, d in D.items():
        m = np.nanmax(list(d['box_touch_core'].values()))
        print('     %-14s max=%.0f ⇒ %s' % (t, m, '✅' if m == 0 else '❌'))
    # ---- S-2 形态学 ----
    print()
    print('  **S-2 形态学结论变不变**')
    for c in COLS:
        ka, kb = sorted(a[c]), sorted(b[c])
        ks = sorted(set(ka) & set(kb))
        if not ks:
            print('     %-14s （无共同步）' % c)
            continue
        va = [a[c][k] for k in ks]
        vb = [b[c][k] for k in ks]
        ga = va[-1] - va[0]
        gb = vb[-1] - vb[0]
        rel = (vb[-1] - va[-1]) / max(abs(va[-1]), 1e-9)
        print('     %-14s 对照 %6.0f→%6.0f nm（Δ%+7.0f）  对调 %6.0f→%6.0f nm（Δ%+7.0f）'
              '   末态差 %+.1f%%'
              % (c, va[0], va[-1], ga, vb[0], vb[-1], gb, 100 * rel))
    # 增长方向（哪一个长得更多）
    print()
    for lab, d in (('对照 `none`', a), ('对调 `invariant`', b)):
        ks = sorted(d['blk_alen_nm'])
        da = d['blk_alen_nm'][ks[-1]] - d['blk_alen_nm'][ks[0]]
        dw = d['blk_wlen_nm'][ks[-1]] - d['blk_wlen_nm'][ks[0]]
        print('     %-20s `a` 增长 %+7.0f nm、`w` 增长 %+7.0f nm ⇒ **%s**'
              % (lab, da, dw, 'a 快（拉长）' if da > dw else 'w 快（肥化）'))
    print()
    print('  `blk_nprof`：对照 = %s（早于 R76 接线，列不存在）  ;  对调 = %s'
          % (a['_nprof'][sorted(a['_nprof'])[-1]] or '（无列）',
             b['_nprof'][sorted(b['_nprof'])[-1]]))
    print('  `nblk_sig` 末态：对照 %s ; 对调 %s'
          % (a['_nblk'][sorted(a['_nblk'])[-1]],
             b['_nblk'][sorted(b['_nblk'])[-1]]))
    print()
    print('  ---- 判读（**S-2 的出口是二选一，先写死**）----')
    print('  * 若 `a`/`w` 的**增长方向相反**，或末态跨度差 **> 20%%** ⇒')
    print('       **形态学结论会变** ⇒ 这是一个**更大的发现**，R75/R77 的相关结论要重做。')
    print('  * 若方向相同且末态差 **< 20%%** ⇒ **形态学结论不变** ⇒')
    print('       已有结果**全部有效**，只是"哪个方向叫 `n*`"的**晶体学归属**要改。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
