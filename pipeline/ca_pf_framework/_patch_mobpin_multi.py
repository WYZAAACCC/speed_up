# -*- coding: utf-8 -*-
"""P0.5 补丁：LevelSetMulti.advance 支持**迁移率各向异性**（mob_aniso / mpin / pin_min）。
   幂等。与 P0.4 的 LevelSetSurface 版同机制，但参考取向走"按配对"（ncmp/npref）。"""
import io
P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s

# --- 1) 签名 ---
old = ("                drag=None, pair_kernel=False, per_field=False, pair_aniso=False):")
new = ("                drag=None, pair_kernel=False, per_field=False, pair_aniso=False,\n"
       "                mob_aniso=0.0, pin_min=True):")
assert old in s
if 'mob_aniso=0.0, pin_min=True' not in s:
    s = s.replace(old, new, 1)

# --- 2) 把参考取向的计算从 "pair_aniso 专用" 改成 "pair_aniso 或 mob_aniso 共用" ---
old2 = "        if pair_aniso and aniso > 0 and getattr(self, 'ncmp', None) is not None:\n"
new2 = ("        _need_ref = (pair_aniso and aniso > 0) or (mob_aniso > 0.0)\n"
        "        nd_ref_ = None\n"
        "        if _need_ref and getattr(self, 'ncmp', None) is not None:\n")
assert old2 in s
if '_need_ref' not in s:
    s = s.replace(old2, new2, 1)

# --- 3) 在 c2p 之后保存 ndir_/nd_ref_，并让 gamma 分支只用 pair_aniso ---
old3 = ("            c2p = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref) ** 2, 0.0, 1.0)\n"
        "            stk = herring_stiffness(c2p, self.gamma if gamma0 is None else gamma0,\n"
        "                                    aniso, herring)\n"
        "            self._pair_aniso_used = True\n"
        "        elif pair_aniso:\n"
        "            self._pair_aniso_used = False\n")
new3 = ("            c2p = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref) ** 2, 0.0, 1.0)\n"
        "            nd_ref_ = nd_ref\n"
        "            if pair_aniso and aniso > 0:\n"
        "                stk = herring_stiffness(c2p, self.gamma if gamma0 is None else gamma0,\n"
        "                                        aniso, herring)\n"
        "            self._pair_aniso_used = True\n"
        "        elif pair_aniso:\n"
        "            self._pair_aniso_used = False\n")
assert old3 in s, 'c2p block not found'
if 'nd_ref_ = nd_ref' not in s:
    s = s.replace(old3, new3, 1)

# --- 4) v_cell 之后乘 M(n) 因子 ---
old4 = ("        # ★★ （本轮修·关键）界面速度的**配对规范形**（跨界面连续化）。\n")
new4 = '''        # ---- P0.5 (2026-09-26): 界面**迁移率**各向异性（facet pinning）----------
        #   物理与 D8 正对照（_chk_m8_mobpin.py，真实驱动力 df=1e8 下）：
        #     gamma(n) 通道被驱动力完全淹没（P0.3），而 M(n) 是**动力学**量、
        #     无热力学凸性约束 => 强度可任意大，实测能把形状取向精确钉住（主轴偏差 0.0 deg）。
        #   形式： M(n) = M0 * [1 - a*(n.n*)^2]        (pin_min=True, 默认)
        #          => n 平行 n* 时迁移率最小（法向长得慢）、面内长得快
        #          => 形状是"沿 n* 法向的薄片" = **板条**的几何（不是"沿 n* 的针"）
        #          这与惯习面物理一致：板条的**宽面**是惯习面，其法向 = n*。
        #      M(n) = M0 * [1 - a*(1-(n.n*)^2)]    (pin_min=False)
        #          => 沿 n* 长得最快 => 形状沿 n* 拉长（"针状"形态）
        #   ⚠ 记账：D8 的 a00..a100 用的是 pin_min=False（当时 mref = 快生长方向），
        #     所以它给的是"沿 mref 拉长"；那组数据证明的是**机制有效**（主轴 0.0 deg、
        #     长径比单调 1.00->2.15），不是"板条已得到"。板条要用 pin_min=True + n*=惯习面法向。
        if mob_aniso > 0.0 and nd_ref_ is not None:
            c2r_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            Mfac = 1.0 - mob_aniso * (c2r_ if pin_min else (1.0 - c2r_))
            v_cell = v_cell * Mfac

        # ★★ （本轮修·关键）界面速度的**配对规范形**（跨界面连续化）。
'''
assert old4 in s, 'v_cell canonical block not found'
if 'P0.5 (2026-09-26)' not in s:
    s = s.replace(old4, new4, 1)

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('patched LevelSetMulti: mob_aniso/pin_min')
else:
    print('nothing to do')
