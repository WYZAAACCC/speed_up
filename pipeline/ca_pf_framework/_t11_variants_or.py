#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_variants_or.py —— 先验证「从 F 取取向」这个方法本身对不对（量具自检）。

背景：`windowB_ti64_variants.build_F` 返回的是**对应矩阵 F**（β 点阵 → α′ 点阵，
含贝恩畸变），不是纯旋转。上一版我用 `polar(F)` 的旋转部分当取向，得到变体间
取向差只有 5–10°，**没有**文献里的 60°/63.26° ⇒ 先怀疑量具。

本工具：
  A. 用 meta 里的 (n, d, e) 直接验证 **OR 的两个必要条件**（Burgers OR）：
       A1 `d` 是 {110}_β 面内的一条 <111>        （|d·n̂| ≈ 0，|d| = 1）
       A2 `F(d) ∥ d`（长度 = a_α）                ← 引擎自检 C6 的前半
       A3 `F(d) 与 F(e)` 夹角 = 60°
     ⇒ 若 A1–A3 全过，"F 确实是 Burgers 对应"就稳了，问题只在"怎么从 F 取取向"。
  B. 用**点阵向量对应**（而不是 polar）构造取向：
       在 β 系里取三个正交单位向量 (u1,u2,u3)；
       α′ 系里它们对应 (F u1, F u2, F u3)；
       把两边各自 Gram–Schmidt 正交归一 ⇒ R = [α′系] · [β系]^T
     这才是"取向"的标准取法（忽略畸变，只看转动）。
  C. 用 B 的取法重算取向差谱，并与 A 的结论对照。
"""
import itertools
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_ti64_variants as V  # noqa: E402

A_B, A_A, C_A = V.A_B, V.A_A, V.C_A
strains, F, meta = V.variants()
n = len(F)
print(f"n = {n}   a_b={A_B} a_a={A_A} c_a={C_A} nm")

# ---------------- A. OR 必要条件 ----------------
print("\n" + "=" * 90)
print("A. OR 必要条件（用 meta 的 n/d/e，直接验 F 是不是 Burgers 对应）")
print("=" * 90)
okA = []
for i in range(n):
    nv = np.asarray(meta[i]['n'], float)
    d = np.asarray(meta[i]['d'], float)
    e = np.asarray(meta[i]['e'], float)
    nv = nv / np.linalg.norm(nv)
    A1 = abs(d @ nv)                              # d 应在面内
    Fd = F[i] @ d
    A2a = np.linalg.norm(Fd)                      # 应为 a_α
    A2b = np.linalg.norm(Fd / np.linalg.norm(Fd) - d)   # F(d) ∥ d
    Fe = F[i] @ e
    cos = (Fd @ Fe) / (np.linalg.norm(Fd) * np.linalg.norm(Fe))
    A3 = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    okA.append((A1, A2a, A2b, A3))
    if i < 4 or i == n - 1:
        print(f"  V{i+1}: |d·n̂|={A1:.2e}  |F(d)|={A2a:.5f} nm (a_α={A_A})  "
              f"|F(d)/|F(d)|−d|={A2b:.2e}  ∠(F(d),F(e))={A3:.4f}°")
A1s = max(x[0] for x in okA)
A2as = [x[1] for x in okA]
A2bs = max(x[2] for x in okA)
A3s = [x[3] for x in okA]
print(f"\n  汇总: max|d·n̂|={A1s:.2e}（应≈0）  |F(d)| ∈ [{min(A2as):.5f},{max(A2as):.5f}]（应=a_α={A_A}）")
print(f"        max|F(d)方向偏差|={A2bs:.2e}（应≈0）  ∠(F(d),F(e)) ∈ [{min(A3s):.4f},{max(A3s):.4f}]°（应=60）")
print(f"  ⇒ {'PASS：F 确实是 Burgers 对应，量具问题在"取取向"这一步' if (A1s<1e-9 and A2bs<1e-9 and all(abs(a-60)<1e-6 for a in A3s)) else 'FAIL：F 本身与 Burgers 对应不符'}")

# ---------------- B. 用点阵向量对应构造取向 ----------------
def orientation(Fm, ref):
    """R: 把 β 系向量映到 α′ 系。ref = β 系里的 3 个正交单位向量（列）。"""
    img = Fm @ ref                      # α′ 系（未归一）
    # Gram–Schmidt
    def gs(M):
        Q = np.zeros_like(M)
        for k in range(3):
            v = M[:, k].copy()
            for j in range(k):
                v -= (Q[:, j] @ v) * Q[:, j]
            Q[:, k] = v / np.linalg.norm(v)
        return Q
    Qb, Qa = gs(ref), gs(img)
    return Qa @ Qb.T


ref = np.eye(3)
R = [orientation(f, ref) for f in F]
print("\n" + "=" * 90)
print("B. 用点阵向量对应构造的取向 ⇒ 重算取向差谱")
print("=" * 90)

# α(hcp) 点群 24 个操作
def hex_sym():
    ops = []
    c6 = np.array([[np.cos(np.pi / 3), -np.sin(np.pi / 3), 0],
                   [np.sin(np.pi / 3), np.cos(np.pi / 3), 0], [0, 0, 1.0]])
    two = np.diag([1.0, -1.0, -1.0])
    for k in range(6):
        Rk = np.linalg.matrix_power(c6, k)
        ops += [Rk, Rk @ two]
    return ops


SYM = hex_sym()
print(f"  α 点群操作数 = {len(SYM)}")


def mis(Ra, Rb):
    best = (999.0, None)
    for S in SYM:
        D = Ra.T @ Rb @ S
        ang = np.degrees(np.arccos(np.clip((np.trace(D) - 1) / 2, -1, 1)))
        if ang < best[0]:
            ax = np.array([D[2, 1] - D[1, 2], D[0, 2] - D[2, 0], D[1, 0] - D[0, 1]])
            nn = np.linalg.norm(ax)
            best = (ang, ax / nn if nn > 1e-12 else np.array([0, 0, 1.0]))
    return best


pairs = sorted((mis(R[i], R[j])[0], i + 1, j + 1) for i, j in itertools.combinations(range(n), 2))
import collections
hist = collections.Counter(round(p[0], 2) for p in pairs)
print("\n  角度直方图：")
for a, c in sorted(hist.items()):
    print(f"    {a:8.2f}°  ×{c}")
print("\n  检索文献两个特殊角（容差 0.6°）：")
for name, tgt in (("60.00° [11-20]α → V1+V4+V6", 60.0),
                  ("63.26° [10-553]α → V1+V9+V11", 63.26)):
    hits = [p for p in pairs if abs(p[0] - tgt) < 0.6]
    print(f"    {name}: 命中 {len(hits)} 对  {[(p[1],p[2],round(p[0],3)) for p in hits[:6]]}")

print("\n  关于「哪一组才是自协调三变体簇」的直接判据（不依赖文献标号）：")
print("    对每个三变体组合求 Σ dev(ε0_i) 的范数 ⇒ 最小者即自协调最好的一组")
best = []
for combo in itertools.combinations(range(n), 3):
    s = sum(np.eye(3) * 0 + (strains[k] - np.trace(strains[k]) / 3 * np.eye(3)) for k in combo)
    best.append((np.linalg.norm(s), tuple(k + 1 for k in combo)))
best.sort()
for v, c in best[:6]:
    print(f"    Σdev 范数 = {v:.6e}   组合 {c}")
print(f"    最差一组: {best[-1][0]:.6e}  组合 {best[-1][1]}")
print(f"    全 12 变体之和的范数 = {np.linalg.norm(sum(strains[k]-np.trace(strains[k])/3*np.eye(3) for k in range(n))):.6e}（C4 判据：应≈0）")
