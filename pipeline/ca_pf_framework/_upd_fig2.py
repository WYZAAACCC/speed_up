import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_pool_grains_3d_v2.py"
s = io.open(P, encoding="utf-8").read()

# 1) 面板⑤ 用"池内最大的两个晶粒"的动态 pair
old = '''    add("⑤ 只用 gid5|gid6 之间的那张晶界面（不剖切，看整张面）",
        keep_pool, False, True, (5, 6), {k: GB_56 for k in GCOL}, 26, -48)'''
new = '''    top2 = sorted(frac, key=lambda k: -frac[k])[:2]
    if len(top2) == 2:
        p2 = (min(top2), max(top2))
        add("⑤ 只用 gid%d|gid%d 之间的那张晶界面（不剖切，看整张面）" % p2,
            keep_pool, False, True, p2, {k: GB_56 for k in GCOL}, 26, -48)
    else:
        add("⑤ （池内只有一个晶粒，无晶界面）", keep_pool, False, True, (1, 2),
            {k: GB_56 for k in GCOL}, 26, -48)'''
if old not in s: print("!! 1"); raise SystemExit(1)
s = s.replace(old, new)

# 2) 图例里 GB_56 的标签也动态化
old = '''    hs.append(plt.Line2D([], [], marker="s", ls="", ms=11, color=GB_56, label="gid5|gid6 界面"))'''
new = '''    if len(top2) == 2:
        hs.append(plt.Line2D([], [], marker="s", ls="", ms=11, color=GB_56,
                             label="gid%d|gid%d 界面" % (min(top2), max(top2))))'''
if old not in s: print("!! 2"); raise SystemExit(1)
s = s.replace(old, new)

# 3) add(): 空面片时画占位文字，不要崩
old = '''        P, gidv, kind, cell, axn = build_faces(g_pad, kp, dx, want_skin, want_gb, pair)
        nrm = face_normals(cell, gidv, axn, GN)'''
new = '''        P, gidv, kind, cell, axn = build_faces(g_pad, kp, dx, want_skin, want_gb, pair)
        if len(P) == 0:
            img = np.ones((H, W, 3), np.float32)
            print("  [%s] 面片 0（该晶界对不存在）-> 占位" % title)
            views.append((title, img))
            return
        nrm = face_normals(cell, gidv, axn, GN)'''
if old not in s: print("!! 3"); raise SystemExit(1)
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8").write(s)
print("fig 脚本已加固")