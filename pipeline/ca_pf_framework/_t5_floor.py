#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_floor.py --- ★★★★★★ 决定性计算：**法向零错配下薄板罚能的理论下限**

## 为什么这是决定性的一步
`windowB_ti64_variants.py` 的 docstring 逐字：
```
3) 沿面法向 n: **d_(110)=a_b/√2=0.23408 nm 与 c_a/2=0.23415 nm 几乎相等（+0.03%）**,
   所以**贝恩畸变的法向分量几乎为零** --- **这正是 bcc→hcp 能发生的经典原因。**
```
⇒ **薄板的法向错配 ≈ 0** ⇒ **板条在法向可以自由伸缩（几乎不付能量）**
⇒ ⇒ **薄板罚能的理论下限 ≈ "把 ε⁰ 中沿惯习面法向的分量全部释放掉"之后的能量。**

## 判据（**预先写死**）
| 理论下限 vs 实测 2.96e8 | 结论 |
|---|---|
| **≈ 2.96e8（±35%）** | 实测**合理** ⇒ 罚能本就该这么大 ⇒ 回到 **Ms/判据** 方向 |
| **≪ 2.96e8**（如 <1.5e8）| **弹性求解驰豫不充分** ⇒ 查**弹性求解器**为何没利用法向零错配 |

## 三个口径（都报，避免再犯口径错误）
1. **能量口径** `½ε:C:ε`；2. **`ed` 口径** `ε:σ`（= 能量的 2 倍，见 s274 记账）；
3. 两者都报，并显式给出因子关系。
"""
import sys
import numpy as np

sys.path.insert(0, '.')
from windowB_ti64_variants import variants
from windowB_pf3d import C_cubic

C = np.asarray(C_cubic(134.0e9, 110.0e9, 36.0e9), float)
EPS0, _F, _M = variants()
EPS0 = np.asarray(EPS0, float)

print('=' * 96)
print('★ 法向零错配下薄板罚能的**理论下限**（真实 ε⁰，纯晶体学）')
print('=' * 96)
print('  C 形状 = %s ｜ ε⁰ 形状 = %s（%d 变体）' % (C.shape, EPS0.shape, len(EPS0)))


def energy(e):
    """½ ε:C:ε（能量口径）"""
    return 0.5 * float(np.einsum('ij,ijkl,kl->', e, C, e))


def ed_of(e):
    """ed 口径 = ε:σ，完全约束(ε=0)时 σ=−C:ε⁰ ⇒ ed = −ε:C:ε = −2×energy"""
    return -2.0 * energy(e)


# ── 找每个变体的惯习面法向（零错配方向）= C 的最软方向 / ε⁰ 的主方向 ──
# 惯习面法向：`windowB_surface.argmin_normal_cached` 的语义 = "能量最小的法向"
# 这里用等价做法：对每个单位法向 n，释放 n⊗n 方向的分量后的剩余能量，取最小者。
def energy_with_normal_released(e, n):
    """把 e 中沿 n 的分量去掉（模拟"法向自由"），返回剩余能量。"""
    n = n / (np.linalg.norm(n) + 1e-300)
    comp = float(n @ e @ n)              # 法向应变分量
    e_rel = e - comp * np.outer(n, n)    # 释放法向分量
    return energy(e_rel), comp


# 球面采样找最小能量法向
rng = np.random.default_rng(0)
best = None
for _ in range(4000):
    v = rng.normal(size=3)
    n = v / np.linalg.norm(v)
    E, comp = energy_with_normal_released(EPS0[0], n)
    if best is None or E < best[0]:
        best = (E, n, comp)
E_rel, n_hab, comp_hab = best
E_full = energy(EPS0[0])
frac = E_rel / E_full
ed_full = ed_of(EPS0[0])
ed_rel = ed_of(EPS0[0] - comp_hab * np.outer(n_hab, n_hab))

print()
print('  ── 变体 1 的三口径数值 ──')
print('     **完全约束**（未驰豫）:  能量 `½ε:C:ε` = **%.4e** ｜ `ed` 口径 = **%+.4e**'
      % (E_full, ed_full))
print('     **法向自由**（薄板理想）: 能量 = **%.4e**（= 完全约束的 **%.1f%%**）'
      % (E_rel, 100 * frac))
print('                               `ed` 口径 = **%+.4e**' % ed_rel)
print('     ⇒ 惯习面法向 n_hab = [%.4f, %.4f, %.4f]' % tuple(n_hab))
print('     ⇒ **法向应变分量** = **%+.5f**（≈0 则与 docstring 的 +0.03%% 一致）' % comp_hab)
print()
print('     ★ **薄板罚能的理论下限（`ed` 口径）= %.4e**' % ed_rel)

MEAS = 2.96e8
print()
print('  ── 判据（**预先写死**）──')
print('     实测（模型的薄板 `|ed|`）    = **%.3e**' % MEAS)
print('     理论下限（法向自由，`ed` 口径）= **%.3e**' % abs(ed_rel))
ratio = MEAS / abs(ed_rel)
print('     ⇒ **实测 / 理论下限 = %.2f**' % ratio)
if 0.65 <= ratio <= 1.35:
    print('     ⇒ ✅ **实测合理**（在 ±35%% 内）⇒ 罚能本就该这么大')
    print('        ⇒ **回到 Ms/判据方向**：是 Ms 与罚能不匹配，而不是弹性求解的问题')
else:
    print('     ⇒ ❌ **实测远大于理论下限** ⇒ **弹性求解驰豫不充分**')
    print('        ⇒ 需查**弹性求解器为何没利用"法向零错配"**（边界条件/Eshelby/法向自由度）')
print()
print('  ── 附：球体参照 ──')
# 球体（各向同性近似下的 Eshelby 因子）
C11, C12, C44 = C[0, 0, 0, 0], C[0, 0, 1, 1], C[0, 1, 0, 1]
K = (C11 + 2 * C12) / 3.0
G = (C11 - C12 + 3 * C44) / 5.0
nu = (3 * K - 2 * G) / (6 * K + 2 * G)
f_sph = 2 * (1 - 2 * nu) / (3 * (1 - nu))
print('     各向同性等效 ν=%.3f ⇒ 球体 `|ed|` ≈ %.4e' % (nu, abs(ed_full) * f_sph))
print('     ⇒ **薄板下限 %.3e  vs  球体 %.3e** ⇒ 薄板%s球体'
      % (abs(ed_rel), abs(ed_full) * f_sph,
         '**优于**（与物理一致 ✓）' if abs(ed_rel) < abs(ed_full) * f_sph else '**劣于**（与物理相反 ✗）'))
print('     ★ 代码自己的球体基准（模拟实测，R=120 nm）= **1.43e8**')
