#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_wulff.py --- 判决：M(n) = M0 exp[-b_h (n.n_hab)^2 - b_w (n.w)^2] 的
   **Huygens/Wulff 渐近形状到底有多长**。

为什么必须做：项目用 "长/厚 = e^{b_h}" 反推 beta（LATH_FACET_PLAN §9.3/§10.2）。
但 level-set 推进 v_n|grad phi| 的渐近解是 v(n) **极图的凸包（Wulff 形）**，不是极图本身。
对强各向异性的指数形式，极图在 n_hab 附近是**非凸**的，凸包把它换成**平面刻面** ⇒
沿 n_hab 的半宽不是 e^{-b_h}，而是支持函数 h(n_hab) = max_theta r(theta) cos(theta)。
闭式：h(n_hab)/h(a) = e^{-1/2}/sqrt(2 b_h)  ⇒  **长/厚 = sqrt(2 b_h) * e^{1/2}**。
本脚本用 3D 凸包数值验证这条闭式，并给出"要 25 该取多少 b_h"。
"""
import os, sys
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial import ConvexHull

# 正交晶体学标架：n_hab = ẑ（薄方向）, a = x̂（长轴）, w = ŷ
n_hab = np.array([0.0, 0.0, 1.0])
av = np.array([1.0, 0.0, 0.0])
wv = np.array([0.0, 1.0, 0.0])

rng = np.random.default_rng(1)
U = rng.normal(size=(400000, 3))
U /= np.linalg.norm(U, axis=1)[:, None]


def wulff_extents(bh, bw):
    r = np.exp(-bh * (U @ n_hab) ** 2 - bw * (U @ wv) ** 2)
    P = U * r[:, None]
    h = ConvexHull(P)
    V = P[h.vertices]
    ext = []
    for u in (av, wv, n_hab):
        p = V @ u
        ext.append(0.5 * (p.max() - p.min()))
    return ext


def closed_form(bh, bw):
    return [1.0, np.exp(-0.5) / np.sqrt(2 * bw), np.exp(-0.5) / np.sqrt(2 * bh)]


print('%-28s %-34s %-34s' % ('(bh, bw)', 'Wulff 凸包数值 [a,w,n]', '闭式 h/h(a)'))
for bh, bw in ((3.5, 2.3), (3.5, 0.0), (6.0, 2.3), (6.0, 0.0), (20.0, 10.0),
               (115.0, 18.0), (1.0, 1.0), (0.0, 0.0)):
    e = np.array(wulff_extents(bh, bw)); c = np.array(closed_form(bh, bw))
    print('b_h=%-6.1f b_w=%-6.1f  [%.4f %.4f %.4f]   [%.4f %.4f %.4f]'
          % (bh, bw, e[0], e[1], e[2], c[0], c[1], c[2]))
    print('%-28s 长/厚=%6.2f 长/宽=%6.2f 宽/厚=%6.2f | 闭式 %6.2f / %6.2f / %6.2f | 朴素 e^b: %6.1f / %6.1f'
          % ('', e[0] / e[2], e[0] / e[1], e[1] / e[2], c[0] / c[2], c[0] / c[1], c[1] / c[2],
             np.exp(bh), np.exp(bw)))

print()
print('=== 反解：要得到目标长/厚 与 长/宽，beta 应该取多少 ===')
print('闭式  长/厚 = sqrt(2 b_h) * e^{1/2}  =>  b_h = (AR_thick/e^{1/2})^2 / 2')
for AR in (4.19, 5.01, 10.0, 25.0, 30.0):
    bh = (AR / np.exp(0.5)) ** 2 / 2
    bw = ((AR / 2.5) / np.exp(0.5)) ** 2 / 2     # 假设 长/宽 = 长/厚 / 2.5
    print('   目标 长/厚 = %5.1f  =>  b_h = %8.2f   (配套 长/宽=%4.1f -> b_w = %7.2f)'
          % (AR, bh, AR / 2.5, bw))
