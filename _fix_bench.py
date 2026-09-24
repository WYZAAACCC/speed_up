import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_bench.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("    Nx, dx = 2048, 1e-9", "    Nx, dx = 256, 1e-9        # ★ 别写大：类只支持方阵，2048^2 会卡")
s = s.replace("        for _ in range(4000):\n            pf.step(dt, cap_sum=False)",
              "        for _ in range(1500):\n            pf.step(dt, cap_sum=False)")
s = s.replace("        v = (front(pf.phi[0]) - front(p0)) / (4000 * dt)", "        v = (front(pf.phi[0]) - front(p0)) / (1500 * dt)")
s = s.replace("    ns = 8000", "    ns = 2500")
io.open(P, 'w', encoding='utf-8').write(s)
print('已改小算例规模')