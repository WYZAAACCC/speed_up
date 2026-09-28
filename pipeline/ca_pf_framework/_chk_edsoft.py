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

# ============================================================================
# ★★★ E-4（本轮**加了才知道为什么必须加**）：**端到端**检验 —— 开关必须改得动**动力学**。
#   为什么：`E-2` 只查了 `elastic_driving()`（**诊断路径**），而 `advance` 实际走的是
#     `elastic_driving_pair()` —— 它**也**硬编码了硬 `reg`。
#   实测症状（`_w2_edhard2.log` vs `_w2_edsoft2.log`，引擎 `a1eb151f`，只差 `elastic_soft`）：
#     **形状逐位相同**（L=1458.6 W=1414.5 T=844.0、胞=233、M-3/M-5 全同），
#     而 M-6 的 `ed` 却不同 ⇒ 只看 E-2 会**误判"修好了"**，实际动力学一点没变。
#   ⇒ 判据：两臂各推 `NSTEP` 步，`region()` **必须不同**。
#     （`AGENTS.md §3.7`：改完必须确认**框架真正调用的那条路**也变了。）
# ============================================================================
NSTEP = 3
DT = 0.15 * dx / (1e-9 * 3.5e8)


def _run(nstep, soft):
    gg = W.LevelSetMulti(a.N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                         df=[0.0] + [3.5e8] * NV, workers=2, reinit_every=0)
    gg.elastic_soft = bool(soft)
    gg.seed_plate(K, np.array([L / 2] * 3), n_hab, 500e-9, 700e-9)
    gg.init_parent()
    for _ in range(nstep):
        gg.advance(DT, aniso=0.4, npref=NPF, band_cells=20,
                   mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
    return gg.region()


r_hard = _run(NSTEP, False)
r_soft = _run(NSTEP, True)
dyn_same = bool(np.array_equal(r_hard, r_soft))
ndiff = int((r_hard != r_soft).sum())
print('\n【E-4 ★★端到端】同样种子、同样 %d 步，只差 `elastic_soft`：'
      '`region()` 不同胞数 = **%d** ⇒ %s'
      % (NSTEP, ndiff, '**逐位相同**（开关到不了动力学）' if dyn_same
         else '✅ 动力学确实被改变了'))
if dyn_same:
    print('   ⇒ ⛔ `elastic_soft` 仍然到不了 `advance` 实际走的那条路径。')
    print('      查 `elastic_driving_pair()`（`windowB_surface.py`）—— 它必须也 honor 软剖面。')
    print('      这正是 `AGENTS.md §3.7` 的形状：**改了 A，框架走的是 B**。')
else:
    print('   ⇒ ✅ 两条路径（`elastic_driving` 诊断 / `elastic_driving_pair` 动力学）都吃到了软剖面。')

print('\n' + '=' * 96)
_ok = (not same) and (not dyn_same)
print('结论：%s' % ('✅ `elastic_soft` 有效（诊断路径 + 动力学路径都验证过）' if _ok
                  else '⛔ **F-2 未完全修复** —— 见上 E-2 / E-4'))
print('=' * 96)
sys.exit(0 if _ok else 1)
