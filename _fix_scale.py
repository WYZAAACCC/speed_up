import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_bench.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("MINT = 1e-4            # 目标：v = M_int·Δf 的\"sharp-interface 迁移率\" [m^4/(J s)]",
              "MINT = 1e-6            # 目标：v = M_int·Δf 的\"sharp-interface 迁移率\" [m^4/(J s)] ⇒ v≈10 m/s")
s = s.replace("        pf.W = WBAR; pf.Lmob = 1e-12", "        pf.W = WBAR; pf.Lmob = 1e-6      # trial L（要选到位移可测）")
s = s.replace("        dt = 1e-9\n        p0 = pf.phi[0].copy()", "        dt = 1e-3                        # trial dt（稳定：dt·L·W<1）\n        p0 = pf.phi[0].copy()")
s = s.replace("        C1 = v / (1e-12 * df)", "        C1 = v / (1e-6 * df)")
s = s.replace("    ns = 2500\n    dt = 5e-9", "    ns = 3000\n    dt = 1e-11")
io.open(P, 'w', encoding='utf-8').write(s)
print('标定/时间尺度已改')