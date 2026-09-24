import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_wc_cet.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("    G = 5.0e5\n", "    G = 1.0e6\n", 1)
s = s.replace('    bulk = (12.0, 4.0, 4.0e15)      # (dT_mean, dT_sigma, N_max)  [A] 演示参数',
              '    bulk = (14.0, 4.0, 2.0e14)      # (dT_mean, dT_sigma, N_max)  [A] 演示参数', 1)
s = s.replace("        ca = CA3DSolute(40, 40, 52, dx, irf=irf, seed=seed,",
              "        ca = CA3DSolute(40, 40, 72, dx, irf=irf, seed=seed,", 1)
s = s.replace("    nst = 240\n    bulk = (14.0", "    nst = 300\n    bulk = (14.0", 1)
s = s.replace('"最高种子层: thermal k={} vs constitutional k={} (域高 {} 层)".format(\n            A["zmax"], B["zmax"], 52), B["zmax"])',
              '"最高种子层: thermal k={} vs constitutional k={} (域高 {} 层)".format(\n            A["zmax"], B["zmax"], 72), B["zmax"])', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("retuned T7")