#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_dxconsist.py --- ★ 把"`norm_smooth` 的 Δx 无关性只有 2 个点"升级为**统计陈述**

问题
----
`norm_smooth=4` 的合格判据是"Δx=250 nm 与 Δx=125 nm 必须给**同一个** `ΔL:ΔW`"。
我此前只报了"0.115 vs 0.098，**只有 2 个点，证据偏弱**" —— 那是**没做不确定度分析**。

其实 `R3`/`R21` 早就规定了量化口径：跨度读数的量化不确定度是 **±0.5 胞**。
把它传到比值上，就能判断"两个点是不是同一个值"。

做法
----
`ΔL:ΔW` 的**净增量**（`R21`）各有 `ΔN_L`、`ΔN_W` 胞。设每轴 ±0.5 胞的量化误差、独立，
则 `r = ΔN_L/ΔN_W` 的相对不确定度为 `sqrt((0.5/ΔN_L)² + (0.5/ΔN_W)²)`。
两臂之差用 `sqrt(σ1²+σ2²)` 比较 ⇒ 报 **σ 倍数**。

数据来源：`_r1_analyze.py` 的 `R21 整段净增量`（各臂的 series.csv）。
"""
import os
import csv
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def rate(d, dx_nm, i0=8):
    """★ `R20`：**必须用全样本最小二乘回归**求速率（端点差有 ±1 胞的噪声地板，会给出 26% 散布）。
       σ 由**残差**给出（它已经包含了 ±0.5 胞的量化噪声）。
       ⚠ 记账：本脚本第一版用了 `(L[-1]-L[0])/dx` 的**净增量之比** —— 那是 `R20` **明令禁止**
         的端点差口径，而且给出 8.13 / 6.79 两个数（与回归口径的 8.70 / 10.2 明显不同）。
         ⇒ 已改为回归。**差一点又犯一次"用错口径还算出一个数"的错。**"""
    p = os.path.join(HERE, d, 'series.csv')
    rows = list(csv.DictReader(open(p)))

    def col(k):
        v = []
        for r in rows:
            try:
                v.append(float(r[k]))
            except (ValueError, KeyError):
                v.append(np.nan)
        return np.array(v)
    L, W = col('L_cal'), col('W_cal')
    st = np.arange(len(L), dtype=float) * 4.0
    j = np.where(np.isfinite(L) & np.isfinite(W))[0]
    j = j[j >= i0]
    if j.size < 6:
        return None
    t = st[j]

    def fit(y):
        A = np.vstack([t, np.ones_like(t)]).T
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ sol
        dof = max(j.size - 2, 1)
        s2 = float(resid @ resid) / dof
        cov = s2 * np.linalg.inv(A.T @ A)
        return float(sol[0]), float(np.sqrt(cov[0, 0]))
    sL, eL = fit(L[j])
    sW, eW = fit(W[j])
    if sW <= 0 or sL <= 0:
        return None
    r = sL / sW
    sig = r * np.sqrt((eL / sL) ** 2 + (eW / sW) ** 2)
    return r, sig, sL * 1e9, eL * 1e9, sW * 1e9, eW * 1e9, j.size


A = ('_exp/mid250_ns4', 250.0, 'Δx=250 nm（种子 ×2，T=2.56 胞）')
B = ('_exp/mid192_ns4', 125.0, 'Δx=125 nm（R24，T=2.56 胞）')
print('=' * 96)
print('`norm_smooth=4` 的 Δx 无关性：**R20 回归口径** + 残差不确定度')
print('=' * 96)
res = {}
for d, dxn, tag in (A, B):
    o = rate(d, dxn)
    if o is None:
        print('%-46s  ✗ 数据不足' % tag); continue
    r, sig, sL, eL, sW, eW, n = o
    res[tag] = (r, sig)
    print('%-40s  `ΔL:ΔW` = **%.3f ± %.3f**' % (tag, r, sig))
    print('%-40s     L 速率 %.3f±%.3f nm/步 ；W 速率 %.3f±%.3f nm/步 ；n=%d'
          % ('', sL, eL, sW, eW, n))
if len(res) == 2:
    (r1, s1), (r2, s2) = list(res.values())
    dd = abs(r1 - r2)
    ss = np.hypot(s1, s2)
    print('\n  两臂之差 = %.3f ± %.3f  ⇒  **%.2f σ**' % (dd, ss, dd / ss))
    print('  ⇒ 判定：%s'
          % ('**两臂一致（<2σ）⇒ Δx 无关性成立**（"只有 2 个点"的顾虑被量化排除）'
             if dd / ss < 2.0 else
             '**两臂不一致（≥2σ）⇒ 该正则化与 Δx 耦合，不能当修复用**'))
    print('  ⚠ 样本仍只有 **2 个 Δx**；要写成"Δx 收敛"仍需第三个点。')
print('=' * 96)
