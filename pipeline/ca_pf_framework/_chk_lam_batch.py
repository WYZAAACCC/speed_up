#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_lam_batch.py --- ★ 正对照：向量化 `_lam_full_batch` 必须与逐点 `_lam_full` 一致

`AGENTS §3.19`：新量具/新实现**必须先与已知答案对照**。
`argmin_normal` 依赖 `_lam_full_batch`；若它与 `_lam_full` 不一致，
则「收敛的 argmin」求的是**另一个泛函**，整个 Round 141 的修复作废。

判据（先定判据再看数）
--------------------
  B-1 逐元素一致：`max|_lam_full_batch(C,N)[s] − _lam_full(C,N[s])| / max|C| < 1e-13`
  B-2 **`argmin_normal` 必须比 400 点随机抽样好**（同一泛函、同一 `e`）：
      报 `E(400点最优)/E(argmin_normal)` 与两者夹角 ⇒ 应 ≫1、≫0（复现 `_chk_habit2`)
  B-3 **收敛指标** `E_glob_scan/E_star` ⇒ 应 ≈1（否则全局扫描没找到盆地）
  B-4 `argmin_normal` 的**可复现性**：同输入两次调用必须逐位相同（`seed` 固定）

用法：python3 _chk_lam_batch.py
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_pf3d import (C_cubic, _lam_full, _lam_full_batch,   # noqa: E402
                          argmin_normal, E_normal, _fib_sphere)
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)

print('=' * 104)
print('_chk_lam_batch —— 向量化核的正对照 + `argmin_normal` 的收敛性')
print('=' * 104)

# ---- B-1 ----
NS = _fib_sphere(500)
t0 = time.time()
Lb = _lam_full_batch(C, NS)
Ls = np.array([_lam_full(C, n) for n in NS])
dt = time.time() - t0
err = float(np.max(np.abs(Lb - Ls)))
sc = float(np.max(np.abs(C)))
print('\nB-1 逐元素：max|batch − scalar| = %.3e ；相对 %.2e  （判据 < 1e-13）⇒ %s'
      % (err, err / sc, 'PASS' if err / sc < 1e-13 else 'FAIL'))
print('    （500 点 batch+scalar 合计 %.2f s ⇒ 20k 点 batch 约 %.1f s）'
      % (dt, dt * 0.5 * 20000 / 500))

# ---- B-2 / B-3 / B-4：对全部 12 个变体 ----
print('\nB-2/B-3/B-4 逐变体（`e` = 变体形状应变）')
print('  %-4s %12s %12s %9s %9s %8s %8s' %
      ('变体', 'E(400点best)', 'E(argmin)', '比值', '<n400,n*>', '收敛指标', '台时(s)'))
ratios, angs, cons = [], [], []
for k in range(1, NV + 1):
    e = np.asarray(EPS0[k - 1], float)
    t0 = time.time()
    nstar, vstar, consv = argmin_normal(C, e, nsamp=20000)
    el = time.time() - t0
    # 复现旧行为：400 点随机抽样
    rng = np.random.default_rng(0)
    NSr = rng.normal(size=(400, 3))
    NSr /= np.linalg.norm(NSr, axis=1)[:, None]
    vr = E_normal(C, e, NSr)
    jr = int(np.argmin(vr))
    n400, v400 = NSr[jr], float(vr[jr])
    d = float(np.degrees(np.arccos(np.clip(abs(n400 @ nstar), -1, 1))))
    ratios.append(v400 / vstar)
    angs.append(d)
    cons.append(consv)
    print('  %-4d %12.4e %12.4e %9.3f %8.2f° %8.4f %8.2f'
          % (k, v400, vstar, v400 / vstar, d, consv, el))

print('\n  B-2 `E(400点)/E(argmin)`：min %.2f  中位 %.2f  max %.2f  （应 ≫1）'
      % (min(ratios), float(np.median(ratios)), max(ratios)))
print('      `<n400, n*>`：min %.2f°  中位 %.2f°  max %.2f°  （应 ≫0）'
      % (min(angs), float(np.median(angs)), max(angs)))
print('  B-3 收敛指标 `E_glob_scan/E_star`：min %.4f  中位 %.4f  max %.4f  （判据 < 1.05）⇒ %s'
      % (min(cons), float(np.median(cons)), max(cons),
         'PASS' if max(cons) < 1.05 else 'FAIL（须加大 nsamp）'))
e0 = np.asarray(EPS0[0], float)
a1 = argmin_normal(C, e0, nsamp=20000)
a2 = argmin_normal(C, e0, nsamp=20000)
print('  B-4 可复现性：两次调用 max|Δn| = %.3e ；max|ΔE|/E = %.3e ⇒ %s'
      % (float(np.max(np.abs(a1[0] - a2[0]))),
         abs(a1[1] - a2[1]) / max(abs(a1[1]), 1e-30),
         'PASS' if np.array_equal(a1[0], a2[0]) else 'FAIL'))
print('=' * 104)
