import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
old = '''        if n_new:
            si = bsrc[cap]
            ti = flat[cap]
            self.gid.flat[ti] = self.gid.flat[si]
            # decentering: 新胞继承【剩余】半对角 = L - 已用掉的距离
            if self.capture == "decentered":
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            else:
                self.L.flat[ti] = np.maximum(bthr[cap] * 0.0, 0.0)   # 未使用'''
new = '''        if n_new:
            ti = flat[cap]
            # decentering: 新胞继承【剩余】半对角 = L - 已用掉的距离
            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            else:
                self.gid[cap] = bsrc[cap]             # analytic: 存的是 grain id
                self.L[cap] = 0.0                     # 未使用'''
assert old in s, "post anchor"
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("fixed")