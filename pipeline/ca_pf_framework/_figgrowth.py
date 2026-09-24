import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("GB_DARK = 0.32", "GB_DARK = 0.72", 1)
s = s.replace("SHELL_ALPHA = 0.10", "SHELL_ALPHA = 0.09\nSL_COLOR = (0.20, 0.55, 0.95)\nSL_ALPHA = 0.45", 1)
# faces(): 增加"固液界面"类别  kind: 0=域外边界 1=晶界 2=固液界面
s = s.replace("""                shell = (a > 0) & (b == 0)
                gb = (a > 0) & (b > 0) & (b != a)
                for m, is_gb in ((shell, False), (gb, True)):
                    if is_gb and step == +1:
                        continue                     # 晶界面片只从低索引侧出一次，避免 z-fighting
                    if not m.any():
                        continue
                    uu, vv = np.where(m)
                    for t in range(len(uu)):
                        c = _idx(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        P.append(_quad(plane, axis, dx))
                        GI.append(int(g[c])); ISGB.append(is_gb)""",
"""                gb = (a > 0) & (b > 0) & (b != a)
                if gb.any() and step == +1:
                    gb = np.zeros_like(gb)           # 晶界面片只从低索引侧出一次，避免 z-fighting
                if gb.any():
                    uu, vv = np.where(gb)
                    for t in range(len(uu)):
                        c = _idx(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(1)
                sl = (a > 0) & (b == 0)
                if sl.any():
                    uu, vv = np.where(sl)
                    for t in range(len(uu)):
                        c = _idx(axis, i, uu[t], vv[t])
                        plane = list(c); plane[axis] = max(i, j)
                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(2)""", 1)
s = s.replace("    P, GI, ISGB = [], [], []\n", "    P, GI, KIND = [], [], []\n", 1)
s = s.replace("                        GI.append(int(a[uu[t], vv[t]])); ISGB.append(False)",
              "                        GI.append(int(a[uu[t], vv[t]])); KIND.append(0)", 1)
s = s.replace("    return (np.array(P, float), np.array(GI, int), np.array(ISGB, bool))",
              "    return (np.array(P, float), np.array(GI, int), np.array(KIND, int))", 1)
# render(): 用 KIND 上色
s = s.replace("""    P, GI, ISGB = faces(g, dx)
    if gb_only:
        P, GI, ISGB = P[ISGB], GI[ISGB], ISGB[ISGB]""",
"""    P, GI, KIND = faces(g, dx)
    if gb_only:
        m = KIND == 1
        P, GI, KIND = P[m], GI[m], KIND[m]""", 1)
s = s.replace("""        c = cmap(norm(GI[k]))
        if gb_only or ISGB[k]:
            cols.append((c[0] * GB_DARK, c[1] * GB_DARK, c[2] * GB_DARK, 1.0))
        else:
            cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, SHELL_ALPHA))""",
"""        c = cmap(norm(GI[k]))
        if gb_only or KIND[k] == 1:
            cols.append((c[0] * GB_DARK, c[1] * GB_DARK, c[2] * GB_DARK, 1.0))
        elif KIND[k] == 2:
            cols.append((SL_COLOR[0], SL_COLOR[1], SL_COLOR[2], SL_ALPHA))
        else:
            cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, SHELL_ALPHA))""", 1)
# 新增：生长过程三维序列
s = s.replace("def main():", '''def growth_3d(snaps, ts, dx, cmap, norm):
    """生长过程三维序列：每帧 = 域壳 + 晶界(实心深色) + 固液界面(浅蓝)"""
    n = len(snaps)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.4 * ncol, 4.6 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for k in range(n):
        g = snaps[k][::DOWN, ::DOWN, ::DOWN]
        P, GI, KIND = faces(g, dx)
        e, a = np.radians(22.0), np.radians(-58.0)
        d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
        up = np.array([0.0, 0.0, 1.0])
        right = np.cross(d, up); right /= np.linalg.norm(right)
        up2 = np.cross(right, d)
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
                cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, SHELL_ALPHA))
            polys.append(list(zip(sx[q], sy[q])))
        ax = axes[k]
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="none", linewidths=0))
        ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")
        liq = float((snaps[k] == 0).sum()) / float(snaps[k].size)
        ax.set_title("t = {:.2e} s   液相占比 {:.1f}%".format(ts[k], 100 * liq), fontsize=11)
    for k in range(n, len(axes)):
        axes[k].axis("off")
    fig.suptitle("熔池底部外延生长【过程】三维序列：晶界(实心深色) + 固液界面(浅蓝)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(HERE, "FIG_meltpool_growth_3d.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("saved", p)


def main():''', 1)
s = s.replace('''    render(os.path.join(HERE, "FIG_meltpool_gb_network_3d.png"), g, dx, cmap, norm, elev=22,
           azim=-58, gb_only=True,
           title="晶界网络单独视图（相邻晶粒的共享面片，按晶粒身份着色）")''',
'''    render(os.path.join(HERE, "FIG_meltpool_gb_network_3d.png"), g, dx, cmap, norm, elev=22,
           azim=-58, gb_only=True,
           title="晶界网络单独视图（相邻晶粒的共享面片，按晶粒身份着色）")
    d2 = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    if "snaps" in d2:
        growth_3d(d2["snaps"], d2["snap_t"], dx, cmap, norm)''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched fig script (kind + growth_3d)")