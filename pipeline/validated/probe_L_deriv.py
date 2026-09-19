#!/usr/bin/env python3
"""
最小探针：MOOSE 提供的 `L_dgr0`（= ∂L/∂η₀）到底对不对？

## 为什么需要它

T1 的二分已经把范围压到「`L` 的一阶 η 导数」，主导在 `L2b`/`align4` 分支
（见 VALIDATION_STATUS.md §1.4）。但最后一个分岔口必须先回答：

    **是 MOOSE 给的导数属性本身不对，还是我们的材料写法有问题？**

两者修法完全不同。

## 做法：**只用 MOOSE 自己的输出做自洽性检验**

不重实现表达式（那会引入自己的错误），而是：

1. 造一个**单单元**算例：η₀…η₇ 是**非线性变量**（`ConstantIC` 给定），
   只放 `TimeDerivative` 核（**没有 AC 驱动力**）⇒ `∂η/∂t = 0` ⇒ η 精确不随时间变，
   而材料在初始态被求值。
2. 用 `MaterialRealAux`（`MONOMIAL CONSTANT`，本项目踩过节点变量的坑）把
   `L` 与 `L_dgr0 … L_dgr7` **抽成 AuxVariable**，再用 `ElementAverageValue` 打出来
   —— 这些正是 MOOSE 喂给 `ACInterface` / `ACGrGrPoly` 的导数属性。
3. η₀ 从 A 挪到 A+h 再跑一次，取 **L 的差分** `(L(A+h) − L(A))/h`。
4. 比对：`差分 ≈ L_dgr0(A)` ？

* **不符** ⇒ MOOSE 的导数属性与它自己的 L 值不自洽 ⇒ 缺陷在导数属性侧。
* **相符** ⇒ 导数属性是对的 ⇒ 缺陷在我们的材料写法（例如 gdir 的耦合方式）。

## 用法

    python3 probe_L_deriv.py --src <生产 D 输入> --outdir /root/work/probeL
    cd /root/work/probeL/A && phase_field-opt -i probe.i     # WSL 里，先 conda activate moose
    cd /root/work/probeL/B && phase_field-opt -i probe.i
"""

import argparse
import os
import re
import sys

NEEDED = ["gdir_p", "gdir_q", "align4_prop", "L2b", "L2a", "gamma_aniso", "L_aniso"]
N_OP = 8
# 要抽出来看的材料属性。⚠ MOOSE 的派生属性名是**分式**风格，不是 `L_dgr0`：
#   `DerivativeMaterialPropertyNameInterface::derivativePropertyName()`
#   （framework/src/materials/DerivativeMaterialPropertyNameInterface.C:16）
#   一阶 -> `dL/dgr0`；二阶 -> `d^2L/dgr0dgr1`（变量名**按字母排序**）。
#   第一版按 `L_dgr0` 写，MOOSE 直接报 "Material property 'L_dgr0' is not defined"。
TARGETS = [("L", "L"), ("align4", "align4")] + [(f"dL/dgr{i}", f"dLdgr{i}") for i in range(N_OP)]


def extract_block(text, name):
    m = re.search(r"^  \[" + re.escape(name) + r"\](.*?)\n  \[\]\n", text, re.S | re.M)
    if not m:
        sys.exit(f"错误：在生产输入里找不到材料块 [{name}]")
    return "  [" + name + "]" + m.group(1) + "\n  []\n"


def build(mats, eta_vals):
    # ⚠ MOOSE 只允许**一个**顶层 [Functions] 块 —— 序参量常量函数与 gdir 用的
    #   fx/fy 必须合并进同一个块。第一版写成两块，MOOSE 会直接报错。
    fn = "\n".join(
        f"    [v{i}]\n      type = ParsedFunction\n      expression = '{v}'\n    []"
        for i, v in enumerate(eta_vals))
    fn += ("\n    [fx]\n      type = ParsedFunction\n      expression = '1.0'\n    []"
           "\n    [fy]\n      type = ParsedFunction\n      expression = '0.3'\n    []"
           "\n    [fT]\n      type = ParsedFunction\n      expression = '1900'\n    []")
    auxvar = "\n".join(
        f"    [{a}]\n      family = MONOMIAL\n      order = CONSTANT\n    []"
        for _, a in TARGETS)
    auxker = "\n".join(
        f"    [k_{a}]\n      type = MaterialRealAux\n      variable = {a}\n"
        f"      property = '{p}'\n      execute_on = 'timestep_end'\n    []"
        for p, a in TARGETS)
    pois = "\n".join(
        f"    [{a}]\n      type = ElementAverageValue\n      variable = {a}\n    []"
        for _, a in TARGETS)
    return f"""# 自动生成，勿手改 —— 见 probe_L_deriv.py
# 目的：检验 MOOSE 给的 L_dgr0 与它自己的 L 值是否自洽。
[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 1
  xmin = 0
  xmax = 1
  elem_type = EDGE2
[]

[Variables]
  [gr0]
  []
  [gr1]
  []
  [gr2]
  []
  [gr3]
  []
  [gr4]
  []
  [gr5]
  []
  [gr6]
  []
  [gr7]
  []
[]

[Functions]
{fn}
[]

[ICs]
  [ic0]
    type = FunctionIC
    variable = gr0
    function = v0
  []
  [ic1]
    type = FunctionIC
    variable = gr1
    function = v1
  []
  [ic2]
    type = FunctionIC
    variable = gr2
    function = v2
  []
  [ic3]
    type = FunctionIC
    variable = gr3
    function = v3
  []
  [ic4]
    type = FunctionIC
    variable = gr4
    function = v4
  []
  [ic5]
    type = FunctionIC
    variable = gr5
    function = v5
  []
  [ic6]
    type = FunctionIC
    variable = gr6
    function = v6
  []
  [ic7]
    type = FunctionIC
    variable = gr7
    function = v7
  []
[]

[AuxVariables]
  [grad_Tx]
    family = MONOMIAL
    order = CONSTANT
  []
  [grad_Ty]
    family = MONOMIAL
    order = CONSTANT
  []
  [T]
    family = MONOMIAL
    order = CONSTANT
  []
{auxvar}
[]

[Kernels]
  [dt0]
    type = TimeDerivative
    variable = gr0
  []
  [dt1]
    type = TimeDerivative
    variable = gr1
  []
  [dt2]
    type = TimeDerivative
    variable = gr2
  []
  [dt3]
    type = TimeDerivative
    variable = gr3
  []
  [dt4]
    type = TimeDerivative
    variable = gr4
  []
  [dt5]
    type = TimeDerivative
    variable = gr5
  []
  [dt6]
    type = TimeDerivative
    variable = gr6
  []
  [dt7]
    type = TimeDerivative
    variable = gr7
  []
  # ⚠ 这个核的唯一作用是**让 MOOSE 请求 `dL/dgr*`**
  #   （MOOSE 只为被请求过的派生属性生成属性，见上面 TARGETS 处的说明）。
  #   `mu = 0`（见 [Materials]）⇒ 它的残差恒为 0 ⇒ η 不随时间变，
  #   材料就在我们设定的初始态被求值。
  [ac0]
    type = ACGrGrPolyJ
    variable = gr0
    v = 'gr1 gr2 gr3 gr4 gr5 gr6 gr7'
    mob_name = L
    coupled_variables = 'T gr1 gr2 gr3 gr4 gr5 gr6 gr7'
  []
[]

[AuxKernels]
  [gx]
    type = FunctionAux
    variable = grad_Tx
    function = fx
    execute_on = 'initial timestep_end'
  []
  [gy]
    type = FunctionAux
    variable = grad_Ty
    function = fy
    execute_on = 'initial timestep_end'
  []
  [Tk]
    type = FunctionAux
    variable = T
    function = fT
    execute_on = 'initial timestep_end'
  []
{auxker}
[]

[Materials]
{mats}  [mu_zero]
    type = GenericConstantMaterial
    prop_names = 'mu'
    prop_values = '0'
  []
[]

[Postprocessors]
{pois}
[]

[Executioner]
  type = Transient
  # ⚠ 别用极小的时间（如 1e-12）：实测 MOOSE 会**一步都不走**、直接结束，
  #   CSV 里只剩 t=0 那一行、而且材料还没求值（全是 0）。
  #   核只有 TimeDerivative（+ 一个 mu=0 的 AC 核）⇒ ∂η/∂t ≡ 0 ⇒ η 与 dt 无关。
  end_time = 1.0
  dt = 1.0
  solve_type = NEWTON
  nl_abs_tol = 1e-14
  nl_rel_tol = 1e-14
[]

[Outputs]
  csv = true
[]
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--outdir", default="/root/work/probeL")
    ap.add_argument("--eta0", type=float, default=0.6)
    ap.add_argument("--h", type=float, default=1e-4)
    a = ap.parse_args()

    src = open(a.src, encoding="utf-8").read()
    mats = "".join(extract_block(src, n) for n in NEEDED)

    etas_rest = [0.05] * (N_OP - 1)
    for tag, e0 in (("A", a.eta0), ("B", a.eta0 + a.h)):
        d = os.path.join(a.outdir, tag)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "probe.i"), "w", encoding="utf-8") as f:
            f.write(build(mats, [e0] + etas_rest))

    print(f"探针已写到 {a.outdir}/A 与 {a.outdir}/B（η0 = {a.eta0} 与 {a.eta0 + a.h}）")
    print("下一步（WSL，先 conda activate moose）：")
    print(f"  cd {a.outdir}/A && phase_field-opt -i probe.i")
    print(f"  cd {a.outdir}/B && phase_field-opt -i probe.i")
    print("然后看两份 probe_out.csv 的 L 与 L_dgr0。")


if __name__ == "__main__":
    main()
