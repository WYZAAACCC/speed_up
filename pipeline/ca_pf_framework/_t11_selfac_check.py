#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_selfac_check.py —— 把「自协调变体组合」变成可 FAIL 的判据。

文献依据（用户指定的那篇，本次已抽全文）：
  * Wang et al.（经该文转述，第 1019-1030 行）：把 β→α 当马氏体处理，算出 12 个变体的形状应变，
    以及**三变体簇**的平均形状应变 ⇒ **自协调程度最高的是**：
        · `60°/[11̄20]α`  型 —— 代表组合 **V1+V4+V6**
        · `63.26°/[10̄553]α` 型 —— 代表组合 **V1+V9+V11**
    并指出这两种取向差在 OIM 里的**出现频率远高于随机**（纯 Ti 与 Ti 合金都如此）。
  * 该文自己的相场模拟也复现了同一结论（"the most favored misorientation occurs among
    α plates of variants V1, V4 and V6, followed by V1, V9 and V11"）。

本工具做：
  Q1 由 `windowB_ti64_variants.variants()` 的 12 个 F 算出**变体间取向差角/轴**；
  Q2 检验 `60°` 与 `63.26°`（含等价角/轴，六角对称）是否出现，以及**出现次数**；
  Q3 **正对照**：随机取向（或立方对称操作）应**不**给出这两个特殊角；
  Q4 若成立 ⇒ 给出"块内变体应取哪几组"的判据，用于 ⑧ 的监控项。
"""
import itertools
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_ti64_variants as V  # noqa: E402

strains, F, meta = V.variants()
n = len(F)
print(f"变体数 n = {n}   （应 12）")
for i, f in enumerate(F):
    print(f"  F[{i+1}] det={np.linalg.det(f):.6f}   eps_diag={np.round(np.diag(strains[i]),4)}")
print(f"\n  迹 ε00（引擎的 eps0）：{np.round([float(np.trace(s)) for s in strains],4)}")
print(f"  引擎 |ε| 各向异性（主轴跨度）：{np.round([float(s.max()-s.min()) for s in strains],4)}")

# ---- 由 F 取取向（极分解去掉拉伸，只留旋转）----
def rot_of(Fm):
    U, s, Vt = np.linalg.svd(Fm)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


R = [rot_of(f) for f in F]

# ---- hcp α 的点群对称操作（24 个，c/a 任意都用同一组）----
def hex_sym():
    ops = []
    c6 = np.array([[np.cos(np.pi / 3), -np.sin(np.pi / 3), 0],
                   [np.sin(np.pi / 3), np.cos(np.pi / 3), 0], [0, 0, 1.0]])
    mz = np.diag([1.0, 1.0, -1.0])
    # 六次轴 + 垂直二次轴
    two = np.diag([1.0, -1.0, -1.0])
    for k in range(6):
        Rk = np.linalg.matrix_power(c6, k)
        ops.append(Rk)
        ops.append(Rk @ two)
    return ops


SYM = hex_sym()
print(f"α 相点群操作数（应 24）= {len(SYM)}")


def misorient(Ra, Rb):
    """返回最小取向差角（度）与轴（在 α 参考系里）。"""
    best = (999.0, None)
    for S in SYM:
        D = Ra.T @ Rb @ S
        ang = np.degrees(np.arccos(np.clip((np.trace(D) - 1) / 2, -1, 1)))
        if ang < best[0]:
            axis = np.array([D[2, 1] - D[1, 2], D[0, 2] - D[2, 0], D[1, 0] - D[0, 1]])
            nrm = np.linalg.norm(axis)
            best = (ang, axis / nrm if nrm > 1e-12 else np.array([0, 0, 1.0]))
    return best


print("\n" + "=" * 90)
print("Q1/Q2 变体间最小取向差（度）与轴")
print("=" * 90)
pairs = []
for i, j in itertools.combinations(range(n), 2):
    ang, ax = misorient(R[i], R[j])
    pairs.append((ang, i + 1, j + 1, ax))

pairs.sort()
import collections
hist = collections.Counter(round(p[0], 2) for p in pairs)
print("\n角度直方图（四舍五入到 0.01°）：")
for a, c in sorted(hist.items()):
    print(f"  {a:8.2f}°  ×{c}")

print("\n=== 检索文献指定的两个特殊角 ===")
targets = {"60°/[11-20]α (V1+V4+V6)": 60.0, "63.26°/[10-553]α (V1+V9+V11)": 63.26}
for name, tgt in targets.items():
    hits = [p for p in pairs if abs(p[0] - tgt) < 0.6]
    print(f"\n  {name}: 命中 {len(hits)} 对（容差 0.6°）")
    for ang, i, j, ax in hits[:8]:
        print(f"     V{i}-V{j}  Δθ={ang:.3f}°  轴={np.round(ax,4)}")

print("\n=== 参考：本项目变体在该容差内的**全部**角 ===")
for t in (60.0, 63.26, 10.53, 70.53):
    hits = [p for p in pairs if abs(p[0] - t) < 0.6]
    print(f"  {t:6.2f}° -> {len(hits):3d} 对")

print("\n" + "=" * 90)
print("Q3 正对照：把 F 换成与 α 无关的立方对称旋转 ⇒ 不应出现这些特殊角")
print("=" * 90)
cub = []
for perm in itertools.permutations(range(3)):
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                M = np.zeros((3, 3))
                for a, b in enumerate(perm):
                    M[a, b] = 1.0
                M = M @ np.diag([sx, sy, sz])
                if np.linalg.det(M) > 0:
                    cub.append(M)
print(f"  立方旋转操作数（应 24）= {len(cub)}")
cnt = {t: 0 for t in (60.0, 63.26)}
for i, j in itertools.combinations(range(len(cub)), 2):
    ang, _ = misorient(cub[i], cub[j])
    for t in cnt:
        if abs(ang - t) < 0.6:
            cnt[t] += 1
print(f"  正对照里 60.00° 命中 {cnt[60.0]} 对、63.26° 命中 {cnt[63.26]} 对")
print(f"  ⇒ {'PASS：特殊角不是随机出现的（量具有分辨力）' if sum(cnt.values())==0 else 'FAIL：正对照也命中 ⇒ 判据无分辨力'}")
