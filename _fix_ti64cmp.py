import io
P = "/mnt/f/speed_up/_ti64_compare.py"
s = io.open(P, encoding="utf-8").read()
# 修正热场（R 是冷却速率 K/s）+ 步数对齐 ExaCA 的 Ti64 运行长度 2000 + 20 个种子
s = s.replace("N, DX, G, R, DT_S, NSTEP = 20, 1.0e-6, 5.0e5, 3.0e5, 0.0666667e-6, 3000",
              "N, DX, G, R, DT_S, NSTEP = 20, 1.0e-6, 5.0e5, 3.0e5, 0.0666667e-6, 2000")
s = s.replace("        dT = G * (R * t - z * DX)",
              "        dT = R * t - G * (z + 0.5) * DX      # ExaCA: ΔT = R·t − G·z_phys（R=冷却速率 K/s）")
s = s.replace("for s in range(5):\n    fp = run_exaca(s)", "for s in range(20):\n    fp = run_exaca(s)")
s = s.replace("mine = [run_mine(s) for s in range(5)]", "mine = [run_mine(s) for s in range(20)]")
io.open(P, "w", encoding="utf-8").write(s)
print('patched')