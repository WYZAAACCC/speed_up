#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r105_saverdict.py —— **R103 自协调实验的判决**（判据已在 `_r103_selfac.sh` 预先写死）。

## 预登记判据（原文见 `_r103_selfac.sh` 头部）

| # | 判据 |
|---|---|
| **SA-0** | 各臂 `nf2(t=0) == 0` 且 `nblk_sig == 6`（量具自证） |
| **SA-1** | `saPair`（不可自协调集 `{1..6}`）的 `r_selfac` **下降** |
| **SA-2** | `saOdd`（可自协调集）的 `r_selfac` **保持低位**（末态 ≤ 0.20） |
| **SA-3** | `saPairE0`（`el=0`）**不下降**（降幅显著小于 `saPair`） |
| **SA-4** | 三臂 `box_touch_core == 0` 全程 |

## ⚠ 口径（必须随结论报）

* 变体**预先规定**（`--laths`）⇒ 测的是**体积分数漂移**，**不是变体选择**。
* 两臂 `G` 不同 ⇒ **裸 `r_selfac` 不可跨臂比** ⇒ 同时报
  `r_norm = (r − r_min(G))/(1 − r_min(G))`。
* ODD/PAIR 的**几何不同**（`u` 由变体 `a` 轴决定）⇒ 跨臂比较要记账。
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
from T16_verify_rve import EPS0                             # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
E_ALL = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
SCALE = float(np.mean([np.linalg.norm(e) for e in E_ALL]))
VEC = np.array([e.reshape(-1) for e in E_ALL])
ARMS_DEFAULT = [('saPair', 'PAIR {1..6}（**不可**自协调，r_min=0.4828）'),
                ('saPairE0', 'PAIR + el=0（机制归因）'),
                ('saOdd', 'ODD {1,3,5,7,9,11}（**可**自协调，r_min≈0）')]


def arms_from_argv():
    """★★ 修（**自己踩的坑**）：原来 `ARMS` 是**写死**的、**完全忽略命令行参数**
    ⇒ `_r105_saverdict.py saOddG saSet2` 读到的仍是**旧的、已中止的 R110 三条臂**
    （每个只有 3 行）⇒ **判决完全跑偏**。
    ⇒ 现在：给了参数就**只读参数里的臂**（`tag` 或 `tag=标签`）。"""
    if len(sys.argv) <= 1:
        return ARMS_DEFAULT
    out = []
    for s in sys.argv[1:]:
        if '=' in s:
            t, lab = s.split('=', 1)
        else:
            t, lab = s, s
        out.append((t.strip(), lab.strip()))
    return out


ARMS = []                                                   # 在 main() 里赋值


def rmin_of(vs):
    if not vs:
        return float('nan')
    if len(vs) == 1:
        return float(np.linalg.norm(E_ALL[vs[0] - 1])) / SCALE
    return R78._simplex_r(VEC[[v - 1 for v in vs]], SCALE)


def load(tag):
    d = os.path.join(MB, 'dry_' + tag)
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None, None
    rows = list(csv.DictReader(open(p)))
    meta = {}
    mj = os.path.join(d, 'meta.json')
    if os.path.exists(mj):
        meta = json.load(open(mj))
    return rows, meta


def col(rows, name):
    out = []
    for r in rows:
        try:
            out.append(float(r[name]))
        except (KeyError, TypeError, ValueError):
            out.append(float('nan'))
    return np.array(out)


def equal_w(G):
    """等体积分数的 `r`（= t=0 时各块同尺寸的期望值）。"""
    acc = np.sum([E_ALL[v - 1] for v in G], axis=0) / len(G)
    return float(np.linalg.norm(acc)) / SCALE


def main():
    global ARMS
    ARMS = arms_from_argv()
    print('=' * 110)
    print('_r105 —— R103/R110/R141 自协调实验判决')
    print('  读的臂：%s' % [a[0] for a in ARMS])
    print('=' * 110)
    print('  ★ **可动范围**（`saPair` 只能从"等分"降到"单纯形最优"）：')
    for lab, G in (('PAIR {1..6}', tuple(range(1, 7))),
                   ('ODD {1,3,5,7,9,11}', (1, 3, 5, 7, 9, 11))):
        e, m = equal_w(G), rmin_of(G)
        print('     %-20s 等分 r=%.4f  →  **下界 r_min=%.4f**'
              '（最多可降 %.1f%%）' % (lab, e, m, 100 * (1 - m / e)))
    print()
    res = {}
    for tag, lab in ARMS:
        rows, meta = load(tag)
        if not rows:
            print('  %-10s （无数据）' % tag)
            continue
        vmap = {int(k): int(v) for k, v in dict(meta.get('vmap', {})).items()}
        G = sorted(set(vmap.values()))
        rmin = rmin_of(G)
        r = col(rows, 'r_selfac')
        steps = col(rows, 'step')
        nf2 = col(rows, 'nf2')
        touch = col(rows, 'box_touch_core')
        # ★★★ R119 新增（`§118/§119` 的要求）：**必须同时报 `E_el/Vt`**。
        #   为什么：实测 `r_selfac` 与弹性能密度 `E_el/Vt` **散得没有规律**
        #   （82 对可比对里比值 0.22–66、中位 1.73）⇒ **`r` 不能当能量的代理**
        #   ⇒ 任何"自协调"结论**不得**只报 `r`。
        #   ⚠ 口径：`E_el_J` 与 `Vt` 都是**广延量** ⇒ 只报**比值**（`§84` 规程③）。
        _E = col(rows, 'E_el_J')
        _V = col(rows, 'Vt')
        with np.errstate(divide='ignore', invalid='ignore'):
            edens = np.where(_V > 0, _E / np.maximum(_V, 1e-300), np.nan)
        nblk = col(rows, 'nblk_sig')
        npr = [x for x in rows[-1].get('blk_nprof', '').split('/') if x.strip()]
        res[tag] = dict(G=G, rmin=rmin, r=r, steps=steps, nf2=nf2,
                        touch=touch, nblk=nblk, npr=npr,
                        rn=[(a - rmin) / (1 - rmin) if rmin < 1 - 1e-12 else float('nan')
                            for a in r])
        print()
        print('  ### %-9s %s' % (tag, lab))
        print('     G=%s   r_min(G)=%.4f   步数 %d' % (G, rmin, len(r)))
        print('     %-8s %-11s %-11s %-11s %-9s %s'
              % ('step', 'r_selfac', 'r_norm', 'nf2', '撞壁', 'nblk_sig'))
        idx = list(range(0, len(r), max(1, len(r) // 8)))
        for i in idx + ([len(r) - 1] if (len(r) - 1) not in idx else []):
            print('     %-8d %-11.4f %-11.4f %-11.0f %-9.0f %s'
                  % (steps[i], r[i], res[tag]['rn'][i], nf2[i], touch[i], nblk[i]))
        # ★ R119：**弹性能密度**逐步表（与 `r` 并列，判"能量意义上自不自在"）
        print('     %-8s %-13s %s' % ('step', 'E_el/Vt', '（相对首行）'))
        _fin_e = np.isfinite(edens)
        if _fin_e.sum() >= 2:
            # ⚠ step 0 的 `E_el_J = 0`（**那时还没算/没落盘**，不是真值）
            #   ⇒ 参考值取**第一个非零**的 `E_el/Vt`，否则会打出 `nan/inf`。
            _nz = _fin_e & (edens > 0)
            _e0 = edens[_nz][0] if _nz.any() else float('nan')
            print('     ⚠ 参考值 = **第一个非零** `E_el/Vt` = %.4g'
                  '（step 0 的 `E_el_J = 0` 是"还没算"，不是真值）' % _e0)
            for i in idx + ([len(r) - 1] if (len(r) - 1) not in idx else []):
                if not np.isfinite(edens[i]) or not (_e0 == _e0) or _e0 <= 0:
                    continue
                print('     %-8d %-13.4g %+.2f%%'
                      % (steps[i], edens[i], 100 * (edens[i] / _e0 - 1)))
            if _nz.sum() >= 3:
                _sl = float(np.polyfit(steps[_nz], edens[_nz], 1)[0])
                print('     **E_el/Vt 趋势 = %+.4g /步**（%+.4g /100步）'
                      % (_sl, _sl * 100))
            print('     ⚠ 记账（`§118/§119`）：`E_el/Vt` 随**转变体积**共模上升是正常的；')
            print('        判"能量意义上的自协调"要**同 `Vt`** 比，不能只看趋势。')
        # SA-0
        print('     SA-0 nf2(t=0)=%.0f（应 0）%s ; nblk_sig=%s ; blk_nprof=%s'
              % (nf2[0], '✅' if nf2[0] == 0 else '❌',
                 set(np.unique(nblk).astype(int).tolist()), res[tag]['npr']))
        # 趋势
        fin = np.isfinite(r)
        if fin.sum() >= 3:
            x = steps[fin]
            y = r[fin]
            sl = float(np.polyfit(x, y, 1)[0])
            print('     **r 的线性趋势 = %+.3e /步**（%+.4f /100步）  初 %.4f → 末 %.4f  '
                  'Δ=%+.4f' % (sl, sl * 100, y[0], y[-1], y[-1] - y[0]))
            mono = bool(np.all(np.diff(y) <= 1e-9))
            print('     **单调不增 = %s**' % mono)
        print('     SA-4 box_touch_core 全程 max = %.0f  ⇒ %s'
              % (np.nanmax(touch), '✅' if np.nanmax(touch) == 0 else '❌'))
    # ---- 汇总 ----
    print()
    print('=' * 110)
    print('### 汇总')
    print('=' * 110)
    print('  %-10s %-22s %-10s %-10s %-10s %s'
          % ('臂', 'G', 'r_min', 'r 初', 'r 末', '趋势/100步'))
    for tag, _ in ARMS:
        if tag not in res:
            continue
        d = res[tag]
        fin = np.isfinite(d['r'])
        sl = float(np.polyfit(d['steps'][fin], d['r'][fin], 1)[0]) * 100 if fin.sum() >= 3 else float('nan')
        print('  %-10s %-22s %-10.4f %-10.4f %-10.4f %+.4f'
              % (tag, str(d['G']), d['rmin'], d['r'][fin][0], d['r'][fin][-1], sl))
    print()
    if 'saPair' in res and np.isfinite(res['saPair']['r']).sum() >= 3:
        d = res['saPair']
        fin = np.isfinite(d['r'])
        sl = float(np.polyfit(d['steps'][fin], d['r'][fin], 1)[0])
        r0, r1 = d['r'][fin][0], d['r'][fin][-1]
        e0, m0 = equal_w(d['G']), d['rmin']
        frac = ((e0 - r1) / (e0 - m0)) if e0 > m0 else float('nan')
        print('  **SA-1** `saPair`：r %.4f → %.4f（Δ=%+.4f，趋势 %+.3e/步）'
              % (r0, r1, r1 - r0, sl))
        print('         **可动范围**：等分 %.4f → 下界 %.4f（共可降 %.4f）'
              % (e0, m0, e0 - m0))
        print('         ⇒ **已走完可动范围的 %.1f%%**（%.1f%% = 完全走到下界）'
              % (100 * frac, 100.0))
        print('         ⇒ %s' % ('**下降** ✅（动力学在走向自协调）' if sl < 0
                                 else '**未下降** ❌（测不到主动自协调）'))
    if 'saOdd' in res:
        d = res['saOdd']
        fin = np.isfinite(d['r'])
        print('  **SA-2** `saOdd` 末态 `r_selfac` = %.4f（判据 ≤ 0.20）⇒ %s'
              % (d['r'][fin][-1], '✅ 保持低位' if d['r'][fin][-1] <= 0.20 else '❌ 升上去了'))
    if 'saPairE0' in res and 'saPair' in res:
        a, b = res['saPairE0'], res['saPair']
        fa, fb = np.isfinite(a['r']), np.isfinite(b['r'])
        sa = float(np.polyfit(a['steps'][fa], a['r'][fa], 1)[0]) if fa.sum() >= 3 else float('nan')
        sb = float(np.polyfit(b['steps'][fb], b['r'][fb], 1)[0]) if fb.sum() >= 3 else float('nan')
        print('  **SA-3** el=0 趋势 %+.3e/步 vs el=1 趋势 %+.3e/步 ⇒ %s'
              % (sa, sb, '**是弹性的** ✅' if (sb < 0 and sa >= -0.1 * abs(sb))
                 else '⚠ 不是（只）弹性的 / 需再查'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
