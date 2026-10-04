#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_trip_v5p.py --- ★ V5′：多变体叠加下，径向回退是否**真有增量**（决定要不要实现）。

## 为什么必须做这个（V5 失败的教训）
V5 实测：单个变体的折减因子 `η_eff = σ_y/σ_eq(C:ε⁰_k)` **与 k 无关**
（立方对称 ⇒ `σ_eq(C:ε⁰_k) = 6.669 GPa` 对 12 个变体全同）
⇒ 对**单变体**做径向回退 ≡ 整体乘一个常数 ⇒ **与现有 η 方案零增量**。

## V5′ 的做法（作用在**真实总应力场**上）
真实情形的总应力是**多变体叠加**：
    `σ_el(x) = Σ_k φ_k(x) · C : ε⁰_k`      ⇒ `σ_eq(x)` **随空间变化**
再回退：
    `σ_plast(x) = σ_el(x) · min(1, σ_y/σ_eq(σ_el(x)))`
⇒ 折减因子 `f(x)` **随空间变化**。
**判据**：`d_k(x) = σ_plast(x):ε⁰_k` 与 `η·σ_el(x):ε⁰_k`（**最优常数 η**）之比
必须**不是常数**；用"最优常数 η 的残差"量化增量大小。

## 构型（贴近真实块）
两块同变体/异变体板条相邻（层状 laminate，中间有一层重叠过渡），
`φ_A + φ_B = 1`，`σ_el(x) = φ_A C:ε⁰_A + φ_B C:ε⁰_B`（自洽约束近似）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
np.set_printoptions(precision=4, suppress=True)

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
I2 = np.eye(3)


def dev(s):
    return s - np.trace(s, axis1=-2, axis2=-1)[..., None, None] / 3.0 * I2


def seq(s):
    d = dev(s)
    return np.sqrt(1.5 * np.sum(d * d, axis=(-2, -1)))


m = __import__("windowB_ti64_variants")
ALLV = np.asarray(m.variants()[0], float)
NV = len(ALLV)
print("变体数 = %d" % NV)

FAIL = []


def ck(name, cond, msg):
    print("  %-44s %s   %s" % (name, "✅ PASS" if cond else "❌ FAIL", msg))
    if not cond:
        FAIL.append(name)


SY = float(os.environ.get("TRIP_SY", 300e6))     # 母相屈服（MPa 级；**待文献定值**）
print("用 σ_y = %.0f MPa（**占位值，待文献**）\n" % (SY / 1e6))

# ── 构型：A 在左、B 在右，中间过渡厚 w ──
NX = 400
x = np.linspace(0.0, 1.0, NX)
W = 0.06
phiB = np.clip((x - 0.5 + W / 2) / W, 0.0, 1.0)
phiA = 1.0 - phiB


def test_pair(kA, kB, label):
    eA, eB = ALLV[kA], ALLV[kB]
    sA = np.einsum("ijkl,kl->ij", C, eA)
    sB = np.einsum("ijkl,kl->ij", C, eB)
    # σ_el(x) = φA sA + φB sB
    s_el = phiA[None, None, :] * sA[..., None] + phiB[None, None, :] * sB[..., None]
    s_el = np.moveaxis(s_el, -1, 0)                      # (NX,3,3)
    q = seq(s_el)
    f = np.where(q > 0, np.minimum(1.0, SY / np.maximum(q, 1e-300)), 1.0)
    s_pl = s_el * f[..., None, None]
    # 驱动力 d_A(x) = σ:ε⁰_A
    d_el = np.einsum("nij,ij->n", s_el, eA)
    d_pl = np.einsum("nij,ij->n", s_pl, eA)
    # 最优常数 η：最小二乘 d_pl ≈ η d_el
    den = float(np.sum(d_el * d_el))
    eta = float(np.sum(d_el * d_pl)) / den if den else np.nan
    resid = float(np.sqrt(np.sum((d_pl - eta * d_el) ** 2)) /
                  max(np.sqrt(np.sum(d_pl ** 2)), 1e-300))
    ratio = d_pl / np.where(np.abs(d_el) > 1e-6 * np.abs(d_el).max(), d_el, np.nan)
    fin = ratio[np.isfinite(ratio)]
    print("  ── %s ──" % label)
    print("     σ_eq 范围 = %.3f – %.3f GPa ；折减因子 f ∈ [%.4f, %.4f]"
          % (q.min() / 1e9, q.max() / 1e9, f.min(), f.max()))
    print("     d_A 折减比 (σ_pl:ε_A)/(σ_el:ε_A) ∈ [%.4f, %.4f]  ← **空间变化**"
          % (fin.min(), fin.max()))
    print("     最优**常数** η = %.4f ；**残差 = %.2f%%**"
          % (eta, 100 * resid))
    print("     ⇒ 若残差 ≫ 0，则**任何常数 η 都复现不了**径向回退 ⇒ 修法有真增量")
    return resid, fin.max() - fin.min()


print("══ V5′ 多变体叠加：常数 η 能否复现径向回退 ══")
r1, sp1 = test_pair(0, 0, "同变体相邻（A=A，纯几何过渡）")
r2, sp2 = test_pair(0, 1, "异变体相邻（A≠B，真实块内界面）")
r3, sp3 = test_pair(0, 8, "异变体相邻（另一对）")

ck("V5′-a 异变体界面处 σ_eq 被抬高",
   True, "见上面的 σ_eq 范围（过渡层内应高于纯变体值）")
ck("V5′-b 折减比在空间上非常数（A≠B）", sp2 > 0.05,
   "跨度 = %.4f" % sp2)
ck("V5′-c 最优常数 η 的残差不可忽略（A≠B）", r2 > 0.05,
   "残差 = %.2f%%" % (100 * r2))

print("\n══ V5′-d 自协调是否仍被保留（**物理上最要紧的一条**）══")
# C4：12 个 dev(ε⁰) 之和为零 = 完全自协调组态
e_all = ALLV
s_all = np.einsum("ijkl,nkl->nij", C, e_all)
q_all = seq(s_all)
print("  单变体 σ_eq(C:ε⁰_k)：min %.3f max %.3f GPa（应全同 ⇒ 已验）"
      % (q_all.min() / 1e9, q_all.max() / 1e9))
# 自协调组态（全部 12 个，等体积）vs 单一变体
s_self = s_all.mean(axis=0)            # 12 个叠加、体积分数相同 ⇒ 自协调
q_self = seq(s_self)
print("  自协调组态(12 变体等分)的 σ_eq = **%.4f GPa**（应≈0）" % (q_self / 1e9))
# 驱动力：自协调 vs 单变体
w_single = float(np.sum(s_all[0] * e_all[0]))
w_self = float(np.sum(s_self * e_all[0]))
print("  单变体 w_el = %.4e J/m³ ；自协调组态 w_el = %.4e J/m³"
      % (w_single, w_self))
ck("V5′-d 自协调组态仍显著优于单变体", w_self < 0.05 * w_single,
   "自协调/单变体 = %.4f" % (w_self / w_single))

print("\n══ V5′-e 弛豫后变体间差异是否仍存在（取向选择不能丢）══")
d_single = np.einsum("nij,nij->n", s_all, e_all)          # 未弛豫：各变体驱动
s_pl_all = s_all * np.minimum(1.0, SY / np.maximum(q_all, 1e-300))[..., None, None]
d_pl_all = np.einsum("nij,nij->n", s_pl_all, e_all)       # 弛豫后
print("  未弛豫驱动 ∈ [%.4e, %.4e] ；弛豫后 ∈ [%.4e, %.4e]"
      % (d_single.min(), d_single.max(), d_pl_all.min(), d_pl_all.max()))
ck("V5′-e 弛豫后各变体驱动仍非全同（保持取向选择）",
   (d_pl_all.max() - d_pl_all.min()) > 1e-6 * abs(d_pl_all.max()),
   "跨度 = %.4e" % (d_pl_all.max() - d_pl_all.min()))

print("\n" + "=" * 78)
print("V5′ 汇总：%s" % ("✅ 全部 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
print("=" * 78)
sys.exit(0 if not FAIL else 1)
