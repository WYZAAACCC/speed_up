import io
P = '/mnt/f/speed_up/_unit_oct.py'
s = io.open(P, encoding='utf-8').read()
s = s.replace("    lv, cv = ca.oct_recenter(np.array([1]), cs2, xn2, cr2)",
              "    lv, cv = ca.oct_recenter(np.array([g]), cs2, xn2, cr2)   # ← 用【本 trial 的】grain")
io.open(P, 'w', encoding='utf-8').write(s)
print('harness 已修')