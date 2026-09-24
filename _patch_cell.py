# -*- coding: utf-8 -*-
'''_patch_cell.py --- 新增 capture="cell"：逐胞 ℓ（局部驱动）+ 种子相对精确判据 + 继承'''
import io, sys
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()

# 1) _ensure_Lc
old = """    def grow_envelopes(self, dt, V, front):"""
new = """    def _ensure_Lc(self):
        \"\"\"逐胞包络尺寸（m）。capture="cell" 用：每个前沿胞按【自己的局部 ΔT】累加，
        判据相对【该晶粒的种子】做精确 L1 隶属，捕获后【继承】(不扣减) ⇒ 不累加路径代价。\"\"\"
        if getattr(self, "_Lcarr", None) is None:
            self._Lcarr = np.zeros(self.shape)
        return self._Lcarr

    def grow_envelopes(self, dt, V, front):"""
if old not in s: print('!! 1'); sys.exit(1)
s = s.replace(old, new, 1)

# 2) 捕获分支：插在 if self.capture == "envelope": 之前
old = """        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----"""
new = """        if self.capture == "cell":
            # ---- capture="cell"（2026-09-24，对齐 ExaCA 形态）----
            # (a) 逐胞 ℓ：只在前沿胞上、按【该胞自己的局部 V】累加
            # (b) 判据：Σ_a|p_a·(x_邻 − x_种子)| ≤ Lc[src]（相对【种子】的精确 L1，与 sup 等价，
            #     不做任何路径累加 ⇒ 不会出现 decentered 那 25~40% 的径向亏损）
            # (c) 赢家：ratio = Lc[src]/sup 最大；捕获后 Lc[new] = Lc[src]（【继承】）
            Lc = self._ensure_Lc()
            Lc += V * dt * front
            fi = np.argwhere(front)
            if len(fi):
                nwx, nwy, nwz = i1 - i0, j1 - j0, k1 - k0
                inside = ((fi[:, 0] >= i0) & (fi[:, 0] < i1) & (fi[:, 1] >= j0) &
                          (fi[:, 1] < j1) & (fi[:, 2] >= k0) & (fi[:, 2] < k1))
                fi = fi[inside]
                if len(fi):
                    fg = gid[fi[:, 0], fi[:, 1], fi[:, 2]].astype(np.int64)
                    fL = Lc[fi[:, 0], fi[:, 1], fi[:, 2]]
                    ok0 = fL > 0.0
                    fi, fg, fL = fi[ok0], fg[ok0], fL[ok0]
                    bf = best.reshape(-1)
                    sf = bsrc.reshape(-1)
                    for o, _ in OFFSETS:
                        tx = fi[:, 0] + o[0]; ty = fi[:, 1] + o[1]; tz = fi[:, 2] + o[2]
                        inb = ((tx >= 0) & (tx < self.nx) & (ty >= 0) & (ty < self.ny) &
                               (tz >= 0) & (tz < self.nz))
                        if not inb.any():
                            continue
                        tx, ty, tz = tx[inb], ty[inb], tz[inb]
                        gg, LL = fg[inb], fL[inb]
                        free = gid[tx, ty, tz] == 0
                        if not free.any():
                            continue
                        tx, ty, tz, gg, LL = tx[free], ty[free], tz[free], gg[free], LL[free]
                        sup = self.envelope_sup_vec(gg, tx, ty, tz)      # 从【种子】量的精确 L1
                        cand = sup <= LL
                        if not cand.any():
                            continue
                        cx, cy, cz = tx[cand], ty[cand], tz[cand]
                        gg2, LL2 = gg[cand], LL[cand]
                        sup2 = sup[cand]
                        ratio = LL2 / np.maximum(sup2, 1e-30)
                        fidx = (cx * self.ny + cy) * self.nz + cz
                        # 源胞的扁平索引（用于继承）
                        src_flat = ((fi[inb][free][cand][:, 0]) * self.ny +
                                    (fi[inb][free][cand][:, 1])) * self.nz + fi[inb][free][cand][:, 2]
                        prev = bf[fidx]
                        upd = (ratio > prev) | ((ratio == prev) & (gg2 < gid.flat[sf[fidx]].clip(0)))
                        bf[fidx[upd]] = ratio[upd]
                        sf[fidx[upd]] = src_flat[upd]

        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----"""
if old not in s: print('!! 2'); sys.exit(1)
s = s.replace(old, new, 1)

# 3) 写回：cell 模式继承 Lc
old = """            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)"""
new = """            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            elif self.capture == "cell":
                si = bsrc[cap]                        # 存的是扁平胞索引
                Lc = self._ensure_Lc()
                self.gid.flat[ti] = self.gid.flat[si]
                Lc.flat[ti] = Lc.flat[si]             # 【继承】：不扣减 ⇒ 无路径累积"""
if old not in s: print('!! 3'); sys.exit(1)
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('已加 capture="cell"; 行数 =', s.count(chr(10)) + 1)