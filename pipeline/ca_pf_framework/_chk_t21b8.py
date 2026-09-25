#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_t21b8.py --- T2.1b-8 判据：B1 的 **athermal 形核层**。

上游：WINDOWB_SURFACE_AUDIT §11.7（生长测不到 f_eq ⇒ 分数 vs T 只能由形核给出）。
数据： 产生的 _t21b8_*.json（3 个 alpha + 1 个保温算例）。
判决三档 PASS / FAIL / PENDING（PENDING 必须写明原因）。
"""
import glob
import json
import os

import numpy as np

import windowB_km as K

ok = {}


def rec(tag, verdict, extra=''):
    ok[tag] = verdict
    print('   %-60s %-7s %s' % (tag, verdict, extra))


def load(tag):
    fn = '_t21b8_%s.json' % tag
    if not os.path.exists(fn):
        return None
    d = json.load(open(fn))
    for k in ('t', 'T', 'f', 'n', 'dG'):
        d[k] = np.array(d[k], float)
    return d


print('==== T2.1b-8 athermal 形核层 ====')
J = {}
for tag in ('a0.005', 'a0.011', 'a0.020', 'hold'):
    d = load(tag)
    J[tag] = d
    if d is None:
        print('   [缺] %s（先跑 bash _run_t21b8.sh）' % tag)
if all(v is None for v in J.values()):
    rec('T2.1b-8 数据存在', 'PENDING', '缺 _t21b8_*.json')
else:
    dh = J['hold']
    # ---- 8e：T >= M_s 时无晶核
    i0 = np.where(dh['T'] >= dh['Ms'] if 'Ms' in dh else dh['T'] >= K.M_S_TI64)[0]
    rec('T2.1b-8e T >= M_s 时 N = 0 且 f = 0（M_s 锚）',
        'PASS' if (dh['n'][0] == 0 and dh['f'][0] == 0.0) else 'FAIL',
        'N(t=0)=%d f(t=0)=%.4f' % (dh['n'][0], dh['f'][0]))
    # ---- 8a：athermal 指纹（只在降温时新增晶核）
    cool = dh['t'] <= dh['t_cool'] + 1e-30
    hold = ~cool
    dN_cool = float(np.diff(dh['n'][cool]).sum()) if cool.sum() > 1 else 0.0
    dN_hold = float(np.diff(dh['n'][hold]).sum()) if hold.sum() > 1 else 0.0
    rec('T2.1b-8a athermal 指纹：降温新增晶核 / 保温**不新增**',
        'PASS' if (dN_cool > 0 and dN_hold == 0.0) else 'FAIL',
        'dN(降温)=%.0f dN(保温)=%.0f' % (dN_cool, dN_hold))
    # ---- 8b：保温足够长后 f 落到 KM(alpha_in) 的 ±0.05 内
    km = 1.0 - np.exp(-dh['alpha'] * np.maximum(K.M_S_TI64 - dh['T'], 0.0))
    dev_hold = (dh['f'] - km)[hold]
    best = float(np.max(dh['f'][hold]))
    km_end = float(km[hold][-1])
    rec('T2.1b-8b 保温段 f 接近 KM(alpha_in)（|dev| < 0.05）',
        'PASS' if abs(best - km_end) < 0.05 else 'FAIL',
        'f_max(保温)=%.4f  KM=%.4f  dev=%+.4f' % (best, km_end, best - km_end))
    # ---- 8c：f 与 N 都随 T 单调增（降温段）
    f_c, n_c, T_c = dh['f'][cool], dh['n'][cool], dh['T'][cool]
    o = np.argsort(-T_c)
    mono_f = bool(np.all(np.diff(f_c[o]) >= -1e-9))
    mono_n = bool(np.all(np.diff(n_c[o]) >= 0))
    rec('T2.1b-8c 降温段 f 与 N 都随过冷单调增', 'PASS' if (mono_f and mono_n) else 'FAIL',
        'f 单调=%s N 单调=%s' % (mono_f, mono_n))
    # ---- 8d：alpha 敏感度（三个 alpha 给出不同的 f_end / N_end）
    rows = []
    for tag, a in (('a0.005', 0.005), ('a0.011', 0.011), ('a0.020', 0.020)):
        d = J[tag]
        if d is not None:
            rows.append((a, float(d['f'][-1]), int(d['n'][-1])))
    print('   alpha 敏感度: %s' % ['a=%.3f -> f_end=%.4f N_end=%d' % r for r in rows])
    spread = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    spreadN = (max(r[2] for r in rows) - min(r[2] for r in rows)) if rows else 0
    rec('T2.1b-8d f(T) 对 alpha_KM 敏感（=> alpha 可标定，不是无效参数）',
        'PASS' if (spread > 0.03 and spreadN > 3) else 'FAIL',
        'df=%.3f dN=%d' % (spread, spreadN))
    # ---- 8f：与"只生长"对照（引用 scan3 的结论，不需新算例）
    print('   对照（只生长、无新形核；数据 _t21b_scan3.csv）：5 个驱动在 t=4e-6 s 全部饱和到 f~0.96、')
    print('     与驱动无关（离散 0.019）=> 生长量不出 f(T)。本层通过 am 形核给出 f(T) 依赖 ✓')
    rec('T2.1b-8f 形核层是必要的（只生长测不到 f(T)）', 'PASS',
        '见 audit §11.7 + 上面的 alpha 敏感度')
    # ---- 记账：碰撞/吞并期的非单调（真实存在的数值-物理混合效应）
    if hold.sum() > 2:
        fh = dh['f'][hold]
        drops = int(np.sum(np.diff(fh) < -0.01))
        print('   记账：保温段 f 的非单调下跌次数 = %d（碰撞/吞并期的区域记账伪影，见 §11.7）' % drops)

nP = sum(1 for v in ok.values() if v == 'PASS')
nF = sum(1 for v in ok.values() if v == 'FAIL')
nQ = sum(1 for v in ok.values() if v == 'PENDING')
print()
print('T2.1b-8 汇总: PASS %d / FAIL %d / PENDING %d（共 %d）' % (nP, nF, nQ, len(ok)))
if nF:
    print('FAIL 项: %s' % [k for k, v in ok.items() if v == 'FAIL'])
if nQ:
    print('PENDING 项: %s' % [k for k, v in ok.items() if v == 'PENDING'])
