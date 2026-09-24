import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
# 1) faces(): 增加面法向输出
s = s.replace("    P, GI, KIND = [], [], []", "    P, GI, KIND, NRM = [], [], [], []", 1)
s = s.replace("                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(1)",
              "                        nv = [0.0, 0.0, 0.0]\n"
              "                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(1); NRM.append(nv)", 1)
s = s.replace("                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(2)",
              "                        nv = [0.0, 0.0, 0.0]\n"
              "                        P.append(_quad(plane, axis, dx)); GI.append(int(g[c])); KIND.append(2); NRM.append(nv)", 1)
s = s.replace("                        GI.append(int(a[uu[t], vv[t]])); KIND.append(0)",
              "                        nv = [0.0, 0.0, 0.0]\n"
              "                        nv[axis] = -1.0 if plane_at == 0 else 1.0\n"
              "                        GI.append(int(a[uu[t], vv[t]])); KIND.append(0); NRM.append(nv)", 1)
s = s.replace("    return (np.array(P, float), np.array(GI, int), np.array(KIND, int))",
              "    return (np.array(P, float), np.array(GI, int), np.array(KIND, int),\n"
              "            np.array(NRM, float))", 1)
# 2) render(): 加 crop / 背面剔除 / alpha / legend
s = s.replace("""def render(fname, g, dx, cmap, norm, elev=22.0, azim=-58.0, gb_only=False,
           title="", figsize=(9.2, 7.4), dpi=160):
    P, GI, KIND = faces(g, dx)
    if gb_only:
        m = KIND == 1
        P, GI, KIND = P[m], GI[m], KIND[m]""",
"""def render(fname, g, dx, cmap, norm, elev=22.0, azim=-58.0, gb_only=False,
           title="", figsize=(9.2, 7.4), dpi=160, crop=None, cull_front=True,
           legend=True, shell_alpha=SHELL_ALPHA):
    g0 = g
    if crop is not None:
        (z0, z1), (y0, y1), (x0, x1) = crop
        g = g[x0:x1, y0:y1, z0:z1]
    P, GI, KIND, NRM = faces(g, dx)
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    if cull_front:
        front = (NRM @ d) > 1e-9
        keep = ~((KIND == 0) & front)
        P, GI, KIND, NRM = P[keep], GI[keep], KIND[keep], NRM[keep]
    if gb_only:
        m = KIND == 1
        P, GI, KIND, NRM = P[m], GI[m], KIND[m], NRM[m]""", 1)
s = s.replace("            cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, SHELL_ALPHA))",
              "            cols.append((c[0] * SH_SIDE, c[1] * SH_SIDE, c[2] * SH_SIDE, shell_alpha))", 1)
s = s.replace('''    if title:
        ax.set_title(title, fontsize=12)
    fig.tight_layout(); fig.savefig(fname, dpi=dpi); plt.close(fig)''',
'''    if title:
        ax.set_title(title, fontsize=12)
    if legend and not gb_only:
        from matplotlib.patches import Patch
        ng_ = int(g0.max())
        tot = float((g0 > 0).sum())
        hs = []
        for gid in range(1, ng_ + 1):
            frac = 100.0 * float((g0 == gid).sum()) / tot
            hs.append(Patch(facecolor=cmap(norm(gid)),
                            label="gid %d   %4.2f%%" % (gid, frac)))
        ax.legend(handles=hs, loc="upper left", fontsize=9, framealpha=0.85,
                  title="晶粒（体积占比）")
    fig.tight_layout(); fig.savefig(fname, dpi=dpi); plt.close(fig)''', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched render: crop + cull + legend")