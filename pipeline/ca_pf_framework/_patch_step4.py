# -*- coding: utf-8 -*-
"""_patch_step4.py --- Step 4：CA3D 内置局部凝固化学（逐胞 fs 路径 + 液相扩散）"""
import io, sys

P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
src = io.open(P, encoding="utf-8").read()

# ---- 1) __init__ 签名 + 状态 ----
old = '''                 periodic=(False, False, False), capture="envelope",
                 lg_percentile=90.0):'''
new = '''                 periodic=(False, False, False), capture="envelope",
                 lg_percentile=90.0, chem_local=True):'''
if old not in src: print("!! init 签名未找到"); sys.exit(1)
src = src.replace(old, new)

old = '''        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）
        self._Lg = None'''
new = '''        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）
        self._Lg = None
        # --- 局部凝固化学（默认开；见 CA3D_AUDIT §F5~F7）---
        # 旧 scheil_chemistry() 用【全局】固相分数代入 Scheil ⇒ 池内 c 几乎常数、
        # 基底给 k*c0（应为 c0）、全局质量守恒只有 0.732。这条路径按【逐胞局部凝固路径】演化，
        # 并允许相邻胞间液相扩散（空间偏析图案的真正来源）。旧路径完整保留（测试零风险）。
        self.chem_local = bool(chem_local)
        self.D_L = 9.5e-9            # m2/s  液相扩散 (V in Ti64)  [L] JOM 2018
        self.tort = 1.0
        self.dtf_default = 1.73e-4   # s  局部凝固时间兜底 = dT0/(GR)，框架 4.5
        self.fs = np.zeros(self.shape)              # 亚网格固相分数
        self.c_sol = np.full(self.shape, C0_V)      # 固相成分
        self.A_liq = np.full(self.shape, C0_V)      # (1-fs)*c_L（主守恒量）
        self.c_liq = np.full(self.shape, C0_V)      # 局部液相成分（Window C 输入）
        self.cl = np.full(self.shape, C0_V)
        self.c_cell = np.full(self.shape, C0_V)     # 体平均成分（质量守恒）'''
if old not in src: print("!! init 状态未找到"); sys.exit(1)
src = src.replace(old, new)

# ---- 2) 新方法插到 scheil_chemistry 之前 ----
anchor = '''    # ---------------------------------------------------------------- 化学
    def fs_at(self, t):'''
NEW = '''    # ---------------------------------------------------------------- 化学
    def _dtf_field(self, T, V):
        """局部凝固时间 dt_f(x) = dT0 /(|grad T| V(x))（框架 4.5 的 t_f = dT0/(GR)）。
        梯度取不到/异常时退化为常数 dtf_default。"""
        try:
            gz, gy, gx = np.gradient(T, self.dx)
        except Exception:
            return np.full(self.shape, self.dtf_default)
        G = np.sqrt(gx * gx + gy * gy + gz * gz)
        with np.errstate(divide="ignore", invalid="ignore"):
            dtf = (T_LIQ - T_SOL) / np.maximum(G * V, 1e-12)
        bad = (~np.isfinite(dtf)) | (dtf <= 0.0) | (dtf > 1.0e3)
        return np.where(bad, self.dtf_default, dtf)

    def _diffuse_liquid(self, dt):
        """液相扩散（显式有限体积，通道面积 = (1-fs)^tort）: dA/dt = div(D_L (1-fs) grad c_L)。
        稳定性: dt <= dx^2/(2 D_L)（本框架 dx=3um, D_L=9.5e-9 时上限 ~0.47 s，远大于 dt）。"""
        A = self.A_liq
        cl = A / np.maximum(1.0 - self.fs, 1e-6)
        cond = (1.0 - self.fs) ** self.tort
        coef = self.D_L * dt / self.dx ** 2
        dA = np.zeros(self.shape)
        for o, _ in OFFSETS:
            if sum(abs(v) for v in o) != 1:
                continue
            pr = self._pair(o, (0, self.nx, 0, self.ny, 0, self.nz))
            if pr is None:
                continue
            sx, tx = pr
            cf = 0.5 * (cond[sx] + cond[tx])
            flux = coef * cf * (cl[tx] - cl[sx])
            dA[sx] += flux
            dA[tx] -= flux
        self.A_liq = np.maximum(A + dA, 0.0)

    def solidify_local(self, dt, T, V, diffuse=True):
        """逐胞局部凝固：fs 沿 age/dt_f 从 0 长到 1-F_MIN，固相按 k*c_L 取走溶质。

        物理: 枝晶间液膜不可约（框架 4.5 的 F_MIN）⇒ fs 饱和在 1-F_MIN，
        c_L 因此有物理上限 c0*F_MIN^(k-1)（不再发散）。守恒量 = A_liq + fs*c_sol（逐胞）。
        返回本步"正在凝固"的胞数。"""
        cap = np.isfinite(self.ts) & (self.ts >= 0.0)
        pending = cap & (self.fs < 1.0 - F_MIN - 1e-12)
        if not pending.any():
            self.c_liq = np.minimum(self.A_liq / np.maximum(1.0 - self.fs, 1e-6),
                                    C0_V * F_MIN ** (K_V - 1.0))
            self.cl = self.c_liq
            self.c_cell = self.fs * self.c_sol + (1.0 - self.fs) * self.c_liq
            return 0
        dtf = self._dtf_field(T, V)
        age = np.where(cap, np.maximum(self.t - self.ts, 0.0), 0.0)
        fs_new = np.clip(age / np.maximum(dtf, 1e-30), 0.0, 1.0 - F_MIN)
        df = np.where(cap, np.maximum(fs_new - self.fs, 0.0), 0.0)
        need = df > 0.0
        n_act = int(need.sum())
        if n_act:
            cl_here = self.c_liq[need]
            take = K_V * cl_here * df[need]
            fs_old = self.fs[need]
            denom = fs_old + df[need]
            self.c_sol[need] = np.where(
                denom > 0,
                (self.c_sol[need] * fs_old + take) / np.maximum(denom, 1e-30), C0_V)
            self.A_liq[need] = self.A_liq[need] - take
            self.fs[need] = fs_old + df[need]
        if diffuse:
            self._diffuse_liquid(dt)
        self.c_liq = self.A_liq / np.maximum(1.0 - self.fs, 1e-6)
        self.n_clip = int((self.c_liq > C0_V * F_MIN ** (K_V - 1.0)).sum())
        self.c_liq = np.minimum(self.c_liq, C0_V * F_MIN ** (K_V - 1.0))
        self.cl = self.c_liq
        self.c_cell = self.fs * self.c_sol + (1.0 - self.fs) * self.c_liq
        return n_act

    def total_solute(self):
        """守恒量（逐胞）: A_liq + fs*c_sol = c0（不受 c_L 显示截断影响）。"""
        return self.A_liq + self.fs * self.c_sol

    def mass_balance(self):
        """全局质量守恒: <总溶质>/c0（1.0 = 守恒）。"""
        return float(self.total_solute().mean() / C0_V)

    def fs_at(self, t):'''
if anchor not in src: print("!! 化学锚点未找到"); sys.exit(1)
src = src.replace(anchor, NEW)

# ---- 3) step 末尾调用 ----
old = '''        self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)
        self._fs_hist.append((self.t, float((self.gid > 0).mean())))'''
new = '''        self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)
        if self.chem_local:
            self.solidify_local(dt, T, V)          # 局部凝固化学（新默认）
        self._fs_hist.append((self.t, float((self.gid > 0).mean())))'''
if old not in src: print("!! step 调用点未找到"); sys.exit(1)
src = src.replace(old, new)

io.open(P, "w", encoding="utf-8").write(src)
print("Step4 已打补丁; 行数 =", src.count("\n") + 1)