# -*- coding: utf-8 -*-
"""P1' 补丁：把 M(n) 各向异性从**唯象线性形式** a 换成**有物理公式的 beta 形式**
       M(n) = M0 * exp[ -beta * (n.n_hab)^2 ]        (pin_min=True)
   beta = dG_misfit / (k_B T)  —— 见 LATH_FACET_PLAN §9 的标定。
   保留 a 形式作为"线性化对照"（a <-> beta 在小 beta 下等价）。幂等。"""
import io
P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s

# ---- LevelSetMulti: 签名加 mob_beta ----
old = "                mob_aniso=0.0, pin_min=True):"
new = "                mob_aniso=0.0, pin_min=True, mob_beta=0.0):"
assert old in s, 'LevelSetMulti sig'
if 'pin_min=True, mob_beta=0.0' not in s:
    s = s.replace(old, new, 1)

# ---- LevelSetMulti: _need_ref 认 mob_beta ----
old = "        _need_ref = (pair_aniso and aniso > 0) or (mob_aniso > 0.0)\n"
new = "        _need_ref = (pair_aniso and aniso > 0) or (mob_aniso > 0.0) or (mob_beta > 0.0)\n"
assert old in s, 'need_ref'
s = s.replace(old, new, 1)

# ---- LevelSetMulti: 应用 beta 形式 ----
old = "        if mob_aniso > 0.0 and nd_ref_ is not None:\n"
new = '''        # ★★ P1' (2026-09-26): **物理形式** M(n) = M0*exp[-beta*(n.n*)^2]，
        #   beta = dG_misfit/(k_B T)（位移型界面靠界面位错保守滑移迁移：
        #   Olson-Cohen / Christian；位错只能在其滑移面=惯习面内滑移 =>
        #   法向生长必须容纳失配 => 额外激活能 ∝ (n.n_hab)^2 的几何投影）。
        #   标定见 LATH_FACET_PLAN §9：位错环形成能 => beta~3.8；板条纵横比反推 => beta~3.0
        #   => 取 beta=3.5（带 [3,6]）。M_min = 3% M0 => 界面不会被冻结（数值安全）。
        if mob_beta > 0.0 and nd_ref_ is not None:
            c2b_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            v_cell = v_cell * np.exp(-mob_beta * (c2b_ if pin_min else (1.0 - c2b_)))
        if mob_aniso > 0.0 and nd_ref_ is not None:
'''
assert old in s, 'mob_aniso apply'
s = s.replace(old, new, 1)

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('patched LevelSetMulti: mob_beta')
else:
    print('nothing to do')
