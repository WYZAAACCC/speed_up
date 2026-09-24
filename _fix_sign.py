import io
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_pf.py'
s = io.open(P, encoding='utf-8').read()
old = "            f[v] += self.dG * 6 * p * (1 - p) + self.W * 2 * p * (1 - p) * (1 - 2 * p)"
new = ("            # −∂f/∂φ：化学驱动 +ΔG·6φ(1−φ)，双阱【负号】−2Wφ(1−φ)(1−2φ)\n"
       "            f[v] += self.dG * 6 * p * (1 - p) - self.W * 2 * p * (1 - p) * (1 - 2 * p)")
if old not in s: print('!! 锚点'); raise SystemExit(1)
io.open(P, 'w', encoding='utf-8').write(s.replace(old, new, 1))
print('双阱项符号已修')