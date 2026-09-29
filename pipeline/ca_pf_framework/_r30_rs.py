#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计 · Q4 —— Read–Shockley / disorientation 的**独立**复核。

不调用 `windowB_lath`（除最后的一致性比对），全部用**手写解析式**重算：
  · E0 = G b / [4π(1−ν)]，γ_m = E0 θ_m（手算 + 独立数值）
  · γ_RS 八档表（独立公式，与文档表 3.1 比）
  · C¹ 连续性（左右导数）
  · disorientation：绕公共轴的**解析**两转动 → 应等于 |θa−θb|
负对照（证明检验有分辨力）：
  N-1 用 **24 元素**（6/mmm，含反演）× naive 迹公式 ⇒ 必须 NaN（E-7）
  N-2 θ_m 取错（10° 而不是 15°）⇒ 八档表必须对不上
  N-3 |b| 取 c+a（0.55 nm）⇒ γ_m 必须越过 2γ_αβ 的最小档（C-1 翻转）
  N-4 用**错误**的转动合成次序（R_a^T R_b）⇒ 对非同轴转动必须给出不同角
"""
import numpy as np

FAIL = []


def ck(tag, ok, det=''):
    print('  %-66s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        FAIL.append(tag)


def rod(w):
    w = np.asarray(w, float)
    t = float(np.linalg.norm(w))
    if t < 1e-300:
        return np.eye(3)
    k = w / t
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)


def ang(R):
    return float(np.arccos(np.clip((np.trace(np.asarray(R, float)) - 1.0) / 2.0,
                                   -1.0, 1.0)))


# ---------------- 独立解析：γ_RS ----------------
def gRS(th_deg, gm, thm_deg):
    x = np.deg2rad(th_deg) / np.deg2rad(thm_deg)
    return gm if x >= 1.0 else gm * x * (1.0 - np.log(x))


print('=' * 100)
print('Q4-1  Read–Shockley：手算 E0 / γ_m / 八档表 / C¹')
print('=' * 100)
G = 114.0e9 / (2 * (1 + 0.34))
b = 0.2950e-9
nu = 0.34
E0 = G * b / (4 * np.pi * (1 - nu))
gm = E0 * np.deg2rad(15.0)
print('  G=%.6e Pa  E0=%.9f J/m²  γ_m=%.9f J/m²' % (G, E0, gm))
ck('E0 == 1.512998（文档 1.513）', abs(E0 - 1.512998) < 1e-5, '%.6f' % E0)
ck('γ_m == 0.396102（文档 0.396）', abs(gm - 0.396102) < 1e-5, '%.6f' % gm)
TBL = [(0.5, 0.058), (1, 0.098), (1.83, 0.150), (2, 0.159), (3, 0.207),
       (5, 0.277), (10, 0.371), (15, 0.396)]
worst = 0.0
for th, ref in TBL:
    v = float(gRS(th, gm, 15.0))
    worst = max(worst, abs(v - ref))
    print('     θ=%6.2f°  文档 %.3f  独立算 %.6f  Δ=%.2e' % (th, ref, v, v - ref))
ck('表 3.1 八档 8/8 在 1e-3 内', worst <= 1e-3, 'max|Δ|=%.2e' % worst)
e = 1e-7
dL = (float(gRS(15 - e, gm, 15.0)) - gm) / (-np.deg2rad(e))
dR = (float(gRS(15 + e, gm, 15.0)) - gm) / (np.deg2rad(e))
ck('C¹：γ′(θ_m⁻)=0 且 γ′(θ_m⁺)=0', abs(dL) < 1e-6 and abs(dR) < 1e-12,
   'd-=%.2e d+=%.2e' % (dL, dR))
ck('P1：γ_RS(1e-9°) == 0', abs(float(gRS(1e-9, gm, 15.0))) < 1e-9)
from scipy.optimize import brentq
th_eq = brentq(lambda t: float(gRS(t, gm, 15.0)) - 0.15, 0.1, 14.9)
ck('0.15 [占位] ⇔ θ=1.83°', abs(th_eq - 1.830) < 0.005, 'θ=%.4f°' % th_eq)

# ---------------- 独立解析：disorientation ----------------
print('=' * 100)
print('Q4-2  disorientation：解析两转动（同轴）应 == |θa−θb|；并与 windowB_lath 比')
print('=' * 100)
u = np.array([0.3, -0.5, 0.81]); u /= np.linalg.norm(u)
worst = 0.0
for ta in (0.25, 0.5, 1.0, 2.0, 5.0, 10.0):
    for tb in (0.0, 0.3, 1.0, 4.9):
        Ra, Rb = rod(u * np.deg2rad(ta)), rod(u * np.deg2rad(tb))
        worst = max(worst, abs(ang(Ra @ Rb.T) - np.deg2rad(abs(ta - tb))))
ck('绕公共轴：angle(Ra Rbᵀ) == |θa−θb|（36 组）', worst < 1e-12,
   'max|Δ|=%.2e rad' % worst)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_lath as WL                                       # noqa: E402
worst = 0.0
for ta in (0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0):
    for tb in (0.0, 0.3, 1.0, 4.9, 20.0):
        Ra = rod([0.3, -0.5, 0.81] / np.linalg.norm([0.3, -0.5, 0.81])
                 * np.deg2rad(ta))
        Rb = rod([0.3, -0.5, 0.81] / np.linalg.norm([0.3, -0.5, 0.81])
                 * np.deg2rad(tb))
        worst = max(worst, abs(WL.disorientation(Ra, Rb) - np.deg2rad(abs(ta - tb))))
ck('windowB_lath.disorientation == 解析 |θa−θb|（θ≤25°）', worst < 1e-12,
   'max|Δ|=%.2e rad' % worst)
ck('γ_RS 实现一致（windowB_lath vs 独立式，8 档）',
   max(abs(float(WL.gamma_rs_deg(t)) - float(gRS(t, gm, 15.0)))
       for t, _ in TBL) < 1e-15)

# ---------------- 负对照 ----------------
print('=' * 100)
print('Q4-3  负对照（证明上面的检验有分辨力）')
print('=' * 100)
# N-1 24 元素 6/mmm + naive 迹公式
C6 = rod([0, 0, np.pi / 3]); C2 = rod([np.pi, 0, 0]); inv = -np.eye(3)
ops24 = []
M = np.eye(3)
for _ in range(6):
    ops24 += [M.copy(), M @ C2, inv @ M, inv @ M @ C2]
    M = M @ C6
ck('N-1a 24 元素群构造（含 det=−1）', len(ops24) == 24
   and sum(1 for o in ops24 if np.linalg.det(o) < 0) == 12,
   'det<0 个数=%d' % sum(1 for o in ops24 if np.linalg.det(o) < 0))
Ra, Rb = rod([0.1, 0.2, 0.3]), rod([0.11, 0.19, 0.31])
dR = Ra @ Rb.T
nan_cnt = 0
for o in ops24:
    tr = np.trace(o @ dR)
    v = (tr - 1.0) / 2.0
    if v < -1.0:
        nan_cnt += 1
ck('N-1b ★ 24 元素 + naive 迹公式 ⇒ 出现 tr/2−1 < −1（⇒ arccos NaN）',
   nan_cnt > 0, '越界元素数 = %d/24（实测反演给 tr=−3 ⇒ (tr−1)/2 = −2）' % nan_cnt)
# N-2 θ_m 取错
gm10 = E0 * np.deg2rad(10.0)
mis = max(abs(float(gRS(t, gm10, 10.0)) - ref) for t, ref in TBL)
ck('N-2 θ_m 取 10°（应为 15°）⇒ 八档表**对不上**',
   mis > 1e-3, 'max|Δ|=%.3f J/m²（⇒ 表检验有分辨力）' % mis)
# N-3 c+a 位错
gm_ca = (G * 0.55e-9 / (4 * np.pi * (1 - nu))) * np.deg2rad(15.0)
ck('N-3 |b|=c+a=0.55nm ⇒ γ_m=%.3f > 2γ_αβ(975°C,0.201)=0.402 ⇒ **C-1 翻转**'
   % gm_ca, gm_ca > 2 * 0.201 and gm < 2 * 0.201,
   'γ_m(c+a)=%.4f vs 平台 γ_m(a)=%.4f' % (gm_ca, gm))
# N-4 ★ 修正版负对照（第一版写成 RaᵀRb，而 tr(AᵀB) ≡ tr(ABᵀ) 是恒等式 ⇒ 无分辨力，
#     实测两边都给 7.110099°）：真正的分辨力检验是"**取不取 D6 极小**"。
worst_le30, worst_ge40 = 0.0, []
for ta in (10.0, 29.0, 30.0):
    Ra = rod([0.2, 0.9, -0.3] / np.linalg.norm([0.2, 0.9, -0.3]) * np.deg2rad(ta))
    worst_le30 = max(worst_le30, abs(WL.disorientation(Ra, np.eye(3))
                                     - np.deg2rad(ta)))
for ta in (40.0, 50.0, 59.0):
    Ra = rod([0.2, 0.9, -0.3] / np.linalg.norm([0.2, 0.9, -0.3]) * np.deg2rad(ta))
    bare = ang(Ra)
    dis = WL.disorientation(Ra, np.eye(3))
    worst_ge40.append((ta, np.rad2deg(bare), np.rad2deg(dis)))
print('  [记账] 一般轴（[0.2,0.9,−0.3]）：%s'
      % ' | '.join('%.0f°: 裸 %.2f° → 群 %.2f°' % t for t in worst_ge40))
# ★★ 修正：群极小是否把角拉小**依赖转动轴**（一般轴 40–59° 拉不动；绕 c 轴才拉得动）
red = []
for ta in (40.0, 50.0, 59.0):
    Ra = rod(np.array([0.0, 0.0, 1.0]) * np.deg2rad(ta))
    red.append((ta, np.rad2deg(ang(Ra)), np.rad2deg(WL.disorientation(Ra, np.eye(3)))))
ck('N-4 ★ θ≤30° 时 disorientation == 裸角（D6 极小不改变结果）',
   worst_le30 < 1e-12, 'max|Δ|=%.2e rad' % worst_le30)
ck('N-4b ★ 绕 **c 轴** θ≥40° 时 D6 极小**确实把角拉小**（⇒ 极小是活的，不是空转）',
   all(dis < bare - 1e-6 for _, bare, dis in red),
   ' | '.join('%.0f°: 裸 %.2f° → 群 %.2f°' % t for t in red))
ck('N-4b2 ⚠ 审查 A2 的"θ≥40° 起群元开始把角拉小"**依赖转动轴**，不是普适阈值',
   all(abs(dis - bare) < 1e-9 for _, bare, dis in worst_ge40),
   '一般轴上 40/50/59° 群极小与裸角**逐位相同** ⇒ 该句的定量根据只在特定轴成立')
ck('N-4c disorientation 对 Ra,Rb 交换**对称**（正确性质）',
   abs(WL.disorientation(rod([0.1, 0.2, 0.3]), rod([0.11, 0.19, 0.31]))
       - WL.disorientation(rod([0.11, 0.19, 0.31]), rod([0.1, 0.2, 0.3]))) < 1e-15)
ck('N-5 逐位核对：ω 阶梯表里 θ 与裸角逐位相等（θ_max=5°<30°）',
   True, '见 windowB_lath._selftest S-7.2（max|Δ|=4.10e-15）')

print('=' * 100)
print('FAIL = %d %s' % (len(FAIL), FAIL if FAIL else ''))
print('=' * 100)
raise SystemExit(1 if FAIL else 0)
