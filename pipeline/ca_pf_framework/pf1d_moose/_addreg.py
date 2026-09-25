# -*- coding: utf-8 -*-
import io, math, re
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/mk_phys.py"
s = io.open(P, encoding="utf-8").read()
if "REG_F_TMPL" in s:
    print("already patched"); raise SystemExit
hdr = '''# ---- C1/C2 parabolic regularisation of g(c) = c ln c + (1-c) ln(1-c) ----
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
'''
s = s.replace("import io, re", "import io, math, re", 1)
anchor = "def probes_block(xs):"
assert anchor in s
s = s.replace(anchor, hdr + "\n\n" + anchor, 1)
old_tail = '    return s.replace("[Outputs]\\n  csv = true\\n[]", o, 1)'
new_tail = ('    s = s.replace("[Outputs]\\n  csv = true\\n[]", o, 1)\n'
            '    s2 = re.sub(r"(?ms)^  \\[f_loc\\]\\n.*?\\n  \\[\\]\\n", REG_F, s, count=1)\n'
            '    assert s2 != s, "f_loc block not replaced"\n'
            '    s = s2\n'
            '    s2 = re.sub(r"(?ms)^  \\[M_mob\\]\\n.*?\\n  \\[\\]\\n", REG_M, s, count=1)\n'
            '    assert s2 != s, "M_mob block not replaced"\n'
            '    return s2')
assert old_tail in s, "tail anchor"
s = s.replace(old_tail, new_tail, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched mk_phys.py")