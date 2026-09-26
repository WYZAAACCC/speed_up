# -*- coding: utf-8 -*-
"""P2 补丁：双轴钉扎 M(n) = M0 exp[-beta_h (n.n_hab)^2 - beta_w (n.w)^2]，
   w = n_hab x a（a = rank-1 分解的位移方向 = 板条长轴；w = 板条宽度方向）。
   幂等。beta_w=0 时回到单轴（旧行为）。"""
import io
P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s

# 1) 静态方法：rank-1 分解 + 每变体的 w 表
anchor = "    @staticmethod\n    def _pair_normals(C, eps0, nsamp=600, seed=0):"
ins = '''    @staticmethod
    def _rank1_axes(eps, nref):
        """对形状应变 eps 做 **rank-1 分解** eps = 0.5*(a n^T + n a^T)，
           并用 nref 选解（分解有**两个**解，取 n 更接近 nref 的那个）。
           返回 (n_hab, a_axis, w_axis)；w = n x a = 板条**宽度方向**。

           物理（MATH_FRAMEWORK 5.6 的 lam2(U)=1 的直接延伸）：
             n = 惯习面法向（大面法向）—— 已被 beta_h 压制
             a = 界面位错的**位移/滑移方向** = 板条**长轴**（不压制）
             w = n x a = 面内垂直方向 = 板条**宽度方向**（第二钉扎轴）
           ★ 记账：a.n 不要求为 0（rank-1 分解中 a.n 正比于 trace(eps)，
             第一版判据误以为要正交，已更正）。判据用**重构误差**。
        """
        eps = np.asarray(eps, float)
        w_, V = np.linalg.eigh(eps)
        o = np.argsort(w_)[::-1]
        w_ = w_[o]; V = V[:, o]
        mu1, mu3 = w_[0], w_[2]
        if mu1 <= 0 or mu3 >= 0:
            return None
        e1, e3 = V[:, 0], V[:, 2]
        r = np.sqrt(-mu3 / mu1)
        cands = []
        for sgn in (+1.0, -1.0):
            n = e1 + sgn * r * e3
            n = n / np.linalg.norm(n)
            a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
            a = a / np.linalg.norm(a)
            cands.append((n, a))
        nd = np.asarray(nref, float); nd = nd / np.linalg.norm(nd)
        best = max(cands, key=lambda t: abs(t[0] @ nd))
        n, a = best
        wv = np.cross(n, a)
        nw = np.linalg.norm(wv)
        if nw < 1e-8:
            wv = np.cross(n, [0.0, 0.0, 1.0])
            nw = np.linalg.norm(wv) + 1e-300
        return n, a, wv / nw

'''
assert anchor in s, 'pair_normals anchor missing'
if '_rank1_axes' not in s:
    s = s.replace(anchor, ins + anchor, 1)

# 2) __init__: 建 wtab（需要 npref -> 由外部传入；这里用弹性最省能法向自算）
anchor2 = "        self.ncmp = None      # (nreg,nreg,3); 母相相关项与对角项 = nan (调用方 fallback)\n"
ins2 = '''        self.ncmp = None      # (nreg,nreg,3); 母相相关项与对角项 = nan (调用方 fallback)
        # ---- P2 (2026-09-26): 每变体的**双轴**（n_hab, w = n_hab x a），a 由 rank-1 分解 ----
        self.wtab = None      # (nreg,3); 母相行 = nan
        if C is not None and eps0 is not None:
            _w = np.full((self.nreg, 3), np.nan)
            _rng = np.random.default_rng(0)
            _ns = _rng.normal(size=(400, 3))
            _ns /= np.linalg.norm(_ns, axis=1)[:, None]
            for _v in range(self.nv):
                _E = np.asarray(eps0[_v], float)
                _val = 0.5 * np.einsum('ij,sijkl,kl->s', _E,
                                       np.array([_lam_full(C, n) for n in _ns]), _E)
                _nref = _ns[int(np.argmin(_val))]
                _R = self._rank1_axes(_E, _nref)
                if _R is not None:
                    _w[_v + 1] = _R[2]
            self.wtab = _w

'''
assert anchor2 in s
if 'self.wtab = None' not in s:
    s = s.replace(anchor2, ins2, 1)
    s = s.replace("        if C is not None and eps0 is not None:\n            self.ncmp = self._pair_normals(C, eps0)",
                  "        if C is not None and eps0 is not None:\n            self.ncmp = self._pair_normals(C, eps0)", 1)

# 3) _lam_full 需在 __init__ 可用
if 'from windowB_pf3d import PF3D, VOIGT, G6 as _G6' in s:
    s = s.replace("            from windowB_pf3d import PF3D, VOIGT, G6 as _G6",
                  "            from windowB_pf3d import PF3D, VOIGT, G6 as _G6, _lam_full", 1)

# 4) 签名加 beta_w
s = s.replace("mob_aniso=0.0, pin_min=True, mob_beta=0.0):",
              "mob_aniso=0.0, pin_min=True, mob_beta=0.0, mob_beta_w=0.0):", 1)

# 5) 应用项：加第二轴
old5 = ("        if mob_beta > 0.0 and nd_ref_ is not None:\n"
        "            c2b_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)\n"
        "            v_cell = v_cell * np.exp(-mob_beta * (c2b_ if pin_min else (1.0 - c2b_)))\n")
new5 = '''        if mob_beta > 0.0 and nd_ref_ is not None:
            c2b_ = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref_) ** 2, 0.0, 1.0)
            # ★ P2：**第二钉扎轴** w = n_hab x a（板条宽度方向）。
            #   只对"变体-母相"界面加（板条成形主要发生在从母相长大的阶段）；
            #   变体-变体界面保持单轴（那里 ncmp 已是不变平面，w 无独立意义）。
            _expo = -mob_beta * (c2b_ if pin_min else (1.0 - c2b_))
            if mob_beta_w > 0.0 and getattr(self, 'wtab', None) is not None:
                ki2 = np.clip(karr, 0, nreg - 1)
                li2 = np.clip(larr, 0, nreg - 1)
                w_of = np.where((karr > 0)[..., None], self.wtab[ki2], self.wtab[li2])
                okw = np.isfinite(w_of).all(-1)
                c2w_ = np.clip(np.einsum('...i,...i->...', ndir_, np.where(
                    okw[..., None], w_of, 0.0)) ** 2, 0.0, 1.0)
                _expo = _expo - mob_beta_w * np.where(okw, c2w_, 0.0)
            v_cell = v_cell * np.exp(_expo)
'''
assert old5 in s, 'beta apply block missing'
s = s.replace(old5, new5, 1)

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('patched: two-axis')
else:
    print('nothing to do')
