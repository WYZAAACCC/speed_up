import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
i0 = s.index("def growth_3d(")
i1 = s.index("def main():")
new = '''def growth_3d(snaps, ts, dx, cmap, norm, crop=None, elev=22.0, azim=-58.0):
    """生长过程三维序列。视口可裁到熔池附近；剔除朝向相机的近侧壳面（切开看内部）。"""
    n = len(snaps); ncol = 3; nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.6 * ncol, 4.8 * nrow))
    axes = np.atleast_1d(axes).ravel()
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(d, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, d)
    for k in range(n):
        g = snaps[k][::DOWN, ::DOWN, ::DOWN]
        if crop is not None:
            (z0, z1), (y0, y1), (x0, x1) = crop
            g = g[x0:x1, y0:y1, z0:z1]
        P, GI, KIND, NRM = faces(g, dx)
        keep = ~((KIND == 0) & ((NRM @ d) > 1e-9))
        P, GI, KIND, NRM = P[keep], GI[keep], KIND[keep], NRM[keep]
        flat = P.reshape(-1, 3)
        sx = (flat @ right).reshape(-1, 4); sy = (flat @ up2).reshape(-1, 4)
        dep = (flat @ d).reshape(-1, 4).mean(axis=1)
        order = np.argsort(dep)
        polys, cols = [], []
        for q in order:
            c = cmap(norm(GI[q]))
            if KIND[q] == 1:
                cols.append((c[0] * GB_DARK, c[1] * GB_DARK, c[2] * GB_DARK, 1.0))
            elif KIND[q] == 2:
                cols.append((SL_COLOR[0], SL_COLOR[1], SL_COLOR[2], SL_ALPHA))
            else:
                cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, 0.30))
            polys.append(list(zip(sx[q], sy[q])))
        ax = axes[k]
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="none", linewidths=0))
        ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
        liq = float((g == 0).sum()) / float(g.size)
        ax.set_title("t = {:.2e} s   液相占【视口】{:.1f}%".format(ts[k], 100 * liq), fontsize=11)
    for k in range(n, len(axes)):
        axes[k].axis("off")
    fig.suptitle("熔池底部外延生长【过程】三维序列（已裁到熔池附近；剔近侧壳面以看内部）："
                 "蓝色=液态熔池，彩色实心面=晶界", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(HERE, "FIG_meltpool_growth_3d.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("saved", p)


'''
s = s[:i0] + new + s[i1:]
# main(): 计算裁剪框（熔池 + 30um 余量）
s = s.replace('''    print("网格 {} (抽稀 {}x, 胞 {:.0f} um)  晶粒 {} 个".format(g.shape, DOWN, dx * 1e6, ng))''',
'''    print("网格 {} (抽稀 {}x, 胞 {:.0f} um)  晶粒 {} 个".format(g.shape, DOWN, dx * 1e6, ng))
    d0 = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    crop = None
    if "snaps" in d0:
        s0 = d0["snaps"][0][::DOWN, ::DOWN, ::DOWN]
        ii, jj, kk = np.where(s0 == 0)
        m = 10
        nx, ny, nz = s0.shape
        crop = ((max(0, kk.min() - m), min(nz, kk.max() + 1 + m)),
                (max(0, jj.min() - m), min(ny, jj.max() + 1 + m)),
                (max(0, ii.min() - m), min(nx, ii.max() + 1 + m)))
        box = (crop[2][1] - crop[2][0]) * dx * 1e6, (crop[1][1] - crop[1][0]) * dx * 1e6, \\
              (crop[0][1] - crop[0][0]) * dx * 1e6
        vf = float((s0 == 0).sum()) / float((crop[2][1]-crop[2][0])*(crop[1][1]-crop[1][0])*(crop[0][1]-crop[0][0]))
        print("裁剪框 = {:.0f} x {:.0f} x {:.0f} um（熔池 + 30um 余量）; 其中首帧液相占 {:.1f}%".format(
            box[0], box[1], box[2], 100 * vf))''', 1)
s = s.replace('''    render(os.path.join(HERE, "FIG_meltpool_final_3d.png"), g, dx, cmap, norm, elev=22, azim=-58,
           title="熔池底部外延生长：三维 prior-beta 晶粒（壳半透明）+ 晶界（实心深色面片）")''',
'''    render(os.path.join(HERE, "FIG_meltpool_final_3d.png"), g, dx, cmap, norm, elev=22, azim=-58,
           crop=crop, shell_alpha=0.34,
           title="最终三维：prior-beta 晶粒（壳半透明，按 gid 着色）+ 晶界（实心面片）；已切开近侧壳面")''', 1)
s = s.replace('''        growth_3d(d2["snaps"], d2["snap_t"], dx, cmap, norm)''',
              '''        growth_3d(d2["snaps"], d2["snap_t"], dx, cmap, norm, crop=crop)''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched main + growth_3d (crop)")