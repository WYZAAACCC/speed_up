#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_axes.py --- ★★★ 板条三轴的**一致性**检查：`npref` / `wtab` / `atab` 是不是同一组轴？

为什么要做（Round 141，用户指示「重新检查初始条件与最终结果，**不要误用数据**」）
--------------------------------------------------------------------------------
`M(n) = M0·exp[−β_h(n·n*)² − β_w(n·w)²]` 里**有两个轴**：`n*`（厚向/惯习面法向）与 `w`（宽向）。
代码里它们的**来源不同**：

  * `npref[K]` —— **调用方传入**（`_probe_shape.py` / `T16_verify_rve.py` 用
    `NPF[K]`，做法 = 在 400 个**随机**法向里取弹性应变能最小的那个）。
    用在 `aniso` 各向异性与 `mob_beta` 的 `(n·n*)²` 惩罚上。
  * `self.wtab[K]` / `self.atab[K]` —— **引擎自己**在 `__init__` 里用
    `_rank1_axes(eps0[v], _nref)` 算的，其中 `_nref` 也是"400 随机法向取能量最小"，
    **但随机数序列与调用方不同**（引擎：一次抽样、所有变体共用；
    `T16`：每个变体**重新抽**一次）。
    用在 `mob_beta_w` 的 `(n·w)²` 惩罚上。

⇒ 若两组 `n` 不一致，则：
  1. `w` 不再垂直于实际使用的 `n*` ⇒ **宽向惩罚施加在偏掉的轴上**；
  2. `_probe_shape.axes_of()` 用 `NPF[K]` 当厚向、`g.wtab[K]` 当宽向 —— 两个**不同来源**的轴
     ⇒ 测出来的 `W` 里混进了 `T`（`w` 不垂直 `n*`）。

判据（先定判据再看数）
--------------------
  X-1 **两组 `n*` 的夹角**：全部 12 个变体都应 `< 1°`（同一物理量、同一定义）。
  X-2 **`|n*·w|`**：`w` 定义上必须 ⊥ `n*` ⇒ 应 `< 0.02`（≈1°）。
  X-3 **`|n*·a|`**：⚠ `a` **不要求** ⊥ `n*`（`_rank1_axes` 自己注释说
      `n·a = cos(82.7°) = 0.127`）—— 所以这一条**不是判据**，只报出来；
      但若 `|n*·a|` 大到 0.5 以上，则"长轴"与"厚向"严重不分离，须记账。
  X-4 **正对照**：把引擎的抽样序列**照抄**给调用方（同一个 `_ns`），
      两组 `n*` 应当**逐位相同**（差 0.000°）⇒ 证明差异**只**来自随机抽样不同。

用法：python3 _chk_axes.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402

print('=' * 100)
print('_chk_axes —— 板条三轴一致性：`npref`（调用方） vs `wtab/atab`（引擎）')
print('=' * 100)


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(u @ v), -1.0, 1.0))))


# 起一个极小引擎实例，只为拿到 wtab/atab
g = W.LevelSetMulti(16, 16 * 50e-9, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [3.5e8] * NV, workers=1, reinit_every=0)
# `_rank1_axes` 的 `n` 没被存下来，但 `w = n × a` ⇒ `n ∝ w × a`
#   （`w = n×a` 仍然 ⊥ n 且 ⊥ a ⇒ `n` 落在 `w × a` 的方向上，差一个符号）
assert g.wtab is not None and g.atab is not None, '引擎未生成 wtab/atab'
print('\nX-1/X-2/X-3 逐变体（`npref`=调用方 `NPF`；`w`,`a`=引擎 `wtab/atab`）')
print('  %-5s %-28s %-28s %8s %8s %8s' % ('变体', 'npref (NPF)', 'n_eng = w × a', '<npref,neng>', '|npref·w|', '|npref·a|'))
rows = []
for k in range(1, NV + 1):
    npref = np.asarray(NPF[k], float)
    npref = npref / np.linalg.norm(npref)
    w_ = np.asarray(g.wtab[k], float)
    a_ = np.asarray(g.atab[k], float)
    w_ = w_ / np.linalg.norm(w_)
    a_ = a_ / np.linalg.norm(a_)
    neng = np.cross(w_, a_)
    neng = neng / np.linalg.norm(neng)
    d1 = ang(npref, neng)
    d2 = abs(float(npref @ w_))
    d3 = abs(float(npref @ a_))
    rows.append((k, d1, d2, d3))
    print('  %-5d (%+.4f,%+.4f,%+.4f)   (%+.4f,%+.4f,%+.4f)   %7.3f° %8.4f %8.4f'
          % (k, npref[0], npref[1], npref[2], neng[0], neng[1], neng[2], d1, d2, d3))

d1 = np.array([r[1] for r in rows])
d2 = np.array([r[2] for r in rows])
d3 = np.array([r[3] for r in rows])
print('\n  汇总：<npref,n_eng>  max=%.3f°  mean=%.3f°   （判据 X-1 < 1°）'
      % (d1.max(), d1.mean()))
print('        |npref·w|     max=%.4f (%.2f°)            （判据 X-2 < 0.02）'
      % (d2.max(), np.degrees(np.arccos(min(1.0, d2.max())))))
print('        |npref·a|     max=%.4f (%.2f°)            （非判据，仅记账）'
      % (d3.max(), np.degrees(np.arccos(min(1.0, d3.max())))))

print('\nX-4 正对照：若调用方**照抄**引擎的抽样序列，两组 `n*` 应逐位相同')
_rng = np.random.default_rng(0)
_ns = _rng.normal(size=(400, 3))
_ns /= np.linalg.norm(_ns, axis=1)[:, None]
same = 0
dmax = 0.0
for k in range(1, NV + 1):
    _E = np.asarray(EPS0[k - 1], float)
    _val = 0.5 * np.einsum('ij,sijkl,kl->s', _E,
                           np.array([W._lam_full(C, n) for n in _ns]), _E)
    _n = _ns[int(np.argmin(_val))]
    d = ang(_n, NPF[k])
    dmax = max(dmax, d)
    if d < 1e-9:
        same += 1
print('  用引擎的 `_ns`（一次抽样、共用）重算 ⇒ 与 `NPF` **逐位相同**的变体数 = %d/%d，'
      '最大夹角 %.4f°' % (same, NV, dmax))
print('  ⇒ 若不为 %d/%d ⇒ 差异**不只是随机抽样**，还有别的来源（须继续查）。' % (NV, NV))
print('=' * 100)
