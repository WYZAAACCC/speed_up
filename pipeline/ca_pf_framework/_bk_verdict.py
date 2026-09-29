#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_verdict.py —— **阶段 3 的判决**（判据**先登记**，不许事后改口径）。

## 预登记判据（`BLOCK_STATUS.md` §4 / `BLOCK_DERIVATION.md` §8）

| # | 判据 | 阈值 | 依据 |
|---|---|---|---|
| **V-1 块结构** | `nslab_n == M` **且** `nf3_col == M-1` **且** `nf3_faces > 0` | 全部测点成立 | ★ **`nf3_col` 单独不够**：它只数"柱里相邻的同变体板条对"，若两根板条之间夹了母相 β，`nf3_col` 仍是 M−1 而 `f3_faces` 会掉到 0 ⇒ **必须两者同时成立**才算"被界面分隔" |
| **V-2 每根都在长** | 每根板条的体积**单调不减**且末值 > 初值 | 全部 k | 用**落盘快照**重测（CSV 只存总量） |
| **V-3 界面不动** | `max\|Δpos\| < 0.12 Δx`（P-1） | 全程 | §6.6.2 |
| **V-4 没撞盒壁** | `box_touch == 0` 全程 | 全程 | §9.5（否则几何读数作废） |
| **V-5 数值健康** | `ncomp_max` 末值 ≤ 2（不碎裂） | 末值 | §9.4 |
| **V-6 通道是活的** | 与 `gpos`（γ=100）配对：`gpos` 的 \|Δpos\| **显著大于** `dry` | 比 > 3× | 没它，"界面不动"没有意义 |

跑法：  python3 _bk_verdict.py --tag p2 --arms dry,wet --ctrl-tag ctrl --ctrl-arm gpos
"""
import argparse
import csv
import glob
import json
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402


def load_series(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def fnum(r, k, dv=float('nan')):
    v = r.get(k, '')
    try:
        return float(v)
    except Exception:
        return dv


def arm_report(tagroot, arm):
    d = os.path.join(_HERE, tagroot, arm)
    if not os.path.isdir(d):
        return None
    meta = {}
    mp = os.path.join(d, 'meta.json')
    if os.path.exists(mp):
        meta = json.load(open(mp, encoding='utf-8'))
    rows = load_series(d)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    mtime = os.path.getmtime(os.path.join(d, 'series.csv')) if rows else 0.0
    out = dict(arm=arm, dir=d, meta=meta, rows=rows, snaps=snaps, mtime=mtime)
    if snaps:
        per = []
        for s in snaps:
            z = np.load(s)
            reg = z['region']
            vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
            r = BM.measure_state(reg, float(z['L']) / reg.shape[0], z['n_hab'],
                                 z['w_ax'], z['a_ax'], vmap)
            per.append((int(z['step']),
                        {k: r['vol_%d' % k] for k in sorted(vmap)},
                        r['nslab_n'], r['nf3_col'], r['f3_faces'],
                        max(r['ncomp_%d' % k] for k in sorted(vmap))))
        out['per'] = per
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_block')
    ap.add_argument('--tag', default='p2')
    ap.add_argument('--arms', default='dry,wet')
    ap.add_argument('--ctrl-root', default='_exp/_bk_ctrl')
    ap.add_argument('--ctrl-tag', default='ctrl')
    ap.add_argument('--ctrl-arm', default='gpos')
    a = ap.parse_args()

    print('=' * 104)
    print('_bk_verdict —— 阶段 3 判决（判据**先登记**）')
    print('=' * 104)
    reps = {}
    for arm in [x for x in a.arms.split(',') if x]:
        r = arm_report('%s' % a.root, '%s_%s' % (arm, a.tag))
        if r is None:
            print('  ⚠ 找不到臂 %s' % arm)
            continue
        reps[arm] = r
    if not reps:
        return 1

    for arm, r in reps.items():
        M = int(r['meta'].get('nv', 0)) or None
        rows = r['rows']
        print('-' * 104)
        print('臂 %s   M=%s   测点=%d   快照=%d' % (arm, M, len(rows), len(r['snaps'])))
        if not rows:
            continue
        ns = [fnum(x, 'nslab_n') for x in rows]
        nc = [fnum(x, 'nf3_col') for x in rows]
        nf = [fnum(x, 'nf3') for x in rows]
        dp = [abs(fnum(x, 'f3_pos_dx')) for x in rows]
        bt = [fnum(x, 'box_touch') for x in rows]
        ncm = [fnum(x, 'ncomp_max') for x in rows]
        ck = []
        ck.append(('V-1 块结构 (nslab==M & nf3col==M-1 & nf3faces>0)',
                   bool(M) and all(v == M for v in ns)
                   and all(v == M - 1 for v in nc) and all(v > 0 for v in nf[1:]),
                   'nslab=%s  nf3col=%s  nf3faces=%s'
                   % (sorted(set(ns)), sorted(set(nc)), [int(x) for x in nf[:3]])))
        if 'per' in r and len(r.get('per', [])) >= 2:
            vols = {}
            for (_st, vd, _a, _b, _c, _d) in r['per']:
                for k, v in vd.items():
                    vols.setdefault(k, []).append(v)
            mono = all(all(vols[k][i] <= vols[k][i + 1] + 1e-30
                           for i in range(len(vols[k]) - 1)) for k in vols)
            grew = all(vols[k][-1] > vols[k][0] for k in vols)
            ck.append(('V-2 每根都在长 (单调不减 & 末>初)', mono and grew,
                       '; '.join('%d:%.4f→%.4f' % (k, vols[k][0] * 1e18,
                                                   vols[k][-1] * 1e18)
                                 for k in sorted(vols))))
        else:
            ck.append(('V-2 每根都在长', None,
                       '**数据不足**：只有 %d 个快照（需 ≥2）⇒ 判据不适用'
                       % len(r.get('per', []))))
        ck.append(('V-3 界面不动 max|Δpos| < 0.12 Δx',
                   max(dp) < 0.12, 'max=%.3f Δx（末=%+.3f）'
                   % (max(dp), fnum(rows[-1], 'f3_pos_dx'))))
        ck.append(('V-4 没撞盒壁 (box_touch==0)', all(v == 0 for v in bt),
                   'box_touch=%s' % sorted(set(bt))))
        ck.append(('V-5 数值健康 (ncomp_max 末 ≤ 2)',
                   ncm[-1] <= 2, 'ncomp_max: %.0f → %.0f' % (ncm[0], ncm[-1])))

        # ---- V-1g：**「长出来的块」**专用判据 ----------------------------------
        # ★ 为什么 V-1 不能直接用在生长臂上：生长臂按定义 **t=0 只有 1 个核**
        #   （`dry_gs2` 实测 nslab_n 首值 = 1），而 V-1 要求**每个测点都 == M**
        #   ⇒ 生长臂必然 FAIL，但这不是物理失败，是判据不适用。
        # ★ 生长臂该证的是**三件事**（缺一不可）：
        #   ① 末态与预装臂**同构**：`nslab_n == M` 且 `nf3_col == M-1` 且面 > 0；
        #   ② `nslab_n` 从 1 出发、**单调不减**、**每次只 +1**（= 一次一个新场，
        #      不是一次劈裂出多片，也不是并成一片）；
        #   ③ 阶梯的**级数 == M-1**（确实发生了 M-1 次形核）。
        if r['meta'].get('grow_stack'):
            n1s = [int(round(v)) for v in ns]
            steps_up = [i for i in range(1, len(n1s)) if n1s[i] != n1s[i - 1]]
            ok_up = all(n1s[i] - n1s[i - 1] == 1 for i in steps_up)
            ok_fin = (bool(M) and n1s[-1] == M and int(round(nc[-1])) == M - 1
                      and int(round(nf[-1])) > 0)
            ck.append(('V-1g 长出来的块 (末态同构 + 单调+1 阶梯 + 级数 M-1)',
                       bool(ok_up and ok_fin and n1s[0] == 1
                            and len(steps_up) == M - 1),
                       'nslab 阶梯=%s（首=%d 末=%d，级数=%d 应为 %d，'
                       '面=%d）' % ('→'.join(str(x) for x in
                                             [n1s[0]] + [n1s[i] for i in steps_up]),
                                    n1s[0], n1s[-1], len(steps_up), M - 1,
                                    int(round(nf[-1])))))
        for t, ok, det in ck:
            print('   %-52s %s  %s'
                  % (t, 'PASS' if ok else ('—' if ok is None else '**FAIL**'), det))

    # V-6 通道活性（与正对照配对）
    cr = arm_report(a.ctrl_root, '%s_%s' % (a.ctrl_arm, a.ctrl_tag))
    if cr and cr['rows']:
        dmax = max(abs(fnum(x, 'f3_pos_dx')) for x in cr['rows'])
        print('-' * 104)
        print('正对照 %s（γ=100）：max|Δpos| = %.3f Δx' % (a.ctrl_arm, dmax))
        for arm, r in reps.items():
            dm = max(abs(fnum(x, 'f3_pos_dx')) for x in r['rows'])
            ratio = dmax / dm if dm > 1e-12 else float('inf')
            print('   V-6 %-6s vs 正对照：%.3f / %.3f = **%.1f×**  ⇒ %s'
                  % (arm, dmax, dm, ratio,
                     'PASS（通道是活的）' if ratio > 3 else '**FAIL（量具无分辨力）**'))
    else:
        print('-' * 104)
        print('⚠ 正对照（%s/%s）尚未产出 ⇒ **V-6 无法判定**（在那之前"界面不动"不作结论）'
              % (a.ctrl_root, a.ctrl_arm))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
