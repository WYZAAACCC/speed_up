import io
P = "/mnt/f/speed_up/_mine_mirror.py"
s = io.open(P, encoding="utf-8").read()
# 修正热场：ExaCA 的 R 是冷却速率 K/s（不是 µm/s）。其 Directional 约定:
#   ΔT(z,t) = R*t - G*z_phys  (z_phys = (z+0.5)*dx), InitUndercooling 默认 0
s = s.replace("""        dTfield = G * (R * t - z * DX)                     # ΔT(z,t)""",
"""        # ★ 修正: ExaCA 的 R 是【冷却速率 K/s】; ΔT(z,t) = R*t - G*z_phys, z_phys=(z+0.5)dx
        dTfield = R * t - G * (z + 0.5) * DX               # ΔT(z,t) [K]""")
s = s.replace("""DX, N, G, R = 1.0e-6, 20, 5.0e5, 3.0e5""",
"""DX, N, G, R = 1.0e-6, 20, 5.0e5, 3.0e5      # R = 冷却速率 [K/s]（ExaCA 约定）""")
io.open(P, "w", encoding="utf-8").write(s)
print('已修正热场公式')