import io
P = "/mnt/f/speed_up/_mine_mirror.py"
s = io.open(P, encoding="utf-8").read()
# 记录每个基底晶粒/形核晶粒的取向（min_angle 与 +Z）
s = s.replace("""    gg = ca.gid
    ids, cnt = np.unique(gg[gg > 0], return_counts=True)""",
"""    gg = ca.gid
    ids, cnt = np.unique(gg[gg > 0], return_counts=True)""")
s = s.replace("""    return dict(seed=seed, n_grain=len(ids), n_nuke=len(gids_of_nuc), frac_nuke=frac,
                mean_size=float(cnt.mean()), max_size=int(cnt.max()), tot=tot)""",
"""    def mang(g):
        Pm = ca.axes[g]
        c = np.abs(Pm[2, :]) / np.linalg.norm(Pm, axis=0)
        return float(np.degrees(np.arccos(np.clip(c.max(), 0, 1))))
    # 尺寸加权的 min_angle（与 ExaCA 侧同一算法）
    ang = np.array([mang(g) for g in ids])
    w = cnt / cnt.sum()
    nucmask = np.array([g in nucset for g in ids])
    return dict(seed=seed, n_grain=len(ids), n_nuke=len(gids_of_nuc), frac_nuke=frac,
                mean_size=float(cnt.mean()), max_size=int(cnt.max()), tot=tot,
                ang_w=float((ang * w).sum()), ang_simple=float(ang.mean()),
                ang_w_sub=float((ang[~nucmask] * w[~nucmask]).sum() / max(w[~nucmask].sum(), 1e-9)),
                ang_w_nuc=float((ang[nucmask] * w[nucmask]).sum() / max(w[nucmask].sum(), 1e-9))
                if nucmask.any() else None)""")
io.open(P, "w", encoding="utf-8").write(s)
print('patched')