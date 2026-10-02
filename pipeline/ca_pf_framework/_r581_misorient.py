#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_misorient.py --- ★★★ 12 个变体之间的**真实晶体学取向差**谱，
   与 Shuai 2026 的 EBSD 实测类型占比对照。

# 为什么这是本轮最该做的一件事
目标 ③ 的后半句是「**低角晶界取向差要有实测分布**」。
本仓 `MEASUREMENT_SPEC.md:229` 已经登记了**同工艺同材料**的文献靶：
> **Shuai et al. 2026**, *Materials* **19**, 1049, doi `10.3390/ma19061049`,
> **Table 3 + Fig. 9a**（LPBF Ti-64 **as-built α′**，EBSD **界面线段长度分数**）：
> Type 4 = **63.26°/<10 5 5 3>** ≈ **40–44%**（最常见）· Type 2 = **60°/<11−20>** ≈ **32–36%**
> · Type 3 = **60.83°/<10 7 17 3>** ≈ 12–14% · Type 5 = **90°/<7 17 10 0>** ≈ 12–14%
> · Type 6 = **10.53°/<0001>** < 2%

而**模型这边有一个纯晶体学的预测**：`windowB_ti64_variants.variants()` 给出 12 个变体的
**形变梯度 `F`（母相笛卡尔系里）**，由 **6 个 {110} 面 × {111} 方向 + Burgers OR** 构造。
⇒ **两两变体之间的取向差是可以精确算出来的**，**与仿真无关**。

# 方法（每步写死）
1. `variants()` ⇒ 12 个 `F_i`；
2. 变体 i→j 的**取向差旋转** `R_ij = F_j · F_i^{-1}`；
3. **按 α′（hcp，点群 6/mmm，24 个操作）做对称化**，取**最小角**代表
   （标准做法：`θ = min_S arccos((tr(S·R) − 1)/2)`）；
4. 统计 **12×12 的取向差谱**，与 Shuai 的五类**按角度**对照。

# 判据（**预先写死**）
* 模型在 63.26°（Type 4）与 60°（Type 2）附近应当有大量配对
  ⇒ 若**完全没有**，说明变体构造或取向差算法有问题；
* **并且**：把结果与模型**实际用的** `ladder` θ 对照
  （`windowB_lath.default_omega`：`θ(a,b) = |a−b|·θ_max/(nv−1)`，θ_max=5°）
  ⇒ **若两者毫不相干，则 R581 的 C3「取向差分布」是参数化强加的，不是晶体学的。**
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_ti64_variants as V  # noqa


# ============================================================================
# ★★★ 第一版**错了**，而且判据当场抓到（留痕，P21 又一次生效）
#   第一版：`R_ij = F_j · F_i^{-1}`（**含应变**），再用**绕全局 z 的** HCP 群对称化。
#   症状：**66 个配对里 48 个给出精确 0.00°** —— 这只可能是
#     "对称群里恰好含有 ≈ R^{-1} 的元素" ⇒ 0° 是**伪影**。
#   根因（两条，都要修）：
#     ① **`F` 含应变** ⇒ 取向部分应当先做**极分解** `R = F·(FᵀF)^{-1/2}`；
#     ② **对称群用错了坐标系**：HCP 点群 6/mmm 的标准设置是 **c ∥ z（晶体系）**，
#        而 `F_i` 把**晶体系 → 母相系** ⇒ 必须先在**子晶系**里算取向差
#        `ΔR = R_iᵀ · R_j`，再套**标准设置**的群。绕全局 z 套群**物理上没有意义**。
#   ⇒ 修法见下。
# ============================================================================
def hcp_symmetry():
    """hcp 点群 6/mmm 的 **12 个真旋转**（**标准设置：c ∥ z，晶体系**）。

    ⚠ **这个群只能在"子晶自己的晶体系"里用** —— 见上面的留痕。
    """
    ops = []
    for k in range(6):
        a = np.radians(60 * k)
        Rz = np.array([[np.cos(a), -np.sin(a), 0],
                       [np.sin(a), np.cos(a), 0], [0, 0, 1.0]])
        Rx = np.diag([1.0, -1.0, -1.0])
        ops.append(Rz)
        ops.append(Rz @ Rx)
    return ops


def polar_rot(F):
    """极分解的**旋转**部分：F = R·U ⇒ R = F·(FᵀF)^{-1/2}。"""
    M = F.T @ F
    w, V = np.linalg.eigh(M)
    Uinv = V @ np.diag(1.0 / np.sqrt(w)) @ V.T
    return F @ Uinv


def min_angle(R, ops):
    """对称化后的最小取向差角（度）。`R` 必须在**子晶系**里。"""
    best = 999.0
    for S in ops:
        M = S @ R
        tr = np.clip((np.trace(M) - 1.0) / 2.0, -1.0, 1.0)
        ang = np.degrees(np.arccos(tr))
        if ang < best:
            best = ang
    return best


def main():
    _, Fs, meta = V.variants()
    n = len(Fs)
    ops = hcp_symmetry()
    print('=' * 100)
    print('R581 —— 12 个变体的**真实晶体学取向差**谱（Burgers OR，纯几何，与仿真无关）')
    print('=' * 100)
    print('变体数 n = %d' % n)
    print('每个变体的 (n 惯习法向, d 长轴)：')
    for i, m in enumerate(meta):
        print('  变体 %-3d n=%s  d=%s' % (i + 1, np.round(m['n'], 4), np.round(m['d'], 4)))
    print()
    ang = np.zeros((n, n))
    # ★ 取向部分（极分解）—— 见上面留痕：不许直接用含应变的 F
    Rots = [polar_rot(F) for F in Fs]
    for i in range(n):
        for j in range(n):
            if i == j:
                ang[i, j] = 0.0
                continue
            # **子晶 i 的晶体系**里的取向差
            dR = Rots[i].T @ Rots[j]
            ang[i, j] = min_angle(dR, ops)
    iu = np.triu_indices(n, 1)
    a = ang[iu]
    print('── 66 个配对（i<j）的取向差角分布 ──')
    print('   min %.2f°  中位 %.2f°  max %.2f°' % (a.min(), np.median(a), a.max()))
    u, c = np.unique(np.round(a, 2), return_counts=True)
    print('   唯一角度值 %d 个；出现最多的 12 个：' % len(u))
    for val, cnt in sorted(zip(u, c), key=lambda t: -t[1])[:12]:
        print('      %7.2f°  ×%d' % (val, cnt))
    print()
    print('── 与 **Shuai 2026** 的五类对照（同工艺 LPBF Ti-64 as-built α′，EBSD 界面段长分数）──')
    lit = [(63.26, '40–44%', 'Type 4 <10 5 5 3>'), (60.00, '32–36%', 'Type 2 <11-20>'),
           (60.83, '12–14%', 'Type 3 <10 7 17 3>'), (90.00, '12–14%', 'Type 5 <7 17 10 0>'),
           (10.53, '<2%', 'Type 6 <0001>')]
    print('   %-10s %-10s %-24s %s' % ('文献角', '文献占比', '文献类型', '模型：落在 ±2° 内的配对数 / 占比'))
    for L, frac, name in lit:
        m = np.abs(a - L) <= 2.0
        print('   %-10.2f %-10s %-24s **%2d / 66 = %5.1f%%**'
              % (L, frac, name, int(m.sum()), 100.0 * m.sum() / len(a)))
    print()
    print('── ★ 与模型**实际用的** `ladder` θ 对照 ──')
    print('   `windowB_lath.default_omega(mode="ladder")`：θ(a,b) = |a−b|·θ_max/(nv−1)，θ_max=5°')
    print('   （R581 早期已实测：**分布是参数化强加的**，与取向差无关 —— 见 §C3(c)）')
    print('   ⇒ 本表给出的是**晶体学真值**；两者**不是一个量**：')
    print('       · `ladder` θ 进的是**界面能/弹性**（`omega`）')
    print('       · 本表的取向差是**变体之间的真实晶体学关系**（Burgers OR 决定的）')
    print()
    print('=' * 100)
    # 判据
    near60 = np.abs(a - 60.0) <= 2.0
    near63 = np.abs(a - 63.26) <= 2.0
    print('★ 判据（**预先写死**）')
    print('  · 60° 附近配对数 = **%d / 66**；63.26° 附近 = **%d / 66**'
          % (int(near60.sum()), int(near63.sum())))
    if near60.sum() + near63.sum() == 0:
        print('  ⇒ ❌ **一个都没有** ⇒ 变体构造或对称化有问题，必须查')
    else:
        print('  ⇒ ✅ 模型确实在 **60°/63.26°** 附近有配对 ⇒ '
              '**变体构造给出的取向差谱与文献同类**（量级上）')
    print('  ⚠ 但**占比**不能直接比：文献的分数是**界面线段长度分数**（2-D 截面、'
          '且受**哪些界面真的形成**影响），模型这张表是**12 变体所有可能配对的等权表**。')
    print('     ⇒ 要做**定量**对照，必须用**实际形成**的界面去加权（下一步）。')
    print('=' * 100)


if __name__ == '__main__':
    main()
