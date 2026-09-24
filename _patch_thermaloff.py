import io
P = "/mnt/f/speed_up/_mine_mirror.py"
s = io.open(P, encoding="utf-8").read()
# 增加参数：关掉"热力学约束"归属（对齐 ExaCA：它没有这条规则）
s = s.replace("def run(seed, mode='envelope', pct=90.0):", "def run(seed, mode='envelope', pct=90.0, thermal_off=False):")
s = s.replace("""    irf = CubicIRF()
    ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode, lg_percentile=pct)""",
"""    irf = CubicIRF()
    ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode, lg_percentile=pct)
    if thermal_off:
        ca.allow_spont = False        # 关掉 T<T_SOL 的强制归属（ExaCA 没有这条规则）""")
s = s.replace("""print()
print('C) 集总敏感度""", """print()
print('D) 关掉"热力学约束归属"（对齐 ExaCA）后重跑，看择优/形核占比是否向 ExaCA 靠拢:')
for seed in (0, 1, 2, 3, 4):
    r = run(seed, thermal_off=True)
    print('  seed %d: 晶粒数 %3d, 形核占比 %.3f, 基底加权 min∠ %.2f°' % (
        seed, r['n_grain'], r['frac_nuke'], r['ang_w_sub']))
print()
print('C) 集总敏感度""")
io.open(P, "w", encoding="utf-8").write(s)
print('patched')