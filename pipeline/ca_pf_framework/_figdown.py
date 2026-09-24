import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/fig_meltpool_3d.py"
s = io.open(P, encoding="utf-8").read()
if "DOWN = 2" in s:
    print("already"); raise SystemExit
s = s.replace("""def load():
    d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    return d["gid"], float(d["dx"])""",
"""DOWN = 2          # 统一抽稀因子（晶粒与晶界【同一套索引】，否则坐标不一致会糊成一团）


def load():
    d = np.load(os.path.join(HERE, "meltpool_growth_gid.npz"))
    g = d["gid"][::DOWN, ::DOWN, ::DOWN]
    return g, float(d["dx"]) * DOWN""", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched DOWN=2")