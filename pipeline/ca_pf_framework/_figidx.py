import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
if "# 统一用【索引单位】" in s:
    print("already"); raise SystemExit
# 面片也用索引单位
s = s.replace("        polys.append(quad_pts(c, axis, ds))", "        polys.append(quad_pts(c, axis, 1.0))   # 索引单位", 1)
# 轴范围用索引
s = s.replace("    ax.set_xlim(0, nx * ds * 1e6); ax.set_ylim(0, ny * ds * 1e6); ax.set_zlim(0, nz * ds * 1e6)",
              "    # 统一用【索引单位】（voxels 只能放在整数格点上），刻度另标 um\n"
              "    ax.set_xlim(0, nx); ax.set_ylim(0, ny); ax.set_zlim(0, nz)", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched to index units")