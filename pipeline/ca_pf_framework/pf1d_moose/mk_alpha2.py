import io
s = io.open("p1c_alpha.i", encoding="utf-8").read()
# 1) 迁移率改成相依赖 (固/液区分), 与生产同构
old = chr(34) + "DL*Vm*c*(1-c)/(R*T)" + chr(34)
new = chr(34) + "(DS+(DL-DS)*(1-phi))*Vm*c*(1-c)/(R*T)" + chr(34)
assert old in s; s = s.replace(old, new, 1)
s = s.replace(chr(34) + "DL R Vm" + chr(34), chr(34) + "DL DS R Vm" + chr(34), 1)
s = s.replace(chr(34) + "9.5e-9 8.314 1.1345e-5" + chr(34), chr(34) + "9.5e-9 5.0e-13 8.314 1.1345e-5" + chr(34), 1)
s = s.replace(chr(34) + "c T" + chr(34), chr(34) + "c phi T" + chr(34), 1)
# 2) 探针改到固相区（界面扫过之后）+ 保留界面正前方两个
old2 = s[s.index("[Postprocessors]"):s.index("[Executioner]")]
new2 = chr(10).join([
 "[Postprocessors]",
 "  [c_1000]",
 "    type = PointValue",
 "    variable = c",
 "    point = \"1.00e-6 0 0\"",
 "  []",
 "  [c_1100]",
 "    type = PointValue",
 "    variable = c",
 "    point = \"1.10e-6 0 0\"",
 "  []",
 "  [c_1200]",
 "    type = PointValue",
 "    variable = c",
 "    point = \"1.20e-6 0 0\"",
 "  []",
 "  [c_1700]",
 "    type = PointValue",
 "    variable = c",
 "    point = \"1.70e-6 0 0\"",
 "  []",
 "  [c_2000]",
 "    type = PointValue",
 "    variable = c",
 "    point = \"2.00e-6 0 0\"",
 "  []",
 "[]",
 "",
 "",
])
s = s.replace(old2, new2, 1)
io.open("p1c_alpha2.i", "w", encoding="utf-8").write(s)
print("written p1c_alpha2.i")
