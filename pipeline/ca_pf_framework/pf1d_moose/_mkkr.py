import io, os
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
s = io.open(H + "/p1c_alpha2.i", encoding="utf-8").read()
old = "expression = \"ALPHA*W*(1-k_eq)*c*(1-phi)\""
assert old in s, "没找到原 F_at 表达式"
# ★ Karma–Rappel / Plapp 形式：Δc 用**局部平衡**的 c_l = c/(1-(1-k)h(phi))，h = 3phi^2-2phi^3；
#   不再额外乘 (1-phi)（KR 的定位来自 dphi/dt*grad(phi)/|grad(phi)| 本身）。
new = "expression = \"ALPHA*W*(1-k_eq)*c/(1-(1-k_eq)*(3*phi^2-2*phi^3))\""
s = s.replace(old, new, 1)
s = s.replace("# P1-c:", "# P1-c (KR/Plapp 形式):", 1)
io.open(H + "/p1c_kr.i", "w", encoding="utf-8").write(s)
print("wrote p1c_kr.i ; F_at 新表达式:", new.split('"')[1])