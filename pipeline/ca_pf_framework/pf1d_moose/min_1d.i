[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = 100
    xmin = 0
  xmax = 1e-5
[]
[Variables]
  [phi]
  []
[]
[Kernels]
  [dt]
    type = CoefTimeDerivative
    variable = phi
    Coefficient = 1.0e-9
  []
  [src]
    type = Reaction
    variable = phi
  []
  [drv]
    type = BodyForce
    variable = phi
    function = f
  []
[]
[Functions]
  [f]
    type = ParsedFunction
    expression = '0.1*t'
  []
[]
[Executioner]
  type = Transient
  dt = 5.0e-8
  end_time = 5.0e-7
  solve_type = NEWTON
  nl_abs_tol = 1e-14
  nl_rel_tol = 1e-9
  l_tol = 1e-12
[]
[Postprocessors]
  [pv]
    type = PointValue
    variable = phi
    point = '5e-6 0 0'
  []
[]
[Outputs]
  csv = true
[]