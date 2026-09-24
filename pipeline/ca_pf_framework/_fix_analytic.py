import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
old = '''        cap = bsrc >= 0
        n_new = int(cap.sum())
        if n_new:
            si = bsrc[cap]
            ti = flat[cap]
            self.gid.flat[ti] = self.gid.flat[si]
            if self.capture == "decentered":
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            else:
                self.L.flat[ti] = np.maximum(bthr[cap] * 0.0, 0.0)   # 未使用
            self.ts.flat[ti] = self.t + dt
            self.Tc.flat[ti] = T.flat[ti]
            self.n_captured_steps += 1'''
new = '''        cap = bsrc >= 0
        n_new = int(cap.sum())
        if n_new:
            ti = flat[cap]
            if self.capture == "decentered":
                si = bsrc[cap]                       # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            else:
                self.gid[cap] = bsrc[cap]            # analytic: 存的是 grain id
                self.L[cap] = 0.0                    # 未使用
            self.ts.flat[ti] = self.t + dt
            self.Tc.flat[ti] = T.flat[ti]
            self.n_captured_steps += 1'''
assert old in s, "post anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("fixed analytic post-processing")