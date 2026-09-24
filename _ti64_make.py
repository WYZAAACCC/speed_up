#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_ti64_make_material.py --- 把项目 Ti64 的 LKT 表拟合成 ExaCA 可用形式，两码共用'''
import numpy as np, json
tab = np.loadtxt('/mnt/f/speed_up/pipeline/ca_pf_framework/irf_ti64.csv', delimiter=',', skiprows=1)
dT, V = tab[:, 0], tab[:, 1]
lo, hi = dT.min(), dT.max()
print('Ti64 LKT 表: dT %.3f..%.3f K, V %.4g..%.4g m/s' % (lo, hi, V.min(), V.max()))

# 1) 三次拟合 V = A dT^3 + B dT^2 + C dT + D
Ac = np.polyfit(dT, V, 3)                      # [A3,A2,A1,A0]
Vc = np.polyval(Ac, dT)
# 2) 幂律拟合 V = A dT^b + C（非线性最小二乘）
from scipy.optimize import curve_fit
def pw(x, A, b, C):
    return A * x ** b + C
try:
    pp, _ = curve_fit(pw, dT, V, p0=[1e-5, 4.0, 0.0], maxfev=200000)
    Vp = pw(dT, *pp)
except Exception as e:
    pp, Vp = None, None
    print('power 拟合失败', e)

def report(name, Vfit):
    if Vfit is None: return
    rel = np.abs(Vfit - V) / V
    print('  %-8s 最大相对误差 %6.1f%%  平均 %5.1f%%  在 dT=10K 处 %+5.1f%%' % (
        name, 100 * rel.max(), 100 * rel.mean(),
        100 * (np.interp(10, dT, Vfit) - np.interp(10, dT, V)) / np.interp(10, dT, V)))
print('拟合质量:')
report('cubic', Vc)
report('power', Vp)

use = 'cubic'
if Vp is not None and np.abs(Vp - V).max() / V.max() < np.abs(Vc - V).max() / V.max():
    use = 'power'
print('=> 采用 %s' % use)

if use == 'cubic':
    mat = dict(**{'function': 'cubic',
                  'coefficients': {'A': float(Ac[0]), 'B': float(Ac[1]),
                                   'C': float(Ac[2]), 'D': float(Ac[3])},
                  'freezing_range': float(hi), 'velocity_cap': True})
    mine = dict(form='cubic', A=float(Ac[0]), B=float(Ac[1]), C=float(Ac[2]), D=float(Ac[3]))
else:
    mat = dict(**{'function': 'power',
                  'coefficients': {'A': float(pp[0]), 'B': float(pp[1]), 'C': float(pp[2])},
                  'freezing_range': float(hi), 'velocity_cap': True})
    mine = dict(form='power', A=float(pp[0]), B=float(pp[1]), C=float(pp[2]))
json.dump(mat, open('/root/bench/run/Ti64.json', 'w'), indent=1)
json.dump(mat, open('/mnt/f/speed_up/bench/exaca/Ti64.json', 'w'), indent=1)
json.dump(mine, open('/mnt/f/speed_up/bench/exaca/ti64_fit_mine.json', 'w'), indent=1)
print(json.dumps(mat, indent=1))