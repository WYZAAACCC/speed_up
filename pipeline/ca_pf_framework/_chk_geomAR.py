#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_geomAR.py --- **`geom_ar()` 的正对照**（`MEASUREMENT_SPEC R0`）

背景（第 24 处修正）
------------------
`T24` 的三个臂（m=0 / m=2 / m=2+形核）打出"几何长:厚 中位=p90=max=**0.00**"
⇒ 量具坏了、已禁用。本脚本在**已知几何**的种子上把每一环都打印出来定位根因。

期望（`seed_plate(k, c, nrm, R, t)` 造的是**圆盘**：法向 `nrm`、面内半径 `R`、厚 `t`）：
  沿 `NPF[k]`（= `nrm`）的尺度 = **t**
  沿 `atab[k]`（真长轴 `a`）的尺度 = **2R**
  沿 `wtab[k]`（宽轴 `w`）的尺度 = **2R**

用法：python3 _chk_geomAR.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, R_SEED, T_SEED      # noqa: E402
from T24_verify_grouping import connected_components             # noqa: E402

L, DX = 2.4e-6, 25e-9
N = int(round(L / DX))
K = 1

g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
n_hab = np.asarray(NPF[K], float)
n_hab = n_hab / np.linalg.norm(n_hab)
g.seed_plate(K, np.array([L / 2] * 3), n_hab, R_SEED, T_SEED)
g.init_parent()
reg = g.region()

print('=' * 100)
print('_chk_geomAR —— `geom_ar()` 的正对照（变体 V%d，种子 R=%.0f nm t=%.0f nm）'
      % (K, R_SEED * 1e9, T_SEED * 1e9))
print('=' * 100)
print('  `atab[K]` = [%+.4f %+.4f %+.4f]  finite=%s'
      % (*g.atab[K], np.isfinite(g.atab[K]).all()))
print('  `wtab[K]` = [%+.4f %+.4f %+.4f]  finite=%s'
      % (*g.wtab[K], np.isfinite(g.wtab[K]).all()))
print('  `NPF[K] ` = [%+.4f %+.4f %+.4f]' % (*n_hab,))
a_raw = np.asarray(g.atab[K], float)
w_raw = np.asarray(g.wtab[K], float)
print('  点积：a·n=%+.4f  w·n=%+.4f  a·w=%+.4f  |a|=%.4f  |w|=%.4f'
      % (a_raw @ n_hab, w_raw @ n_hab, a_raw @ w_raw,
         np.linalg.norm(a_raw), np.linalg.norm(w_raw)))
print('  ★ 记账（`windowB_surface.py:946`）：**`a·n` 不要求为 0**'
      '（rank-1 分解里 `a·n ∝ trace(eps)`）⇒ 用它之前必须**正交化**。')


def ext(vec):
    v = np.asarray(vec, float)
    v = v / (np.linalg.norm(v) + 1e-300)
    idx = np.argwhere(reg == K).astype(float)
    p = idx @ v
    return float(p.max() - p.min()) * DX


print('\n【逐轴尺度】')
print('  沿 `NPF[K]`（应 = t = %.0f nm）  ：**%.1f nm**' % (T_SEED * 1e9, ext(n_hab) * 1e9))
print('  沿 `atab[K]`（未正交化，应 ≈ 2R = %.0f nm）：%.1f nm'
      % (2 * R_SEED * 1e9, ext(a_raw) * 1e9))
av = a_raw - (a_raw @ n_hab) * n_hab
print('  沿 `atab` 正交化后（应 ≈ 2R）：%.1f nm   （|正交化前向量| = %.4f，正交化后 = %.4f）'
      % (ext(av) * 1e9, np.linalg.norm(a_raw), np.linalg.norm(av)))
print('  沿 `wtab[K]`（应 ≈ 2R）        ：%.1f nm' % (ext(w_raw) * 1e9))

print('\n【`geom_ar` 内部逻辑复算】')
lab, n = connected_components(reg == K)
sz = np.bincount(lab.ravel())
sz[0] = 0
idx = np.argwhere(lab == int(np.argmax(sz))).astype(float)
print('  连通分量数 = %d；最大分量胞数 = %d' % (n, idx.shape[0]))
t_ = float((idx @ n_hab).max() - (idx @ n_hab).min()) * DX
print('  `t_`（沿 n*）= %.1f nm' % (t_ * 1e9))
av2 = a_raw - (a_raw @ n_hab) * n_hab
L_ = float((idx @ (av2 / np.linalg.norm(av2))).max()
           - (idx @ (av2 / np.linalg.norm(av2))).min()) * DX
print('  `L_`（沿正交化 a）= %.1f nm' % (L_ * 1e9))
print('  ⇒ `L_/t_` = **%.3f**（期望 ≈ 2R/t = %.2f）' % (L_ / t_, 2 * R_SEED / T_SEED))

print('\n【诊断】')
if abs(ext(n_hab) / T_SEED - 1) > 0.06:
    print('  ✗ 沿 `NPF[K]` 的尺度不等于 t ⇒ **种子法向或 `NPF` 对不上**')
elif L_ / t_ < 0.1:
    print('  ✗ `L_/t_` 近 0 ⇒ **`atab` 不可用作长轴**（可能 `a` 退化成与 `n` 平行）')
    print('     `|正交化前| = %.4f`，`|正交化后| = %.4f` ⇒ 若前者远大于 1 或后者的方向随机，'
          '须改用 **`wtab × npref`** 当长轴（`w` 定义 = `n × a`）'
          % (np.linalg.norm(a_raw), np.linalg.norm(av2)))
else:
    print('  ✓ `geom_ar` 的算法本身可用 ⇒ 上一轮返回 0.00 是**调用侧**的问题（如 `NPF` 表不匹配）')
print('=' * 100)
