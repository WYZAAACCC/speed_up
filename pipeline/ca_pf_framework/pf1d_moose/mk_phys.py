# -*- coding: utf-8 -*-
# Physically correct antitrapping susceptibility (Plapp PRE 84, 031601 Eq.102;
# Echebarria, Folch, Karma, Plapp, PRE 70, 061604 (2004)):
#     j_at = -a W (c_l - c_s) (dphi/dt) grad(phi)/|grad(phi)|
# MOOSE's AntitrappingCurrent realizes  j_at = F (grad v/|grad v|) dv/dt,  so
#     F = a W [ c_l(mu) - c_s(mu) ]      (POSITIVE)
# Both phase compositions follow in closed form from our own f_loc:
#   mu = RT/Vm ln(c/(1-c)) + h dg/Vm,  h = 3phi^2-2phi^3,  dg = dgB + dHf(1-T/Tm)
#   c_l = 1/(1 + ((1-c)/c) exp(-h dg/(RT)))      c_s = 1/(1 + ((1-c)/c) exp((1-h) dg/(RT)))
import io, math, re

HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BASE = HERE + "/p1c_alpha2.i"
PROBES = [4.0e-6, 6.0e-6, 8.0e-6]
# Echebarria's general a(phi) = [h(phi)-1][1-q(phi)]/[sqrt2 (phi^2-1)] evaluated with
# OUR h = 3phi^2-2phi^3 and OUR q = 1-phi  ->  a(phi) = (1-phi)(2phi+1)/(2 sqrt2)
AXPR = "(1-phi)*(2*phi+1)/(2*sqrt(2))"
A_LIT = "0.35355339059327373"          # 1/(2 sqrt 2)

H = "(3*phi^2-2*phi^3)"
DG = "(dgB+dHf*(1-T/Tm))"
CO = "((1-max(c,C1))/max(c,C1))"   # clip c so that (1-c)/c can never blow up in a trial state
CL = "(1/(1+" + CO + "*exp(-" + H + "*" + DG + "/(R*T))))"
CS = "(1/(1+" + CO + "*exp((1-" + H + ")*" + DG + "/(R*T))))"
DC = "(" + CL + "-" + CS + ")"

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


# ---- C1/C2 parabolic regularisation of g(c) = c ln c + (1-c) ln(1-c) ----
#   copied in spirit from pipeline/gibbs/prod3d/make_gibbs3d.py: for c < C1 (and c > C2)
#   replace g by the parabola matching g, g-prime, g-double-prime at the joint.
#   => C^1 + C^2, no jump, g-double-prime > 0 by construction so f_cc > 0 / M > 0.
#   C1 must sit clearly BELOW the physical minimum of c; our c_min ~ 0.01 => C1 = 1e-3.
C1 = 1.0e-3
C2 = 9.5e-1
G1 = C1 * math.log(C1) + (1.0 - C1) * math.log(1.0 - C1)
GP1 = math.log(C1) - math.log(1.0 - C1)
GPP1 = 1.0 / C1 + 1.0 / (1.0 - C1)
G2 = C2 * math.log(C2) + (1.0 - C2) * math.log(1.0 - C2)
GP2 = math.log(C2) - math.log(1.0 - C2)
GPP2 = 1.0 / C2 + 1.0 / (1.0 - C2)
G_EXPR = ("if(c<C1, G1+GP1*(c-C1)+0.5*GPP1*(c-C1)^2, "
          "if(c>C2, G2+GP2*(c-C2)+0.5*GPP2*(c-C2)^2, "
          "c*log(c)+(1-c)*log(1-c)))")
GPP_EXPR = "if(c<C1, GPP1, if(c>C2, GPP2, 1/c+1/(1-c)))"
REG_F_TMPL = """  [f_loc]
    type = DerivativeParsedMaterial
    property_name = f_loc
    coupled_variables = "c phi T"
    constant_names = "R Vm dgB dHf Tm C1 C2 G1 GP1 GPP1 G2 GP2 GPP2"
    constant_expressions = "8.314 1.1345e-5 7334 14150 1941 %C1% %C2% %G1% %GP1% %GPP1% %G2% %GP2% %GPP2%"
    expression = "R*T/Vm*(%G_EXPR%) + (3*phi^2-2*phi^3)*(dgB+dHf*(1-T/Tm))*c/Vm"
    derivative_order = 2
  []
"""
REG_M_TMPL = """  [M_mob]
    type = DerivativeParsedMaterial
    property_name = M
    coupled_variables = "c phi T"
    constant_names = "DL DS R Vm C1 C2 GPP1 GPP2"
    constant_expressions = "9.5e-9 5.0e-13 8.314 1.1345e-5 %C1% %C2% %GPP1% %GPP2%"
    expression = "(DS+(DL-DS)*(1-phi))*Vm/(R*T*(%GPP_EXPR%))"
    derivative_order = 1
  []
"""
def _fill(t):
    return (t.replace("%C1%", "%.10e" % C1).replace("%C2%", "%.10e" % C2)
             .replace("%G1%", "%.10e" % G1).replace("%GP1%", "%.10e" % GP1)
             .replace("%GPP1%", "%.10e" % GPP1).replace("%G2%", "%.10e" % G2)
             .replace("%GP2%", "%.10e" % GP2).replace("%GPP2%", "%.10e" % GPP2)
             .replace("%G_EXPR%", G_EXPR).replace("%GPP_EXPR%", GPP_EXPR))
REG_F = _fill(REG_F_TMPL)
REG_M = _fill(REG_M_TMPL)


def probes_block(xs):
    L = ["[Postprocessors]"]
    for i, x in enumerate(xs):
        L += ["  [c_p%d]" % i, "    type = PointValue", "    variable = c",
              "    point = \"%.6e 0 0\"" % x, "  []"]
    L += ["[]"]
    return "\n".join(L)


def make_input(xmax, nx, tend, Wv, aform, lvs_n):
    s = io.open(BASE, encoding="utf-8").read()
    assert OLD_MAT in s and OLD_K in s, "anchor missing"
    if aform == "aphiform":
        aexpr = AXPR
        cname, cval = "W R dgB dHf Tm C1", "%s 8.314 7334 14150 1941 1.0e-3" % Wv
    else:
        aexpr = "A_AT"
        cname = "A_AT W R dgB dHf Tm C1"
        cval = "%s %s 8.314 7334 14150 1941 1.0e-3" % (aform, Wv)
    newmat = ("  [at_susc]\n    type = DerivativeParsedMaterial\n"
              "    property_name = F_at\n"
              "    coupled_variables = \"c phi T w\"\n"
              "    constant_names = \"" + cname + "\"\n"
              "    constant_expressions = \"" + cval + "\"\n"
              "    expression = \"" + aexpr + "*W*" + DC + " + 0*w\"\n"
              "    derivative_order = 1\n  []")
    newk = ("  [antitrap]\n    type = AntitrappingCurrent\n    variable = w\n"
            "    v = phi\n    f_name = F_at\n    coupled_variables = \"c phi T\"\n  []")
    s = s.replace(OLD_MAT, newmat, 1).replace(OLD_K, newk, 1)
    s = s.replace("xmax = 2.4e-6", "xmax = %.4e" % xmax, 1)
    s = s.replace("nx = 1200", "nx = %d" % nx, 1)
    s = s.replace("end_time = 1.4e-5", "end_time = %.4e" % tend, 1)
    s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    out = re.sub(r"(?ms)^\[Postprocessors\]\n.*?\n\[\]\n", probes_block(PROBES) + "\n", s, count=1)
    assert out != s, "probes not replaced"
    s = out
    vp = ("[VectorPostprocessors]\n  [line]\n    type = LineValueSampler\n"
          "    variable = 'c phi'\n    start_point = '0 0 0'\n"
          "    end_point = '%.6e 0 0'\n    num_points = %d\n    sort_by = x\n"
          "    outputs = lineonly\n  []\n[]\n" % (xmax, lvs_n))
    s = s.replace("[Executioner]", vp + "\n[Executioner]", 1)
    o = ("[Outputs]\n  csv = true\n  [lineonly]\n    type = CSV\n"
         "    execute_on = FINAL\n    file_base = profile\n  []\n[]")
    assert "[Outputs]\n  csv = true\n[]" in s, "outputs anchor missing"
    s = s.replace("[Outputs]\n  csv = true\n[]", o, 1)
    s2 = re.sub(r"(?ms)^  \[f_loc\]\n.*?\n  \[\]\n", REG_F, s, count=1)
    assert s2 != s, "f_loc block not replaced"
    s = s2
    s2 = re.sub(r"(?ms)^  \[M_mob\]\n.*?\n  \[\]\n", REG_M, s, count=1)
    assert s2 != s, "M_mob block not replaced"
    return s2


if __name__ == "__main__":
    io.open(HERE + "/_pp.i", "w", encoding="utf-8").write(
        make_input(1.2e-5, 2400, 1.0e-4, "2.0e-7", "aphiform", 400))
    print("DC len", len(DC))