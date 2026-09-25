import io
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
s = io.open(H + "/p1c_alpha2.i", encoding="utf-8").read()
# (1) κ_c: 0 -> 1e-14（与生产一致；w_c = sqrt(κ_c/f'') = 0.105 µm）
old_k = "  [kappa_c]\n    type = GenericConstantMaterial\n    prop_names = kappa_c\n    prop_values = 0.0\n  []"
assert old_k in s, "kappa_c 块没匹配上"
s = s.replace(old_k, old_k.replace("prop_values = 0.0", "prop_values = 1.0e-14"), 1)
# (2) F_at 的宽度因子：W -> w_c = 1.05e-7（字面量，避免与驱动器替换 constants 冲突）
old_f = "expression = \"ALPHA*W*(1-k_eq)*c*(1-phi)\""
assert old_f in s
s = s.replace(old_f, "expression = \"ALPHA*1.05e-7*(1-k_eq)*c*(1-phi)\"", 1)
s = s.replace("# P1-c:", "# P1-c (kappa_c=1e-14, F_at ∝ w_c 而非 W):", 1)
io.open(H + "/p1c_kcw.i", "w", encoding="utf-8").write(s)
print("wrote p1c_kcw.i  (kappa_c=1e-14, F_at ∝ 1.05e-7*(1-k)c(1-phi))")