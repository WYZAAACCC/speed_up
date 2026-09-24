# -*- coding: utf-8 -*-
'''_patch_cell2.py --- 新增 capture="cell"（严谨版：显式 bgid 做全序 tie-break）'''
import io, sys
P = '/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py'
s = io.open(P, encoding='utf-8').read()
if '_ensure_Lc' in s:
    print('已存在 _ensure_Lc（可能上次已打），先退出以免重复'); sys.exit(1)

# 1) _ensure_Lc
old = "    def grow_envelopes(self, dt, V, front):"
new = '''    def _ensure_Lc(self):
        """逐胞包络尺寸（m）。capture="cell" 用：每个前沿胞按【自己的局部 ΔT】累加；
        判据相对【该晶粒的种子】做精确 L1 隶属；捕获后【继承】(不扣减) ⇒ 不累加路径代价。"""
        if getattr(self, "_Lcarr", None) is None:
            self._Lcarr = np.zeros(self.shape)
        return self._Lcarr

    def grow_envelopes(self, dt, V, front):'''
s = s.replace(old, new, 1)

# 2) 捕获分支
anchor = '''        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----'''
branch = '''        if self.capture == "cell":
            # ---- capture="cell"（2026-09-24，对齐 ExaCA 的形态）----
            # (a) 逐胞 ℓ：只在前沿胞上，按【该胞自己的局部 V(ΔT)】累加
            # (b) 判据：Σ_a|p_a·(x_邻 − x_种子)| ≤ Lc[src]（相对【种子】的精确 L1，等价 sup）
            #     不做任何路径累加 ⇒ 不会重演 decentered 的 25~40% 径向亏损
            # (c) 赢家：ratio = Lc[src]/sup 最大；并列按 gid 小（全序 ⇒ 与遍历顺序无关）
            # (d) 捕获后 Lc[new] = Lc[src]（【继承】）
            Lc = self._ensure_Lc()
            Lc += V * dt * front
            fi_all = np.argwhere(front)
            if len(fi_all):
                inside = ((fi_all[:, 0] >= i0) & (fi_all[:, 0] < i1) & (fi_all[:, 1] >= j0) &
                          (fi_all[:, 1] < j1) & (fi_all[:, 2] >= k0) & (fi_all[:, 2] < k1))
                fi0 = fi_all[inside]
                if len(fi0):
                    fg0 = gid[fi0[:, 0], fi0[:, 1], fi0[:, 2]].astype(np.int64)
                    fL0 = Lc[fi0[:, 0], fi0[:, 1], fi0[:, 2]]
                    ok0 = fL0 > 0.0
                    fi0, fg0, fL0 = fi0[ok0], fg0[ok0], fL0[ok0]
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
                        gg, LL = fg0[inb], fL0[inb]
                        sflat = src0[inb]
                        free = gid[tx, ty, tz] == 0
                        if not free.any():
                            continue
                        tx, ty, tz = tx[free], ty[free], tz[free]
                        gg, LL, sflat = gg[free], LL[free], sflat[free]
                        sup = self.envelope_sup_vec(gg, tx, ty, tz)
                        cand = sup <= LL
                        if not cand.any():
                            continue
                        cx, cy, cz = tx[cand], ty[cand], tz[cand]
                        gg2, LL2 = gg[cand], LL[cand]
                        sfl2 = sflat[cand]
                        ratio = LL2 / np.maximum(sup[cand], 1e-30)
                        fidx = (cx * self.ny + cy) * self.nz + cz
                        prev = bf[fidx]
                        prevg = bgid[fidx]
                        upd = (ratio > prev) | ((ratio == prev) & (gg2 < prevg))
                        bf[fidx[upd]] = ratio[upd]
                        sf[fidx[upd]] = sfl2[upd]
                        bgid[fidx[upd]] = gg2[upd]

        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----'''
if anchor not in s: print('!! 锚点'); sys.exit(1)
s = s.replace(anchor, branch, 1)

# 3) 写回
old = '''            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)'''
new = '''            if self.capture == "decentered":
                si = bsrc[cap]                        # 存的是扁平胞索引
                self.gid.flat[ti] = self.gid.flat[si]
                self.L.flat[ti] = np.maximum(self.L.flat[si] - bthr[cap], 0.0)
            elif self.capture == "cell":
                si = bsrc[cap]                        # 存的是扁平胞索引
                Lc = self._ensure_Lc()
                self.gid.flat[ti] = self.gid.flat[si]
                Lc.flat[ti] = Lc.flat[si]             # 【继承】：不扣减 ⇒ 无路径累积'''
if old not in s: print('!! 写回锚点'); sys.exit(1)
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('OK 已加 capture="cell"; 行数 =', s.count(chr(10)) + 1)