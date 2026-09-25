# -*- coding: utf-8 -*-
# Patch make_gibbs3d.py: replace the ad-hoc antitrapping susceptibility with the
# physically correct Plapp/Echebarria form  F = a W [c_l(mu) - c_s(mu)].
import io, re, shutil, sys

P = "/mnt/f/speed_up/pipeline/gibbs/prod3d/make_gibbs3d.py"
shutil.copyfile(P, P + ".bak_atphys")
s = io.open(P, encoding="utf-8").read()

# ---- (1) AT_ALPHA -> AT_A -------------------------------------------------
old1 = 'AT_ALPHA = float(os.environ.get("AT_ALPHA", "2.0"))'
new1 = '\n'.join([
    '# 【2026-09-23 物理正确化】抗截留系数 a（不再叫 ALPHA：语义已变）',
    '#   F = a * W * [ c_l(mu) - c_s(mu) ]',
    '#   Plapp, PRE 84, 031601 (2011) 式(102); Echebarria/Folch/Karma/Plapp,',
    '#   PRE 70, 061604 (2004) 式 (j_at = -a W (1-k) c_l^0 e^u (dphi/dt) n)',
    '#   Echebarria 对其插值对给出 a = 1/(2 sqrt2) = 0.35355；',
    '#   在本模型形式下的 1D 同构标定值见 ca_pf_framework/P11_SPEC.md §22',
    '#   （W=200 nm 给出 a* ≈ 2.04；W 无关性待确认）。',
    'AT_A = float(os.environ.get("AT_A", os.environ.get("AT_ALPHA", "2.04")))',
])
assert s.count(old1) == 1, "AT_ALPHA anchor"
s = s.replace(old1, new1, 1)

# ---- (2) the at_susc material + the 8 kernels' coupled_variables ----------
pat = re.compile(r"    at = \[\n(?:.*\n)*?    report\.append\(\(\"at_susc\(内联 h_gb\)\", ok\)\)\n")
assert pat.search(s), "at_susc block anchor"
new_block = '''    # 【2026-09-23 物理正确化】抗截留电流 susceptibility（替换掉旧式）
    #   Plapp PRE 84 031601 (2011) 式(102):
    #       j_at = -a W (c_l - c_s) (dphi/dt) grad(phi)/|grad(phi)|
    #   MOOSE 的 AntitrappingCurrent 实现的是  j_at = F (grad v/|grad v|) dv/dt
    #   =>  F = a W [ c_l(mu) - c_s(mu) ]                       （a > 0）
    #   【旧式两处错】
    #     (1) 用 (1-k_eq)*c 当 Delta c 的替身。Delta c 必须由**局部 mu** 解出两相
    #         平衡成分之差：
    #         本分支 f = FREF[(T/TREF) g(c) - (-ln KPART) c (1-h_solid)], g' = ln(c/(1-c))
    #         => mu/FREF = (T/TREF) ln(c/(1-c)) + ln(KPART)(1-h_solid)
    #         => a_s = (c/(1-c)) exp( ln(KPART)(1-h_solid) TREF/T ),  c_s = a_s/(1+a_s)
    #            a_l = a_s exp( -ln(KPART) TREF/T ),                 c_l = a_l/(1+a_l)
    #            Delta c = c_l - c_s
    #         校核：T=TREF 时 a_l/a_s = 1/KPART => c_s/c_l = KPART ✓
    #     (2) W 用了冻结的 2e-6。W 必须是**本模型真实的界面宽** = wGB（见 AT_W）。
    #   门 (1-h_gb)：固液前沿 h_gb = 0 -> 门 = 1（保留）；
    #                固-固晶界 h_gb = 1 -> 门 = 0。
    #     物理理由：Karma-Rappel 电流的前提是"界面两侧存在分配系数"；
    #     固-固晶界 k = 1，该电流在此处无定义（且 h_gb 项对 mu 的贡献会被双重计入）。
    _as_ = "((c/(1-c))*exp(log(KPART)*(1-" + H_SOLID + ")*(TREF/T)))"
    _al_ = "(" + _as_ + "*exp(-log(KPART)*(TREF/T)))"
    _dc_ = "((" + _al_ + "/(1+" + _al_ + "))-(" + _as_ + "/(1+" + _as_ + ")))"
    at = [
        "  [at_susc]",
        "    type = DerivativeParsedMaterial",
        "    property_name = F_at",
        "    block = '%s'" % bulk,
        "    coupled_variables = 'c w T %s'" % ALLETA,
        "    constant_names = 'A_AT W KPART TREF'",
        "    constant_expressions = '%.6g %.6e %.6g %.6e'" % (AT_A, AT_W, KPART, TREF),
        "    expression = 'A_AT*W*" + _dc_ + "*(1-(" + H_GB + ")) + 0*w'",
        "    derivative_order = 2",
        "  []",
    ]
    txt, ok = sub_block(txt, "at_susc", "\\n".join(at))
    report.append(("at_susc(物理正确 aW Delta c)", ok))

    # 8 个抗截留核的 coupled_variables 必须与新 [at_susc] 逐字一致（新增 T）
    for _i in range(8):
        _m = block_of(txt, "gr%d_antitrap" % _i)
        if _m:
            _b, _ok = set_param(_m.group(1), "coupled_variables", "'c T %s'" % ALLETA)
            if _ok:
                txt = txt[:_m.start()] + _b + txt[_m.end():]
            report.append(("at kernel gr%d cv+T" % _i, _ok))
'''
s = pat.sub(lambda m: new_block, s, count=1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched, new length", len(s))