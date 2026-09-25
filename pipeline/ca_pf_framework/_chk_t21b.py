#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_t21b.py --- T2.1b 判据：B1 子模型（beta -> alpha', 位移型/athermal）的
                       T 依赖驱动力 + KM/Koistinen 动力学。

MATH_FRAMEWORK §5.5 的 B1；IMPLEMENTATION_PLAN §7.6 的 T2.1b；§7.9 的 W-1。

判据（每条都可以失败，不靠自评）：
  T2.1b-1  KM 闭式与反演（解析往返）                     —— 秒级
  T2.1b-2  dG(T) 单调 + T<->dG 往返 + T0 的物理约束带   —— 秒级
  T2.1b-3  athermal 指纹：同一 |df|、两个步数 => 同一 f   —— 读 _t21b_scan.csv
  T2.1b-4  f_eq(|df|) 单调 + 临界驱动力 dG_crit           —— 读 csv
  T2.1b-5  用 (DS 带) 把 f_eq 映射成 f(T)，拟合 alpha_KM  —— 读 csv
  T2.1b-6  界面带健康门：只有 band_ok=1 的点可用于定量     —— 读 csv

数据来源：（8 个并行点，写 _t21b_scan.csv）。
⚠ 不可引用的点（band_ok=0）会被排除并记账；排除后样本不足则该判据记 FAIL 而不是含糊过去。
"""
import math
import os

import numpy as np

import windowB_km as K

CSV = '_t21b_scan.csv'
MS = K.M_S_TI64
ok = {}


def rec(tag, good, extra=''):
    ok[tag] = bool(good)
    print('   %-62s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


def hr(t):
    print(chr(10) + '==== %s ====' % t)


# ---------------------------------------------------------------- T2.1b-1
hr('T2.1b-1 KM 闭式与反演（解析）')
f_t = 0.95
al = K.alpha_from_f(f_t, MS, 298.0)
back = float(K.koistinen(298.0, Ms=MS, alpha=al))
print('   f_end=%.2f => alpha=%.6e 1/K => f(298)=%.12f' % (f_t, al, back))
rec('T2.1b-1a alpha_from_f -> koistinen 往返（|d| < 1e-12）', abs(back - f_t) < 1e-12)

Tg = np.array([840.0, 800.0, 750.0, 700.0, 650.0, 600.0, 500.0, 400.0, 300.0])
fg = K.koistinen(Tg, Ms=MS, alpha=al)
a_fit, r2, slope, icept = K.fit_alpha(Tg, fg, Ms=MS)
print('   synthetic KM: alpha_true=%.6e  alpha_fit=%.6e  R2=%.12f  截距=%.3e'
      % (al, a_fit, r2, icept))
rec('T2.1b-1b fit_alpha 反演合成 KM 数据（相对差 < 1e-6）',
    abs(a_fit / al - 1.0) < 1e-6, 'rel=%.2e' % abs(a_fit / al - 1.0))
rec('T2.1b-1c 拟合截距 ~ 0（KM 的理论截距为 0）', abs(icept) < 1e-6, '截距=%.2e' % icept)
edge_ok = (K.koistinen(MS, Ms=MS, alpha=al) == 0.0
           and K.koistinen(MS + 50.0, Ms=MS, alpha=al) == 0.0)   # T>=Ms 应为 0
rec('T2.1b-1d T >= M_s 时 f = 0（KM 只在 T < M_s 定义）', bool(edge_ok))

# ---------------------------------------------------------------- T2.1b-2
hr('T2.1b-2 dG(T) 单调 / 往返 / T0 的物理约束')
Ts = np.linspace(300.0, 1300.0, 101)
T0 = K.T0_from_Ms(MS, K.DG_CRIT_REF, K.DS_REF)
dg = K.dG_chem(Ts, T0, K.DS_REF)
# dG(T) = -DS(T0 - T) 在 T < T0 为负、T > T0 为正 => 随 T **递增**
mono = bool(np.all(np.diff(dg) > 0))
print('   T0(DS=%.1e) = %.2f K ; dG 从 %.3e(T=300) 到 %.3e(T=1300)' % (K.DS_REF, T0, dg[0], dg[-1]))
rec('T2.1b-2a dG_chem(T) 严格单调递增（T 升 -> 驱动变小、过 T0 后变正）', mono)
rt = np.array([K.T_from_dG(K.dG_chem(t, T0, K.DS_REF), T0, K.DS_REF) for t in Ts])
rec('T2.1b-2b T <-> dG 往返（逐点 < 1e-9 K）', float(np.max(np.abs(rt - Ts))) < 1e-9,
    'max|dT|=%.2e' % float(np.max(np.abs(rt - Ts))))
rec('T2.1b-2c dG(M_s) = -|dG_crit| < 0（M_s 处驱动为负 = 有利）',
    K.dG_chem(MS, T0, K.DS_REF) < 0, 'dG(Ms)=%.3e' % K.dG_chem(MS, T0, K.DS_REF))
# 物理约束：T0 必须 > M_s，且（推导）T0 < T_beta => DS >= |dG_crit|/(T_beta - M_s)
DS_min = K.DG_CRIT_REF / (K.T_BETA_TI64 - MS)
print('   推导下界：T0 < T_beta = %.0f K  =>  DS >= |dG_crit|/(T_beta - M_s) = %.3e J/m3/K'
      % (K.T_BETA_TI64, DS_min))
band_ok = [d for d in K.DS_scale() if d >= DS_min]
print('   DS 带里满足该约束的档：%s' % ['%.1e' % d for d in band_ok])
rec('T2.1b-2d DS 带里至少有一档满足 T0 < T_beta（否则参数带自相矛盾）',
    len(band_ok) >= 1, 'DS_min=%.2e' % DS_min)
rec('T2.1b-2e 全部档都满足 T0 > M_s（必须有过冷）',
    all(K.T0_from_Ms(MS, K.DG_CRIT_REF, d) > MS for d in K.DS_scale()))

# ---------------------------------------------------------------- 读扫描
hr('T2.1b-3/4/5 模型侧 f_eq(|df|) 与 KM 拟合（数据：_t21b_scan.csv）')
rows = []
if os.path.exists(CSV):
    with open(CSV) as f:
        for ln in f.read().strip().split(chr(10))[1:]:
            p = ln.split(',')
            if len(p) == 7:
                rows.append((int(p[0]), float(p[1]), int(p[2]), float(p[3]),
                             int(p[4]), int(p[5]), float(p[6])))
if not rows:
    rec('T2.1b-3..5 扫描数据存在', False, '缺 %s（先跑 bash _run_t21b.sh）' % CSV)
else:
    rows.sort(key=lambda r: abs(r[1]))
    print('   %8s %6s %10s %7s %6s' % ('|df|/1e8', 'nstep', 'f_trans', 'band', 'ok'))
    for r in rows:
        print('   %8.2f %6d %10.6f %7d %6d' % (abs(r[1]) / 1e8, r[2], r[3], r[4], r[5]))
    good = [r for r in rows if r[5] == 1]
    f_seed = None
    try:
        import windowB_surface as W
        o0 = W.M2_twelve_variants(N=32, nstep=0, df=-1e8, quiet=True)
        f_seed = float(o0['f_trans'])
        print('   种子分数 f_seed（nstep=0）= %.6f' % f_seed)
    except Exception as e:
        print('   （种子分数取不到：%s）' % e)
    # athermal 平台：|df|=1e8 的两个步数
    pl = sorted([r for r in good if abs(abs(r[1]) / 1e8 - 1.0) < 1e-9], key=lambda r: r[2])
    if len(pl) >= 2:
        d_if = abs(pl[-1][3] - pl[0][3])
        print('   athermal 平台：nstep=%d -> f=%.6f ; nstep=%d -> f=%.6f ; |d|=%.2e'
              % (pl[0][2], pl[0][3], pl[-1][2], pl[-1][3], d_if))
        rec('T2.1b-3 athermal 指纹：步数加倍 f 不变（|d| < 0.02）', d_if < 0.02,
            '|d|=%.2e' % d_if)
    else:
        rec('T2.1b-3 athermal 指纹（需要同 |df| 的两个步数点）', False,
            '可用点 %d 个' % len(pl))
    # 单调性
    dfs = np.array([abs(r[1]) for r in good])
    fs = np.array([r[3] for r in good])
    o = np.argsort(dfs)
    dfs, fs = dfs[o], fs[o]
    mono_f = bool(np.all(np.diff(fs) > 0))
    rec('T2.1b-4a f_eq 随 |dG| 单调增（驱动越大、转变越多）', mono_f,
        'f = %s' % np.round(fs, 4).tolist())
    if f_seed is not None:
        above = fs > f_seed
        if above.any() and not above.all():
            k = int(np.argmax(above))
            d_crit = float(np.interp(f_seed, [fs[k - 1], fs[k]], [dfs[k - 1], dfs[k]]))
        elif above.all():
            d_crit = float(dfs[0])
        else:
            d_crit = float('nan')
        print('   临界驱动力（f 超过种子 %.4f 的最小 |dG|）dG_crit ~= %.3e J/m3'
              % (f_seed, d_crit))
        rec('T2.1b-4b 存在临界驱动力 dG_crit（低于它晶核不长）',
            bool(np.isfinite(d_crit) and d_crit > 0), 'dG_crit=%.3e' % d_crit)
        # KM 拟合：用 DS 带把 dG 映射成 T，再 fit alpha
        print('   KM 拟合（-ln(1-f) = alpha (M_s - T)）：')
        res = {}
        for DS in K.DS_scale():
            T0d = K.T0_from_Ms(MS, d_crit, DS)      # 用**模型自己的** dG_crit 定 T0
            Td = np.array([K.T_from_dG(-d, T0d, DS) for d in dfs])
            a_f, r2f, sl, ic = K.fit_alpha(Td, fs, Ms=MS)
            res[float(DS)] = (T0d, a_f, r2f, ic, float(Td.max()))
            print('      DS=%.1e -> T0=%.1f K ; 用到的 T 上限=%.1f K ; alpha=%.4e 1/K ; R2=%.5f ; 截距=%.3e'
                  % (DS, T0d, Td.max(), a_f, r2f, ic))
        good_res = [(d, v) for d, v in res.items() if d >= DS_min]
        r2s = [v[2] for _, v in good_res]
        rec('T2.1b-5a KM 形式能拟合模型的 f(T)（R2 > 0.98，DS 带内）',
            len(r2s) > 0 and min(r2s) > 0.98, 'min R2=%.5f' % (min(r2s) if r2s else float('nan')))
        als = [v[1] for _, v in good_res]
        # KM 要求 alpha > 0（f 随过冷单调增）。模型若给出 alpha < 0 => 物理方向反了，
        # 必须记 FAIL 而不是"区间有限就算过"（本轮正是这样：alpha < 0）。
        rec('T2.1b-5b alpha_KM > 0（KM 要求 f 随过冷单调增）',
            len(als) > 0 and min(als) > 0,
            'alpha in [%.3e, %.3e] 1/K（负值 = 方向反）'
            % (min(als), max(als)) if als else 'n/a')
        print('   => alpha_KM 是**预测值**（不是输入）；要落到一个数需要 CALPHAD 给 DS/T0')
    rec('T2.1b-6 界面带健康门：所有进入定量的点 band_ok=1',
        all(r[5] == 1 for r in good) and len(good) == len(rows),
        'good=%d/%d' % (len(good), len(rows)))

print()
print('T2.1b 汇总: %s' % ('ALL PASS' if all(ok.values())
                          else '%d/%d PASS' % (sum(ok.values()), len(ok))))
if not all(ok.values()):
    print('FAIL 项: %s' % [k for k, v in ok.items() if not v])
