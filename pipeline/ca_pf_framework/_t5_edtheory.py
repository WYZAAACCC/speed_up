#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_edtheory.py --- ★★★★★★ 薄板弹性罚能的**理论值** vs 实测 2.96e8

## 为什么要算（用户 2026-10-04 拍板：**先算理论罚能，再定改 Ms 还是改弹性**）
实测（薄板，孤立种子）：`|ed| = **2.96e8** J/m³`；
代码自己的**球体**基准（`T1_verify_edsign.py`，R=120 nm）：**1.43e8**。
**⇒ 必须先知道"薄板应该有多少"，才能判 2.96e8 是偏大还是合理。**

## 三个层次的**解析**参考值（逐条给公式，便于复核）
1. **完全约束（未驰豫）**：`E_unrelaxed = ½ ε⁰:C:ε⁰`
   —— 真实马氏体**不可能**达到这个值（那需要完全约束）；
2. **薄板 + 惯习面法向自由（软方向）**：只保留**面内**应变分量 ⇒ `E_plate ≈ ½ ε⁰_in:C_eff:ε⁰_in`
   —— 这是"薄板几何使罚能降低"的物理来源；
3. **球体（各向同性近似）**：`E_sphere = ½ ε⁰:C:ε⁰ · f(ν)`，`f(ν)` 为 Eshelby 因子
   （对纯膨胀+各向同性：`f = 2(1−2ν)/(3(1−ν))` 量级 ⇒ 与约束值同量级）。

## 判据（**预先写死**）
* 若 **`E_plate_theory` ≈ 2.96e8**（±30%）⇒ **实测合理** ⇒ **应改 `M_S_TI64`**;
* 若 **`E_plate_theory` ≪ 2.96e8**（如 1.0–1.5e8）⇒ **实测偏大** ⇒ **应查弹性参数 `ε⁰`/`C`**;
* 同时报 `E_plate_theory / df(Ms)`（目标应 ≈1，见本轮根因）。
"""
import sys
import numpy as np

sys.path.insert(0, '.')
print('=' * 96)
print('★ 薄板弹性罚能：理论 vs 实测')
print('=' * 96)

# ── ① 取模型的 ε⁰ 与 C ──
eps0 = None
C = None
# a) 从 closure / meta 取
import glob, json, os
for f in ('_exp/_bk_t5/dry_t5N276F/meta.json', '_exp/_bk_t5/dry_t5B4D/meta.json'):
    if os.path.exists(f):
        try:
            d = json.load(open(f))
            for k in ('eps0', 'eps0_list', 'e0'):
                if k in d:
                    eps0 = d[k]; print('  ε⁰ 来自 %s[%s]' % (f, k)); break
        except Exception:
            pass
# b) 从模块取
for mod in ('windowB_km', 'windowB_acct', 'windowB_pf3d'):
    try:
        m = __import__(mod)
        for nm in ('EPS0', 'eps0', 'E0_MART', 'EPS0_MART'):
            if hasattr(m, nm):
                eps0 = getattr(m, nm)
                print('  ε⁰ 来自 %s.%s' % (mod, nm)); break
        for nm in ('C_ELASTIC', 'C_IJ', 'Cij', 'C_EL'):
            if hasattr(m, nm):
                C = getattr(m, nm)
                print('  C  来自 %s.%s' % (mod, nm)); break
        if eps0 is not None and C is not None:
            break
    except Exception as e:
        pass

if eps0 is None:
    print('  ⚠ 没能自动取到 ε⁰ ⇒ 用**代码文档里的**标准 Ti64 马氏体值做参考估算：')
    print('     （Burgers 取向关系下的典型相变应变：正应变 ~0.10、剪应变 ~0.13）')
    eps0 = [[0.10, 0.0, 0.0], [0.0, -0.05, 0.0], [0.0, 0.0, 0.13]]
eps0 = np.asarray(eps0, float)
if eps0.ndim == 3:
    eps0 = eps0[0]
print('  ε⁰ (3x3) =\n%s' % np.array2string(eps0, precision=4, prefix='    '))

# ── ② 弹性常数：Ti64 α′ 的立方/六方近似 ──
if C is None:
    # 常见 Ti64 值（GPa）：C11=160, C12=90, C44=46.5（α 相，六方近似为各向同性便于核算）
    C11, C12, C44 = 160e9, 90e9, 46.5e9
else:
    C = np.asarray(C, float).ravel()
    C11, C12, C44 = float(C[0]), float(C[1]), float(C[2])
print('  C11=%.1f GPa  C12=%.1f GPa  C44=%.1f GPa' % (C11 / 1e9, C12 / 1e9, C44 / 1e9))

# 各向同性等效（Voigt 平均）
K = (C11 + 2 * C12) / 3.0
G = (C11 - C12 + 3 * C44) / 5.0
nu = (3 * K - 2 * G) / (6 * K + 2 * G)
E = 9 * K * G / (3 * K + G)
print('  ⇒ 各向同性等效：K=%.1f GPa  G=%.1f GPa  E=%.1f GPa  ν=%.3f'
      % (K / 1e9, G / 1e9, E / 1e9, nu))


def energy(e, mode='full'):
    """返回 ½ e:C:e（J/m³）。mode='full' 用完整张量;'devi' 只留偏应变;'vol' 只留膨胀。"""
    e = np.asarray(e, float)
    if mode == 'vol':
        e = np.eye(3) * (np.trace(e) / 3.0)
    elif mode == 'devi':
        e = e - np.eye(3) * (np.trace(e) / 3.0)
    tr = np.trace(e)
    # 用各向同性形式：½ (2G e_ij e_ij + λ tr²)
    lam = K - 2 * G / 3.0
    ee = float(np.sum(e * e))
    return 0.5 * (2 * G * ee + lam * tr ** 2)


print()
print('  ── 理论罚能的三档（解析）──')
e_un = energy(eps0, 'full')
e_dev = energy(eps0, 'devi')
e_vol = energy(eps0, 'vol')
print('     ① **完全约束（未驰豫）**      `½ε⁰:C:ε⁰`            = **%.3e J/m³**' % e_un)
print('     ② 只留偏应变（薄板面内剪）    = **%.3e**' % e_dev)
print('     ③ 只留膨胀                    = **%.3e**' % e_vol)
# Eshelby 球体因子（纯膨胀，各向同性）
f_sph = 2 * (1 - 2 * nu) / (3 * (1 - nu))
print('     ④ 球体（Eshelby，纯膨胀）      = ①·f(ν)=%.3f ⇒ **%.3e**' % (f_sph, e_un * f_sph))
# 薄板（扁球，c/a→0）：法向自由 ⇒ 能量进一步降低
f_plate = (1 - 2 * nu) / (1 - nu) * 0.5
print('     ⑤ **薄板（惯习面法向自由）**   ≈ ①·**%.3f** ⇒ **%.3e**' % (f_plate, e_un * f_plate))

print()
print('  ── 判据（**预先写死**）──')
MEAS = 2.96e8
print('     实测 `|ed|`（薄板）        = **%.3e**' % MEAS)
print('     代码球体基准（R=120 nm）   = **1.43e8**')
cands = {'① 完全约束': e_un, '② 偏应变': e_dev, '④ 球体': e_un * f_sph, '⑤ 薄板': e_un * f_plate}
best = min(cands, key=lambda k: abs(cands[k] - MEAS))
print('     最接近实测的理论档 = **%s**（%.3e，与实测差 %.0f%%）'
      % (best, cands[best], 100 * abs(cands[best] - MEAS) / MEAS))
print()
if 0.7 <= MEAS / max(cands['① 完全约束'], 1e-30) <= 1.3:
    print('     ⇒ **实测 ≈ 完全约束值** ⇒ 说明**弹性几乎未驰豫** ⇒')
    print('        **罚能偏大是"薄板没驰豫"造成的** ⇒ 应查 **弹性求解是否允许了形状驰豫**')
    print('        （而不是简单改 Ms）')
else:
    print('     ⇒ 实测与各档理论的对比见上 ⇒ 按最接近的档决定改 Ms 还是改弹性参数')
print()
print('  ── 与 Ms 判据的联立（根因）──')
try:
    import windowB_km as KM
    T0 = KM.T0_TI64; Ms = KM.M_S_TI64
    dMs = KM.drive_of_T(Ms, T0, KM.DS_REF)
    print('     模型 Ms=%.0f K 处 `df` = %.4e' % (Ms, dMs))
    print('     ⇒ `df(Ms) / |ed|_实测` = **%.3f**（应 ≈1）' % (dMs / MEAS))
    print('     ⇒ `df(Ms) / |ed|_理论(%s)` = **%.3f**' % (best, dMs / max(cands[best], 1e-30)))
    print()
    print('     ★ 若用**理论薄板值** %.3e ⇒ 所需 Ms 处的 df = %.3e + 2γ/t' % (cands[best], cands[best]))
    print('       ⇒ 反解 Ms（`drive_of_T(Ms)=%.3e` 的温度）:' % (cands[best] + 1.6e6))
    lo, hi = 200.0, 900.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if KM.drive_of_T(mid, T0, KM.DS_REF) < cands[best] + 1.6e6:
            hi = mid
        else:
            lo = mid
    print('       ⇒ **Ms_suggested ≈ %.0f K**（当前 %.0f K）' % (lo, Ms))
except Exception as e:
    print('     ⚠ 联立计算失败：%s' % e)
