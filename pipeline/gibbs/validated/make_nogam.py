import re, sys
src = r"F:\speed_up\pipeline\gibbs\stage1_meltpool_gibbs.i"
dst = r"F:\speed_up\pipeline\gibbs\stage1_meltpool_nogam.i"
t = open(src, encoding="utf-8", newline="").read()
drop = ["Gam", "c_src_c", "c_src_gam", "gam_dt", "gam_eq", "gam_relax",
        "shape", "hgb_katt_As", "hgb_katt", "neg_hgb_katt",
        "shape_hgb_katt", "neg_shape_hgb_katt_As", "gam_max"]
pat = re.compile(r"^[ \t]*\[(\w+)\](?:.*?)\n[ \t]*\[\]\n?", re.S | re.M)
removed = []
def rep(m):
    if m.group(1) in drop:
        removed.append(m.group(1))
        return ""
    return m.group(0)
t2 = pat.sub(rep, t)
# f_loc / M 里对 Gam 的耦合已随之消失，但自由能注释里提到 Gam 无妨
print("摘掉的块:", sorted(set(removed)))
open(dst, "w", encoding="utf-8", newline="").write(t2)
print("行数 %d -> %d" % (t.count("\n"), t2.count("\n")))
# 自检：不应再出现 Gam 作为变量
for bad in ["[Gam]", "variable = Gam", "v = Gam"]:
    if bad in t2:
        print("  ⚠ 残留:", bad)