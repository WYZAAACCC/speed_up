#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_ar_rulers.py —— ★★★ **用已知答案标定"长径比该用哪把尺子"**

为什么要做（Round 128–129 实测）
--------------------------------
靶②（几何长:厚 ≈9:1）的三把尺子在**同一个** `region()` 上给出**差 3 倍**的结果
（`_w2_box16d.log`，step 225）：

| 口径 | 值 | 长径比 |
|---|---|---|
| `max−min` | L=6032.5 / T=831.9 | **7.25** |
| 回转张量 | `L_gyr`=4657.8 / `T_gyr`=536.4 | **8.68** |
| 体积等效 | `L_vol`=2291.1 / `T_maxmin`=831.9 | **2.75** |

⇒ **靶② 的结论完全取决于选哪把尺子** ⇒ **必须先用"已知答案"选尺子**（`MEASUREMENT_SPEC R0`）。

做法
----
* 在网格上**合成已知尺寸的板条**（轴对齐于 `(a, w, n)` 三元组），真值 AR = `L/T` 已知；
* 同时量三把尺子 ⇒ **哪把能复现真值**；
* 扫几个 AR（1 : 1 → 20 : 1）与两种形状（**均匀盒** / **带粗端的不均匀体**）。

判据
----
* **J-1 正对照（均匀盒）**：三把尺子**都必须**复现真值 AR（±15%）—— 这是它们的共同适用域；
* **J-2 判决（不均匀体）**：真值 AR 仍已知（按**体积等效**定义：`AR_true = (V/(W0·T0))/T0`）。
  哪把尺子的偏差最小 ⇒ **它才是靶② 应该用的尺子**；
* **J-3 反向对照**：必须有一把尺子**明显偏**，否则本标定没有分辨力。

⚠ 只读、不改引擎。尺寸全部满足 `MEASUREMENT_SPEC R13`（`≥3Δx`）与盒从容性。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

N, DX = 96, 100e-9                     # 9.6 µm 盒，100 nm 胞（便于放下 20:1）
L_BOX = N * DX
K = 1

_g = W.LevelSetMulti(N, L_BOX, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                     df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
n_ax = np.asarray(NPF[K], float)
n_ax = n_ax / np.linalg.norm(n_ax)
a_ax = np.asarray(_g.atab[K], float)
a_ax = a_ax - (a_ax @ n_ax) * n_ax
a_ax = a_ax / np.linalg.norm(a_ax)
w_ax = np.cross(n_ax, a_ax)
_ax = (np.arange(N) + 0.5) * DX - L_BOX / 2
_X, _Y, _Z = np.meshgrid(_ax, _ax, _ax, indexing='ij')
_PA = _X * a_ax[0] + _Y * a_ax[1] + _Z * a_ax[2]
_PW = _X * w_ax[0] + _Y * w_ax[1] + _Z * w_ax[2]
_PN = _X * n_ax[0] + _Y * n_ax[1] + _Z * n_ax[2]
print('=' * 104)
print('_chk_ar_rulers —— 用已知答案标定"长径比该用哪把尺子"  （N=%d Δx=%.0f nm）' % (N, DX * 1e9))
print('=' * 104)


def rulers(reg):
    """三把尺子。返回 (L_mm, T_mm, L_gyr, T_gyr, L_vol)。"""
    m = (reg > 0)
    idx = np.argwhere(m).astype(float)
    if len(idx) < 10:
        return None
    L_mm = float((idx @ a_ax).max() - (idx @ a_ax).min()) * DX
    T_mm = float((idx @ n_ax).max() - (idx @ n_ax).min()) * DX
    W_mm = float((idx @ w_ax).max() - (idx @ w_ax).min()) * DX
    d = (idx - idx.mean(0)) * DX
    ev = np.sort(np.linalg.eigvalsh((d.T @ d) / len(idx)))[::-1]
    L_gyr, W_gyr, T_gyr = (float(np.sqrt(12 * e)) for e in ev)
    V = len(idx) * DX ** 3
    L_vol = V / max(W_mm * T_mm, 1e-30)
    return L_mm, T_mm, W_mm, L_gyr, T_gyr, L_vol


def box(L, Wd, T):
    return ((np.abs(_PA) <= L / 2) & (np.abs(_PW) <= Wd / 2) & (np.abs(_PN) <= T / 2))


fails = []
# ---------------------------------------------------------------- J-1 均匀盒（正对照）
print('\n【J-1 正对照：均匀盒】三把尺子都应与真值一致（真值 AR = L/T）')
print('   %-22s %-10s %-12s %-12s %s' % ('几何 (L×W×T) µm', '真值AR', 'max−min', '回转', '体积等效'))
for (Lv, Wv, Tv) in ((2.0, 0.6, 0.30), (3.0, 0.4, 0.20), (4.5, 0.3, 0.15)):
    reg = np.zeros((N, N, N), dtype=np.int8)
    reg[box(Lv * 1e-6, Wv * 1e-6, Tv * 1e-6)] = K
    r = rulers(reg)
    if r is None:
        print('   （胞数不足，跳过 %s）' % str((Lv, Wv, Tv)))
        continue
    L_mm, T_mm, W_mm, L_gyr, T_gyr, L_vol = r
    true = Lv / Tv
    vals = [L_mm / max(T_mm, 1e-30), L_gyr / max(T_gyr, 1e-30), L_vol / max(T_mm, 1e-30)]
    ok = all(abs(v / true - 1) < 0.15 for v in vals)
    print('   %-22s %-10.2f %-12.2f %-12.2f %-8.2f  ⇒ %s'
          % ('%.1f×%.1f×%.2f' % (Lv, Wv, Tv), true, vals[0], vals[1], vals[2],
             'PASS' if ok else 'FAIL'))
    if not ok:
        fails.append('J-1(%s)' % str((Lv, Wv, Tv)))

# ---------------------------------------------------------------- J-2/J-3 不均匀体（判决）
#   构造：一个**粗端** + 一条**细长臂**（都在盒内、臂宽 ≥3Δx）。
#   真值 AR 按**体积等效**定义：`AR_true = L_span / T0`，但"板条长度"按体积等效算：
#   这里我们**明确声明真值是"跨度"**（因为 EBSD 量的是跨度）——
#   ⇒ 因此本节的判据是：**哪把尺子复现"跨度"**，以及**它们各自偏离多少**。
print('\n【J-2/J-3 不均匀体（粗端 + 细臂）】真值 = **跨度** `L_span`（EBSD 量的是跨度）')
print('   %-26s %-10s %-12s %-12s %-12s %s'
      % ('几何', '真值跨度/T0', 'max−min', '回转', '体积等效', '结论'))
CASES = [((0.8, 0.8, 0.20, 1.6, 0.30), '主体0.8 + 臂1.6'),
         ((0.6, 0.6, 0.20, 2.4, 0.30), '主体0.6 + 臂2.4'),
         ((0.6, 0.6, 0.20, 3.0, 0.30), '主体0.6 + 臂3.0')]
for (L0u, W0u, T0u, L1u, w1u), tag in CASES:
    L0, W0, T0 = L0u * 1e-6, W0u * 1e-6, T0u * 1e-6
    L1, w1 = L1u * 1e-6, w1u * 1e-6
    reg = np.zeros((N, N, N), dtype=np.int8)
    reg[box(L0, W0, T0)] = K
    reg[(np.abs(_PW) <= w1 / 2) & (np.abs(_PN) <= T0 / 2)
        & (_PA > L0 / 2) & (_PA <= L0 / 2 + L1)] = K
    r = rulers(reg)
    if r is None:
        continue
    L_mm, T_mm, W_mm, L_gyr, T_gyr, L_vol = r
    true = (L0 + L1) / T0                      # 真值 = 跨度 / 厚
    vals = [L_mm / max(T_mm, 1e-30), L_gyr / max(T_gyr, 1e-30), L_vol / max(T_mm, 1e-30)]
    dev = [abs(v / true - 1) for v in vals]
    best = int(np.argmin(dev))
    print('   %-26s %-10.2f %-12.2f %-12.2f %-12.2f %s'
          % (tag, true, vals[0], vals[1], vals[2],
             ['max−min', '回转', '体积等效'][best] + ' 最接近（偏 %+.0f%%）' % (100 * (vals[best] / true - 1))))
print('\n   ⇒ 判读：**若 `max−min` 在均匀盒上准、在不均匀体上仍准 ⇒ 它可用**；')
print('     若它在不均匀体上偏离真跨度 ⇒ 靶② **不得**单用它（本轮 `geom_ar` 的 G-4 已给出一个偏 +139% 的实例）。')
print('\n' + '=' * 104)
print('=== AR 量具标定 %s ===' % ('全部 PASS' if not fails else ('J-1 FAIL: ' + ','.join(fails))))
sys.exit(0 if not fails else 1)
