import io, sys
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()
old = """            sgn = np.where(u >= 0.0, 1.0, -1.0)"""
new = """            sgn = np.where(u > 0.0, 1.0, -1.0)          # ExaCA 用严格 >0"""
if old not in s: print('!! sign'); sys.exit(1)
s = s.replace(old, new, 1)
old2 = """            e1 = T1 - Tc; e2 = T2 - Tc"""
new2 = """            e1 = Tc - T1; e2 = Tc - T2        # ★ 与 ExaCA 一致: (xc-x1) 方向"""
if old2 not in s: print('!! edges'); sys.exit(1)
s = s.replace(old2, new2, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('已修 sign 与棱方向')