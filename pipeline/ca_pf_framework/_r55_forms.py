#!/usr/bin/env python3
"""R55: **角函数形式的离线筛选** —— 找一种能在**不冻结斜法向**的前提下
把角平均的各向异性推到 ≳12 的 `M(n)`。

## 为什么必须换形式（`R30_AUDIT_LEDGER.md` §40）
现有形式 `M/M0 = exp(−β_h(n·n*)² − β_w(n·w)²)`：把 `β_w` 从 2.3 加到 12，
角平均 `a/w` 也只从 **1.97** 升到 **5.83**，而那时 `M(45°)/M0` 已经掉到 **0.0024**（近乎冻结）。
⇒ **在这个形式里无解。**

## 物理动机（为什么"只压 w"不对）
`β_h` 的来源是**位错只能在惯习面内滑移** ⇒ 惩罚的是 `n·n*`（面外分量）。
可是 **`a` 与 `w` 都在惯习面内** ⇒ `β_h` 对**面内各向异性毫无贡献**
（`a·n* = −0.127` 只给 0.90，`w·n* = 0` 给 1.00 —— **侧面反而更快**）。
面内的 `a/w` 差别**完全靠 `β_w` 那一项**，而它是"惩罚 w"，必然**连带惩罚斜法向**。

⇒ 更符合位错图像的写法是：**"奖励 `a`（滑移方向）"而不是"惩罚 `w`"**：
      `M/M0 = exp(−β_h(n·n*)²) · [ε + (1−ε)·|n·a|^p]`
   * `n = a` ⇒ `exp(−β_h·0.127²) · 1`（与现在同）
   * `n = w` ⇒ `1 · ε`（用 `ε` 直接钉住侧面值，与 `β_w` 等效）
   * **斜法向** ⇒ `|n·a|^p` 随 `p` 迅速下降 ⇒ **只压斜法向，不动两个主面**

## 筛选判据（先写死）
  Q-1 角平均各向异性 `A ≡ <M|cosθ|>/<M|sinθ|>`
      ⚠ **标定**：现有形式给 `A = 1.97`，而实测形状比 `v_a/v_w = 1.24`
      ⇒ 该代理量**高估约 1.6 倍** ⇒ 要实测 ≳12，代理量需 **≳19**。
  Q-2 最小迁移率 `min M/M0 ≥ 0.005`（不得冻结；现有形式在 `β_w=12` 时给 0.0024 = 冻结）
  Q-3 三个主面的值要与现在**可比**（`M(a)=0.90`、`M(w)=0.10`、`M(n*)=0.0015`）
"""
import math

import numpy as np

B_H = 6.477
A_DOT_N = -0.127
TH = np.linspace(0.0, 90.0, 1801)
C = np.abs(np.cos(np.radians(TH)))
S = np.abs(np.sin(np.radians(TH)))


def m_cur(bw, th):
    """现形式：exp(−β_h(n·n*)² − β_w(n·w)²)。"""
    t = np.radians(th)
    return np.exp(-B_H * (np.cos(t) * A_DOT_N) ** 2 - bw * np.sin(t) ** 2)


def m_rew(bw, p, th, eps=None):
    """奖励形式：exp(−β_h(n·n*)²)·[ε + (1−ε)|n·a|^p]；ε 由 β_w 定（保证侧面值与现形式同）。"""
    t = np.radians(th)
    base = np.exp(-B_H * (np.cos(t) * A_DOT_N) ** 2)
    if eps is None:
        # 让 θ=90° 的值等于现形式在同一个 β_w 下的值
        eps = math.exp(-bw)
    return base * (eps + (1.0 - eps) * np.abs(np.cos(t)) ** p)


def stat(fn):
    m = fn(TH)
    A = float(np.trapezoid(m * C, TH) / np.trapezoid(m * S, TH))
    return A, float(m.min()), float(m[0]), float(m[-1])


print('=== 基线（现形式）')
for bw in (2.3, 6.0, 12.0):
    A, mn, m0, m90 = stat(lambda th, bw=bw: m_cur(bw, th))
    print('  β_w=%-5.1f  A=%-6.2f  min=%-8.4f  M(a)=%.4f  M(w)=%.4f' % (bw, A, mn, m0, m90))
print()
print('=== 奖励形式（固定 ε=exp(−2.3)=0.100，只调 p）')
print('  %-6s %-8s %-10s %-10s %s' % ('p', 'A', 'min', 'M(45°)', '判定'))
best = None
for p in (2, 4, 6, 8, 12, 16, 24, 32):
    A, mn, m0, m90 = stat(lambda th, p=p: m_rew(2.3, p, th))
    m45 = float(m_rew(2.3, p, np.array([45.0]))[0])
    flag = 'OK' if (A >= 19 and mn >= 0.005) else (
        'A 不足' if A < 19 else 'min 过低')
    print('  %-6d %-8.2f %-10.4f %-10.4f %s' % (p, A, mn, m45, flag))
    if A >= 19 and mn >= 0.005 and best is None:
        best = p
print()
print('=== 联合调参（p × β_w），找 A ≥ 19 且 min ≥ 0.005 的组合')
print('  %-6s %-6s %-8s %-10s %-10s %s' % ('p', 'β_w', 'A', 'min', 'M(45°)', '判定'))
rows = []
for p in (6, 8, 12, 16, 24):
    for bw in (2.3, 3.0, 4.0, 5.0, 6.0):
        A, mn, m0, m90 = stat(lambda th, p=p, bw=bw: m_rew(bw, p, th))
        m45 = float(m_rew(bw, p, np.array([45.0]))[0])
        ok = (A >= 19 and mn >= 0.005)
        rows.append((p, bw, A, mn, m45, ok))
        if ok or (A >= 15):
            print('  %-6d %-6.1f %-8.2f %-10.4f %-10.4f %s'
                  % (p, bw, A, mn, m45, '**候选**' if ok else '接近'))
print()
ok_rows = [r for r in rows if r[5]]
if ok_rows:
    ok_rows.sort(key=lambda r: abs(r[2] - 19))
    print('★ 最接近目标的候选：')
    for r in ok_rows[:4]:
        print('   p=%d  β_w=%.1f  ⇒ A=%.2f  min=%.4f  M(45°)=%.4f'
              % (r[0], r[1], r[2], r[3], r[4]))
else:
    print('★ **没有**满足 (A ≥ 19 且 min ≥ 0.005) 的组合')
    rows.sort(key=lambda r: -(r[2] if r[3] >= 0.005 else 0))
    print('  在 min ≥ 0.005 约束下 A 最大的几组：')
    for r in rows[:5]:
        if r[3] >= 0.005:
            print('   p=%d  β_w=%.1f  ⇒ A=%.2f  min=%.4f' % (r[0], r[1], r[2], r[3]))
print()
print('⚠ **证据强度**：本筛选用的是**角平均代理量**，它高估实测形状比约 1.6 倍')
print('  （现形式 A=1.97 vs 实测 1.24）⇒ 结论只能用于**排序与量级**，')
print('  真正的验收必须在算例上量 `v_a/v_w`（v2 口径，正对照已过）。')
