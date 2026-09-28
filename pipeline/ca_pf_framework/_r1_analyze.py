#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_analyze.py --- ★ R1 实验台的结果分析（判据 C-1..C-6 + 增量速率）

判据（**先写死**，与 `_r1_exp.py` 的文档一致）
---------------------------------------------
| C-1 | 长轴与 `a` 的夹角 | ≤ 20° |
| C-2 | `L:W`（定标口径） | ≥ 3.0 |
| C-3 | `L:T`（定标口径） | ≥ 8.0 |
| C-4 | `W:T` | 报出 + `θ` 不确定度（文献 3.75，口径未知，只作参考）|
| C-5 | `fill_n` | ≥ 0.70（区分板条/板 与 纺锤/针）|
| C-6 | 界面 `|n·a|>0.9` 占比 | ≤ 25% |

★ `R20`：跨窗口的**速率**必须用**全样本最小二乘回归**，**不得**用端点差
  （端点差 ±1 胞的噪声地板会给出 26% 的散布）。
★ `R21`：必须报**逐方向每步增量的胞数**；任一分量 < 3 胞 ⇒ **结论 INCONCLUSIVE**。
★ `R23`：比值必须是**同一样品配对**的；必须标明估计量（ratio-of-means vs mean-of-ratios）。

用法：python3 _r1_analyze.py _exp/lath1 [更多目录...]
"""
import os
import sys
import csv
import glob
import argparse

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('dirs', nargs='+')
ap.add_argument('--dx-nm', type=float, default=125.0)
ap.add_argument('--skip', type=int, default=0, help='前 N 步不计入回归（瞬态）')
ap.add_argument('--every', type=int, default=4,
                help='采样间隔；当 CSV 的 step 列为空（旧版 bug）时用它按行号重建步号')
a = ap.parse_args()
dx = a.dx_nm * 1e-9


def load(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        return None
    out = {}
    for k in rows[0].keys():
        v = []
        for r in rows:
            s = (r.get(k) or '').strip()
            try:
                v.append(float(s))
            except ValueError:
                v.append(np.nan)
        out[k] = np.array(v)
    return out


def reg(x, y, i0):
    """R20：全样本最小二乘（去掉前 i0 个点的瞬态）⇒ 斜率（m/步）。"""
    x = np.asarray(x[i0:], float)
    y = np.asarray(y[i0:], float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5 or np.ptp(x[m]) <= 0:
        return np.nan, np.nan, 0
    A = np.vstack([x[m], np.ones(m.sum())]).T
    sol, res, *_ = np.linalg.lstsq(A, y[m], rcond=None)
    yh = A @ sol
    ss = 1.0 - np.sum((y[m] - yh) ** 2) / max(np.sum((y[m] - y[m].mean()) ** 2), 1e-30)
    return float(sol[0]), float(ss), int(m.sum())


print('=' * 108)
for d in a.dirs:
    S = load(d)
    print('\n### %s' % d)
    if S is None:
        print('   （没有 series.csv）')
        continue
    st = S['step']
    if not np.any(np.isfinite(st)):
        # 旧版 CSV 的 `step` 列被 NaN 覆盖（见 `_r1_exp.py` 的记账）⇒ 按行号重建
        st = np.arange(len(S['V']), dtype=float) * a.every
        print('   ⚠ CSV 的 `step` 列为空（旧版 bug）⇒ 按行号 × %d 重建' % a.every)
    n = len(st)
    last = n - 1
    # ★★ 判据修正（记账）：`fill_n`（CSV 里那列）用的是 **`+dx` 三口径的乘积**，
    #   而 `T` 的 `+dx` 在本变体上**高读 +48%** ⇒ `fill_n` 被系统性压低 32%
    #   （种子实测 fill_n = 0.621，而它**确实是**一个长方体，真值应为 1.000）。
    #   ⇒ 形态判据必须用**定标口径**的填充率 `fill_cal = V/(L_cal·W_cal·T_cal)`。
    with np.errstate(invalid='ignore', divide='ignore'):
        fill_cal = S['V'] / (S['L_cal'] * S['W_cal'] * S['T_cal'])
    print('   样本 %d 行，步 %d..%d；末态：V=%.4f µm³ 胞=%d  夹角=%.1f°  '
          '**fill_cal=%.3f**（CSV 里的 fill_n=%.3f，口径有偏）  ncomp=%d  gmed=%.3f'
          % (n, int(st[0]), int(st[-1]), S['V'][last] * 1e18, int(S['ncell'][last]),
             S['ang_a_deg'][last], fill_cal[last], S['fill_n'][last],
             int(S['ncomp'][last]), S['gmed'][last]))
    # 守卫汇总
    nb = int(np.nansum(S['box_touch']))
    ng = int(np.nansum((S['ncomp'] > 1).astype(float)))
    nh = int(np.nansum(S['band_bad']))
    print('   守卫：盒壁 %d 次；分量>1 %d 次；带病 %d 次；非有限 %d 次'
          % (nb, ng, nh, int(np.sum(~np.isfinite(S['V'])))))
    if nb:
        i = int(np.argmax(S['box_touch'] > 0))
        print('   ⛔ G-1 首次触发于 step %d ⇒ **该步及之后的形貌读数无效**（R24）'
              % int(st[i]))

    i0 = max(a.skip, 0)
    i0 = min(i0, max(n - 6, 0))
    print('\n   --- 增量速率（R20 全样本回归，去掉前 %d 个采样）---' % i0)
    rates = {}
    for tag, col in (('L', 'L_cal'), ('W', 'W_cal'), ('T', 'T_cal'),
                     ('L(maxmin)', 'L'), ('W(maxmin)', 'W'), ('T(maxmin)', 'T'),
                     ('L(+dx)', 'Lb'), ('W(+dx)', 'Wb'), ('T(+dx)', 'Tb')):
        sl, r2, nn = reg(st, S[col], i0)
        rates[tag] = sl
        if tag in ('L', 'W', 'T'):
            print('   %-10s d/dt = %+9.4f nm/步   R²=%.4f  (n=%d)  ⇒ %+6.2f 胞/步'
                  % (tag, sl * 1e9 if np.isfinite(sl) else float('nan'),
                     r2, nn, sl / dx if np.isfinite(sl) else float('nan')))
    if all(np.isfinite(rates[t]) and rates[t] > 0 for t in ('L', 'W', 'T')):
        L, W, T = rates['L'], rates['W'], rates['T']
        print('   ⇒ **ΔL : ΔW : ΔT = 1 : %.3f : %.3f**（设计 1 : %.3f : %.3f）'
              % (W / L, T / L, np.exp(-2.3), np.exp(-3.5)))
        print('   ⇒ 相对设计的**倍率**：W 快 ×%.1f  T 快 ×%.1f'
              % ((W / L) / np.exp(-2.3), (T / L) / np.exp(-3.5)))
        # ★★ **碎片守卫**（第 2 轮记账）：`norm_smooth > 0` 的臂出现过 `ncomp>1`
        #   （最大到 3）。而 `L_cal` 用的是**全体胞**口径 ⇒ 卫星碎片会把 L 拉长。
        #   ⇒ 用 `L_big`（**最大连通分量**的跨度）做一次**独立**回归来交叉核对。
        sb, r2b, nb = reg(st, S['L_big'], i0)
        fb = float(np.nanmin(S['frac_big'])) if np.any(np.isfinite(S['frac_big'])) else float('nan')
        if np.isfinite(sb) and sb > 0:
            print('   ★ 碎片守卫：`L_big`（最大分量）回归 = %+.4f nm/步（R²=%.4f）'
                  ' ⇒ `ΔL:ΔW` = 1 : %.3f（全体口径给 %.3f）；`frac_big` 最小 %.3f'
                  % (sb * 1e9, r2b, (W / sb), (W / L), fb))
            if abs((W / sb) - (W / L)) > 0.25 * (W / L):
                print('      ⚠ **全体口径与最大分量口径差 >25%% ⇒ 形貌读数被碎片污染，低置信度**')
        if fb < 0.95:
            print('      ⚠ `frac_big` 最小值 %.3f < 0.95 ⇒ 过程中确实分裂过' % fb)
        # R21：逐方向胞数（**整段**的净增量，不是每步）
        dL = (S['L_cal'][last] - S['L_cal'][0]) / dx
        dW = (S['W_cal'][last] - S['W_cal'][0]) / dx
        dT = (S['T_cal'][last] - S['T_cal'][0]) / dx
        print('   R21 **整段净增量**：ΔL=%.2f 胞  ΔW=%.2f 胞  ΔT=%.2f 胞'
              % (dL, dW, dT))
        if min(dL, dW, dT) < 3.0:
            print('   ⚠ **R21：有分量净增量 < 3 胞 ⇒ 速率比 INCONCLUSIVE**'
                  '（离散噪声地板 ±0.5 胞；要拉长总时长或加密网格）')
            print('      ⚠ 特别地：**厚度方向** ΔT=%.2f 胞 ⇒ 本轮的 T 相关比值一律低置信度'
                  % dT)
    else:
        print('   ⚠ 速率回归无效（样本太少或全为 nan）')

    # 判据
    print('\n   --- 判据（先写死，再看数）---')
    lastv = last
    LW = S['LW_cal'][lastv]
    LT = S['LT_cal'][lastv]
    WT = S['WT_cal'][lastv]
    ang = S['ang_a_deg'][lastv]
    fc = fill_cal[lastv]
    fa = S['f_a'][lastv]
    print('   ⚠ **遗传性判据**：`L:W`/`L:T` 的**绝对**值有一部分是**种子形状**带来的')
    print('     （种子 LW=%.2f LT=%.2f）⇒ 单看绝对值**不能**证明"长成了板条"；' % (
        S['LW_cal'][0], S['LT_cal'][0]))
    print('     **必须**同时看上面的**速率比**与下面的**增量**。')
    tests = [('C-1 长轴与 a 夹角 ≤20°', ang <= 20.0, '%.1f°' % ang),
             ('C-2 L:W ≥ 3.0', LW >= 3.0, '%.2f' % LW),
             ('C-3 L:T ≥ 8.0', LT >= 8.0, '%.2f' % LT),
             ('C-4 W:T（报出，无靶）', True, '%.2f' % WT),
             ('C-5 fill_cal ≥ 0.70', fc >= 0.70, '%.3f' % fc),
             ('C-6 |n·a|>0.9 占比 ≤25%', fa <= 0.25, '%.1f%%' % (100 * fa))]
    npass = 0
    for name, okv, val in tests:
        print('     %-30s %-6s  实测 %s' % (name, 'PASS' if okv else 'FAIL', val))
        npass += int(okv)
    print('   ⇒ **%d/6 通过**' % npass)
    if nb:
        print('   ⛔ 但 G-1 已触发 ⇒ 上面的 L/W/T 与比值**不可作为形态结论**')
print('\n' + '=' * 108)
