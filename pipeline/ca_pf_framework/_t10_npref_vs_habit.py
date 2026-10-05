#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_npref_vs_habit.py --- ★ 引擎的 `npref`（能量最优法向）**是不是**晶体学惯习面 `{011}_β`？

## 为什么要问
* 引擎 `:5787`：`npref[v+1] = _argmin_normal(C, eps0[v])[0]`
* `_argmin_normal`（`:947`）最小化 `½·ε⁰ : Λ(C,n) : ε⁰` ⇒ **弹性能最小的板条法向**
* 而 `RESEARCH_INTENT.md:101-102` 定义：**同一惯习面族的不同变体 ⇒ packet** ⇒ **晶体学口径 `{011}_β`**
⇒ **若两者不同，"packet" 的判据就不是晶体学的**，与意图不符。**本脚本判定这件事。**

## 判据（**可 FAIL**）
* **H1 正对照**：把 6 个 `{011}` 法向逐个喂进同一套比对器，每个都应判为"命中自己"（max|cos| = 1）。
* **H2 主判定**：12 个 `_argmin_normal` 输出对 `{011}` 集合的 **max|cos|**
  * ≈ 1 ⇒ **一致**（能量最优法向恰是 `{011}`）⇒ `npref` 口径没问题；
  * ≪ 1 ⇒ **不一致** ⇒ `npref` 不是晶体学惯习面 ⇒ 与 `RESEARCH_INTENT` 的 `packet` 定义有口径差。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
C11, C12, C44 = 134.0e9, 110.0e9, 36.0e9


def C_cubic(c11, c12, c44):
    C = np.zeros((3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            C[i, i, j, j] = c12
    for i in range(3):
        C[i, i, i, i] = c11
    for i in range(3):
        for j in range(3):
            if i != j:
                C[i, j, i, j] += c44
                C[i, j, j, i] += c44
    return C


C = C_cubic(C11, C12, C44)
# Burgers OR：惯习面族 {011}_β 的 6 个独立法向（± 等价）
HABIT = np.array([[0., 1., 1.], [0., 1., -1.],
                  [1., 0., 1.], [1., 0., -1.],
                  [1., 1., 0.], [1., -1., 0.]])
HABIT /= np.linalg.norm(HABIT, axis=1, keepdims=True)
print("══ 引擎 npref vs 晶体学惯习面 {011}_β  ══\n")
print("  {011} 集合（6 个独立法向）:\n%s\n" % np.array2string(HABIT, precision=4))


def maxcos(v, refs):
    v = np.asarray(v, float).ravel()
    v = v / (np.linalg.norm(v) + 1e-300)
    return float(np.abs(refs @ v).max())


# ---- H1 正对照 ----
ok = all(abs(maxcos(h, HABIT) - 1.0) < 1e-12 for h in HABIT)
print("  H1 正对照：6 个 {011} 各自对集合的 max|cos| = %s  %s"
      % ([round(maxcos(h, HABIT), 6) for h in HABIT], "✅ PASS" if ok else "❌ FAIL"))
if not ok:
    print("  ❌ 比对器自身不可靠 ⇒ 不作主判定")
    sys.exit(1)

# ---- H2 主判定 ----
try:
    import windowB_surface as WS
    f = WS._argmin_normal
except Exception as e:
    print("  ⚠ 取 _argmin_normal 失败：%s ⇒ 无判定" % e)
    sys.exit(2)
mv = __import__("windowB_ti64_variants")
ALLV = np.asarray(mv.variants()[0], float)
print("\n  逐变体：_argmin_normal(C, ε⁰_k) 对 {011} 的 max|cos|")
vals = []
for k, e in enumerate(ALLV):
    n = np.asarray(f(C, e)[0], float).ravel()
    mc = maxcos(n, HABIT)
    vals.append(mc)
    if k < 12:
        print("     变体 %2d : n = (%+.4f,%+.4f,%+.4f)   max|cos|({011}) = %.4f"
              % (k + 1, n[0], n[1], n[2], mc))
vals = np.array(vals)
print("\n  ★ 12 个变体的 max|cos|({011})：min=%.4f  中位=%.4f  max=%.4f"
      % (vals.min(), np.median(vals), vals.max()))
thr = 0.99
n_hit = int((vals > thr).sum())
print("  ★ 判为「是 {011}」的变体数（阈值 max|cos| > %.2f）= **%d / 12**" % (thr, n_hit))
print()
if n_hit == 12:
    print("  ⇒ ✅ **一致**：能量最优法向恰是晶体学 `{011}_β` ⇒ `npref` 口径与 `RESEARCH_INTENT` 的")
    print("       `packet` 定义**不冲突**。")
elif n_hit >= 6:
    print("  ⇒ ⚠ **部分一致**（%d/12）⇒ 需逐变体核对，可能是简并/对称性导致的等价取向。" % n_hit)
else:
    print("  ⇒ ❌ **不一致**（仅 %d/12 落在 {011}）⇒ 引擎的 `npref` **不是**晶体学惯习面，"
          % n_hit)
    print("       而 `RESEARCH_INTENT` 定义 `packet` 用**晶体学**惯习面族 ⇒ **口径差成立**，")
    print("       ⇒ 「同一惯习面族的不同变体」这个 packet 判据**不能用 `npref` 直接实现**。")
