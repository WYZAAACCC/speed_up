import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
if "self.periodic" in s:
    print("already patched"); raise SystemExit

old_init = "    def __init__(self, nx, ny, nz, dx, irf=None, seed=12345, n_halo=2):\n        self.nx, self.ny, self.nz, self.dx = nx, ny, nz, dx"
new_init = ("    def __init__(self, nx, ny, nz, dx, irf=None, seed=12345, n_halo=2,\n"
            "                 periodic=(False, False, False)):\n"
            "        self.nx, self.ny, self.nz, self.dx = nx, ny, nz, dx\n"
            "        # 轴向周期边界（默认全关；开后在 _pair 里环绕）。\n"
            "        # 用途：倾斜/竖直梯度下的晶粒竞争，去掉侧壁对竞争的约束。\n"
            "        self.periodic = tuple(bool(p) for p in periodic)")
assert old_init in s, "init anchor"
s = s.replace(old_init, new_init, 1)

old_pair = '''    def _pair(self, o, box):
        """返回 (src_slices, tgt_slices)，使得 src 处的胞与 tgt=src+o 处的胞配对。
        box = (i0,i1,j0,j1,k0,k1) 是当前活动窗口（滑动窗口的落点）。"""
        i0, i1, j0, j1, k0, k1 = box
        rr = []
        for (a0, a1, d, n) in ((i0, i1, o[0], self.nx),
                               (j0, j1, o[1], self.ny),
                               (k0, k1, o[2], self.nz)):
            s0 = max(a0, -d)
            s1 = min(a1, n - d)
            if s1 <= s0:
                return None
            rr.append((s0, s1, s0 + d, s1 + d))
        src = tuple(slice(r[0], r[1]) for r in rr)
        tgt = tuple(slice(r[2], r[3]) for r in rr)
        return src, tgt'''
new_pair = '''    def _pair(self, o, box):
        """返回 (src_idx, tgt_idx)：两个 np.ix_ 索引元组，使 src 处的胞与 tgt=src+o 配对。

        非周期轴上与旧的 slice 实现**逐位等价**（arange(s0,s1) 就是原来的 slice(s0,s1)）；
        周期轴（self.periodic）上环绕：ti = (si + d) % n。
        两个索引数组都只含【互不相同】的下标，所以 `A[tgt] = ...` 的赋值语义与 slice 版一致。
        box = (i0,i1,j0,j1,k0,k1) 是当前活动窗口（滑动窗口的落点）。"""
        i0, i1, j0, j1, k0, k1 = box
        si_ax, ti_ax = [], []
        for (a0, a1, d, n, per) in ((i0, i1, o[0], self.nx, self.periodic[0]),
                                    (j0, j1, o[1], self.ny, self.periodic[1]),
                                    (k0, k1, o[2], self.nz, self.periodic[2])):
            if per:
                if d == 0:
                    return None                      # 周期轴上 d=0 即自身配对，无意义
                si = np.arange(a0, a1)
                ti = (si + d) % n
            else:
                s0 = max(a0, -d)
                s1 = min(a1, n - d)
                if s1 <= s0:
                    return None
                si = np.arange(s0, s1)
                ti = si + d
            si_ax.append(si)
            ti_ax.append(ti)
        return np.ix_(*si_ax), np.ix_(*ti_ax)'''
assert old_pair in s, "pair anchor"
s = s.replace(old_pair, new_pair, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched ca3d.py")