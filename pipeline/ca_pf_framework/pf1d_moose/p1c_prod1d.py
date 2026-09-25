#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p1c_prod1d.py --- **在"生产公式"上**标定抗截留（V4-(b)），并回答"生产现在用 ALPHA=+2 是否合理"

为什么必须另建这个仪器（记账）：`p1c_alpha2.i` 的 1D 模板用的是**简化** `f_loc`（线性分凝项 + 理想溶液）
且 `kappa_c = 0`；而生产用的是（`stage1_meltpool_c.i` 逐块抄来，不改原件）：

  [f_loc]  f = k_c/2*(c-c0)^2 + A_part*c^2*min(1,2S) + (Omega0/wgb)*(c-c0)*8*(S^2-Q)
           k_c=0.9 c0=0.036 A_part=0.264 Omega0=-5e-11 wgb=4e-6
           ⇒ 平衡分凝 k = 1/(1+2*A_part/k_c) = 0.6303（**无温度依赖** ⇒ k_e 是常数）
  [M]      M = (D_L + (D_S-D_L)h_solid + (D_GB-D_S)h_gb)/(k_c + 2 A_part min(1,2S))
           D_L=1.2e-6(生产子网格闭合) D_S=4e-13 D_GB=4e-10
  [S_eta2] S = Σgr_j^2 ; Q = Σgr_j^4 ; h_solid = min(1,2S) ; h_gb = 8(S^2-Q)
  [F_at]   F_at = ALPHA*W*(1-k_eq)*c*(1-h_gb)   (生产: ALPHA=2, W=2e-6, k_eq=0.6303)
  [kappa_c] 1e-14（Gate-1 值）

**与生产同离散度**：生产 `dx = 1 µm`、`int_width = 4 µm`（= 4 dx）⇒ 本仪器也用 dx = 1 µm、η 的
10–90 宽 = 4 µm（tanh 参数 = 4/2.754 µm）。判据：末态 `c_int`（gr0 = 0.5 处）→ **c0/k = 0.05712**。

用法: p1c_prod1d.py <ALPHA> <W_F_at> <kappa_c> [tend] [V] [dx] [nx]
"""
import io
import os
import re
import sys
import time
import subprocess

BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
HERE = os.path.dirname(os.path.abspath(__file__))
C0, K_EQ, K_C, A_PART = 0.036, 0.6303, 0.9, 0.264
TARGET = C0 / K_EQ


def make_input(A, WF, kappa_c, tend, V, dx, nx, wt_um=4.0):
    wtan = wt_um * 1e-6 / 2.754  # 10-90 宽 = wt_um µm（= 生产 int_width）
    x0 = 2.0e-6
    s = """[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = %(nx)d
  xmin = 0.0
  xmax = %(xmax).6e
[]
[Variables]
  [c]
  []
  [w]
  []
  [gr0]
  []
[]
[AuxVariables]
  [gr0_targ]
    order = CONSTANT
    family = MONOMIAL
  []
%(zeros)s
[]
[ICs]
  [c_ic]
    type = ConstantIC
    variable = c
    value = %(c0).4f
  []
  [gr0_ic]
    type = FunctionIC
    variable = gr0
    function = gr0_f
  []
[]
[Functions]
  [gr0_f]
    type = ParsedFunction
    expression = "0.5*(1-tanh((x-%(x0).4e-%(V).4e*t)/(sqrt(2)*%(wtan).6e)))"
  []
  [zero_f]
    type = ParsedFunction
    expression = '0'
  []
[]
[AuxKernels]
  [gr0_targ_k]
    type = FunctionAux
    variable = gr0_targ
    function = gr0_f
  []
%(zero_kernels)s
[]
[Materials]
  [solute_S]
    type = DerivativeParsedMaterial
    property_name = S_eta2
    coupled_variables = 'gr0'
    expression = 'gr0^2'
    derivative_order = 2
  []
  [solute_Q]
    type = DerivativeParsedMaterial
    property_name = Q_eta4
    coupled_variables = 'gr0'
    expression = 'gr0^4'
    derivative_order = 2
  []
  [h_solid]
    type = DerivativeParsedMaterial
    property_name = h_solid
    coupled_variables = 'gr0'
    material_property_names = 'S_eta2'
    expression = 'min(1, 2*S_eta2)'
    derivative_order = 2
  []
  [h_gb]
    type = DerivativeParsedMaterial
    property_name = h_gb
    coupled_variables = 'gr0'
    material_property_names = 'S_eta2 Q_eta4'
    expression = '8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []
  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = 'c gr0'
    material_property_names = 'S_eta2 Q_eta4'
    constant_names     = 'k_c c0 A_part Omega0 wgb'
    constant_expressions = '%(k_c).4f %(c0).4f %(A_part).4f -5e-11 4e-06'
    expression = 'k_c/2*(c-c0)^2 + A_part*c^2*min(1, 2*S_eta2) + (Omega0/wgb)*(c-c0)*8*(S_eta2^2 - Q_eta4)'
    derivative_order = 2
  []
  [kappa_c]
    type = GenericConstantMaterial
    prop_names = kappa_c
    prop_values = %(kappa_c).6e
  []
  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = 'gr0'
    material_property_names = 'S_eta2 h_gb h_solid'
    constant_names = 'D_L D_S D_GB k_c A_part'
    constant_expressions = '1.2e-06 4.0e-13 4.0e-10 %(k_c).4f %(A_part).4f'
    expression = '(D_L + (D_S-D_L)*h_solid + (D_GB-D_S)*h_gb) / (k_c + 2*A_part*min(1, 2*S_eta2))'
    derivative_order = 2
  []
  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = 'c gr0'
    material_property_names = 'h_gb'
    constant_names = 'ALPHA W k_eq'
    constant_expressions = '%(A).6f %(WF).6e %(k_eq).4f'
    expression = 'ALPHA*W*(1-k_eq)*c*(1-h_gb)'
    derivative_order = 2
  []
[]
[Kernels]
  [w_dot]
    type = CoupledTimeDerivative
    variable = w
    v = c
  []
  [coupled_res]
    type = SplitCHWRes
    variable = w
    mob_name = M
    coupled_variables = 'gr0'
  []
  [coupled_parsed]
    type = SplitCHParsed
    variable = c
    f_name = f_loc
    kappa_name = kappa_c
    w = w
    coupled_variables = 'gr0'
  []
  [gr0_dt]
    type = CoefTimeDerivative
    variable = gr0
    Coefficient = 1.0e-9
  []
  [gr0_a]
    type = Reaction
    variable = gr0
  []
  [gr0_b]
    type = CoupledForce
    variable = gr0
    v = gr0_targ
    coef = 1.0
  []
  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = gr0
    f_name = F_at
    coupled_variables = 'c gr0'
  []
[]
[BCs]
  [c_far]
    type = DirichletBC
    variable = c
    boundary = right
    value = %(c0).4f
  []
[]
[Postprocessors]
  [c_mid]
    type = PointValue
    variable = c
    point = "%(xmid).6e 0 0"
  []
[]
[Executioner]
  type = Transient
  solve_type = NEWTON
  end_time = %(tend).6e
  dt = %(dt).6e
%(stepper)s
  nl_rel_tol = 1e-6
  nl_abs_tol = 1e-7
  nl_max_its = 120
  l_tol = 1e-10
  line_search = bt
  dtmin = 1e-14
[]
[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]
[VectorPostprocessors]
  [line]
    type = LineValueSampler
    variable = 'c gr0'
    start_point = '0 0 0'
    end_point = '%(xmax).6e 0 0'
    num_points = %(npts)d
    sort_by = x
    outputs = lineonly
  []
[]
[Outputs]
  csv = true
  [lineonly]
    type = CSV
    execute_on = FINAL
    file_base = profile
  []
[]
""" % dict(nx=nx, xmax=nx * dx, c0=C0, x0=x0, V=V, wtan=wtan, k_c=K_C,
           A_part=A_PART, kappa_c=kappa_c, A=A, WF=WF, k_eq=K_EQ,
           dt=DT, stepper=STEPPER, tend=tend, xmid=(x0 + V * tend) - 0.0,
           npts=min(4000, nx + 1),
           zeros="".join("  [gr%d]\n    order = CONSTANT\n    family = MONOMIAL\n  []\n"
                         % j for j in range(1, 8)),
           zero_kernels="".join("  [gr%d_zero]\n    type = FunctionAux\n    variable = gr%d\n"
                                "    function = zero_f\n  []\n" % (j, j) for j in range(1, 8)))
    return s


ADAPTIVE_STEPPER = """  [TimeStepper]
    type = IterationAdaptiveDT
    dt = %(dt).6e
    optimal_iterations = 8
    iteration_window = 2
    cutback_factor = 0.5
    growth_factor = 1.5
  []"""

if __name__ == "__main__":
    A = float(sys.argv[1]); WF = float(sys.argv[2]); KC = float(sys.argv[3])
    tend = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0e-5
    V = float(sys.argv[5]) if len(sys.argv) > 5 else 0.6
    dx = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0e-6
    nx = int(sys.argv[7]) if len(sys.argv) > 7 else 60
    global DT, STEPPER
    DT = float(os.environ.get("PROD1D_DT", "0") or (0.05 * dx ** 2 / 1.2e-6))
    STEPPER = ADAPTIVE_STEPPER if os.environ.get("PROD1D_ADAPT", "0") == "1" else ""
    print("dt = %.4e s (fixed=%s)  dt/(l_D^2/D_L) = %.4f"
          % (DT, not STEPPER, DT / ((1.2e-6 / V) ** 2 / 1.2e-6)))
    tag = "A%g_W%g_kc%g" % (A, WF * 1e6, KC)
    suf = os.environ.get("PROD1D_SUFFIX", "")
    if suf:
        tag += "_" + suf
    d = os.path.join(HERE, "prod1d_" + tag)
    os.makedirs(d, exist_ok=True)
    # defensive: a reused directory would mix profile_line_<timestep>.csv from
    # earlier runs and max() would then read a STALE profile (AGENTS lesson #25).
    for f in os.listdir(d):
        if f.startswith("profile_line_") or f == "p1c_prod1d_out.csv":
            os.remove(os.path.join(d, f))
    io.open(os.path.join(d, "p1c_prod1d.i"), "w", encoding="utf-8").write(
        make_input(A, WF, KC, tend, V, dx, nx))
    print("target c_int = c0/k = %.5f ; dx=%.2f um  nx=%d  V=%.2f m/s  tend=%.1e s"
          % (TARGET, dx * 1e6, nx, V, tend))
    t0 = time.time()
    r = subprocess.run([BIN, "-i", "p1c_prod1d.i"], cwd=d, capture_output=True,
                       text=True, timeout=3600, env=ENV)
    out = r.stdout + "\n--STDERR--\n" + r.stderr
    io.open(os.path.join(d, "run.log"), "w", encoding="utf-8").write(out)
    print("rc=%d  %.0f s  JIT失败=%d" % (r.returncode, time.time() - t0,
                                      out.count("JIT compile failed")))
    for l in out.splitlines():
        if "ERROR" in l:
            print("   ERR: " + l.strip()[:160]); break
    fs = [f for f in os.listdir(d) if re.match(r"profile_line_\d+\.csv$", f)]
    if fs:
        f = max(fs, key=lambda f: int(re.search(r"_(\d+)\.csv$", f).group(1)))
        rows = io.open(os.path.join(d, f), encoding="utf-8").read().strip().splitlines()
        hdr = rows[0].split(",")
        ix = {h: i for i, h in enumerate(hdr)}
        dat = [[float(v) for v in r_.split(",")] for r_ in rows[1:]]
        c_int = None
        for i in range(len(dat) - 1):
            p0, p1 = dat[i][ix["gr0"]], dat[i + 1][ix["gr0"]]
            if (p0 - 0.5) * (p1 - 0.5) <= 0:
                c_int = dat[i][ix["c"]]
                break
        cmin = min(r_[ix["c"]] for r_ in dat)
        cmax = max(r_[ix["c"]] for r_ in dat)
        print("   ALPHA=%.3f W_F=%.2e kc=%.1e  c_int=%.6f (目标 %.5f, 偏差 %+.1f%%)"
              % (A, WF, KC, c_int, TARGET, 100.0 * (c_int / TARGET - 1)))
        print("   c 范围 %.5f ~ %.5f" % (cmin, cmax))
