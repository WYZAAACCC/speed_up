# -*- coding: utf-8 -*-
# 1D isomorph with **PRODUCTION's quadratic f_loc** (k_c, c0, A_part), to test whether the
# calibrated a transfers across the free-energy form.
#   f_loc = k_c/2 (c-c0)^2 + A_part c^2 h_solid,      h_solid = 3phi^2-2phi^3
#   f_cc  = k_c + 2 A_part h_solid
#   M     = D(phi)/f_cc,   D(phi) = D_S + (D_L-D_S)(1-phi)      => D = M f_cc exact
#   mu    = k_c(c-c0) + 2 A_part c h_solid
#   c_l   = c0 + mu/k_c ;  c_s = (mu + k_c c0)/(k_c + 2 A_part)
#   Delta c = 2 A_part (k_c c + 2 A_part c h_solid) / (k_c (k_c + 2 A_part))
#   F_at  = A_AT * W * Delta c  + 0*w        (no T dependence: production f_loc has none)
import io, re

HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BASE = HERE + "/p1c_alpha2.i"
PROBES = [4.0e-6, 6.0e-6, 8.0e-6]

OLD_MAT = """  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = "c phi"
    constant_names = "ALPHA W k_eq"
    constant_expressions = "-1.0 3.0e-8 0.6303"
    expression = "ALPHA*W*(1-k_eq)*c*(1-phi)"
    derivative_order = 2
  []"""
OLD_K = """  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = phi
    f_name = F_at
    coupled_variables = "c phi"
  []"""

QUAD = """  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = "c phi"
    constant_names = "k_c c0 A_part"
    constant_expressions = "0.9 0.036 0.264"
    expression = "1.0e9*(k_c/2*(c-c0)^2 + A_part*c^2*(3*phi^2-2*phi^3))"
    derivative_order = 2
  []
  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = "c phi"
    constant_names = "DL DS k_c A_part"
    constant_expressions = "9.5e-9 5.0e-13 0.9 0.264"
    expression = "(DS+(DL-DS)*(1-phi))/(1.0e9*(k_c+2*A_part*(3*phi^2-2*phi^3)))"
    derivative_order = 1
  []
  [kappa_c]
    type = GenericConstantMaterial
    prop_names = kappa_c
    prop_values = 0.0
  []
  [at_susc]
    type = DerivativeParsedMaterial
    property_name = F_at
    coupled_variables = "c phi w"
    constant_names = "A_AT W k_c A_part"
    constant_expressions = "AATV WV 0.9 0.264"
    expression = "A_AT*W*2*A_part*(k_c*c + 2*A_part*c*(3*phi^2-2*phi^3))/(k_c*(k_c+2*A_part)) + 0*w"
    derivative_order = 1
  []"""


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(xmax, nx, tend, Wv, aform, lvs_n, front="smooth"):
    s = io.open(BASE, encoding="utf-8").read()
    assert OLD_MAT in s and OLD_K in s, "anchors"
    # replace f_loc + M_mob + at_susc in one go
    m = re.search(r"(?s)  \[f_loc\]\n.*?\n  \[\]\n  \[M_mob\]\n.*?\n  \[\]\n  \[at_susc\]\n.*?\n  \[\]\n", s)
    assert m, "material span"
    Q = QUAD.replace("3*phi^2-2*phi^3", "min(1,2*phi^2)") if front == "prod" else QUAD
    s = s[:m.start()] + Q.replace("AATV", aform).replace("WV", Wv) + "\n" + s[m.end():]
    s = s.replace(OLD_K, """  [antitrap]
    type = AntitrappingCurrent
    variable = w
    v = phi
    f_name = F_at
    coupled_variables = "c phi"
  []""", 1)
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % xmax, 1)
    s = s.replace("nx = 1200", "nx = %d" % nx, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % tend, 1)
    s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(PROBES) + "\n", s, count=1)
    assert out != s, "probes"
    s = out
    vp = ("[VectorPostprocessors]\n  [line]\n    type = LineValueSampler\n"
          "    variable = 'c phi'\n    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n    num_points = %d\n    sort_by = x\n"
          "    outputs = lineonly\n  []\n[]\n" % (xmax, lvs_n))
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    o = ("[Outputs]\n  csv = true\n  [lineonly]\n    type = CSV\n"
         "    execute_on = FINAL\n    file_base = profile\n  []\n[]")
    assert "[Outputs]\n  csv = true\n[]" in s
    s = s.replace("[Outputs]\n  csv = true\n[]", o, 1)
    # production-style units => |R0| ~ 1e-9 ; nl_abs_tol must be ~1e-3 |R0| (handoff rule)
    # energy normalisation 1e9 makes |R0| = O(1); automatic_scaling additionally makes the
    # absolute tolerances robust w.r.t. the cell measure (|R0| ~ dx^dim) -- this is what makes
    # dim>=2 cases actually solve instead of fake-converging at 0 iterations.
    return s


if __name__ == "__main__":
    io.open(HERE + "/_quad.i", "w", encoding="utf-8").write(
        make_input(1.2e-5, 2400, 1.0e-4, "2.0e-7", "2.04", 400))
    print("ok")