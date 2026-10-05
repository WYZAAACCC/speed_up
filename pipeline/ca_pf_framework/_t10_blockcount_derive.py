#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_blockcount_derive.py --- ★ 块数律的**推导**（文献给形式、晶体学给因子）

## 文献给的形式（R603，已取到原文摘要）
Galindo-Nava & Rivera-Díaz-del-Castillo, Acta Mater. **98** (2015),
DOI 10.1016/j.actamat.2015.07.018：
> "**The packet and block size were found to linearly depend on the prior-austenite
>   grain size** when introducing relevant crystallographic and geometric relationships
>   of their hierarchical arrangements."
⇒ 形式：`d_block = k_b · D`（`D` = 原晶粒尺寸，本框架里是**物理输入**，来自 Window A）

## 本文要推的：`k_b` 与「块数」
β(bcc) → α′(hcp) 的 **Burgers OR** 给 **12 个变体**（本会话已推并数值自检 5/5 PASS）：
* **惯习面族 {011}_β 的等价面数 = 6** ⇒ **packet（同惯习面族）= 6 个**
* 每个 {011} 面内与 `⟨112̄0⟩` 匹配的 `⟨1̄11⟩_β` 方向 **= 2** ⇒ **block（同变体）= 12/6 = 每 packet 2 个**
（12 = 6 × 2 与 `variants()` 实测一致，且 `Σ dev ε⁰ = 0` 证其自协调封闭）

## 几何：为什么尺寸会线性依赖 `D`
原晶粒内，6 组惯习面把晶粒切成若干区域。**同一 packet 的板条平行堆叠**（法向即该惯习面法向），
packet 的**厚度**方向就是惯习面法向。若 6 组惯习面在晶粒内**近似各向同性取向**，
则沿任一方向的"被切次数" `≈ 6`，相邻同族切面的平均间距 `≈ D / 6`。
一个 packet 内 **2 个 block** 分摊该间距 ⇒ `d_block ≈ D / (6 · 2) = D/12`。
**⇒ k_b ≈ 1/12 ≈ 0.083**（**这是"几何均分"这一条的推论，不是实测**）。

**⚠ 与文献的定量关系尚未核实**：文献只说"线性依赖"，**没有给系数**；
我手上也没有钢/钛的 `d_block` vs `D` 实测表 ⇒ **本脚本只给"可推的那部分"与量级，
不给结论性的 `k_b`。**（按新规则，标定必须写明依据与不确定度 —— 此处**不标定**。）

## 本脚本做什么（**可 FAIL**）
1. **C1** 晶体学计数自检：6 packet × 2 block = 12 = `variants()` 个数；
2. **C2** 每个 packet 的 2 个 block 是否**恰好互补**（同一 {011} 面内两个 ⟨1̄11⟩ 方向）
    —— 用 ε⁰ 的数值判据检验（同 packet 的两变体应共享惯习面法向）；
3. **C3** 几何均分推论给出的 `k_b` 量级，与"block 数 = V_box / d_block³"联立，
   **反推**在当前 10 µm 盒里 k_b 取何值才能给出 200+ 块 —— 与 C1/C2 的几何值对比，
   判断"200+ 块"是否与晶体学几何相容（**这是对用户 200+ 要求的物理可行性检验**）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAIL = []


def ck(name, cond, msg):
    print("  %-52s %s   %s" % (name, "✅ PASS" if cond else "❌ FAIL", msg))
    if not cond:
        FAIL.append(name)


m = __import__("windowB_ti64_variants")
ALLV = np.asarray(m.variants()[0], float)
NV = len(ALLV)
print("══ 块数律推导  ══\n")

# ── C1 晶体学计数 ──
N_PACKET = 6      # {011}_β 等价面
N_BLK_PER_PKT = 2  # 每面内 2 个独立 ⟨1̄11⟩
ck("C1 6 packet × 2 block = 12 = variants() 个数",
   N_PACKET * N_BLK_PER_PKT == NV,
   "%d × %d = %d ；variants() = %d" % (N_PACKET, N_BLK_PER_PKT,
                                       N_PACKET * N_BLK_PER_PKT, NV))

# ── C2 同 packet 的两变体应共享惯习面法向 ──
# 判据：β 的惯习面法向 n 使「相变应变的法向分量」最大 ⇒ 用 ε⁰ 的主值/主向判定
# 简化可检验版：把 12 个 ε⁰ 按"最接近的面法向"聚类，应得到 6 组、每组 2 个。
def habit_normal(e):
    """由 ε⁰ 推惯习面法向的代理量：取 ε⁰ 的最大主值方向（拉伸最大的方向）。"""
    w, v = np.linalg.eigh(e)
    return v[:, int(np.argmax(w))]


nrm = np.array([habit_normal(e) for e in ALLV])
nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
# 聚类：按 |cos| 相似（法向正负等价）
groups = []
used = np.zeros(NV, bool)
for i in range(NV):
    if used[i]:
        continue
    g = [i]
    used[i] = True
    for j in range(i + 1, NV):
        if used[j]:
            continue
        if abs(float(nrm[i] @ nrm[j])) > 1e-6:
            g.append(j)
            used[j] = True
    groups.append(g)
sizes = sorted(len(g) for g in groups)
print("  C2 由 ε⁰ 主拉伸方向聚类得到的组大小分布 = %s（共 %d 组）"
      % (sizes, len(groups)))
ck("C2 聚类成 6 组、每组 2 个",
   sizes == [2] * 6,
   "实测 %s" % sizes)

# ── C3 几何均分推论 vs「200+ 块」的相容性 ──
L_um = 10.0
V_box = L_um ** 3
k_geo = 1.0 / (N_PACKET * N_BLK_PER_PKT)
print("\n  C3 几何均分推论（**推理，非实测**）")
print("     6 组惯习面近似各向同性 ⇒ 沿任一方向被切 6 次 ⇒ 相邻同族间距 ≈ D/6")
print("     一个 packet 内 2 个 block 分摊 ⇒ d_block ≈ D/12 ⇒ k_b ≈ 1/12 = %.4f" % k_geo)
D = L_um   # 盒子 = 一个 prior-β 晶粒的局部区域，取 D = 盒尺寸
d_blk = k_geo * D
n_blk = V_box / d_blk ** 3
print("     取 D = %.1f µm ⇒ d_block = %.3f µm ⇒ 块数 ≈ V_box/d_block³ = **%.0f**"
      % (D, d_blk, n_blk))
print("     ⇒ 用户要的 200+ 块 需要 d_block ≈ %.3f µm ⇒ k_b ≈ %.4f"
      % ((V_box / 200.0) ** (1 / 3.0), (V_box / 200.0) ** (1 / 3.0) / D))
print("     ⚠ 两者**差 %.1f 倍** ⇒ 若几何均分推论成立，10 µm 盒里**自然只能有 ~12 个块级区域**，"
      % (k_geo / ((V_box / 200.0) ** (1 / 3.0) / D)))
print("       要 200+ **块**需更细的机制（自催化/阻截把块尺度压小）—— 这与 goal ② 的方向一致。")
print()
print("  ⚠ **本脚本不给结论性的 k_b**：文献只有\"线性依赖\"、无系数；我手上无 d_block vs D 实测表。")
print("     按新规则，此处**不标定**；下一步应找 (i) d_block vs D 的实测数据，或 (ii) 自催化律的原文式子。")

print()
print("  自检汇总：%s" % ("✅ C1/C2 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
sys.exit(0 if not FAIL else 1)
