#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_snapinfo.py --- 快照解剖：碎裂到底是"什么"碎了（不需要引擎，秒级）

为什么需要
----------
阶段③（实验 4/6）在 step ~120 起出现**大量连通分量**：
`e4_lath6` 的 `ncomp` 21→24、最大分量只占 **17%**；`e6_mid6` 的 `ncomp` 到 **51**。
必须回答：**是主块裂开了，还是主块完好、旁边多了一堆小碎片？**
两者的物理含义完全不同，而 `nc`/`big_frac` 两个汇总数**分不开**它们。

做法
----
读 `snap_XXXXX.npz` 的 `region()`（int8）⇒ `scipy.ndimage.label` ⇒
按体积排序，报**每个分量的体积、质心、沿 a/w/n* 的跨度**，以及
"去掉小于 k 胞的碎片之后，主分量还剩多少"。
"""
import os
import sys
import glob
import argparse

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ap = argparse.ArgumentParser()
ap.add_argument('snaps', nargs='*')
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--kv', type=int, default=1)
ap.add_argument('--shape', default='mid',
                help='现场定标用的种子形状族（`lath`/`mid`/`equi`）')
ap.add_argument('--top', type=int, default=10)
ap.add_argument('--series', default=None,
                help='给定一个 `_exp/<name>` 目录：遍历**全部**快照，输出'
                     ' `nsig`/`debris`/`big_frac` 的**时间序列** CSV 到该目录')
a = ap.parse_args()
dx = a.dx_nm * 1e-9

if a.series:
    d = a.series if os.path.isabs(a.series) else os.path.join(HERE, a.series)
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                   key=lambda p: int(os.path.basename(p)[5:-4]))
    print('遍历 %d 个快照：%s' % (len(snaps), d))
    # ★ 需要设计三轴才能量"沿 a/w/n* 的跨度" ⇒ 建一个 N 很小的引擎（几十秒）只为取表
    import windowB_surface as W2                                # noqa: E402
    from T16_verify_rve import (C as _C, EPS0 as _E, DF as _DF, MOB as _MOB,
                                NV as _NV, NPF as _NPF)
    _g = W2.LevelSetMulti(16, 16 * 2.5e-8, C=_C, eps0=_E, gamma=0.15, Mob=_MOB,
                          df=[0.0] + [_DF] * _NV, workers=1, reinit_every=0)
    _nh = np.asarray(_NPF[a.kv], float)
    _nh = _nh / np.linalg.norm(_nh)
    _w = np.asarray(_g.wtab[a.kv], float)
    _w = _w / np.linalg.norm(_w)
    _a = np.asarray(_g.atab[a.kv], float)
    _a = _a - (_a @ _nh) * _nh
    _a = _a / np.linalg.norm(_a)
    # ★ 读 `meta.json` 里的逐轴定标（`_r1_exp.py` 起算时自动测的）
    import json
    cal = None
    mp = os.path.join(d, 'meta.json')
    if os.path.exists(mp):
        try:
            cal = json.load(open(mp)).get('cal')
        except Exception:
            cal = None
    if cal:
        print('★ 已读 meta.json 的逐轴定标：%s（将同时输出定标口径 `L_cal/W_cal/T_cal`）'
              % {k: (v[0], round(v[1], 4)) for k, v in cal.items()})
    else:
        # ★★★ 记账（第 6 轮自查抓到的**真偏差**）：`components.csv` 原来一律用 `+dx` 口径，
        #   而按 `_r1_calib.py`：`a`、`n*` 与网格**斜交**时 `+dx` 高读（实测 T **+48%**），
        #   `w` 是低指数方向 (1,1,0)/√2 时 `+dx` 才对。
        #   ⇒ 未定标时 `LT_big` 被**低读约 30%**，绝对值不可引用。
        #   修法：**现场算一次定标**（解析长方体 + 同一 Δx，不需要引擎；两个 N³ 场 ≈ 108 MB）。
        try:
            from _r1_exp import calibrate_axes, SHAPES
            _N = int(round(24.0e-6 / dx))
            _L = _N * dx

            class _Stub(object):
                def __init__(self):
                    self.N = _N
                    self.L = _L
                    self.dx = dx
            _dims = SHAPES.get(a.shape, SHAPES['mid'])
            _dn = ((_dims['L'], _dims['W'], _dims['T']) if _dims['kind'] == 'prism'
                   else (2 * _dims['R'], 2 * _dims['R'], 2 * _dims['R']))
            cal, _ = calibrate_axes(_Stub(), _dn, (_a, _w, _nh))
            print('★ **现场定标**（解析长方体 %.0f×%.0f×%.0f nm，Δx=%.1f nm）：%s'
                  % (_dn[0], _dn[1], _dn[2], dx * 1e9,
                     {k: (v[0], round(v[1], 4)) for k, v in cal.items()}))
            for k in ('L', 'W', 'T'):
                if k in cal:
                    print('     %s：%s（偏差 max−min %+.2f%% / +dx %+.2f%%）⇒ ×%.4f'
                          % (k, cal[k][0], 100 * cal[k][2], 100 * cal[k][3], cal[k][1]))
        except Exception as _e:
            print('⚠ 现场定标失败（%s）⇒ 只有 `+dx` 口径，`LT_big` 低读约 30%%' % _e)
            cal = None
    rows = []
    for p in snaps:
        z = np.load(p)
        reg = z['region']
        step = int(z['step'])
        m = (reg == a.kv)
        tot = int(m.sum())
        if tot < 8:
            continue
        lab, ncomp = nd.label(m)
        sz = np.bincount(lab.ravel())[1:]
        thr = 0.01 * tot
        sig = int((sz >= thr).sum())
        big = int(sz.max())
        # ★ Q-c：**最大分量**的 L/W/T（逐板条的涌现量）
        bi = int(np.argmax(sz)) + 1
        idx = np.argwhere(lab == bi).astype(np.float64)
        pa, pw, pn = idx @ _a, idx @ _w, idx @ _nh
        # ⚠ 口径：`+dx`（对轴对齐无偏；斜交方向由 `_r1_calib.py` 的定标表处理）
        Li = (pa.max() - pa.min() + 1) * dx
        Wi = (pw.max() - pw.min() + 1) * dx
        Ti = (pn.max() - pn.min() + 1) * dx
        # ★ 定标口径（有 `cal` 时）：逐轴用它自己那条偏差更小的口径 × 修正因子
        def _pick(ax_tag, arr_plusdx, arr_maxmin):
            if not cal or ax_tag not in cal:
                return arr_plusdx
            conv, fac = cal[ax_tag][0], cal[ax_tag][1]
            return (arr_maxmin if conv == 'maxmin' else arr_plusdx) * fac
        Lim = (pa.max() - pa.min()) * dx
        Wim = (pw.max() - pw.min()) * dx
        Tim = (pn.max() - pn.min()) * dx
        Lc_ = _pick('L', Li, Lim)
        Wc_ = _pick('W', Wi, Wim)
        Tc_ = _pick('T', Ti, Tim)
        rows.append((step, ncomp, sig, big / tot,
                     1.0 - sz[sz >= thr].sum() / tot, Li, Wi, Ti, Li / Wi, Li / Ti,
                     Lc_, Wc_, Tc_, Lc_ / max(Wc_, 1e-30), Lc_ / max(Tc_, 1e-30)))
    out = os.path.join(d, 'components.csv')
    with open(out, 'w') as f:
        f.write('step,ncomp,nsig,big_frac,debris,L_big,W_big,T_big,LW_big,LT_big,'
                'L_cal,W_cal,T_cal,LW_cal,LT_cal\n')
        for r in rows:
            f.write('%d,%d,%d,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g,%.6g\n'
                    % r)
    print('已写 %s' % out)
    print('  %6s %7s %6s %9s %9s | %8s %8s %8s %7s %7s | **%7s %7s**'
          % ('step', 'ncomp', 'nsig', 'big_frac', 'debris',
             'L_big', 'W_big', 'T_big', 'LW', 'LT', 'LW_cal', 'LT_cal'))
    for r in rows:
        print('  %6d %7d %6d %9.4f %9.4f | %8.0f %8.0f %8.0f %7.2f %7.2f | **%7.2f %7.2f**'
              % (r[0], r[1], r[2], r[3], r[4],
                 r[5] * 1e9, r[6] * 1e9, r[7] * 1e9, r[8], r[9], r[13], r[14]))
    sys.exit(0)

import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, DF, MOB                 # noqa: E402
from _r1_exp import axes_of                                     # noqa: E402

for sp in a.snaps:
    for pat in ([sp] if os.path.exists(sp) else
                sorted(glob.glob(os.path.join(HERE, sp, 'snap_*.npz')))[-3:]):
        z = np.load(pat)
        reg = z['region']
        step = int(z['step']) if 'step' in z else -1
        print('=' * 96)
        print('快照 %s  step=%d' % (os.path.relpath(pat), step))
        for K in ([a.kv] if a.kv > 0 else sorted(set(reg.ravel().tolist()))):
            m = (reg == K)
            nc_all = int(m.sum())
            if nc_all < 8:
                continue
            lab, ncomp = nd.label(m)
            sz = np.bincount(lab.ravel())
            order = np.argsort(-sz[1:]) + 1
            big = sz[order[0]]
            print('  变体 V%d：总胞 %d，分量数 %d，最大分量 %d 胞（%.1f%%）'
                  % (K, nc_all, ncomp, big, 100.0 * big / nc_all))
            # 去掉碎片后的"主分量"
            for kmin in (1, 8, 50, 500):
                keep = sum(s for s in sz[1:] if s >= kmin)
                print('     去掉 <%-4d 胞的碎片后剩 %6d 胞（%.1f%%），'
                      '碎片贡献 %5.1f%%'
                      % (kmin, keep, 100.0 * keep / nc_all,
                         100.0 * (nc_all - keep) / nc_all))
            print('     最大 %d 个分量：' % min(a.top, ncomp))
            for ci in order[:a.top]:
                mm = (lab == ci)
                n = int(mm.sum())
                idx = np.argwhere(mm).astype(np.float64)
                c = idx.mean(0) * dx * 1e6
                print('        #%-3d %7d 胞  %5.1f%%  质心 (%.2f, %.2f, %.2f) µm'
                      % (ci, n, 100.0 * n / nc_all, c[0], c[1], c[2]))
        print()
