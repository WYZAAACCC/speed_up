import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
if "快速路径：与历史实现逐位一致" in s:
    print("already patched"); raise SystemExit
old = '''        i0, i1, j0, j1, k0, k1 = box
        si_ax, ti_ax = [], []
        for (a0, a1, d, n, per) in ((i0, i1, o[0], self.nx, self.periodic[0]),'''
new = '''        i0, i1, j0, j1, k0, k1 = box
        if not any(self.periodic):
            # 快速路径：与历史实现逐位一致（slice）。
            rr = []
            for (a0, a1, d, n) in ((i0, i1, o[0], self.nx),
                                   (j0, j1, o[1], self.ny),
                                   (k0, k1, o[2], self.nz)):
                s0 = max(a0, -d)
                s1 = min(a1, n - d)
                if s1 <= s0:
                    return None
                rr.append((s0, s1, s0 + d, s1 + d))
            return (tuple(slice(r[0], r[1]) for r in rr),
                    tuple(slice(r[2], r[3]) for r in rr))
        si_ax, ti_ax = [], []
        for (a0, a1, d, n, per) in ((i0, i1, o[0], self.nx, self.periodic[0]),'''
assert old in s, "anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched fast path")