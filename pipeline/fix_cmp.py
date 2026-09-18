import re

def diag_block(cls, prop):
    return (f"  [I_{prop}]\n"
            f"    type = {cls}\n"
            f"    mat_prop = {prop}\n"
            f"    execute_on = 'initial'\n"
            f"  []\n")

for src, cls in (("base_ad", "ADElementIntegralMaterialProperty"),
                 ("base_nonad", "ElementIntegralMaterialProperty")):
    p = f"/root/work/cmp_mat/{src}/x.i"
    s = open(p, encoding="utf-8").read()
    # 删掉上次插入的四个后处理（无论哪种类型）
    for prop in ("kappa_op", "gamma_asymm", "L", "align4"):
        s = re.sub(rf"\n  \[I_{prop}\]\n.*?\n  \[\]\n", "\n", s, flags=re.S)
    blk = "".join(diag_block(cls, p_) for p_ in ("kappa_op", "gamma_asymm", "L", "align4"))
    i = s.index("\n[Postprocessors]\n") + len("\n[Postprocessors]\n")
    s = s[:i] + blk + s[i:]
    open(p, "w", encoding="utf-8").write(s)
    print(f"  {src}: {cls}")
