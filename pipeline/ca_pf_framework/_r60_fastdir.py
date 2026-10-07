#!/usr/bin/env python3
"""R60: **`M(n)` 的极大值到底在哪个方向？** —— `h(a)=0.992 > M(a)=0.901` 只能这样解释。

## 疑点
`h(a) = max_n [ M(n)·(n·a) ] ≤ max_n M(n) · 1`。
而 `M(a)/M0 = exp(−β_h·0.127²) = 0.901`。
但 3D 计算给 `h(a) = 0.992` ⇒ **必有某个方向的 `M` 比 `a` 处更大**。

## 解析
`M(n)/M0 = exp(−β_h(n·n*)² − β_w(n·w)²)` ⇒ **极大值在 `n·n* = 0` 且 `n·w = 0`**，
即 `n = ±(n* × w)`（两个单位向量正交 ⇒ 叉积是单位向量）。
⇒ **模型的"最快方向"是 `n* × w`，不是 `a`！**
（这正是 `a·n* = −0.127`（7.3° 失配）的后果 —— 而该失配是 R30 早就实测过的。）
"""
import numpy as np

B_H, B_W = 6.477, 2.3
nh = np.array([-0.4424, 0.4425, -0.7801]); nh /= np.linalg.norm(nh)
a = np.array([-0.4909, 0.4909, 0.7198]); a /= np.linalg.norm(a)
w = np.cross(nh, a); w /= np.linalg.norm(w)
print('a·n* = %+.4f  （⇒ %+.2f° 失配）' % (a @ nh, np.degrees(np.arccos(a @ nh)) - 90))
print('a·w  = %+.4f   n*·w = %+.4f' % (a @ w, nh @ w))
print()

fast = np.cross(nh, w)
fast /= np.linalg.norm(fast)
print('n* × w = %s   |·| = %.6f' % (np.array2string(fast, precision=4),
                                    np.linalg.norm(fast)))
print('  (n*×w)·n* = %+.2e   (n*×w)·w = %+.2e   ⇒ M/M0 = exp(0) = 1.0000'
      % (fast @ nh, fast @ w))
print('  (n*×w)·a  = %+.4f  ⇒ 与 a 的夹角 = %.2f°'
      % (fast @ a, np.degrees(np.arccos(np.clip(abs(fast @ a), -1, 1)))))
print()


def mrel(n):
    return np.exp(-B_H * (n @ nh) ** 2 - B_W * (n @ w) ** 2)


print('  %-22s %-12s %s' % ('方向', 'M/M0', '与 a 的夹角'))
for nm, n in (('a（板条长轴）', a), ('w（宽度）', w), ('n*（惯习面法向）', nh),
              ('n* × w（最快）', fast), ('−a', -a)):
    ang = np.degrees(np.arccos(np.clip(abs(n @ a), -1, 1)))
    print('  %-22s %-12.4f %.2f°' % (nm, mrel(n), ang))
print()
print('=== 球面扫描：真正的 argmax 与它的方向')
i = np.arange(200000) + 0.5
phi = np.arccos(1 - 2 * i / 200000)
gold = np.pi * (1 + 5 ** 0.5)
th = gold * i
N = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], -1)
v = mrel(N.T).ravel() if N.ndim == 3 else None
v = np.exp(-B_H * (N @ nh) ** 2 - B_W * (N @ w) ** 2)
k = int(np.argmax(v))
print('  argmax M/M0 = %.6f  在方向 %s' % (v[k], np.array2string(N[k], precision=4)))
print('    该方向与 a 的夹角 = %.2f°   与 (n*×w) 的夹角 = %.2f°'
      % (np.degrees(np.arccos(np.clip(abs(N[k] @ a), -1, 1))),
         np.degrees(np.arccos(np.clip(abs(N[k] @ fast), -1, 1)))))
print()
print('★ 结论：模型的**最快长大方向不是板条长轴 `a`，而是偏离 7.3° 的 `n*×w`**。')
print('  ⇒ 这不是 bug，是 `a·n* = −0.127` 这个**已知失配**的直接后果；')
print('    但它意味着"`M(a)/M(w)`"**不是**该看的比值 —— 该看的是 `h(a)/h(w)`（凸化后的支撑函数）。')
