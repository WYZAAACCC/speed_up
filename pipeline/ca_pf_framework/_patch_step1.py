# -*- coding: utf-8 -*-
"""_patch_step1.py --- CA3D 审计修复 Step 1-3：逐晶粒连续包络 + 顺序无关归属 + 化学/初始图改造"""
import io, re, sys

P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
src = io.open(P, encoding="utf-8").read()
orig = src
edits = []


def rep(old, new, tag):
    global src
    if old not in src:
        print("!! 未找到锚点:", tag)
        sys.exit(1)
    if src.count(old) != 1:
        print("!! 锚点不唯一(%d):" % src.count(old), tag)
        sys.exit(1)
    src = src.replace(old, new)
    edits.append(tag)


# ---------------------------------------------------------------- 1) __init__
rep(
'''                 periodic=(False, False, False), capture="decentered"):
        self.nx, self.ny, self.nz, self.dx = nx, ny, nz, dx
        # capture: "decentered"（默认，历史/生产用的格点路径规则）
        #          "analytic"（种子相对的【连续八面体】判据，去掉格点路径偏差）
        self.capture = capture''',
'''                 periodic=(False, False, False), capture="envelope",
                 lg_percentile=90.0):
        self.nx, self.ny, self.nz, self.dx = nx, ny, nz, dx
        # capture 三档（见 CA3D_AUDIT_2026-09-23.md）：
        #   "envelope"   ← **新默认**（审计后修复）：逐晶粒连续包络 l_g + 外延(26)邻接
        #                  + 逐胞 argmax(l_g/sup_g) 定归属 ⇒ 顺序无关、各向异性正确。
        #                  实测 r(<100>)/l=1.00+-0.05、<100>:<111>=1.73+-0.10、体积 +-5%。
        #   "analytic"   历史：从【种子】出发的连续八面体，但 l 只记在种子胞上
        #                  ⇒ 滑动窗口下会僵死（审计 N6），仅留作对照。
        #   "decentered" 历史/生产：逐胞 L 预算 + 格点路径代价 ⇒ 各向异性被毁
        #                  （r(<100>)/l=0.60~0.76、体积 -25%、不随 dx 收敛），仅留作考古对照。
        self.capture = capture
        self.lg_percentile = float(lg_percentile)   # l_g 驱动量取前沿 V 的该分位（规划 D1）
        self._Lg = None''', "init")

# ---------------------------------------------------------------- 2) add_grain
rep('''        self.gid[i, j, k] = g
        self.L[i, j, k] = 0.0
        self.ts[i, j, k] = self.t
        return g''',
'''        self.gid[i, j, k] = g
        self.L[i, j, k] = 0.0
        self.ts[i, j, k] = self.t
        self._ensure_Lg()[g] = 0.0          # 逐晶粒包络半轴（新默认判定用）
        return g''', "add_grain")

# ---------------------------------------------------------------- 3) 新方法
rep('''    # ---------------------------------------------------------- 取向阈值表
    def _thr_tables(self):''',
'''    # =============================================== 逐晶粒连续包络（新默认判定）
    # 物理依据: MATH_FRAMEWORK 4.4
    #     晶粒 g 的虚拟包络 = 晶体坐标系下的 L1 球 { sum_a |p_a.(x-x_g)| <= l_g }
    #     径向函数  r_g(n_hat) = l_g / sum_a |p_a . n_hat|
    #     推进      l_g(t+dt) = l_g(t) + V(dT) dt
    # 职责划分（审计 §5 的架构结论）：
    #     **热场定"哪个胞此刻可固"，包络竞争定"归哪个晶粒"** —— 不再让 CA 前沿去追等温线、
    #     追不上就交给"格点洪泛"（那个构件既顺序依赖又会自形核，已删）。
    def _ensure_Lg(self):
        n = len(self.axes)
        if getattr(self, "_Lg", None) is None or len(self._Lg) < n:
            old = getattr(self, "_Lg", None)
            self._Lg = np.zeros(n + 8)
            if old is not None:
                self._Lg[:len(old)] = old[:len(self._Lg)]
        return self._Lg

    def grow_envelopes(self, dt, V, front):
        """逐晶粒推进包络半轴 l_g：取该晶粒【前沿胞】上 V 的 lg_percentile 分位（默认 90%）。

        为什么用分位而不是裸 max：单个热胞（例如池心）不该把整个晶粒的包络带走；
        分位既保留"最深尖端驱动"的物理，又对单点噪声稳健。lg_percentile=100 即裸 max。
        """
        Lg = self._ensure_Lg()
        if not front.any():
            return Lg
        gf = self.gid[front]
        Vf = V[front]
        for g in np.unique(gf):
            if g <= 0:
                continue
            vg = float(np.percentile(Vf[gf == g], self.lg_percentile))
            Lg[int(g)] += vg * dt
        return Lg

    def envelope_sup(self, g, ix, iy, iz):
        """sup_g(x) = sum_a |p_a.(x - x_g)|（单位 m），x 取胞心。
        ix/iy/iz 是胞索引（标量或任意形状数组）。"""
        Pp = self.axes[int(g)]
        s = self.seeds[int(g)]
        dxv = (np.asarray(ix) - s[0]) * self.dx
        dyv = (np.asarray(iy) - s[1]) * self.dx
        dzv = (np.asarray(iz) - s[2]) * self.dx
        return (np.abs(Pp[0, 0] * dxv + Pp[1, 0] * dyv + Pp[2, 0] * dzv) +
                np.abs(Pp[0, 1] * dxv + Pp[1, 1] * dyv + Pp[2, 1] * dzv) +
                np.abs(Pp[0, 2] * dxv + Pp[1, 2] * dyv + Pp[2, 2] * dzv))

    def envelope_sup_vec(self, gvec, ix, iy, iz):
        """一组 (晶粒, 胞) 对的 sup（每对晶粒取自己的取向）。"""
        gvec = np.asarray(gvec, dtype=np.int64)
        out = np.zeros(len(gvec))
        for g in np.unique(gvec):
            m = (gvec == g)
            out[m] = self.envelope_sup(int(g), np.asarray(ix)[m], np.asarray(iy)[m],
                                       np.asarray(iz)[m])
        return out

    def capture_ratio(self, gvec, ix, iy, iz):
        """ratio = l_g / sup_g(x)：无量纲的"该晶粒的包络还差多远"。
        ratio >= 1 表示包络已经覆盖该胞。"""
        Lg = self._ensure_Lg()
        sup = self.envelope_sup_vec(gvec, ix, iy, iz)
        return Lg[np.asarray(gvec, dtype=np.int64)] / np.maximum(sup, 1e-30)

    # ---------------------------------------------------------- 取向阈值表
    def _thr_tables(self):''', "new_methods")

# ---------------------------------------------------------------- 4) step: 推进 l_g
rep('''        Ls = self.L[sl]
        Ls += V[sl] * dt * solid[sl]
        self.L[sl] = Ls''',
'''        Ls = self.L[sl]
        Ls += V[sl] * dt * solid[sl]
        self.L[sl] = Ls
        if self.capture == "envelope":
            self.grow_envelopes(dt, V, front)      # 逐晶粒 l_g 推进（新默认）''', "step_lg")

# ---------------------------------------------------------------- 5) step: 新捕获分支
rep('''        if self.capture == "analytic":
            # ---- 连续八面体判据（种子相对）：去掉格点路径代价的取向偏差 ----''',
'''        if self.capture == "envelope":
            # ---- 新默认：逐晶粒连续包络 + 外延邻接 + 逐胞 argmax（与语句顺序无关）----
            # 候选胞 x 被 g 捕获 <=> sup_g(x) <= l_g 且 x 的 26 邻居里有 g 的胞（外延附着）
            Lg = self._ensure_Lg()
            wsub = (slice(i0, i1), slice(j0, j1), slice(k0, k1))
            gwin = gid[wsub]
            fw = front[wsub]
            if fw.any():
                fi = np.argwhere(fw)
                fg = gwin[fi[:, 0], fi[:, 1], fi[:, 2]]
                bf = best.reshape(-1)
                sf = bsrc.reshape(-1)
                for g in np.unique(fg):
                    g = int(g)
                    if g <= 0 or Lg[g] <= 0.0:
                        continue
                    sel = fi[fg == g]                      # 该晶粒的前沿胞（窗口内）
                    lo = sel.min(0) - 1
                    hi = sel.max(0) + 2
                    lo = np.maximum(lo, 0)
                    hi = np.minimum(hi, (i1 - i0, j1 - j0, k1 - k0))
                    if np.any(hi <= lo):
                        continue
                    gx, gy, gz = np.meshgrid(np.arange(i0 + lo[0], i0 + hi[0]),
                                             np.arange(j0 + lo[1], j0 + hi[1]),
                                             np.arange(k0 + lo[2], k0 + hi[2]),
                                             indexing="ij")
                    sup = self.envelope_sup(g, gx, gy, gz)
                    cand = (gid[gx, gy, gz] == 0) & (sup <= Lg[g])
                    if not cand.any():
                        continue
                    ci = np.argwhere(cand)
                    cx = gx[ci[:, 0], ci[:, 1], ci[:, 2]]
                    cy = gy[ci[:, 0], ci[:, 1], ci[:, 2]]
                    cz = gz[ci[:, 0], ci[:, 1], ci[:, 2]]
                    ok = np.zeros(len(ci), bool)
                    for o, _ in OFFSETS:
                        ox = cx + o[0]; oy = cy + o[1]; oz = cz + o[2]
                        inb = ((ox >= 0) & (ox < self.nx) & (oy >= 0) & (oy < self.ny) &
                               (oz >= 0) & (oz < self.nz))
                        vv = np.zeros(len(ci), np.int32)
                        vv[inb] = gid[ox[inb], oy[inb], oz[inb]]
                        ok |= (vv == g)
                    if not ok.any():
                        continue
                    cx = cx[ok]; cy = cy[ok]; cz = cz[ok]
                    sup_ok = sup[ci[ok, 0], ci[ok, 1], ci[ok, 2]]
                    ratio = Lg[g] / np.maximum(sup_ok, 1e-30)
                    fidx = (cx * self.ny + cy) * self.nz + cz
                    upd = ratio > bf[fidx]             # 平局（测度零）保留先到者=小 gid
                    bf[fidx[upd]] = ratio[upd]
                    sf[fidx[upd]] = g

        if self.capture == "analytic":
            # ---- 连续八面体判据（种子相对）：去掉格点路径代价的取向偏差 ----''', "step_capture")

io.open(P, "w", encoding="utf-8").write(src)
print("已打补丁:", ", ".join(edits))
print("行数 %d -> %d" % (orig.count("\n") + 1, src.count("\n") + 1))