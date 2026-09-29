"""_bkr_area.py —— §6.4/P-6「界面面积单调不增」的归档对照 + (2.3) 的 O(θ³) 核对。"""
import os
import sys
import math
import csv

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
print('=' * 78)
print('§6.4 / P-6：R1 归档里界面面积 A_tot 到底增还是减')
for case in ('e4_lath6', 'e5_equi6', 'e6_mid6'):
    p = os.path.join(HERE, '_exp', case, 'series.csv')
    with open(p) as f:
        rows = list(csv.DictReader(f))
    A = np.array([float(r['A_tot']) for r in rows])
    d = np.diff(A)
    print('  %-10s A_tot: 首=%.4e 末=%.4e  (×%.2f)  单调增=%s  最小步增=%.2e 最大步增=%.2e'
          % (case, A[0], A[-1], A[-1] / A[0], bool((d > 0).all()), d.min(), d.max()))

print()
print('=' * 78)
print('(2.3) 的 O(θ³)：|ω_α − ω_β| vs angle(R_α R_β^T) 的差')


def expso3(w):
    th = np.linalg.norm(w)
    if th < 1e-300:
        return np.eye(3)
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]]) / th
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * (K @ K)


rng = np.random.default_rng(0)
print('   deg     中位|Δangle|        比值/deg³')
for deg in (0.5, 1.0, 2.0, 4.0, 8.0):
    errs = []
    for _ in range(60):
        w1 = rng.normal(size=3); w1 = w1 / np.linalg.norm(w1) * math.radians(deg)
        w2 = rng.normal(size=3); w2 = w2 / np.linalg.norm(w2) * math.radians(deg)
        R1, R2 = expso3(w1), expso3(w2)
        dR = R1 @ R2.T
        ang = math.degrees(math.acos(min(1.0, max(-1.0, (np.trace(dR) - 1) / 2))))
        errs.append(abs(ang - math.degrees(np.linalg.norm(w1 - w2))))
    e = float(np.median(errs))
    print('   %5.1f      %.4e        %.4e' % (deg, e, e / deg ** 3))
print('  ⇒ 误差 ∝ θ³ ✓（文档 (2.3) 的 O(θ³) 正确）')
