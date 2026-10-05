#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_c2_redo.py --- ★ C2 重做（用**引擎自己的** `_argmin_normal`，不是我的代理量）

## 上次 C2 为什么错
我用「ε⁰ 的最大主拉伸方向」当惯习面法向的代理 ⇒ **12 个变体由立方对称相联系，
该量完全相同 ⇒ 聚成 1 组**（退化）。
**但引擎里有正确的函数**：`windowB_surface.py:5787`
```
npref[v + 1] = _argmin_normal(C, np.asarray(eps0[v], float))[0]
```
⇒ **惯习面法向确实可由 (`C`, `ε⁰`) 算出** ⇒ 我此前"C2 不可算"的撤回**过度**了。

## 本次判据（**可 FAIL**）
* **C2a** 12 个变体各求 `_argmin_normal` ⇒ 法向（按 ±等价）应聚成 **6 组**；
* **C2b** 每组恰 **2** 个 ⇒ 与 Burgers OR「6 惯习面 × 每面 2 方向 = 12」一致；
* **C2c** **正对照**：把同一个 `ε⁰` 喂两次，法向必须逐位相同（量具自检）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAIL = []


def ck(n, c, m):
    print("  %-46s %s   %s" % (n, "✅ PASS" if c else "❌ FAIL", m))
    if not c:
        FAIL.append(n)


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
mv = __import__("windowB_ti64_variants")
ALLV = np.asarray(mv.variants()[0], float)
NV = len(ALLV)
print("══ C2 重做（用引擎的 _argmin_normal）  ══\n")

# 找 _argmin_normal
f = None
WS = None
try:
    import windowB_surface as WS
    if hasattr(WS, "_argmin_normal"):
        f = WS._argmin_normal
        print("  ✅ 从 windowB_surface 模块级取到 _argmin_normal")
except Exception as e:
    print("  ⚠ import windowB_surface 失败：%s" % e)
if f is None:
    # 退一步：扫源码找定义
    import re
    try:
        src = open(os.path.join(HERE, "windowB_surface.py"),
                   encoding="utf-8", errors="replace").read()
        m = re.search(r"^def _argmin_normal\(.*?(?=^def |\Z)", src, re.S | re.M)
        print("  %s 源码里有 _argmin_normal 定义" % ("✅" if m else "❌"))
        if m:
            ns = {"np": np}
            exec(compile(m.group(0), "<argmin_normal>", "exec"), ns)
            f = ns["_argmin_normal"]
            print("  ✅ 已从源码 exec 出该函数")
    except Exception as e:
        print("  ⚠ 源码抽取失败：%s" % e)

if f is None:
    print("\n  ❌ 拿不到 _argmin_normal ⇒ C2 本次**无法判定**（按纪律：不作结论）")
    sys.exit(2)

# ---- C2c 正对照：同输入必须同输出 ----
n0 = np.asarray(f(C, ALLV[0])[0], float).ravel()
n0b = np.asarray(f(C, ALLV[0])[0], float).ravel()
ck("C2c 正对照：同 ε⁰ 两次调用逐位相同", np.array_equal(n0, n0b),
   "‖Δ‖ = %.3e" % float(np.abs(n0 - n0b).max()))

# ---- 求 12 个法向 ----
NRM = []
for e in ALLV:
    v = np.asarray(f(C, e)[0], float).ravel()
    NRM.append(v / (np.linalg.norm(v) + 1e-300))
NRM = np.array(NRM)
print("\n  12 个惯习面法向（|cos| 矩阵的对角外分布）：")
A = np.abs(NRM @ NRM.T)
off = A[~np.eye(NV, dtype=bool)]
print("     |cos| 取值集合（前 8）= %s" % np.unique(np.round(off, 6))[:8])

# ---- 聚类（|cos| 接近 1 视为同族，容差 1e-6）----
used = np.zeros(NV, bool)
groups = []
for i in range(NV):
    if used[i]:
        continue
    g = [i]
    used[i] = True
    for j in range(i + 1, NV):
        if not used[j] and abs(float(NRM[i] @ NRM[j])) > 1 - 1e-6:
            g.append(j)
            used[j] = True
    groups.append(g)
sizes = sorted(len(g) for g in groups)
print("  聚类组大小 = %s（共 %d 组）" % (sizes, len(groups)))
ck("C2a 聚成 6 组", len(groups) == 6, "实测 %d 组" % len(groups))
ck("C2b 每组恰 2 个（6×2=12）", sizes == [2] * 6, "实测 %s" % sizes)

print()
print("  自检汇总：%s" % ("✅ 全部 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
print("  ⇒ 若 C2a/C2b PASS：**Burgers OR 的「6 packet × 2 block」在数值上被证实**，")
print("     而不只是代数计数 —— 这是 `packet` 定义的可验证判据。")
sys.exit(0 if not FAIL else 1)
