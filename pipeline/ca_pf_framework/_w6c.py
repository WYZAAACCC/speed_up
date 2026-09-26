# -*- coding: utf-8 -*-
import io, ast
p='windowB_surface.py'
s=io.open(p,encoding='utf-8').read()
log=[]

# 1) __init__：加 Gam_mol（在 self.Gam 初始化处）
a = "        self.Gam = np.zeros((N, N, N))"
assert a in s, 'Gam init'
b = ("        self.Gam = np.zeros((N, N, N))\n"
     "        # ★★ W-6c（2026-09-25）：**面量的权威状态改按「摩尔/胞」存**（Gam_mol）。\n"
     "        #   为什么： 里的 A_c 是 coarea 测度、**界面一动它就变** ⇒ 账面逐步漏\n"
     "        #   （实测 advance 侧 rel 1.1e-5/步，30 步累积 1.2e-4；update_Gamma 侧是 2.5e-32）。\n"
     "        #   改法：内部只对 Gam_mol 做加减（与测度无关）， 只作为\n"
     "        #   **派生量**供物理（McLean Gamma_eq）与面扩散的通量换算使用 ⇒  用\n"
     "        #   ，**与时间无关、必然闭合**。\n"
     "        #   兼容：判据若直接写 （A3/H6/M3 的老写法），update_Gamma 开头会检测\n"
     "        #   到不一致并以  为准重新同步 Gam_mol（见那里的 guard）。")
s=s.replace(a,b,1); log.append('Gam_mol init')

# 2) update_Gamma：开头 guard + (1) 交换改摩尔 + (2) 扩散改摩尔 + (3) 离带改摩尔 + 末尾派生 Gam
a2 = """        m = A_c > 0
        # (3) 先把"离开带"的胞的面过剩还给体相（保守）
        if hasattr(self, '_m_prev'):
            left = self._m_prev & (~m)
            if left.any():
                moles = self.Gam[left] * self._A_prev[left]
                self.c[left] += moles / (self.rho * self.dx ** 3)
        self._m_prev, self._A_prev = m.copy(), A_c.copy()
        Gam_eq = self.Gamma_eq(self.c)"""
b2 = """        m = A_c > 0
        # ---- W-6c：Gam_mol 的兼容 guard（外部若写 Gam，以 Gam 为准重新同步）----
        if not hasattr(self, 'Gam_mol') or self.Gam_mol.shape != A_c.shape:
            self.Gam_mol = self.Gam * A_c
        else:
            _chk = self.Gam * A_c
            _sc = max(float(np.max(np.abs(self.Gam_mol))), 1e-300)
            if float(np.max(np.abs(self.Gam_mol - _chk))) > 1e-12 * _sc:
                self.Gam_mol = _chk
        # (3) 先把"离开带"的胞的面过剩还给体相（保守；按摩尔）
        if hasattr(self, '_m_prev'):
            left = self._m_prev & (~m)
            if left.any():
                self.c[left] += self.Gam_mol[left] / (self.rho * self.dx ** 3)
                self.Gam_mol = np.where(left, 0.0, self.Gam_mol)
        self._m_prev, self._A_prev = m.copy(), A_c.copy()
        Gam_eq = self.Gamma_eq(self.c)"""
assert a2 in s, 'guard block'
s=s.replace(a2,b2,1); log.append('guard + (3) moles')

a3 = """        dG = np.where(m, (Gam_eq - self.Gam) * frac, 0.0)
        self.Gam = np.where(m, self.Gam + dG, 0.0)
        self.c -= dG * A_c / (self.rho * self.dx ** 3)"""
b3 = """        # (1) 局部平衡交换：**按摩尔**做（目标摩尔 = Gamma_eq * A_c）⇒ 体/面等量反号，精确守恒
        dmol = np.where(m, (Gam_eq * A_c - self.Gam_mol) * frac, 0.0)
        self.Gam_mol = np.where(m, self.Gam_mol + dmol, 0.0)
        self.c -= dmol / (self.rho * self.dx ** 3)"""
assert a3 in s, 'exchange'
s=s.replace(a3,b3,1); log.append('(1) exchange in moles')

a4 = """                J = np.where(conn, -D_s * Ae * sin_t
                             * (np.roll(self.Gam, -1, axis=ax) - self.Gam) / self.dx ** 2,
                             0.0)
                dq = dt * J
                self.J_edge.append(J)
                # Δq_i = dt·(J_{i−1→i} − J_{i→i+1}) ⇒ roll(+1) 把上一条边的 J 搬到 i
                Ac_safe = np.where(m, A_c, 1.0)      # 带外 A_c=0 ⇒ 避免除零告警
                self.Gam = np.where(m, self.Gam + (np.roll(dq, 1, axis=ax) - dq) / Ac_safe,
                                    self.Gam)"""
b4 = """                # W-6c：通量里的 Γ 由派生量给出（Gamma = Gam_mol/A_c），**更新量本来就是摩尔**
                m_safe = np.where(m, A_c, 1.0)
                Gam_v = np.where(m, self.Gam_mol / m_safe, 0.0)
                J = np.where(conn, -D_s * Ae * sin_t
                             * (np.roll(Gam_v, -1, axis=ax) - Gam_v) / self.dx ** 2,
                             0.0)
                dq = dt * J
                self.J_edge.append(J)
                # Δ(摩尔)_i = dt·(J_{i−1→i} − J_{i→i+1}) ⇒ roll(+1) 把上一条边的 J 搬到 i
                self.Gam_mol = np.where(m, self.Gam_mol
                                        + (np.roll(dq, 1, axis=ax) - dq), self.Gam_mol)"""
assert a4 in s, 'diffusion'
s=s.replace(a4,b4,1); log.append('(2) diffusion in moles')

# 末尾：派生 Gam（供 A3/H6/M3 读取）
a5 = """        else:
            self.J_edge = [np.zeros_like(self.Gam)] * 3"""
b5 = """        else:
            self.J_edge = [np.zeros_like(self.Gam)] * 3
        # 派生 Gamma（per-area）供物理/判据读取；Gam_mol 才是权威状态
        self.Gam = np.where(m, self.Gam_mol / np.where(m, A_c, 1.0), 0.0)"""
assert a5 in s, 'tail'
s=s.replace(a5,b5,1); log.append('derive Gam')

# 3) totals()：用 Gam_mol（与测度无关）
a6 = """        mb = float(self.c.sum()) * self.rho * self.dx ** 3
        A_c = self.cell_area_geom()"""
assert a6 in s, 'totals head'
i=s.index(a6)
j=s.index('        return mb, ms', i)
k=s.index(chr(10), j)+1
b6 = """        mb = float(self.c.sum()) * self.rho * self.dx ** 3
        # ★★ W-6c：面量用**权威状态 Gam_mol（摩尔/胞）**求和 —— 与面积测度无关 ⇒ 必然闭合。
        if not hasattr(self, 'Gam_mol'):
            A_c = self.cell_area_geom()
            self.Gam_mol = self.Gam * A_c
        ms = float(self.Gam_mol.sum())
        return mb, ms
"""
s = s[:i] + b6 + s[k:]
log.append('totals via Gam_mol')

# 4) _stefan：存/取改摩尔
a7 = """            if kind == 'grow':
                self.Gam = np.where(swept & (A_c > 0),
                                    self.Gam + amount / np.maximum(A_c, 1e-30), self.Gam)
                amount = np.where(swept & (A_c > 0), 0.0, amount)
            else:
                avail = self.Gam * A_c                      # 面上可用的摩尔量
                take = np.where(swept & (A_c > 0), np.minimum(avail, -amount), 0.0)
                self.Gam = np.where(swept & (A_c > 0),
                                    self.Gam - take / np.maximum(A_c, 1e-30), self.Gam)
                amount = amount + take"""
b7 = """            # ★★ W-6c：**直接按摩尔存/取**（不再经过 A_c 的除法/乘法，避免测度漂移）
            msk = swept & (A_c > 0)
            if kind == 'grow':
                self.Gam_mol = np.where(msk, self.Gam_mol + amount, self.Gam_mol)
                amount = np.where(msk, 0.0, amount)
            else:
                take = np.where(msk, np.minimum(self.Gam_mol, -amount), 0.0)
                self.Gam_mol = np.where(msk, self.Gam_mol - take, self.Gam_mol)
                amount = amount + take
            # 派生 Gam 保持一致（供读 Gam 的判据/物理使用）
            self.Gam = np.where(A_c > 0, self.Gam_mol / np.maximum(A_c, 1e-30), 0.0)"""
assert a7 in s, '_stefan'
s=s.replace(a7,b7,1); log.append('_stefan in moles')

io.open(p,'w',encoding='utf-8').write(s); ast.parse(s)
print('W-6c applied:', ' | '.join(log))
