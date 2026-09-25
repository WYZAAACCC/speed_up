import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose/mk_phys.py"
s = io.open(P, encoding="utf-8").read()
old_co = 'CO = "((1-c)/c)"'
new_co = 'CO = "((1-max(c,C1))/max(c,C1))"   # clip c so that (1-c)/c can never blow up in a trial state'
assert old_co in s, "CO anchor"
s = s.replace(old_co, new_co, 1)
old_cn = '''        aexpr = "A_AT"
        cname = "A_AT W R dgB dHf Tm"
        cval = "%s %s 8.314 7334 14150 1941" % (aform, Wv)'''
new_cn = '''        aexpr = "A_AT"
        cname = "A_AT W R dgB dHf Tm C1"
        cval = "%s %s 8.314 7334 14150 1941 1.0e-3" % (aform, Wv)'''
assert old_cn in s, "const anchor 1"
s = s.replace(old_cn, new_cn, 1)
old_cn2 = '''        aexpr = AXPR
        cname, cval = "W R dgB dHf Tm", "%s 8.314 7334 14150 1941" % Wv'''
new_cn2 = '''        aexpr = AXPR
        cname, cval = "W R dgB dHf Tm C1", "%s 8.314 7334 14150 1941 1.0e-3" % Wv'''
assert old_cn2 in s, "const anchor 2"
s = s.replace(old_cn2, new_cn2, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")