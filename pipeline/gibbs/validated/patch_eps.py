import re, sys
p = r"F:\speed_up\pipeline\gibbs\stage1_meltpool_gibbs.i"
t = open(p, encoding="utf-8", newline="").read()
HGB = "8*((gr0^2+gr1^2+gr2^2+gr3^2+gr4^2+gr5^2+gr6^2+gr7^2)^2 - (gr0^4+gr1^4+gr2^4+gr3^4+gr4^4+gr5^4+gr6^4+gr7^4))"
EPS = 1e-6
# 只在追加的 6 个 Gibbs 速率材料里，把 h_gb 换成 (h_gb + eps)
names = ["hgb_katt_As", "hgb_katt", "neg_hgb_katt", "shape_hgb_katt", "neg_shape_hgb_katt_As"]
pat = re.compile(r"(^[ \t]*\[(\w+)\](?:.*?))\n[ \t]*\[\]", re.S | re.M)
count = 0
def repl(m):
    global count
    blk, name = m.group(1), m.group(2)
    if name not in names:
        return m.group(0)
    b2 = blk.replace(HGB + ")^2", "(" + HGB + ")*((" + HGB + ")+%g))" % EPS)
    if b2 == blk:
        b2 = blk.replace(HGB, "((" + HGB + ")+%g)" % EPS)
    count += 1
    return b2 + "\n  []"
t2 = pat.sub(repl, t)
print("改写材料数 =", count)
# 加一条说明
t2 = t2.replace("  [shape]\n", "  # ⚠ 正则化：h_gb=0 处 Gam 方程会退化成 dGam/dt=0（零行 ⇒ LU breakdown）。\n"
                             "  #   全部速率材料里把 h_gb 换成 (h_gb + 1e-6)：物理上可忽略（<1e-5 相对），\n"
                             "  #   但让方程在全域良定。shape 仍用纯 h_gb ⇒ 体相源保持局域。\n  [shape]\n", 1)
open(p, "w", encoding="utf-8", newline="").write(t2)
print("done")