#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_burgers_spec.py —— 用**显式晶体学构造** Burgers OR 的 12 变体取向差谱。

判定目标：引擎的 12 变体取向差谱里没有 60°/63.26°，是**量具问题**还是**真问题**。

修正（上一版两处 bug，已记账）：
  * hcp 点群只生成了 12 个操作（生成元重复）⇒ 现用 3 个生成元闭包并**按矩阵去重**得 24 个；
  * {110} 面内 <111> 的筛选条件写错 ⇒ 现用"面内 8 个 <111> 中与法向正交者"。
"""
import itertools
from collections import Counter

import numpy as np


def norm(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot(axis, deg):
    a = norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    t = np.radians(deg)
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)


# ---- hcp α 点群 24 个操作（3 生成元闭包 + 去重）----
def hex_sym():
    gens = [rot([0, 0, 1], 60),            # 6 次轴
            rot([1, 0, 0], 180),           # ⊥c 的 2 次轴
            rot([1, 0, 0], 180) @ rot([0, 0, 1], 30)]   # 另一族 2 次轴
    ops = [np.eye(3)]
    changed = True
    while changed:
        changed = False
        for g in gens:
            for o in list(ops):
                for nw in (g @ o, o @ g):
                    if not any(np.abs(nw - x).max() < 1e-9 for x in ops):
                        ops.append(nw)
                        changed = True
    return ops


SYM = hex_sym()
print(f"α 点群操作数 = {len(SYM)}（应 24）")
assert len(SYM) == 24, len(SYM)

# ---- 8 个 <111> 与 6 个 {110} ----
L111 = sorted({tuple(norm(v)) for v in itertools.product((1, -1), repeat=3)})
PLANES = [(1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1)]
print(f"<111> 方向数 = {len(L111)}（应 8）")

Rs, labels = [], []
for nv in PLANES:
    nv = np.asarray(nv, float)
    dl_all = [d for d in L111 if abs(np.asarray(d) @ nv) < 1e-9]
    # 反平行等价（d 与 −d 给同一取向）⇒ 去重后应剩 2 条
    dl_in = []
    for d in dl_all:
        if not any(abs(abs(np.asarray(d) @ np.asarray(u)) - 1) < 1e-9 for u in dl_in):
            dl_in.append(d)
    assert len(dl_in) == 2, (nv, len(dl_in), len(dl_all))
    for dl in dl_in:
        b1, b2 = norm(dl), norm(nv)
        b3 = np.cross(b1, b2)
        B = np.column_stack([b1, b2, b3])
        A = np.column_stack([[1.0, 0, 0], [0, 0, 1.0], np.cross([1.0, 0, 0], [0, 0, 1.0])])
        if np.linalg.det(B) < 0 or np.linalg.det(A) < 0:
            continue
        Rs.append(A @ B.T)
        labels.append((tuple(int(x) for x in nv), tuple(np.round(dl, 3))))
print(f"构造出 {len(Rs)} 个变体（应 12）")


def mis(Ra, Rb):
    best = 999.0
    for S in SYM:
        D = Ra.T @ Rb @ S
        ang = np.degrees(np.arccos(np.clip((np.trace(D) - 1) / 2, -1, 1)))
        best = min(best, ang)
    return best


pairs = sorted(mis(Rs[i], Rs[j]) for i, j in itertools.combinations(range(len(Rs)), 2))
hist = Counter(round(a, 2) for a in pairs)
print(f"\n两两取向差谱（{len(pairs)} 对）—— **正确 Burgers OR 应有的样子**：")
for a, c in sorted(hist.items()):
    print(f"  {a:8.2f}°  ×{c}")

print("\n文献特征角检索（容差 0.6°）：")
for t in (10.53, 60.0, 60.83, 63.26, 70.53, 90.0):
    hits = [p for p in pairs if abs(p - t) < 0.6]
    print(f"  {t:6.2f}° -> {len(hits):3d} 对   {[round(h, 2) for h in hits[:6]]}")

print(f"\n唯一角数 = {len(hist)}；最小 {min(pairs):.2f}°、最大 {max(pairs):.2f}°")
print("\n⇒ 判据：这里若出现 60° 与 63.26° 而引擎谱里没有，则是**真问题**（两套 12 变体不是同一组）。")
print("   若这里也没有，则是我对文献角的口径有误（**量具问题**）。")
