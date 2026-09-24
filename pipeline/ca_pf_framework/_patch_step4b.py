# -*- coding: utf-8 -*-
"""_patch_step4b.py --- Step 4 修正：(1) 扩散用调和平均 (2) 默认化学改为【池尺度 Scheil + 逐胞捕获时刻】"""
import io, sys
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
src = io.open(P, encoding="utf-8").read()

# ---- 1) chem_local 默认关（逐胞路径留作可选/Window B 用）----
old = "lg_percentile=90.0, chem_local=True):"
new = "lg_percentile=90.0, chem_local=False):"
if old not in src: print("!! 1"); sys.exit(1)
src = src.replace(old, new)

# ---- 2) _diffuse_liquid 改调和平均 ----
old = '''        A = self.A_liq
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
        self.A_liq = np.maximum(A + dA, 0.0)'''
new = '''        A = self.A_liq
        a = np.clip(1.0 - self.fs, 0.0, 1.0) ** self.tort
        cl = A / np.maximum(a, 1e-6)
        coef = self.D_L * dt / self.dx ** 2
        dA = np.zeros(self.shape)
        for o, _ in OFFSETS:
            if sum(abs(v) for v in o) != 1:
                continue
            pr = self._pair(o, (0, self.nx, 0, self.ny, 0, self.nz))
            if pr is None:
                continue
            sx, tx = pr
            a1 = a[sx]; a2 = a[tx]
            den = a1 + a2
            # 【调和平均】面导电率：任一侧没有液相(1-fs=0) ⇒ 面通量必须为 0。
            # 用算术平均会让 1-fs->0 的胞里 c_L=A/(1-fs) 被放大成假浓度，A 指数爆炸
            # （2026-09-23 实测：算术平均使 A 由 0.036 涨到 3382）。
            harm = np.where(den > 1e-12, 2.0 * a1 * a2 / np.maximum(den, 1e-30), 0.0)
            flux = coef * harm * (cl[tx] - cl[sx])
            dA[sx] += flux
            dA[tx] -= flux
        Anew = A + dA
        self.n_Aclip = int((Anew < 0.0).sum())
        self.A_liq = np.maximum(Anew, 0.0)'''
if old not in src: print("!! 2"); sys.exit(1)
src = src.replace(old, new)

# ---- 3) step 里记录"初始液相"与池尺度固相分数历史 ----
old = '''        self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)
        if self.chem_local:
            self.solidify_local(dt, T, V)          # 局部凝固化学（新默认）
        self._fs_hist.append((self.t, float((self.gid > 0).mean())))'''
new = '''        self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)
        if self.chem_local:
            self.solidify_local(dt, T, V)          # 可选的逐胞亚网格路径（Window B 用）
        self._fs_hist.append((self.t, float((self.gid > 0).mean())))
        # 【新默认化学的驱动量】合金【体积元】= t=0 时的液相区（熔池）。
        # 旧 scheil_chemistry() 用【全域】固相分数：基底占 91.5% ⇒ 池一凝固 f 就跳到 0.95，
        # 液相成分立刻顶到 F_MIN 天花板 ⇒ 池内 c 几乎常数（审计 F5）。
        if getattr(self, "_liq0", None) is None:
            self._liq0 = (self.gid == 0)
            self._n_liq0 = max(int(self._liq0.sum()), 1)
            self._fpool_hist = [(0.0, 0.0)]
        f_pool = 1.0 - float((self._liq0 & (self.gid == 0)).sum()) / self._n_liq0
        self._fpool_hist.append((self.t, f_pool))'''
if old not in src: print("!! 3"); sys.exit(1)
src = src.replace(old, new)

# ---- 4) 新增 finalize_chemistry（池尺度 Scheil）插到 scheil_chemistry 之前 ----
anchor = '''    def scheil_chemistry(self):
        """逐胞 Scheil 闭式（模型声明见 MATH_FRAMEWORK 4.5）。'''
NEW = '''    def finalize_chemistry(self, k_eff=None):
        """**新默认化学**：合金【体积元（= t=0 的液相区，即熔池）】尺度的 Scheil 路径 + 逐胞捕获时刻。

        物理（框架 4.5 的口径，但把体积元取对）：
            c_l(f) = c0 (1-f)^(k-1),   c_s(f) = k c_l(f),   f = 体积元的固相分数
          体积元的固相分数在该胞【被捕获那一刻】的值 f_i 决定该胞刚沉积那一层壳的成分：
            cl_i = c_l(f_i)  (正则化到 F_MIN) ;  c_i = k cl_i
        逐胞质量恒等式 f*c_s_avg + (1-f)*c_l = c0 保证【体积元总体守恒】（见 mass_balance）。
        基底（ts<0，t=0 前就是固相）取 c = c0（审计 F6：旧代码给 k*c0 = 0.0227，偏低 37%）。
        输出字段:
          self.cl / self.c_liq  -> 该胞凝固时刻的【枝晶间液相成分】（Window C 输入）
          self.c  / self.c_sol  -> 该胞沉积固相的成分（Window B 输入）
          self.c_cell           -> 体平均成分 = c0（守恒恒等式 ⇒ 全域常数，作为守恒核对）
        返回 (cl_min, cl_max, c_sol_min, c_sol_max)。
        """
        kk = K_V if k_eff is None else float(k_eff)
        cap = np.isfinite(self.ts)
        hist = getattr(self, "_fpool_hist", None)
        if hist is None or len(hist) < 2:
            th = np.array([[0.0, 0.0], [1.0, 1.0]])
        else:
            th = np.array(hist)
        f = np.clip(np.interp(np.where(cap, self.ts, 0.0), th[:, 0], th[:, 1]), 0.0, 1.0)
        f_eff = np.minimum(f, 1.0 - F_MIN)
        cl = C0_V * (1.0 - f_eff) ** (kk - 1.0)
        self.cl_max = C0_V * F_MIN ** (kk - 1.0)
        self.c_last = self.cl_max
        self.fcap = np.where(cap, f, 0.0)
        self.cl = np.where(cap, cl, C0_V)
        self.c_liq = self.cl
        self.c = np.where(cap, kk * cl, C0_V)
        self.c_sol = self.c
        # 基底（t=0 前就是固相）与仍为液相的胞都取 c0
        sub = np.isfinite(self.ts) & (self.ts < 0.0)
        self.c[sub] = C0_V
        self.c_sol[sub] = C0_V
        self.cl[sub] = C0_V
        self.c_liq[sub] = C0_V
        self.c_cell = np.full(self.shape, C0_V)
        return (float(self.cl[cap].min()), float(self.cl[cap].max()),
                float(self.c[cap].min()), float(self.c[cap].max()))

    def mass_balance(self):
        """全局质量守恒核对（体积元口径）:
             f*c_s_avg(f) + (1-f)*c_l(f) = c0  ⇒ 每个胞体平均 = c0。
        返回 <体平均成分>/c0（1.0 = 守恒）。"""
        cap = np.isfinite(self.ts) & (self.ts >= 0.0)
        if not cap.any():
            return 1.0
        f = np.clip(self.fcap[cap], 0.0, 1.0)
        cs_avg = np.where(f > 1e-12, C0_V * (1.0 - (1.0 - f) ** K_V) / np.maximum(f, 1e-12),
                          K_V * C0_V)
        cl = C0_V * (1.0 - np.minimum(f, 1.0 - F_MIN)) ** (K_V - 1.0)
        tot = f * cs_avg + (1.0 - f) * cl
        # 基底胞按 c0 计（它们不在 cap 里），整体平均
        n_sub = int((np.isfinite(self.ts) & (self.ts < 0.0)).sum())
        val = float(tot.sum() + n_sub * C0_V) / float(cap.sum() + n_sub)
        return val / C0_V

    def scheil_chemistry(self):
        """【旧路径，保留】用【全域】固相分数代入 Scheil 闭式。

        ⚠ 2026-09-23 审计（F5）：基底占全域 91.5% ⇒ 池凝固时 f_global 从 0.915 跳到 1
        ⇒ 池内 c 几乎常数、60% 顶在 F_MIN 天花板。Window C 的输入请用 finalize_chemistry()。
        本方法保留是为了不改变既有回归判据的数值（G5a~G5f）。'''
if anchor not in src: print("!! 4"); sys.exit(1)
src = src.replace(anchor, NEW)

io.open(P, "w", encoding="utf-8").write(src)
print("Step4b 已打补丁; 行数 =", src.count("\n") + 1)