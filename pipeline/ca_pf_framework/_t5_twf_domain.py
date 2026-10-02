#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_twf_domain.py --- ★★★★★ `wide_face_thickness` 的**适用域**（解析正对照）

## 要回答什么（第 36 轮提出的问题）
真实方形种子（1000 × 500 × 312.5 nm，长宽比 ~3.2:1.6:1）上读数偏 **+3.95Δx**，
而**细长平板**（合成 SDF）上只偏 **+1.00Δx**。
**⇒ 假设**：量具的"宽面"判据 `(n·n*)² > 0.81`（⇒ 25°）在**长宽比小**的几何上会把**侧面**也算进来。

## 做法（**判据先写死**）
用**解析长方体 SDF**（真值 = 厚度 `t` 已知）扫**平面内长宽比**：
```
φ(x) = max( |n·(x−x0)| − t/2 ,  |a·(x−x0)| − La/2 ,  |b·(x−x0)| − Lb/2 )
```
固定 `t = 250 nm`、`La = 2000 nm`（沿 a 轴足够长），**只扫 `Lb`（宽度）**：
`Lb/t ∈ {1, 1.6, 2, 3, 4, 6, 8, 12, 20}`。

## 判据（**预先写死**）
* **`t_wf` 与真值相对差 ≤ 20%** ⇒ 该长宽比**可用**；
* 找出**最小的可用 `Lb/t`** ⇒ 就是判据② 的**适用阈值**；
* **负对照**：若所有长宽比都给同一个数 ⇒ 说明量具不看形状 ⇒ **假设被否**（须另找原因）。
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import _bk_measure as BM                                     # noqa: E402

N = 128
dx = 62.5e-9
L = N * dx
xs = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(xs, xs, xs, indexing='ij')
n_hab = np.array([1.0, 0.0, 0.0])          # 厚度沿 x
a_ax = np.array([0.0, 1.0, 0.0])
b_ax = np.array([0.0, 0.0, 1.0])
r = np.stack([X - L / 2, Y - L / 2, Z - L / 2], -1)


def box_sdf(t, la, lb):
    """解析长方体 SDF（真值：厚 t、沿 a 长 la、沿 b 宽 lb）。"""
    dn = np.abs(r @ n_hab) - t / 2
    da = np.abs(r @ a_ax) - la / 2
    db = np.abs(r @ b_ax) - lb / 2
    return np.maximum(np.maximum(dn, da), db)


def pick(res):
    if isinstance(res, dict):
        for kk in ('t_wf', 't_wf_m', 't', 'thickness'):
            if kk in res:
                return float(np.asarray(res[kk]).ravel()[0])
        return None
    try:
        return float(np.asarray(res).ravel()[0])
    except Exception:
        return None


t = 250e-9
la = 2000e-9
print('=' * 96)
print('`wide_face_thickness` 的适用域（解析长方体 SDF，真值 t = 250 nm，La = 2000 nm）')
print('=' * 96)
print('  %-10s %-12s %14s %12s %8s' % ('Lb/t', 'Lb(nm)', 't_wf(nm)', '相对差', '判定'))
print('  ' + '-' * 62)
ok_min = None
for ratio in (1.0, 1.6, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 20.0):
    lb = ratio * t
    phi = box_sdf(t, la, lb)
    try:
        v = pick(BM.wide_face_thickness(phi[None], dx, n_hab, 0))
    except Exception as e:
        print('  %-10.1f %-12.0f  ❌ %s' % (ratio, lb * 1e9, str(e)[:40]))
        continue
    if v is None:
        print('  %-10.1f %-12.0f  （无厚度键）' % (ratio, lb * 1e9))
        continue
    err = (v - t) / t
    good = abs(err) <= 0.20
    if good and ok_min is None:
        ok_min = ratio
    print('  %-10.1f %-12.0f %14.1f %11.1f%% %8s'
          % (ratio, lb * 1e9, v * 1e9, err * 100, '✅' if good else '❌'))
print()
print('  ── 判据（预先写死）──')
if ok_min is not None:
    print('  **最小可用平面内长宽比 Lb/t = %.1f** ⇒ 判据② 的适用阈值' % ok_min)
    print('   （真实方形种子是 500/312.5 = **1.6** ⇒ 若阈值 ≥ 2，则**种子落在适用域外** ✓ 与 +3.95Δx 一致）')
else:
    print('  ❌ **没有任何长宽比可用** ⇒ 假设（侧面污染）未被支持 ⇒ 必须另找原因')

# ══════════════════════════════════════════════════════════════════════
# ★★★★★ 追加：**带内截断**的影响（检验"我的离线重建是否引入伪影"）
#   动机：真实快照的带外胞**不在文件里**，我重建时把它们填成 `1e3`
#   ⇒ 带边缘出现巨大跳变 ⇒ `∇φ` 在那里是垃圾 ⇒ 宽面判据可能被污染。
#   本段用**同一个解析长方体**做对照：
#     (a) 整场光滑 φ        ⇒ 已知读数 312.5 nm（= t + 1Δx）
#     (b) **只留 |φ| ≤ 6Δx，带外填 1e3**（模拟我的重建）
#   **判据（预先写死）**：若 (b) ≠ (a) ⇒ **我的重建确实是伪影来源**，
#   判据② 的离线厚度**不可用**（除非快照带整场 φ）。
# ══════════════════════════════════════════════════════════════════════
print()
print('=' * 96)
print('★ 带内截断的影响（模拟我的离线重建；Lb/t = 2）')
print('=' * 96)
lb = 2.0 * t
full = box_sdf(t, la, lb)
BAND = 6
trunc = np.where(np.abs(full) <= BAND * dx, full, 1e3)
for name, arr in (('(a) 整场光滑 φ', full), ('(b) 带内截断（带外填 1e3）', trunc)):
    try:
        v = pick(BM.wide_face_thickness(arr[None], dx, n_hab, 0))
        s = ('%.1f nm（相对差 %+.1f%%）' % (v * 1e9, (v - t) / t * 100)) if v else '（无）'
    except Exception as e:
        s = '❌ %s' % str(e)[:44]
    print('  %-30s ⇒ %s' % (name, s))
va = pick(BM.wide_face_thickness(full[None], dx, n_hab, 0))
vb = None
try:
    vb = pick(BM.wide_face_thickness(trunc[None], dx, n_hab, 0))
except Exception:
    pass
print()
if va is not None and vb is not None:
    if abs(va - vb) < 1e-12:
        print('  ⇒ ✅ 两者相同 ⇒ **带内截断不影响读数** ⇒ 我的重建**不是**伪影来源')
        print('     （那 +3.95Δx 就必须另找原因：真实种子几何 / 锚定厚度 / 引擎实际写的剖面）')
    else:
        print('  ⇒ ❌ 两者不同（%.1f vs %.1f nm）⇒ **我的带内重建引入伪影**'
              % (va * 1e9, vb * 1e9))
        print('     ⇒ 判据② 的**离线厚度不可用**，除非快照带**整场 φ**（`--phi-every > 0`）')
print('=' * 96)
