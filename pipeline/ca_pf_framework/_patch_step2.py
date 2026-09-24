# -*- coding: utf-8 -*-
"""_patch_step2.py --- Step 1/2：thermal_capture 改顺序无关归属；seed_solid_from_substrate 改各向异性 Voronoi"""
import io, re, sys

P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
src = io.open(P, encoding="utf-8").read()
edits = []

# ---------------- 1) thermal_capture 整体替换 ----------------
NEW_TC = '''    def thermal_capture(self, T, spontaneous=None, mode=None, dt=None):
        """热力学约束: T < T_SOL 的液相胞必须为固相（合金不能在固相线以下长期保持液态）。

        【2026-09-23 审计后重写】旧实现是"按 OFFSETS 顺序的 26 邻域洪泛（最多 6 层）"，实测两个致命问题：
          (1) 归属依赖扫描顺序 —— 碰撞前沿有 0.13~0.31% 的胞换主、晶粒面积 ±10%；
          (2) 洪泛后残留的孤立冷液相会【每胞一颗】自发形核（41^3 盒造出 68578 个 1 胞晶粒）。
        新规则（逐胞 argmax，与语句顺序无关、无层数上限、**不自形核**）：
          每个冷液相胞 x，在【与 x 26 邻接】的固相晶粒里选
              key = (ratio = l_g/sup_g(x) 最大, 然后 sup 最小, 然后 gid 最小)   ← 全序、确定
          · 相邻固相取"归属前的固相图"，所以整步结果与遍历顺序无关；
          · 没有固相邻居的冷液相胞**不**被强行固化（物理上它需要形核，不是"立即变固")，
            只计入 self.n_unresolved —— 下一步前沿推进后它们会有邻居。
        mode:
          "count"（默认）只计数记账；"fail" 一旦出现未归属就抛错（严格档）；
          "spectrum" 走连续形核谱（需 self.bulk_spec=(dT_mean,dT_sigma,N_max) 与 dt）。
        返回 (n_assigned, n_unresolved)。
        """
        if mode is None:
            mode = "none" if spontaneous is False else "count"
        cold = T < T_SOL
        ti = np.argwhere((self.gid == 0) & cold)
        M = len(ti)
        n_th = 0
        n_left = M
        if M:
            Lg = self._ensure_Lg()
            best = np.full(M, -1.0)
            bsup = np.full(M, np.inf)
            bg = np.full(M, 1 << 30, np.int64)
            for o, _ in OFFSETS:
                ox = ti[:, 0] + o[0]; oy = ti[:, 1] + o[1]; oz = ti[:, 2] + o[2]
                inb = ((ox >= 0) & (ox < self.nx) & (oy >= 0) & (oy < self.ny) &
                       (oz >= 0) & (oz < self.nz))
                nb = np.zeros(M, np.int32)
                nb[inb] = self.gid[ox[inb], oy[inb], oz[inb]]
                sn = np.nonzero(nb > 0)[0]
                if not len(sn):
                    continue
                gg = nb[sn].astype(np.int64)
                sup = self.envelope_sup_vec(gg, ti[sn, 0], ti[sn, 1], ti[sn, 2])
                rr = Lg[gg] / np.maximum(sup, 1e-30)
                b_r = best[sn]; b_s = bsup[sn]; b_g = bg[sn]
                upd = (rr > b_r) | ((rr == b_r) & ((sup < b_s) | ((sup == b_s) & (gg < b_g))))
                sel = sn[upd]
                best[sel] = rr[upd]; bsup[sel] = sup[upd]; bg[sel] = gg[upd]
            got = bg < (1 << 30)
            if got.any():
                gi = np.nonzero(got)[0]
                ii, jj, kk = ti[gi, 0], ti[gi, 1], ti[gi, 2]
                self.gid[ii, jj, kk] = bg[gi]
                self.ts[ii, jj, kk] = self.t
                self.Tc[ii, jj, kk] = T[ii, jj, kk]
                n_th = int(got.sum())
                n_left = int(M - n_th)
        if n_left and mode == "spectrum":
            spec = getattr(self, "bulk_spec", None)
            if spec is None:
                raise RuntimeError('thermal_capture: mode="spectrum" 需要 self.bulk_spec=(dT_mean,dT_sigma,N_max)')
            n_new = self.nucleate_bulk(T, spec[0], spec[1], spec[2], dt if dt else 0.0)
            self.n_spont = getattr(self, "n_spont", 0) + int(n_new)
            n_left = int(((self.gid == 0) & cold).sum())
        if n_left and mode == "fail":
            raise RuntimeError(
                "thermal_capture: %d 个 T<T_SOL 的液相胞在 26 邻域里没有固相邻居（无法外延）。"
                "若确实需要形核请设 mode='spectrum' 并给 bulk_spec。" % n_left)
        self.n_thermal = getattr(self, "n_thermal", 0) + n_th
        self.n_unresolved = getattr(self, "n_unresolved", 0) + n_left
        return n_th, n_left
'''
pat = re.compile(r"    def thermal_capture\(self, T, spontaneous=True\):.*?\n        return n_th, n_sp\n", re.S)
if not pat.search(src):
    print("!! thermal_capture 锚点未找到"); sys.exit(1)
src = pat.sub(NEW_TC, src, count=1)
edits.append("thermal_capture")

# ---------------- 2) seed_solid_from_substrate 整体替换 ----------------
NEW_SS = '''    def seed_solid_from_substrate(self, T, T_thresh, max_iter=500):
        """把 T < T_thresh 的胞划为固相, 并把已有晶粒身份按【各向异性 L1 距离】分给它们。

        【2026-09-23 审计后重写】旧版是按 OFFSETS 顺序的 26 邻域洪泛：
          实测打乱顺序会让 **30.16% / 32.84%** 的胞换归属 ⇒ 初始条件不是良定义的；
          而且它是**各向同性**的，丢掉了取向 —— 方向错了：基底晶粒同样是定向凝固的产物。
        新规则（顺序无关 + 带取向）：冷区每个胞归给 min_g sup_g(x) 的晶粒
          （= 各晶粒的 KD 包络"谁先到"；t=0 时 l_g 全为 0、V 相同 ⇒ 就是各向异性 Voronoi）。
        max_iter 只为兼容保留，不再使用。
        """
        cold = T < T_thresh
        n0 = int(((self.gid == 0) & cold).sum())
        seeds = [(g, self.seeds[g]) for g in range(1, len(self.axes))
                 if self.seeds[g] is not None]
        ti = np.argwhere((self.gid == 0) & cold)
        if len(ti) and seeds:
            best = np.full(len(ti), np.inf)
            bg = np.full(len(ti), 1 << 30, np.int64)
            for g, _s in seeds:
                sup = self.envelope_sup(g, ti[:, 0], ti[:, 1], ti[:, 2])
                upd = (sup < best) | ((sup == best) & (g < bg))
                best[upd] = sup[upd]
                bg[upd] = g
            self.gid[ti[:, 0], ti[:, 1], ti[:, 2]] = bg
        done = (self.gid > 0) & cold
        self.ts[done] = -1.0            # 负时间 = t=0 之前就是固相
        self.L[done] = 0.0
        if hasattr(self, "fs"):
            self.fs[done] = 1.0
            self.c_sol[done] = C0_V
            if hasattr(self, "A_liq"):
                self.A_liq[done] = 0.0
                self.c_liq = self.A_liq / np.maximum(1.0 - self.fs, 1e-6)
        return int(n0 - ((self.gid == 0) & cold).sum())
'''
pat2 = re.compile(r"    def seed_solid_from_substrate\(self, T, T_thresh, max_iter=500\):.*?\n        return int\(n0 - \(\(self\.gid == 0\) & cold\)\.sum\(\)\)\n", re.S)
if not pat2.search(src):
    print("!! seed_solid 锚点未找到"); sys.exit(1)
src = pat2.sub(NEW_SS, src, count=1)
edits.append("seed_solid_from_substrate")

# ---------------- 3) step 里的调用点：把 dt 传进去 ----------------
old = 'self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", True))'
new = 'self.thermal_capture(T, spontaneous=getattr(self, "allow_spont", None), dt=dt)'
if old not in src:
    print("!! 调用点未找到"); sys.exit(1)
src = src.replace(old, new)
edits.append("step_call")

io.open(P, "w", encoding="utf-8").write(src)
print("已打补丁:", ", ".join(edits), " 行数 =", src.count("\n") + 1)