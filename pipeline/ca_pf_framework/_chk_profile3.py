#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T1.1c —— 判据 3：平面前沿稳态溶质剖面 vs 解析解（在**薄界面**算例上，零新增算力）

解析（无返扩散、frozen gradient、移动坐标系 ξ = x − x_if）：
    液相:  c_l(ξ) = c0·[1 + (1−k)/k · exp(−V ξ / D_L)]      (ξ > 0)
    固相:  c_s = c0                                          (ξ < 0)
判据：(a) 由 ln(c−c0) vs ξ 拟合出的**衰减长度** = l_D = D_L/V（相对差 <5%）；
      (b) 剖面相对解析解的最大偏差（在信号 > 噪声地板的区间内）<10%；
      (c) 固相侧平坦（|c−c0|/c0 < 1e-3）；(d) c_l(0) vs c0/k（= 本会话的 c_int 判据）。
用已有算例：pf1d_moose/ak3_p1c_alpha2_W10_A2/（W=10 nm、ALPHA=2、dx=2.5 nm、V=0.1）
"""
import io, os, re
import numpy as np

H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
CASES = [("ak3_thin_W10_A0", 0.0), ("ak3_thin_W10_A2", 2.0), ("ak3_thin_W10_A4", 4.0),
         ("ak3_thin_W10_A8", 8.0), ("ak3_p1c_kcw_W10_A0", 0.0),
         ("ak3_p1c_kcw_W10_A1", 1.0), ("ak3_p1c_kcw_W10_A2", 2.0)]
C0, K, DL, V = 0.036, 0.6303, 9.5e-9, 0.1
LD = DL / V
TARGET = C0 / K
print("解析：l_D = D_L/V = %.1f nm ; c_l(0) = c0/k = %.5f" % (LD * 1e9, TARGET))
print("%-26s %8s %10s %10s %9s %9s" % ("case", "ALPHA", "l_D_meas", "偏差", "c_int", "vs目标"))


def load(d, tag="profile_line_"):
    fs = [f for f in os.listdir(d) if f.startswith(tag) and f.endswith(".csv")]
    if not fs:
        return None
    f = max(fs, key=lambda s: int(re.search(r"_(\d+)\.csv$", s).group(1)))
    rows = io.open(os.path.join(d, f), encoding="utf-8").read().strip().splitlines()
    hdr = rows[0].split(",")
    ix = {h.strip(): i for i, h in enumerate(hdr)}
    a = np.array([[float(v) for v in r.split(",")] for r in rows[1:]])
    return a[:, ix["x"]], a[:, ix["c"]], a[:, ix["gr0"]]


for tag, A in CASES:
    d = os.path.join(H, tag)
    if not os.path.isdir(d):
        print("%-26s %8.1f  （无算例目录）" % (tag, A)); continue
    pr = load(d)
    if pr is None:
        print("%-26s %8.1f  （无剖面）" % (tag, A)); continue
    x, c, gr = pr
    k = int(np.argmax(gr < 0.5))
    x_if = x[k]
    # (a) 液相侧拟合 ln(c−c0)
    m = (x > x_if + 1.0 * LD) & (c - C0 > 1e-5)
    if m.sum() >= 5:
        p = np.polyfit(x[m] - x_if, np.log(c[m] - C0), 1)
        ld_m = -1.0 / p[0]
    else:
        ld_m = np.nan
    # (b) 剖面 vs 解析
    ana = C0 * (1.0 + (1.0 - K) / K * np.exp(-V * (x - x_if) / DL))
    mm = (x > x_if) & (c - C0 > 1e-4)
    dev = np.max(np.abs(c[mm] - ana[mm]) / np.maximum(np.abs(ana[mm] - C0), 1e-12)) if mm.any() else np.nan
    # (c) 固相平坦
    ms = x < x_if - 2.0 * LD
    flat = np.max(np.abs(c[ms] - C0)) / C0 if ms.any() else np.nan
    c_int = c[k]
    print("%-26s %8.1f %8.1f nm %+8.2f%% %9.6f %+8.1f%%   [固相平坦 %.1e ; 剖面最大偏差 %.1f%%]"
          % (tag, A, ld_m * 1e9, 100 * (ld_m / LD - 1.0), c_int,
             100 * (c_int / TARGET - 1.0), flat, 100 * dev))
print()
print("判据：(a) 衰减长度偏差 <5% ; (c) 固相平坦 <1e-3 ; (d) c_int 见上（本会话的 c_int 判据）")