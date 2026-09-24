# -*- coding: utf-8 -*-
"""_patch_step5.py --- Step 5: (1) active_box 复用前沿（去掉重复的全预扫描）(2) run() 支持液相归零即停"""
import io, sys
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
src = io.open(P, encoding="utf-8").read()

# ---- 1) active_box 接受已算好的 front ----
old = '''    def active_box(self, margin=None):
        """前沿（有液相邻居的实心胞）的包围盒 + margin。
        这就是「滑动窗口」在本实现中的落点：只在前沿邻域计算。"""
        if margin is None:
            margin = 2
        solid = self.gid > 0
        liquid = ~solid
        if not solid.any():
            return (0, self.nx, 0, self.ny, 0, self.nz)
        # 与液相相邻的实心胞
        nb_liq = np.zeros_like(solid)
        full = (0, self.nx, 0, self.ny, 0, self.nz)
        for o, _ in OFFSETS:
            pr = self._pair(o, full)
            if pr is None:
                continue
            sx, tx = pr
            nb_liq[tx] |= liquid[sx]
        front = solid & nb_liq
        if not front.any():
            front = solid'''
new = '''    def active_box(self, margin=None, front=None):
        """前沿（有液相邻居的实心胞）的包围盒 + margin。
        这就是「滑动窗口」在本实现中的落点：只在前沿邻域计算。

        front 可传入 step() 里已经算好的 `_front_solid()` 结果，避免每步重复做一次
        26 偏移的全域扫描（审计 N9 的冗余项）。传 None 时自带计算，行为不变。"""
        if margin is None:
            margin = 2
        solid = self.gid > 0
        if not solid.any():
            return (0, self.nx, 0, self.ny, 0, self.nz)
        if front is None:
            liquid = ~solid
            nb_liq = np.zeros_like(solid)
            full = (0, self.nx, 0, self.ny, 0, self.nz)
            for o, _ in OFFSETS:
                pr = self._pair(o, full)
                if pr is None:
                    continue
                sx, tx = pr
                nb_liq[tx] |= liquid[sx]
            front = solid & nb_liq
        if not front.any():
            front = solid'''
if old not in src: print("!! 1"); sys.exit(1)
src = src.replace(old, new)

old = '''        if window is None:
            window = self.active_box()'''
new = '''        if window is None:
            window = self.active_box(front=front)      # 复用本步已算好的前沿（省一次全域扫描）'''
if old not in src: print("!! 1b"); sys.exit(1)
src = src.replace(old, new)

# ---- 2) run() 液相归零即停 ----
old = '''def run(ca, T_func, t_end, dt, bulk=None, verbose=True, every=None):
    """时间推进。T_func(t) -> 温度场。bulk=(dT_mean,dT_sigma,N_max) 打开体形核。"""
    n = int(round(t_end / dt))
    hist = []
    for s in range(n):
        ca.t = s * dt
        T = T_func(ca.t)
        nnew = ca.step(dt, T)'''
new = '''def run(ca, T_func, t_end, dt, bulk=None, verbose=True, every=None, stop_when_solid=False):
    """时间推进。T_func(t) -> 温度场。bulk=(dT_mean,dT_sigma,N_max) 打开体形核。

    stop_when_solid=True: 域内没有液相（gid 全 > 0）就停。**纯效率改动**：
    液相归零之后 CA 没有任何事可做（审计实测：熔池算例第 103 步就全固，
    却跑到 1083 步 ⇒ 90.5% 的步是白算，省 ~94% 机时；结果逐位不变）。"""
    n = int(round(t_end / dt))
    hist = []
    for s in range(n):
        ca.t = s * dt
        T = T_func(ca.t)
        nnew = ca.step(dt, T)'''
if old not in src: print("!! 2"); sys.exit(1)
src = src.replace(old, new)

old = '''            if verbose:
                print("  t={:.3e} s  fs={:.3f}  grains={}  new={} bulk={}".format(
                    ca.t, hist[-1]["fs"], hist[-1]["ng"], nnew, nbulk))'''
new = '''            if verbose:
                print("  t={:.3e} s  fs={:.3f}  grains={}  new={} bulk={}".format(
                    ca.t, hist[-1]["fs"], hist[-1]["ng"], nnew, nbulk))
        if stop_when_solid and not (ca.gid == 0).any():
            break'''
if old not in src: print("!! 2b"); sys.exit(1)
src = src.replace(old, new)

io.open(P, "w", encoding="utf-8").write(src)
print("Step5 已打补丁; 行数 =", src.count("\n") + 1)