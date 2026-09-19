#!/usr/bin/env python3
"""
最小复现：温度截断 T_cap 会不会改变熔池几何？

背景：审计要求给 Rosenthal 点源加温度上限（实测 T_max = 15107 K，而 Ti64 沸点 3315 K）。
我在 `make_variant.py` 里断言了一条「安全性质」：

    只要 T_cap > 液相线 1928 K，熔池几何完全不变
    （liquid_flag 的判据是 T > 1903，cap 远在其上）

**但实测数据反驳了它**：24×12 网格上，off 与 cap3200 的 `liquid_frac`
在 t=0 就已经不同（0.081597222 vs 0.079861111）。

本脚本用最小算例把这件事钉死：同一套 T 场 + 同一个 `liquid_flag` 后处理，
只改 `laser_T` 的表达式，看 `liquid_frac` 到底变不变。

用法：
    python3 repro_liquid_flag.py            # 生成 .i
    # 然后用 phase_field-opt 逐个跑
"""

import pathlib

EXPR = ("353 + 28/(2*pi*20*sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10))"
        "*exp(-0.6*(sqrt((x+1.2e-4-0.6*t)^2+y^2+1e-10)+x+1.2e-4-0.6*t)/(2*6e-06))")

TMPL = """# 最小复现（自动生成，见 repro_liquid_flag.py）
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 24
  ny = 12
  xmin = -2.8e-4
  xmax = 1.5e-4
  ymin = 0.0
  ymax = 1.5e-4
  elem_type = QUAD4
[]
[Variables]
  [dummy]
  []
[]
[Functions]
  [laser_T]
    type = ParsedFunction
    expression = '@EXPR@'
  []
[]
[AuxVariables]
  [T]
    initial_condition = 353
  []
  [liquid_flag]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[AuxKernels]
  [T_field]
    type = FunctionAux
    variable = T
    function = laser_T
    execute_on = initial
  []
  [lflag]
    type = ParsedAux
    variable = liquid_flag
    coupled_variables = T
    expression = if(T>1903,1,0)
    execute_on = initial
  []
[]
[Postprocessors]
  [T_max]
    type = NodalExtremeValue
    variable = T
    value_type = max
  []
  [liquid_frac]
    type = ElementAverageValue
    variable = liquid_flag
  []
  [liquid_sum]
    type = ElementIntegralVariablePostprocessor
    variable = liquid_flag
  []
  [n_elem_above1903]
    type = ElementIntegralVariablePostprocessor
    variable = liquid_flag
  []
[]
[Executioner]
  type = Steady
[]
[Problem]
  solve = false
[]
[Outputs]
  csv = true
[]
"""

VARIANTS = [
    ("raw", EXPR),
    ("off", "min(%s, 1e30)" % EXPR),
    ("cap3200", "min(%s, 3200)" % EXPR),
    ("cap3500", "min(%s, 3500)" % EXPR),
    ("cap2000", "min(%s, 2000)" % EXPR),   # 低于液相线以上但仍 >1903
    ("cap1930", "min(%s, 1930)" % EXPR),   # 贴着判据 1903
]

if __name__ == "__main__":
    d = pathlib.Path("/root/work/valid/capmin")
    d.mkdir(parents=True, exist_ok=True)
    for tag, e in VARIANTS:
        (d / f"{tag}.i").write_text(TMPL.replace("@EXPR@", e), encoding="utf-8")
    print("生成：", " ".join(t for t, _ in VARIANTS))
