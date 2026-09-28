#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_edsoft.py --- `F-2` 的**直接反证**：`elastic_soft` 是不是一个"改不动任何东西"的死开关？

背景（`WINDOWB_ROADMAP_TO_CORRECT.md §9.10c`）
--------------------------------------------
`windowB_surface.py:2097-2102`（AUDIT-#9）声称：硬 `region` 指示场 ⇒ ε⁰ 呈阶梯 ⇒ FFT 谱法解出的
σ 在**界面处**有 O(1) 阶梯噪声 ⇒ `ed` 被污染；并给出 `soft=True` 的缓解。**默认 False。**

本轮 `_run_edsoft.sh` 的 A/B（只差 `elastic_soft`）给出**逐位相同**的轨迹与 `ed`
⇒ 怀疑该开关**从未生效**。代码级根因（走查）：

    windowB_surface.py:2147   sig = self.pf.sigma_tensor(reg)      ← 传**硬 `reg`**
    windowB_pf3d.py:273       sigma_tensor(idx) → _epsh(idx) → eps0_fields_idx(idx)
    windowB_pf3d.py:255       pos = idx > 0 ; e[p] = where(pos, e0v[ii,p], 0)   ← 不读 self.phi

⇒ T3 的 gather 快路径绕过了软剖面。本脚本把这条走查变成**可执行断言**（`AGENTS.md §3.19`）。

判据（**先写死**）
------------------
  E-1 **正对照**：`soft=False` 必须能算出非零 `ed`（否则探针本身没跑起来）；
  E-2 **反向测试（本条就是要抓的 bug）**：`elastic_driving(soft=True)` 与 `(soft=False)`
      **必须不同**。若 `np.array_equal(...) is True` ⇒ **`elastic_soft` 是死开关** ⇒ 报 `F-2`。
  E-3 **旁证**：`self.pf.phi` 在 `soft=True` 之后**确实被写成了软剖面**（证明"写进去了、
      但下游没用"，而不是"根本没写"）。这一条把责任精确定位到 gather 路径。

用法：python3 _chk_edsoft.py [--N 48]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=48)
ap.add_argument('--dx-nm', type=float, default=100.0)
a = ap.parse_args()
dx = a.dx_nm * 1e-9
L = a.N * dx

print('=' * 96)
print('_chk_edsoft —— `F-2` 直接反证：`elastic_soft` 到底改不改得动 `elastic_driving()`？')
print('  N=%d Δx=%.1f nm L=%.2f µm' % (a.N, a.dx_nm, L * 1e6))
print('=' * 96)

g = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=2, reinit_every=0)
K = 1
n_hab = np.asarray(NPF[K], float)
n_hab /= np.linalg.norm(n_hab)
g.seed_plate(K, np.array([L / 2] * 3), n_hab, 500e-9, 700e-9)
g.init_parent()

# E-1 正对照
g.elastic_soft = False
ed_hard = g.elastic_driving()
nz = int((np.abs(ed_hard[K]) > 0).sum())
print('\n【E-1 正对照】`soft=False` ⇒ `ed[V%d]` 非零胞 = %d / %d ；'
      '范围 [%.3e, %.3e] J/m³ ⇒ %s'
      % (K, nz, ed_hard[K].size, ed_hard[K].min(), ed_hard[K].max(),
         'PASS（探针跑起来了）' if nz > 0 else 'FAIL（全零 ⇒ 探针没生效）'))

# E-2 反向测试
phi_before = None if g.pf is None else getattr(g.pf, 'phi', None)
g.elastic_soft = True
ed_soft = g.elastic_driving()
same = bool(np.array_equal(ed_hard, ed_soft))
dmax = float(np.max(np.abs(ed_hard - ed_soft)))
print('\n【E-2 ★反向测试】`soft=True` vs `soft=False`：'
      '`np.array_equal` = **%s** ；max|Δ| = **%.3e** J/m³' % (same, dmax))
if same:
    print('   ⇒ ⛔ **`elastic_soft` 是死开关**（`F-2` 成立）：改它**完全不动** `elastic_driving()`。')
    print('      代码级根因：`windowB_surface.py:2147` 把**硬 `reg`** 传给 `sigma_tensor`，')
    print('      而 `windowB_pf3d.py:242-259` 的 gather 路径用 `idx > 0` 装 ε⁰，**不读 `self.phi`**。')
    print('      ⇒ AUDIT-#9 声称的"用平滑指示场消除界面 σ 噪声"**从未生效**（`AGENTS.md §3.7`）。')
else:
    print('   ⇒ ✅ 开关有效（`F-2` 不成立）⇒ 需要复核 `_run_edsoft.sh` 的逐位相同是怎么来的。')

# E-3 旁证：软剖面到底写没写进去
written = None
if g.pf is not None and getattr(g.pf, 'phi', None) is not None:
    p = np.asarray(g.pf.phi)
    written = (p.dtype, float(p.min()), float(p.max()),
               bool(np.all((p >= 0) & (p <= 1))))
print('\n【E-3 旁证】调用后 `self.pf.phi`：dtype=%s  范围 [%.4f, %.4f]  落在 [0,1]=%s'
      % (written if written else ('—',)))
if written and 0.0 < written[2] < 1.0 and written[3]:
    print('   ⇒ 软剖面**确实被写进去了**（值域 [0,1] 且有非整数值）')
    print('     ⇒ 责任在下游：`sigma_tensor(reg)` 用的是**硬 `reg`**，把刚写好的软剖面丢掉了。')
else:
    print('   ⇒ `self.pf.phi` 看起来不像软剖面 ⇒ 需重新定位（可能连写都没写）。')

print('\n' + '=' * 96)
print('结论：%s' % ('⛔ **F-2 确认** —— `elastic_soft` 死开关，界面 `ed` 一直是硬阶梯污染值'
                  if same else '✅ `elastic_soft` 有效'))
print('=' * 96)
sys.exit(0)
