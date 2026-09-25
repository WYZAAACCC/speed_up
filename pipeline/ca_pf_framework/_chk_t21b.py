#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_t21b.py --- T2.1b 判据：B1 子模型（beta -> alpha', 位移型/athermal）的 T 依赖 + KM。

MATH_FRAMEWORK §5.5 的 B1；IMPLEMENTATION_PLAN §7.6/§7.9 的 W-1；审计 WINDOWB_SURFACE_AUDIT §11。

判决有三档：
  PASS    —— 有数值证据
  FAIL    —— 有数值证据且不成立
  PENDING —— **当前测量/模型还测不了**（必须写明为什么；不许当 PASS 混过去）

数据来源：
  _t21b_scan2.csv : 同一物理时刻 t_end=4e-7 s，|df| = 0.5..5e8   -> 判"f 随驱动单调增"
  _t21b_scan3.csv : 长时刻 t_end=4e-6 s（含 0.8e8 的 8e-6 平台对）-> 判"f_eq 是否存在"
"""
import math
import os

import numpy as np

import windowB_km as K
import windowB_surface as W

MS = K.M_S_TI64
ok = {}


def rec(tag, verdict, extra=''):
    ok[tag] = verdict
    print('   %-58s %-7s %s' % (tag, verdict, extra))


def hr(t):
    print(chr(10) + '==== %s ====' % t)


def read_csv(fn):
    rows = []
    if not os.path.exists(fn):
        return rows
    for ln in open(fn).read().strip().split(chr(10))[1:]:
        p = ln.split(',')
        if len(p) == 9:
            rows.append(dict(N=int(p[0]), df=float(p[1]), t_end=float(p[2]),
                             k=int(p[3]), t=float(p[4]), f=float(p[5]),
                             band=int(p[6]), ok=int(p[7]), secs=float(p[8])))
    return rows


# ---------------------------------------------------------------- T2.1b-1
hr('T2.1b-1 KM 闭式与反演（解析）')
f_t = 0.95
al = K.alpha_from_f(f_t, MS, 298.0)
back = float(K.koistinen(298.0, Ms=MS, alpha=al))
rec('T2.1b-1a alpha_from_f -> koistinen 往返（|d| < 1e-12）',
    'PASS' if abs(back - f_t) < 1e-12 else 'FAIL', 'f(298)=%.12f' % back)
Tg = np.array([840.0, 800.0, 750.0, 700.0, 650.0, 600.0, 500.0, 400.0, 300.0])
fg = K.koistinen(Tg, Ms=MS, alpha=al)
a_fit, r2, slope, icept = K.fit_alpha(Tg, fg, Ms=MS)
rec('T2.1b-1b fit_alpha 反演合成 KM（相对差 < 1e-6）',
    'PASS' if abs(a_fit / al - 1.0) < 1e-6 else 'FAIL', 'R2=%.10f rel=%.1e' % (r2, abs(a_fit / al - 1)))
rec('T2.1b-1c 拟合截距 ~ 0（KM 理论截距为 0）',
    'PASS' if abs(icept) < 1e-6 else 'FAIL', '截距=%.2e' % icept)
rec('T2.1b-1d T >= M_s 时 f = 0',
    'PASS' if (K.koistinen(MS, Ms=MS, alpha=al) == 0.0
               and K.koistinen(MS + 50.0, Ms=MS, alpha=al) == 0.0) else 'FAIL')

# ---------------------------------------------------------------- T2.1b-2
hr('T2.1b-2 dG(T) 单调 / 往返 / T0 的物理约束带')
Ts = np.linspace(300.0, 1300.0, 101)
T0 = K.T0_from_Ms(MS, K.DG_CRIT_REF, K.DS_REF)
dg = K.dG_chem(Ts, T0, K.DS_REF)
rec('T2.1b-2a dG_chem(T) 严格单调递增（T 升 -> 驱动变小、过 T0 变正）',
    'PASS' if np.all(np.diff(dg) > 0) else 'FAIL',
    'dG: %.3e(T=300) -> %+.3e(T=1300)' % (dg[0], dg[-1]))
rt = np.array([K.T_from_dG(K.dG_chem(t, T0, K.DS_REF), T0, K.DS_REF) for t in Ts])
rec('T2.1b-2b T <-> dG 往返（< 1e-9 K）',
    'PASS' if float(np.max(np.abs(rt - Ts))) < 1e-9 else 'FAIL')
rec('T2.1b-2c dG(M_s) = -|dG_crit| < 0', 'PASS' if K.dG_chem(MS, T0, K.DS_REF) < 0 else 'FAIL',
    'dG(Ms)=%.3e' % K.dG_chem(MS, T0, K.DS_REF))
DS_min = K.DG_CRIT_REF / (K.T_BETA_TI64 - MS)
band = [d for d in K.DS_scale() if d >= DS_min]
rec('T2.1b-2d DS 带里至少一档满足 T0 < T_beta（物理约束）',
    'PASS' if band else 'FAIL', 'DS_min=%.2e ; 合格档 %s' % (DS_min, ['%.1e' % d for d in band]))
rec('T2.1b-2e 全部档满足 T0 > M_s（必须过冷）',
    'PASS' if all(K.T0_from_Ms(MS, K.DG_CRIT_REF, d) > MS for d in K.DS_scale()) else 'FAIL')

# ---------------------------------------------------------------- T2.1b-7 符号约定
hr('T2.1b-7 符号约定（由 _chk_t21b7.py 判决，此处引用其结论）')
print('   df[variant] > 0 => 长大（dV1=+18432, v/(M|df|)=+0.9989）')
print('   df[variant] < 0 => 缩小（dV1=-18432, v/(M|df|)=-1.0000）')
rec('T2.1b-7 约定 df > 0 = 变体有利（= PF3D 的 dF/dphi_v = -dG）', 'PASS',
    '见 _chk_t21b7.py（ALL PASS）')

# ---------------------------------------------------------------- 模型侧
hr('T2.1b-3/4 模型侧：同一物理时刻的 f(|dG|)（_t21b_scan2.csv）')
r2 = read_csv('_t21b_scan2.csv')
r3 = read_csv('_t21b_scan3.csv')
if not r2:
    rec('T2.1b-4a 扫描数据存在', 'PENDING', '缺 _t21b_scan2.csv（先跑 bash _run_t21b2.sh）')
else:
    same_t = [r for r in r2 if abs(r['t_end'] - 4e-7) < 1e-12 and r['ok'] == 1]
    same_t.sort(key=lambda r: r['df'])
    print('   %9s %8s %8s %7s' % ('|df|/1e8', 'k_used', 't[s]', 'f'))
    for r in same_t:
        print('   %9.2f %8d %8.3e %7.4f' % (r['df'] / 1e8, r['k'], r['t'], r['f']))
    fs = np.array([r['f'] for r in same_t])
    mono = bool(np.all(np.diff(fs) > 0)) if fs.size > 2 else False
    rec('T2.1b-4a 同一时刻 f 随 |dG| 单调增（物理要求）',
        'PASS' if mono else 'FAIL', 'f = %s' % np.round(fs, 3).tolist())

hr('T2.1b-5 f_eq 是否存在？（长时刻 _t21b_scan3.csv）')
if not r3:
    rec('T2.1b-5a 长时刻扫描存在', 'PENDING', '缺 _t21b_scan3.csv（先跑 bash _run_t21b3.sh）')
else:
    long_t = [r for r in r3 if abs(r['t_end'] - 4e-6) < 1e-12 and r['ok'] == 1]
    long_t.sort(key=lambda r: r['df'])
    print('   %9s %8s %8s %7s' % ('|df|/1e8', 'k_used', 't[s]', 'f'))
    for r in long_t:
        print('   %9.2f %8d %8.3e %7.4f' % (r['df'] / 1e8, r['k'], r['t'], r['f']))
    fl = np.array([r['f'] for r in long_t])
    spread = float(fl.max() - fl.min())
    print('   离散度（max-min）= %.4f  （若与驱动无关则该值应很小）' % spread)
    rec('T2.1b-5a 长时刻 f 与 |dG| **无关**（离散 < 0.05）=> 测到的是几何饱和',
        'PASS' if spread < 0.05 else 'FAIL', 'max-min=%.4f' % spread)
    rec('T2.1b-5b KM 拟合得到 alpha>0（需要真正的 f_eq）', 'PENDING',
        '见 11.7：自协调 12 变体下弹性能~0 => 驱动不随 f 消失 => 生长测不到 f_eq；'
        'B1 的 f(T) 必须由 athermal 形核给出')
    pl = [r for r in r3 if abs(r['df'] - 0.8e8) < 1e-6]
    if len(pl) >= 2:
        pl.sort(key=lambda r: r['t_end'])
        print('   平台检验：|df|=0.8e8  t=%.0e -> f=%.4f ; t=%.0e -> f=%.4f'
              % (pl[0]['t_end'], pl[0]['f'], pl[-1]['t_end'], pl[-1]['f']))
        rec('T2.1b-3 平台：时间加倍后 f 变化 < 0.02', 
            'PASS' if abs(pl[-1]['f'] - pl[0]['f']) < 0.02 else 'FAIL',
            '|d|=%.4f' % abs(pl[-1]['f'] - pl[0]['f']))

nP = sum(1 for v in ok.values() if v == 'PASS')
nF = sum(1 for v in ok.values() if v == 'FAIL')
nQ = sum(1 for v in ok.values() if v == 'PENDING')
print()
print('T2.1b 汇总: PASS %d / FAIL %d / PENDING %d（共 %d）' % (nP, nF, nQ, len(ok)))
if nF:
    print('FAIL 项: %s' % [k for k, v in ok.items() if v == 'FAIL'])
if nQ:
    print('PENDING 项: %s' % [k for k, v in ok.items() if v == 'PENDING'])
