import io
P = "/mnt/f/speed_up/_mine_mirror.py"
s = io.open(P, encoding="utf-8").read()
# 1) 基底位点改成 ExaCA 的连续均匀分布（允许落在同一胞）
s = s.replace("""    nsub = int(round(SUBN * N * N))
    cells = rng.choice(N * N, size=nsub, replace=False)
    seed_gids = []
    for c in cells:
        i, j = int(c // N), int(c % N)
        Pp = VECS[rng.integers(len(VECS))]
        seed_gids.append(ca.add_grain(i, j, 0, quat=quat_from_P(Pp)))""",
"""    nsub = int(round(SUBN * N * N))
    seed_gids = []
    for _ in range(nsub):
        # ExaCA: 连续均匀分布再取整 => 允许两个位点落在同一个胞（它自己的注释也承认会低估密度）
        x = rng.uniform(-0.49999, N - 0.5); y = rng.uniform(-0.49999, N - 0.5)
        i = int(min(max(math.floor(x), 0), N - 1)); j = int(min(max(math.floor(y), 0), N - 1))
        Pp = VECS[rng.integers(len(VECS))]
        g = ca.add_grain(i, j, 0, quat=quat_from_P(Pp))
        seed_gids.append(g)""")
# 2) lg_percentile 可配置（做集总敏感度）
s = s.replace("def run(seed, mode='envelope'):", "def run(seed, mode='envelope', pct=90.0):")
s = s.replace("ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode)",
              "ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode, lg_percentile=pct)")
s = s.replace("""out = []
for seed in (0, 1, 2, 3, 4):
    r = run(seed)""",
"""out = []
for seed in (0, 1, 2, 3, 4):
    r = run(seed)""")
# 3) 末尾追加"仅一个基底位点存活"的统计（应对照 ExaCA 的晶粒数）
s = s.replace("""json.dump(out, open(D + '/mine_stats.json', 'w'), indent=1)""",
"""print()
print('C) 集总敏感度（lg_percentile 50/90/100，同 5 个种子）——查"形核占比偏高"是否来自单-ℓ 集总')
for pct in (50.0, 90.0, 100.0):
    rs = [run(sd, pct=pct) for sd in (0, 1, 2)]
    print('  pct=%-5g 晶粒数 %.1f, 形核占比 %.3f±%.3f, 平均晶粒 %.1f 胞' % (
        pct, np.mean([x['n_grain'] for x in rs]), np.mean([x['frac_nuke'] for x in rs]),
        np.std([x['frac_nuke'] for x in rs]), np.mean([x['mean_size'] for x in rs])))
json.dump(out, open(D + '/mine_stats.json', 'w'), indent=1)""")
io.open(P, "w", encoding="utf-8").write(s)
print('patched')