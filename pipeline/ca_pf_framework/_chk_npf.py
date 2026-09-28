#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_chk_npf.py —— 量化 `NPF[k]`（引擎实际用的惯习面法向）与真值的夹角

发现经过（`_probe_iface_types.py` 的 I-1 自校验把它挖出来的）
------------------------------------------------------------
靶③ 量具第一版把 `NPF` 当变体 k 的 α′ c 轴、`atab[k]` 当基面轴，结果 **66 对里 56 对无法归类**。
追下去发现两件事：

1. `atab[k] · NPF[k] = −0.143` ⇒ **`atab` 不垂直于 `NPF`** ⇒ 它**不是**该变体的基面 <11-20> 方向（我的用法错）；
2. ★ **`NPF[k]` 本身不是 `{110}β` 面法向** —— 看 `T16_verify_rve.py:45-53`：
   ```python
   for n in _rng.normal(size=(400, 3)):        # ← 只用 400 个随机方向
       val = 0.5 * einsum(EPS0[v], Lam(C, n), EPS0[v])
       if val < best: bn = n
   NPF[v + 1] = bn
   ```
   它是**"400 点随机搜索"求弹性应变能 `½ε⁰:Λ(n):ε⁰` 最小**得到的**弹性不变法向**，
   而 `EPS0, _F, _M = variants()` ⇒ `NPF[k]` 与 `_M[k-1]` **本就是同一个变体**（按下标对齐）。

本脚本给出那个误差的**实测量级**。判据：**不设阈值**，只如实报数 ——
因为它是不是问题，取决于它下游喂给谁（见输出末的三条用途分析）。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from windowB_ti64_variants import variants                       # noqa: E402
from T16_verify_rve import NPF, NV                               # noqa: E402

_E, _F, _M = variants()
nrm = lambda v: v / np.linalg.norm(v)
errs = []
for k in range(1, NV + 1):
    t = nrm(np.asarray(_M[k - 1]['n'], float))
    p = nrm(np.asarray(NPF[k], float))
    errs.append(np.degrees(np.arccos(np.clip(abs(p @ t), -1, 1))))
errs = np.array(errs)

print('=' * 96)
print('_chk_npf —— `NPF[k]`（400 点随机搜索）vs 真值 `_M[k-1]["n"]`（Burgers {110}β 面法向）')
print('=' * 96)
print('   夹角：中位 **%.2f°**  最大 **%.2f°**  最小 **%.2f°**'
      % (np.median(errs), errs.max(), errs.min()))
print('   逐个：' + ' '.join('%.1f' % e for e in errs))
print()
print('   ⚠ **不要**把它归因成"随机搜索分辨率不够" —— 400 点随机采样的典型最近邻间距 ≈ %.1f°，'
      % np.degrees(np.sqrt(4 * np.pi / 400)))
print('     而实测是 **85–90°**，**差了一个数量级** ⇒ **不是采样精度问题**。（本脚本第一版就是这样误判的。）')
print()
print('★★ 两个必须分清的可能，**本轮尚未定论**：')
print('   **可能 A（物理对）**：`_lam_full(C, n)` 是**"法向为 n 的板条"的弹性算子** ⇒')
print('      `NPF[k]` 就是变体 k 的**弹性不变面/惯习面法向**，它**本来就不等于 `{110}β` 面法向**。')
print('      则 88° 这个数需要物理判读（Ti-64 α′ 的惯习面常报 {10 11}α′，与 (0001)α′ 成大角）——')
print('      ★ 旁证：全 12 个 `_M[j]["n"]` 里**最近的一个只差 29°**（第一版全局匹配所得）⇒ 像"另一个惯习面族"。')
print('   **可能 B（量错了对象）**：`_lam_full(C, n)` 若是**声学张量**（`C_ijkl n_j n_l`，对应"沿 n 的应变"）')
print('      ⇒ 它的极小方向**本来就垂直于**板条法向 ⇒ **`NPF` 被当成了错误类型的量**。')
print('   ⇒ **定论方法**：读 `windowB_pf3d._lam_full` 的定义（是 `C − C(nn)(nCn)^{-1}(nn)C` 还是 `C_ijkl n_j n_l`）。')
print('      **这一步未做之前，不得声称 `NPF` 对或错。**')
print()
print('【下游用途分析】（决定它要紧到什么程度）')
print('   ① `advance(mob_beta=…)` 的 `M(n)=M0·exp[−β_h(n·n*)²]`：')
print('      若 `n*` 偏 88°，则 `(n·n*)²` 在"本该最小"的方向上 ≈ 0 ⇒ **各向异性钉扎会被整个抹掉**；')
print('      若只是 29°，`cos²θ ≈ %.3f` ⇒ 影响有限。' % (np.cos(np.radians(29)) ** 2))
print('      ⇒ ★ **两种可能的后果差得天壤之别 ⇒ 必须先定 A/B。**')
print('   ② `seed_plate(..., normal=NPF[k])`：种子板条的取向。`T28` 实测 θ=5° 就让几何厚度 **+48.9%**。')
print('   ③ 靶③ 分类：已改用 `windowB_ti64_variants` 的真值 ⇒ **本误差不进入靶③ 量具**。')
print()
print('   ⇒ **登记为高优先开放问题（`L0-e`）**：因为它同时喂 `mob_beta` 的 `n*` 与 `seed_plate` 的取向。')
print('   ⚠ 任何修法（把 400 点换成解析/dense，或直接令 `NPF= _M[k-1]["n"]`）**都会改数 ⇒ 按 `R8` 重跑**。')
print('=' * 96)
