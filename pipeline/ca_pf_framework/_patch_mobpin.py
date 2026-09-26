# -*- coding: utf-8 -*-
"""P0.4 补丁：给 LevelSetSurface.advance 加**界面迁移率各向异性**（facet pinning）。
   幂等；命中即断言。"""
import io
P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s

old_sig = ("    def advance(self, dt, df=0.0, gamma_eff=None, aniso=0.0, npref=None,\n"
           "                herring=True, band=1.5, adv_grad='upwind2', band_cells=6,\n"
           "                extend='edt', ext_iters=14, ext_refresh=5):")
new_sig = ("    def advance(self, dt, df=0.0, gamma_eff=None, aniso=0.0, npref=None,\n"
           "                herring=True, band=1.5, adv_grad='upwind2', band_cells=6,\n"
           "                extend='edt', ext_iters=14, ext_refresh=5,\n"
           "                mob_aniso=0.0, mref=None):")
assert old_sig in s, 'LevelSetSurface.advance signature not found'
if 'mob_aniso=0.0, mref=None' not in s:
    s = s.replace(old_sig, new_sig, 1)

old_vn = "        vn_if = np.where(m, self.M * (df - gk * kap), 0.0)\n"
new_vn = '''        # ---- P0.4 (2026-09-26, LATH_FACET_PLAN): 界面**迁移率**各向异性 --------------
        #   物理：界面迁移率与界面能一样由界面结构决定；{334} 型惯习面是"好界面"，
        #         其他取向的迁移率被结构缺陷拖低（faceted growth 的标准图像）。
        #   ★ 为什么必须走 M(n) 而不是继续调 gamma(n)：
        #     P0.3 实测（_chk_mroute A-D，df=1e8 = dG_chem(M_s) 的真实值）：
        #       aniso=0 与 aniso=0.9 的 M6 中位**都是 55.4 deg**，参考取向换对/换错也不动
        #     => 在真实驱动力下，"界面能 vs 驱动力"的幅度竞争根本不成立。
        #     而 M(n) 是**动力学**量，**没有热力学凸性约束**（不需要 gamma+gamma_tt>0）
        #     => 各向异性强度可以任意大，不会被 Delta G 淹没。
        #   形式： M(n) = M0 * [1 - mob_aniso * (1 - (n.nref)^2)]
        #     mob_aniso=0   -> 各向同性（返回旧行为，逐位相同）
        #     mob_aniso=1   -> 非法向迁移率 = 0（完全钉扎）
        Mloc = self.M
        if mob_aniso > 0.0 and mref is not None:
            nv_, _gn_ = self.normal()
            nd_ = np.asarray(mref, float)
            nd_ = nd_ / (np.linalg.norm(nd_) + 1e-300)
            ndot2_ = np.clip(sum(nv_[i] * nd_[i] for i in range(3)) ** 2, 0.0, 1.0)
            Mloc = self.M * (1.0 - mob_aniso * (1.0 - ndot2_))
        vn_if = np.where(m, Mloc * (df - gk * kap), 0.0)
'''
assert old_vn in s, 'vn_if line not found'
if 'Mloc = self.M' not in s:
    s = s.replace(old_vn, new_vn, 1)

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('patched LevelSetSurface: mob_aniso')
else:
    print('nothing to do (already applied)')
