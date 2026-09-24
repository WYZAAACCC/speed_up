import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
if "c_l=None" in s and "M_L * (c_l - C0_V)" in s:
    print("already"); raise SystemExit
old = '''    def step(self, dt, T, window=None):
        """推进一步。T 为当前温度场（K）。

        window: 可选 (i0,i1,j0,j1,k0,k1) 限制计算区（滑动窗口的 active region）。
        """
        gid = self.gid
        dT = np.clip(T_LIQ - T, 0.0, None)
        V, dT_used, _, _ = self.irf.capped(dT)
        # 越界计数: 只有【前沿固相胞】(有液相邻居的固相胞) 的 V 才真正驱动生长。'''
new = '''    def step(self, dt, T, window=None, c_l=None):
        """推进一步。T 为当前温度场（K）。

        window: 可选 (i0,i1,j0,j1,k0,k1) 限制计算区（滑动窗口的 active region）。
        c_l:    可选，逐胞【液相成分】。给了就启用【成分过冷】驱动 —— 见下。

        【2026-09-23 物理修法：把溶质接进"生长"判据】
        物理上的 CET（等轴晶带）要求热前沿【之前/附近】的液体因溶质富集而被压低液相线：
            ΔT_CS = [T_LIQ + m_L (c_l - c_0)] - T
        只把 c_l 接进【形核】(nucleate_bulk) 不够 —— 决定形貌的是【生长】。
        这里把驱动量换成 ΔT_CS，且**只在前沿固相胞上生效**：
          · 前沿胞里的 c_l 正是"枝晶间液相成分" = 固相此刻正在由它长出的那个液相
            ⇒ 用它是物理正确的局部液相线；
          · 非前沿（深处）固相胞不参与新胞捕获，保持纯热驱动即可（避免无液相的胞
            被 c_liq 的 floor 值污染）。
        c_l=None（默认）时行为与历史完全一致。
        """
        gid = self.gid
        front = self._front_solid()
        dT = np.clip(T_LIQ - T, 0.0, None)
        if c_l is not None:
            dT_cs = np.clip(T_LIQ + M_L * (np.asarray(c_l) - C0_V) - T, 0.0, None)
            dT = np.where(front, dT_cs, dT)
            self.n_cs_cells = int(front.sum())
        V, dT_used, _, _ = self.irf.capped(dT)
        # 越界计数: 只有【前沿固相胞】(有液相邻居的固相胞) 的 V 才真正驱动生长。'''
assert old in s, "step anchor"
s = s.replace(old, new, 1)
s = s.replace("        front = self._front_solid()\n        self.n_front_steps = getattr(self, \"n_front_steps\", 0) + int(front.sum())",
              "        self.n_front_steps = getattr(self, \"n_front_steps\", 0) + int(front.sum())", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("patched CA3D.step (constitutional growth)")

P2 = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d_solute.py"
s2 = io.open(P2, encoding="utf-8").read()
old2 = '''    def step_solute(self, dt, T, window=None):
        """CA 几何推进 + 溶质再分配 + 液相扩散。返回本步捕获胞数。"""
        # ---- 1) CA 几何（固液界面推进 + 捕获）----
        nnew = self.step(dt, T, window=window)'''
new2 = '''    def step_solute(self, dt, T, window=None, constitutional=True):
        """CA 几何推进 + 溶质再分配 + 液相扩散。返回本步捕获胞数。

        constitutional=True（默认）: 把上一步的 c_liq 接进【生长】判据（成分过冷）
        —— 显式交错耦合（先几何、后化学；本步几何用的是上一步的 c_liq）。"""
        # ---- 1) CA 几何（固液界面推进 + 捕获）----
        nnew = self.step(dt, T, window=window,
                         c_l=(self.c_liq if constitutional else None))'''
assert old2 in s2, "step_solute anchor"
s2 = s2.replace(old2, new2, 1)
io.open(P2, "w", encoding="utf-8").write(s2)
print("patched CA3DSolute.step_solute")