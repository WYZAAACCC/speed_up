import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
# 晶粒体积用抽稀版（快）；晶界保持全分辨率
s = s.replace("        if grain_voxels:\n", "        if grain_voxels:\n", 1)
s = s.replace("            gd = g[:, ::2, ::2]", "            gd = g[::3, ::3, ::3]", 1)
s = s.replace("        panel(ax, g, dx, ng, cmap, norm, view)", "        panel(ax, g, dx, ng, cmap, norm, view, grain_voxels=False)", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched")