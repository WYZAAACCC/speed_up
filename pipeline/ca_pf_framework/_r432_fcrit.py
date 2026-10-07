#!/usr/bin/env python3
"""_r432_fcrit.py —— ★★ **`--nuc-fcrit` 能不能拦住"注定溶解"的形核事件？**

## 背景（`§191`）
冷却前段 `ΔG_v(T_k)`（起点 1.23e8）**小于实测弹性罚** `|ed|`（≈2.5e8）
⇒ 播下去的那片是**亚临界的、会溶解**。
引擎里**自带**一条临界核判据 `f_nuc^crit = 4γ/d`（Du 2017），判定式
`(df + max_k ed_k) > fcrit`，但**驱动层从来打不开它**（`§192` 的接线修复）。

## 可证伪问题
**这条判据拦得住那些注定溶解的事件吗？**

## 量级预估（**必须先写下来，再让实测打脸**）
`fcrit = 4γ/t = 4×0.15/250e-9 = **2.4×10⁶ J/m³**`
对比实测：
  * 典型**界面**的 `|dG|`（`dG_tip` 中位）≈ **1.0–1.7×10⁸**
  * `dG_max`（场最大值）≈ **1.5–3.8×10⁸**
⇒ 无论用 `max_k ed_k` 还是面中位数，`(df + max_k ed_k)` 都 **≫ fcrit**
⇒ **预估：拦不住（`dbg['fcrit'] = 0`）**。

## 判据
**F-1** 语法与接线：`--nuc-fcrit 1` 能被解析、能传到 `nuc_cfg`（AST 层核对）。
**F-2** **实测**开/关两档的 `dbg['fcrit']`（被拒位点数）与事件数。
**F-3** 若 `fcrit == 0` 且事件数相同 ⇒ **判据无效**（阈值太小，被物理量级淹没）
     ⇒ 这本身是一条**要写进台账的负面结论**，不是失败。
"""
import ast
import os
import sys

import numpy as np

SRC = '_bk_exp.py'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL          # noqa: E402
import windowB_km as KM               # noqa: E402


def P(s):
    print(s, flush=True)


P('=' * 92)
P('_r432 —— `--nuc-fcrit` 的接线核对 + 阈值量级')
P('=' * 92)

# ---------------------------------------------------------------- F-1
P('\n[F-1] 接线（AST 层）')
tree = ast.parse(open(SRC, encoding='utf-8').read())
found_arg = None
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'add_argument':
        if node.args and isinstance(node.args[0], ast.Constant) \
                and node.args[0].value == '--nuc-fcrit':
            found_arg = {k.arg: getattr(k.value, 'value', None)
                         for k in node.keywords}
P('    `--nuc-fcrit` 的 add_argument：%s' % (found_arg or '❌ 未找到'))
# nuc_cfg 里是否真的传了 use_fcrit
src = open(SRC, encoding='utf-8').read()
passes = 'use_fcrit=bool(int(getattr(a, \'nuc_fcrit\', 0)))' in src
P('    `nuc_cfg(..., use_fcrit=...)` 真的传了：%s' % ('✅' if passes else '❌'))
# 修前是"只在注释里"
n_comment = sum(1 for ln in src.splitlines()
                if 'use_fcrit' in ln and ln.lstrip().startswith('#'))
n_code = sum(1 for ln in src.splitlines()
             if 'use_fcrit' in ln and not ln.lstrip().startswith('#'))
P('    `use_fcrit` 出现：注释里 **%d** 行、代码里 **%d** 行'
  % (n_comment, n_code))
P('    ⇒ 修前是"0 行代码、3 行注释"⇒ 引擎里的判据从驱动层**不可达**（`§192`）')

# ---------------------------------------------------------------- 阈值量级
P('\n[F-2] 判据阈值的量级 vs 实测驱动力')
for gamma, t_nm in ((0.15, 250.0), (0.25, 250.0), (0.15, 510.0)):
    fcrit = 4.0 * gamma / (t_nm * 1e-9)
    P('    γ=%.2f J/m², t=%.0f nm ⇒ fcrit = 4γ/t = **%.3e J/m³**' % (gamma, t_nm, fcrit))
fcrit = 4.0 * 0.15 / 250e-9
P('')
P('    实测（`_r430`/`_r431`，abA/abB 的界面中位数）：')
P('      `dG_tip` ∈ [−1.68e8, +3.3e7]；`ed_tip` ∈ [−3.16e8, −1.95e8]')
P('      `df = ΔG_v(T_1)` = **%.3e**；`dG_max` ∈ [1.5e8, 3.8e8]'
  % KM.drive_of_T(849.0416666666666, KM.T0_TI64, CL.DS_REF))
P('    ⇒ `fcrit / df(T_1)` = %.3e / %.3e = **%.2e**'
  % (fcrit, KM.drive_of_T(849.0416666666666, KM.T0_TI64, CL.DS_REF),
     fcrit / KM.drive_of_T(849.0416666666666, KM.T0_TI64, CL.DS_REF)))
P('    ⇒ `fcrit / |典型 dG_tip|` ≈ %.3e / 1.3e8 = **%.2e**'
  % (fcrit, fcrit / 1.3e8))
P('')
P('    ⚠ **预估（待实测打脸）**：因为 `(df + max_k ed_k) ≫ fcrit`，')
P('       这条判据在**当前物理量级**下**拦不住任何事件**。')
P('       （`df(T_1) = 1.23e8` 已经是 `fcrit` 的 **51 倍**。）')

# ---------------------------------------------------------------- 判据构造上的根本问题
P('\n[F-3] ⚠ 判据**构造**上的根本问题（这条比量级更重要）')
P('    判定式是 `(df + max_k ed_k) > fcrit`，而 `fcrit = 4γ/d` **只含界面能**。')
P('    但 `§191` 实测：**主导项是弹性罚 `|ed| ≈ 2.5e8`，比界面能项 `2γ/t = 1.2e6` 大 200 倍**。')
P('    ⇒ 判据把"能不能形核"归给**界面能**，而真正的门槛是**弹性**。')
P('    ⇒ 即使把 `--nuc-fcrit` 打开，它**在物理上也不是**"临界核判据"。')
P('    ⇒ 这正是 `§191.4` 登记的框架缺口"**athermal 律缺临界核判据**"的准确含义：')
P('       缺的**不是** `4γ/d` 这一条（它已有），而是**把弹性罚计进门槛**的那一条。')
P('=' * 92)
