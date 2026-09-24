# -*- coding: utf-8 -*-
"""_patch_seedfast.py --- seed_solid_from_substrate 分块 + 距离剪枝（sup>=|Δ| ⇒ 可安全剪枝，结果逐位不变）"""
import io, sys
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/ca3d.py"
s = io.open(P, encoding="utf-8").read()
old = '''        ti = np.argwhere((self.gid == 0) & cold)
        if len(ti) and seeds:
            best = np.full(len(ti), np.inf)
            bg = np.full(len(ti), 1 << 30, np.int64)
            for g, _s in seeds:
                sup = self.envelope_sup(g, ti[:, 0], ti[:, 1], ti[:, 2])
                upd = (sup < best) | ((sup == best) & (g < bg))
                best[upd] = sup[upd]
                bg[upd] = g
            self.gid[ti[:, 0], ti[:, 1], ti[:, 2]] = bg'''
new = '''        ti = np.argwhere((self.gid == 0) & cold)
        M = len(ti)
        if M and seeds:
            best = np.full(M, np.inf)
            bg = np.full(M, 1 << 30, np.int64)
            chunk = 400000
            for g, sg in seeds:
                g = int(g)
                for a in range(0, M, chunk):
                    b = min(a + chunk, M)
                    ix = ti[a:b, 0]; iy = ti[a:b, 1]; iz = ti[a:b, 2]
                    # 精确剪枝: sup_g(x) = Σ_a|p_a·Δ| >= |Δ|（正交基上 Σ|c| >= sqrt(Σc²)），
                    # 所以 |Δ| 已经大于当前最优的胞不可能赢 ⇒ 跳过。结果与不剪枝逐位相同。
                    d2 = ((ix - sg[0])**2 + (iy - sg[1])**2 + (iz - sg[2])**2).astype(np.float64)
                    sub = d2 <= (best[a:b] / self.dx) ** 2
                    if not sub.any():
                        continue
                    tmp_best = best[a:b]; tmp_bg = bg[a:b]
                    tmp_sup = np.full(b - a, np.inf)
                    tmp_sup[sub] = self.envelope_sup(g, ix[sub], iy[sub], iz[sub])
                    upd = sub & ((tmp_sup < tmp_best) | ((tmp_sup == tmp_best) & (g < tmp_bg)))
                    tmp_best[upd] = tmp_sup[upd]
                    tmp_bg[upd] = g
            self.gid[ti[:, 0], ti[:, 1], ti[:, 2]] = bg'''
if old not in s: print("!! 锚点未找到"); sys.exit(1)
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8").write(s)
print("已优化; 行数 =", s.count("\n")+1)