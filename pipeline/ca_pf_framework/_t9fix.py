import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("        exs.append(ca.excess_per_volume())",
              "        # QoI 必须是【局部】量: per-volume 的总量会被域尺寸稀释（按构造随域变）\n"
              "        exs.append(float(ca.c.max()))", 1)
s = s.replace('chk("T9 横向域放大时过量溶质收敛",',
              'chk("T9 横向域放大时【晶界旁峰值富集】收敛",', 1)
s = s.replace('        "e_V = {} ; 与最大域的相对偏差 {}".format(\n            " ".join("{:.4e}".format(x) for x in exs),\n            " ".join("{:.3e}".format(x) for x in rel)),',
              '        "c_max = {} ; 与最大域的相对偏差 {}".format(\n            " ".join("{:.6f}".format(x) for x in exs),\n            " ".join("{:.3e}".format(x) for x in rel)),', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched T9 QoI")