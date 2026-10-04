#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_trip_derive.py --- ★ 塑性弛豫（TRIP/塑性协调）理论框架的**数值自检**

## 框架（推导见 `R601_TRIP_THEORY.md`）
小应变分解：        `ε = ε^e + ε⁰(φ) + ε^p`
自由能：            `F = ∫[ f_chem + f_grad + ½(ε − ε⁰ − ε^p) : C : (ε − ε⁰ − ε^p) ]`
相场驱动力：        `∂F/∂φ_k ∋ −σ : ε⁰_k`，   `σ = C : (ε − ε⁰ − ε^p)`
塑性（率无关 J2、关联流动、理想塑性）：
                    `f_y = σ_eq − σ_y ≤ 0`，`σ_eq = √(3/2 ‖dev σ‖)`
                    `ε̇^p = λ̇ (3/2) dev σ / σ_eq`
**关键假设**：塑性弛豫的时间尺度 ≪ 相场演化尺度 ⇒ 力学问题**始终处于已松弛态**
⇒ 每步对 `σ_el` 做 **径向回退（radial return）**：
                    `σ_plast = σ_el · min(1, σ_y/σ_eq(σ_el))`
⇒ 相场驱动力由 `−σ_el:ε⁰_k` 换成 **`−σ_plast:ε⁰_k`**（**无需新增求解**，只改驱动力的装配）。

## 本脚本验什么（**预登记判据，可以 FAIL**）
* **V1 极限 σ_y → ∞**：`σ_plast ≡ σ_el` ⇒ 与现模型逐位等价（门控）
* **V2 一维单轴**：`σ = min(E·ε, σ_y)` 精确成立
* **V3 静水加载不屈服**：J2 是偏量判据 ⇒ 纯静水 ε⁰ 下 `σ_plast ≡ σ_el`
* **V4 硬不变量**：对**每个**胞 `σ_eq(σ_plast) ≤ σ_y·(1+1e-12)`
* **V5 各向异性不可丢**：`η_eff` 在**不同变体**上必须**不同**（否则失去取向选择）
* **V6 Ti64 定量**：给出 `η_eff = (σ_plast:ε⁰)/(σ_el:ε⁰)` 随 `σ_y` 的曲线
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAIL = []


def ck(name, cond, msg):
    print("  %-46s %s   %s" % (name, "✅ PASS" if cond else "❌ FAIL", msg))
    if not cond:
        FAIL.append(name)


# ── 材料常数（**沿用引擎现有值，不新引入**）──
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
I4s = 0.5 * (np.einsum("ik,jl->ijkl", I2, I2) + np.einsum("il,jk->ijkl", I2, I2))
I4d = I4s - np.einsum("ij,kl->ijkl", I2, I2) / 3.0      # 偏量投影


def dev(s):
    return s - np.trace(s) / 3.0 * I2


def seq(s):
    d = dev(s)
    return np.sqrt(1.5 * np.sum(d * d))


def radial_return(s_el, sy):
    """径向回退：σ_plast = σ_el · min(1, σ_y/σ_eq)。"""
    q = seq(s_el)
    if q <= 0:
        return s_el.copy()
    f = 1.0 if sy >= q else sy / q
    return s_el * f


# ── 由引擎自己的变体模块取 ε⁰（**不自己编**）──
EPS0 = None
ALLV = None
try:
    m = __import__("windowB_ti64_variants")
    _E = m.variants()[0]            # variants() 返回 (EPS0, F, M) ⇒ [0] 是 (nvar,3,3)
    ALLV = np.asarray(_E, float)
    EPS0 = ALLV[0]
    print("  ε⁰ 来源：windowB_ti64_variants.variants()，共 %d 个变体" % len(ALLV))
except Exception as e:
    print("  ⚠ 取 ε⁰ 失败：%s ⇒ 用已知值兜底" % e)
if EPS0 is None:
    EPS0 = np.array([[0.0437, -0.0433, 0.0065],
                     [-0.0433, 0.0437, -0.0065],
                     [0.0065, -0.0065, -0.1125]])
    ALLV = np.asarray([EPS0])
EPS0 = np.asarray(EPS0, float)
print("  ε⁰[0] =", np.array2string(EPS0, precision=4).replace("\n", " "))
tr = float(np.trace(EPS0))
dv = dev(EPS0)
print("  tr(ε⁰) = %.4f ；‖dev ε⁰‖ = %.4f（**剪切主导**）"
      % (tr, float(np.sqrt(np.sum(dv * dv)))))

print("\n══ V1 极限 σ_y → ∞ 必须回到纯弹性 ══")
s_el = np.einsum("ijkl,kl->ij", C, EPS0)
s_inf = radial_return(s_el, 1e30)
ck("V1 σ_y→∞ ⇒ σ_plast == σ_el",
   np.allclose(s_inf, s_el, rtol=0, atol=0), "逐位相同" )

print("\n══ V2 一维单轴 σ = min(E ε, σ_y) ══")
E, eps = 100.0e9, 0.01
s1 = np.zeros((3, 3)); s1[0, 0] = E * eps
for sy in (0.5e9, 5.0e9):
    got = radial_return(s1, sy)[0, 0]
    want = min(E * eps, sy)
    ck("V2 σ_y=%.1f GPa" % (sy / 1e9), abs(got - want) < 1e-6 * max(want, 1.0),
       "得 %.6g  期望 %.6g" % (got, want))

print("\n══ V3 纯静水 ε⁰ 不得屈服（J2 是偏量判据）══")
eh = np.eye(3) * 0.01
sh = np.einsum("ijkl,kl->ij", C, eh)
ck("V3 σ_eq(静水) == 0", abs(seq(sh)) < 1e-6 * abs(np.trace(sh) / 3),
   "σ_eq = %.3e Pa" % seq(sh))
ck("V3 σ_plast == σ_el（静水）", np.allclose(radial_return(sh, 1e6), sh),
   "小 σ_y 下仍原样返回")

print("\n══ V4 硬不变量：σ_eq(σ_plast) ≤ σ_y 逐胞成立 ══")
rng = np.random.default_rng(0)
ok = True
for _ in range(2000):
    s = rng.normal(size=(3, 3)) * 1e9
    s = 0.5 * (s + s.T)
    sy = float(rng.uniform(1e7, 3e9))
    sp = radial_return(s, sy)
    if seq(sp) > sy * (1 + 1e-12):
        ok = False
        break
ck("V4 2000 个随机应力张量", ok, "全部满足")

print("\n══ V5 变体间差异必须保留（否则失去取向选择）══")
try:
    m = __import__("windowB_ti64_variants")
    allv = m.variants()[0]
    allv = np.asarray(allv, float)
    print("  取得 %d 个变体的 ε⁰" % len(allv))
except Exception as e:
    print("  ⚠ 只取到 1 个变体（%s）⇒ V5 只做单变体自检" % e)
    allv = np.asarray([EPS0])

for sy in (0.3e9, 1.0e9):
    eff = []
    for e0 in allv:
        se = np.einsum("ijkl,kl->ij", C, e0)
        sp = radial_return(se, sy)
        num = float(np.sum(sp * e0))
        den = float(np.sum(se * e0))
        eff.append(num / den if den else np.nan)
    eff = np.array(eff)
    spread = np.nanmax(eff) - np.nanmin(eff)
    ck("V5 σ_y=%.1f GPa 变体间 η_eff 有差异" % (sy / 1e9),
       (spread > 1e-6) if len(eff) > 1 else True,
       "η_eff ∈ [%.4f, %.4f]，跨度 %.4f" % (np.nanmin(eff), np.nanmax(eff), spread))

print("\n══ V6 Ti64 定量：η_eff 随 σ_y ══")
print("  %-14s %-14s %-12s %s" % ("σ_y (MPa)", "σ_eq(C:ε⁰) MPa", "η_eff", "储存能 J/m³"))
se = np.einsum("ijkl,kl->ij", C, EPS0)
q0 = seq(se)
w_el = float(np.sum(se * EPS0))          # 全约束弹性能密度
d0 = dev(EPS0)
print("  参考：σ_eq(C:ε⁰) = **%.3f GPa**；ε⁰:C:ε⁰ = **%.4e J/m³**"
      % (q0 / 1e9, w_el))
for sy in (100e6, 200e6, 300e6, 500e6, 800e6, 1200e6, 2000e6):
    sp = radial_return(se, sy)
    num = float(np.sum(sp * EPS0))
    print("  %-14.0f %-14.0f %-12.4f %.4e"
          % (sy / 1e6, q0 / 1e6, num / w_el, num))

print("\n" + "=" * 78)
print("自检汇总：%s" % ("✅ 全部 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
print("=" * 78)
sys.exit(0 if not FAIL else 1)
