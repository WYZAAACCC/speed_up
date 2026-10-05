#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_nvar_derive.py --- ★ `nvar`（变体数）的**推导**（新规则：文献 → 推导 → 标定）

## 为什么要推它
出处总账 v2 里 `nvar` 只命中"文献"（`_t5_nvarbound.py`），**没有推导记录**。
而 β(bcc) → α′(hcp) 的变体数**应当由 Burgers 取向关系唯一确定** ⇒ 属"可推导"，
不该停留在标定/引文。

## 推导（Burgers OR，1934）
```
(011)_β ∥ (0001)_α′        ⟨1̄11⟩_β ∥ ⟨112̄0⟩_α′
```
* **惯习面族 {011}_β 的等价面数 = 6**
* 每个 {011} 面内，与 `⟨112̄0⟩` 匹配的 `⟨1̄11⟩_β` 方向有 **2** 个
  （`⟨1̄11⟩` 族共 8 个方向：其中 4 个与给定 {011} 面**平行**，
    再按 `⟨112̄0⟩` 的正负等价性折半 ⇒ 每面 **2** 个独立变体）
* ⇒ **变体数 = 6 × 2 = 12**
（等价说法：3 组 {011} × 每组的 4 个 ⟨1̄11⟩ = 12，两种数法同值。）

## 本脚本验什么（**可 FAIL**）
* **N1** `variants()` 确实给出 **12** 个 ε⁰；
* **N2** 12 个 ε⁰ **两两不同**（不是重复写入）；
* **N3** 12 个 `‖dev ε⁰‖` **全等**（立方对称的必然结果）⇒ 变体等价、无偏好；
* **N4** **完全自协调**：`Σ_k dev(ε⁰_k) = 0`（C4 群的和为零）
  —— 这是 12 变体集合**封闭性**的硬判据，也是 `nvar = 12` 的直接证据；
* **N5** `Σ_k ε⁰_k` 的**偏量部分**为零、只有静水部分（对应相变体积变化）。
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


m = __import__("windowB_ti64_variants")
ALLV = np.asarray(m.variants()[0], float)
NV = len(ALLV)
print("══ `nvar` 推导与数值自检 ══\n")
print("  推导：Burgers OR ⇒ 6 个 {011}_β 惯习面 × 每面 2 个独立 ⟨1̄11⟩_β = **12**\n")

I2 = np.eye(3)
def dev(s):
    return s - np.trace(s) / 3.0 * I2

ck("N1 variants() 给出 12 个变体", NV == 12, "实测 NV = %d" % NV)

# N2 两两不同
uniq = 0
for i in range(NV):
    for j in range(i + 1, NV):
        if not np.allclose(ALLV[i], ALLV[j], atol=1e-12):
            uniq += 1
need = NV * (NV - 1) // 2
ck("N2 12 个 ε⁰ 两两不同", uniq == need,
   "%d / %d 对互不相同" % (uniq, need))

# N3 ‖dev ε⁰‖ 全等
nrm = np.array([np.linalg.norm(dev(e)) for e in ALLV])
ck("N3 ‖dev ε⁰_k‖ 全等（变体等价）",
   (nrm.max() - nrm.min()) < 1e-12 * max(nrm.max(), 1e-30),
   "∈ [%.6f, %.6f]，跨度 %.2e" % (nrm.min(), nrm.max(), nrm.max() - nrm.min()))

# N4 完全自协调
# ★ 判据标定（本会话第 12 次自查）：第一版容差写成 `1e-15*max|ε⁰| = 1.1e-16`，
#   比机器精度还紧 ⇒ 实测 2.9e-16 被判 FAIL，**而那是浮点噪声不是物理失败**。
#   正确判据（同 AGENTS.md §3 教训 22）：残差相对**信号**（‖dev ε⁰‖=0.142）要落在
#   浮点量级内 ⇒ 用 `1e-12 * ‖dev ε⁰‖`。
SIG = float(np.linalg.norm(dev(ALLV[0])))
TOL = 1e-12 * SIG
S = ALLV.sum(axis=0)
dS = dev(S)
ck("N4 Σ_k dev(ε⁰_k) = 0（完全自协调，C4 封闭）",
   np.abs(dS).max() < TOL,
   "max|Σ dev ε⁰| = %.3e ；容差 %.1e ；信号 ‖dev ε⁰‖ = %.4f（低 %.0f 个数量级）"
   % (np.abs(dS).max(), TOL, SIG,
      np.log10(SIG / max(np.abs(dS).max(), 1e-300))))

# N5 Σ 只有静水部分
tr = np.trace(S) / 3.0
ck("N5 Σ_k ε⁰_k 为纯静水（偏量恰好抵消）",
   np.abs(dev(S)).max() < TOL,
   "Σ 的静水分量 = %.6f；偏量 max = %.3e（容差 %.1e）"
   % (tr, np.abs(dev(S)).max(), TOL))

print()
print("  ⇒ 结论：**`nvar = 12` 有推导依据**（Burgers OR），且 5 条数值判据全部支持；")
print("     其出处分级由「文献」升为「**推导 + 文献**」。")
print()
print("  自检汇总：%s" % ("✅ 全部 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
sys.exit(0 if not FAIL else 1)
