import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_bench.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("        pf = MartensitePF(Nx, 1, C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM, dG=df)",
              "        pf = MartensitePF(Nx, Nx * dx, C, eps0, kappa=KAP, M_int=0, w=WW, gamma=GAM, dG=df)")
io.open(P, 'w', encoding='utf-8').write(s)
print('标定盒子长度已修 (L = Nx*dx)')