# -*- coding: utf-8 -*-
'''_patch_cell3.py --- 把 capture="cell" 改成精确复刻 ExaCA：每胞 (c, ℓ) + 角点几何重定心'''
import io, sys, re
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()

# ---- 1) 新的状态与工具函数（放在 _ensure_Lc 之后）----
old = '''    def grow_envelopes(self, dt, V, front):'''
new = '''    # ===== capture="cell"：精确复刻 ExaCA 的 decentered octahedron =====
    # 每胞状态：c = 该胞八面体中心（胞单位, 3 个 float），ℓ = 尺寸（胞单位）
    #   · ℓ 每步按【该胞自己的局部 V(ΔT)】累加：ℓ += V·dt/dx
    #   · 捕获判据：crit = Σ_a|p_a·(x_邻 − c_src)| ≤ ℓ_src   （与 ExaCA 的 max_i|(x0)·f_i| 等价）
    #   · 捕获后新胞的 (c, ℓ) 由【捕获面三角形的角点几何】现算（ExaCA::createNewOctahedron）
    INIT_OCT = 0.01                      # ExaCA 的 _init_oct_size 默认值（胞）

    def _ensure_cell_state(self):
        if getattr(self, "_cellC", None) is None or self._cellC.shape != self.shape + (3,):
            self._cellC = np.zeros(self.shape + (3,), np.float64)   # 八面体中心（胞单位）
            self._cellL = np.zeros(self.shape, np.float64)          # 尺寸 ℓ（胞单位）
        return self._cellL, self._cellC

    def cell_crit_vec(self, gvec, ccoord, xcoord):
        """crit = Σ_a|p_a·(x − c)|（逐个 pair 用其所属晶粒的取向）。ccoord/xcoord 为胞单位。"""
        out = np.zeros(len(gvec))
        for g in np.unique(gvec):
            m = (gvec == g)
            Pg = self.axes[int(g)]
            d = xcoord[m] - ccoord[m]
            out[m] = (np.abs(d @ Pg[:, 0]) + np.abs(d @ Pg[:, 1]) + np.abs(d @ Pg[:, 2]))
        return out

    def oct_recenter(self, gvec, csrc, xnbr, crit, s3=3.0**0.5):
        """ExaCA::createNewOctahedron 的矢量实现。
        输入：源胞中心 csrc、新胞中心 xnbr、crit（=捕获瞬间的面距）；输出 (ℓ_new, c_new)。"""
        M = len(gvec)
        lnew = np.empty(M); cnew = np.empty((M, 3))
        for g in np.unique(gvec):
            m = (gvec == g)
            Pg = self.axes[int(g)]                      # 列 = p1,p2,p3
            x0 = xnbr[m] - csrc[m]                      # (k,3)
            u = np.stack([x0 @ Pg[:, 0], x0 @ Pg[:, 1], x0 @ Pg[:, 2]], 1)
            sgn = np.where(u >= 0.0, 1.0, -1.0)
            T = np.empty((x0.shape[0], 3, 3))           # 3 个角点
            for a in range(3):
                T[:, a, :] = csrc[m] + crit[m][:, None] * sgn[:, a][:, None] * Pg[:, a][None, :]
            dcorner = np.linalg.norm(T - xnbr[m][:, None, :], axis=2)      # (k,3)
            ic = np.argmin(dcorner, axis=1)
            rows = np.arange(x0.shape[0])
            mind = dcorner[rows, ic]
            Tc = T[rows, ic]
            T1 = T[rows, (ic + 1) % 3]
            T2 = T[rows, (ic + 2) % 3]
            e1 = T1 - Tc; e2 = T2 - Tc
            d1 = np.maximum(np.linalg.norm(e1, axis=1), 1e-30)
            d2 = np.maximum(np.linalg.norm(e2, axis=1), 1e-30)
            xn = xnbr[m]
            j1 = np.einsum('ij,ij->i', xn - T1, e1) / d1
            j1n = d1 - j1
            j2 = np.einsum('ij,ij->i', xn - T2, e2) / d2
            j2n = d2 - j2
            zero = (mind <= 1e-12)                       # 新胞中心恰在角点上
            j1 = np.where(zero, 0.0, j1); j1n = np.where(zero, d1, j1n)
            j2 = np.where(zero, 0.0, j2); j2n = np.where(zero, d2, j2n)
            l12 = 0.5 * (np.minimum(j1, s3) + np.minimum(j1n, s3))
            l13 = 0.5 * (np.minimum(j2, s3) + np.minimum(j2n, s3))
            ln = 2.0**0.5 * np.maximum(l12, l13)
            uhat = (Tc - csrc[m]) / np.maximum(np.linalg.norm(Tc - csrc[m], axis=1), 1e-30)[:, None]
            lnew[m] = ln
            cnew[m] = Tc - ln[:, None] * uhat
        return lnew, cnew

    def grow_envelopes(self, dt, V, front):'''
if old not in s: print('!! 1'); sys.exit(1)
s = s.replace(old, new, 1)

# ---- 2) add_grain 初始化 (c, ℓ) ----
old = '''        self._ensure_Lg()[g] = 0.0          # 逐晶粒包络半轴（新默认判定用）
        return g'''
new = '''        self._ensure_Lg()[g] = 0.0          # 逐晶粒包络半轴（新默认判定用）
        Lc, CC = self._ensure_cell_state()  # capture="cell" 的逐胞 (ℓ, 中心)
        Lc[i, j, k] = self.INIT_OCT
        CC[i, j, k, :] = (i + 0.5, j + 0.5, k + 0.5)
        return g'''
if old not in s: print('!! 2'); sys.exit(1)
s = s.replace(old, new, 1)

# ---- 3) 替换 cell 捕获分支 ----
start = s.index('        if self.capture == "cell":')
end = s.index('        if self.capture == "envelope":')
branch = '''        if self.capture == "cell":
            # ---- 精确复刻 ExaCA：逐胞 (c, ℓ) + 角点几何重定心 ----
            Lc, CC = self._ensure_cell_state()
            Lc += (V * dt / self.dx) * front              # ℓ（胞单位）按局部 V 累加
            fi_all = np.argwhere(front)
            if len(fi_all):
                inside = ((fi_all[:, 0] >= i0) & (fi_all[:, 0] < i1) & (fi_all[:, 1] >= j0) &
                          (fi_all[:, 1] < j1) & (fi_all[:, 2] >= k0) & (fi_all[:, 2] < k1))
                fi0 = fi_all[inside]
                if len(fi0):
                    fg0 = gid[fi0[:, 0], fi0[:, 1], fi0[:, 2]].astype(np.int64)
                    fL0 = Lc[fi0[:, 0], fi0[:, 1], fi0[:, 2]]
                    fc0 = CC[fi0[:, 0], fi0[:, 1], fi0[:, 2]]
                    src0 = (fi0[:, 0] * self.ny + fi0[:, 1]) * self.nz + fi0[:, 2]
                    bf = best.reshape(-1)
                    sf = bsrc.reshape(-1)
                    bgid = np.full(gid.size, 1 << 30, np.int32)
                    for o, _ in OFFSETS:
                        tx = fi0[:, 0] + o[0]; ty = fi0[:, 1] + o[1]; tz = fi0[:, 2] + o[2]
                        inb = ((tx >= 0) & (tx < self.nx) & (ty >= 0) & (ty < self.ny) &
                               (tz >= 0) & (tz < self.nz))
                        if not inb.any():
                            continue
                        tx, ty, tz = tx[inb], ty[inb], tz[inb]
                        gg, LL, CCs = fg0[inb], fL0[inb], fc0[inb]
                        sflat = src0[inb]
                        free = gid[tx, ty, tz] == 0
                        if not free.any():
                            continue
                        tx, ty, tz = tx[free], ty[free], tz[free]
                        gg, LL, CCs, sflat = gg[free], LL[free], CCs[free], sflat[free]
                        xn = np.stack([tx + 0.5, ty + 0.5, tz + 0.5], 1).astype(np.float64)
                        crit = self.cell_crit_vec(gg, CCs, xn)      # 从【该胞八面体中心】量的精确 L1
                        cand = crit <= LL
                        if not cand.any():
                            continue
                        cx, cy, cz = tx[cand], ty[cand], tz[cand]
                        gg2, LL2 = gg[cand], LL[cand]
                        crit2, sfl2 = crit[cand], sflat[cand]
                        ratio = LL2 / np.maximum(crit2, 1e-30)
                        fidx = (cx * self.ny + cy) * self.nz + cz
                        prev = bf[fidx]; prevg = bgid[fidx]
                        upd = (ratio > prev) | ((ratio == prev) & (gg2 < prevg))
                        bf[fidx[upd]] = ratio[upd]
                        sf[fidx[upd]] = sfl2[upd]
                        bgid[fidx[upd]] = gg2[upd]

'''
s = s[:start] + branch + s[end:]

# ---- 4) 写回：用角点几何给出新胞的 (c, ℓ) ----
old = '''            elif self.capture == "cell":
                si = bsrc[cap]                        # 存的是扁平胞索引
                Lc = self._ensure_Lc()
                self.gid.flat[ti] = self.gid.flat[si]
                Lc.flat[ti] = Lc.flat[si]             # 【继承】：不扣减 ⇒ 无路径累积'''
new = '''            elif self.capture == "cell":
                si = bsrc[cap]                        # 存的是扁平胞索引（源胞）
                Lc, CC = self._ensure_cell_state()
                gg = self.gid.flat[si].astype(np.int64)
                cs = CC.reshape(-1, 3)[si]            # 源胞八面体中心（胞单位）
                tix = ti % self.nz
                tiy = (ti // self.nz) % self.ny
                tixx = ti // (self.nz * self.ny)
                xn = np.stack([tixx + 0.5, tiy + 0.5, tix + 0.5], 1).astype(np.float64)
                crit = self.cell_crit_vec(gg, cs, xn)
                ln, cn = self.oct_recenter(gg, cs, xn, crit)
                self.gid.flat[ti] = self.gid.flat[si]
                Lc.flat[ti] = ln
                CC.reshape(-1, 3)[ti] = cn'''
if old not in s: print('!! 4'); sys.exit(1)
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('已重写 capture="cell"; 行数 =', s.count(chr(10)) + 1)