# -*- coding: utf-8 -*-
import io
p = r"F:\speed_up\pipeline\gibbs\validated\pf3grain_mercedes.i"
t = open(p, encoding="utf-8", newline="").read()
out = []
n = 0
for ln in t.split("\n"):
    if " & " in ln and ("combinatorial_geometry" in ln or "expression = 'if(" in ln):
        s = ln.replace(" & ", ") & (")
        if "combinatorial_geometry = '" in s:
            s = s.replace("combinatorial_geometry = '", "combinatorial_geometry = '((", 1)
            # 结尾的 ' 之前补两个右括号
            s = s.rstrip()
            assert s.endswith("'"), s
            s = s[:-1] + "))'"
        else:
            s = s.replace("expression = 'if(", "expression = 'if((", 1)
            s = s.replace(", 1, 0)'", "), 1, 0)'")
        n += 1
        out.append(s)
    else:
        out.append(ln)
open(p, "w", encoding="utf-8", newline="").write("\n".join(out))
print("改写表达式条数 =", n)