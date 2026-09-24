import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("        m = 10\n", "        m = 3          # 余量 3 个粗胞 = 18 um（太大则熔池在视口里占比过小）\n", 1)
s = s.replace("熔池 + 30um 余量", "熔池 + 18um 余量", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched margin -> 3 cells")