# -*- coding: utf-8 -*-
"""P0.1/P0.2 补丁：给 LevelSetMulti 加「配对相容法向表」与 advance 的 pair_aniso 开关。
   幂等：已打过就跳过。每处插入都断言命中，不静默失败。"""
import io, sys

P = 'windowB_surface.py'
s = io.open(P, encoding='utf-8').read()
orig = s
n_hit = []

# ---------------- 插入 1：__init__ 里建表 ----------------
anchor1 = "    # ---------- 区域与几何 ----------\n"
ins1 = '''        # ---- P0.1 (2026-09-26, LATH_FACET_PLAN 1-主因①-a): 配对相容法向表 ----
        #   物理依据 = MATH_FRAMEWORK 5.6 的 rank-1 不变平面 (lam2(U)=1):
        #   两个变体 k,l 之间的界面应落在它们的不变平面上, 法向
        #       n*(k,l) = argmin_n 0.5 * dEps0 : Lam(C,n) : dEps0,  dEps0 = eps0_k - eps0_l.
        #   旧代码: 任何界面都用 winner 的 npref[k] (= 对**母相**的惯习面)
        #   => 变体-变体界面用错对象. 生产末态 f=0.9001 => 母相只剩 9.99% 面积
        #   => 绝大多数界面用错 => M6 (58.9 deg vs 随机 59.7 deg) 的第一嫌疑.
        self.ncmp = None      # (nreg,nreg,3); 母相相关项与对角项 = nan (调用方 fallback)
        if C is not None and eps0 is not None:
            self.ncmp = self._pair_normals(C, eps0)

'''
assert anchor1 in s, 'anchor1 missing'
if 'self._pair_normals(C, eps0)' not in s:
    s = s.replace(anchor1, ins1 + anchor1, 1)
    n_hit.append('init')

# ---------------- 插入 2：_pair_normals ----------------
anchor2 = "    # ---------- 区域与几何 ----------\n    def region(self):\n"
ins2 = '''    # ---------- 区域与几何 ----------
    @staticmethod
    def _pair_normals(C, eps0, nsamp=600, seed=0):
        """变体-变体配对 (k,l) 的 rank-1 相容法向表 (MATH_FRAMEWORK 5.6).

        返回 (nv+1, nv+1, 3): ncmp[k,l] = argmin_n 0.5 dEps0:Lam(C,n):dEps0.
        母相相关项 (k==0 或 l==0) 与对角项 = nan (物理上不适用, 调用方 fallback 到 npref).
        与 _chk_morph.py 的 M6 用**同一**定义 (那里也按 de = eps0[k-1]-eps0[l-1] 取 argmin).
        """
        from windowB_pf3d import _lam_full
        nv = len(eps0)
        tab = np.full((nv + 1, nv + 1, 3), np.nan)
        rng = np.random.default_rng(seed)
        ns = rng.normal(size=(nsamp, 3))
        ns /= np.linalg.norm(ns, axis=1)[:, None]
        L = np.array([_lam_full(C, n) for n in ns])            # (nsamp,3,3,3,3)
        E = [np.asarray(e, float) for e in eps0]
        for k in range(1, nv + 1):
            for l in range(k + 1, nv + 1):
                de = E[k - 1] - E[l - 1]
                val = 0.5 * np.einsum('ij,sijkl,kl->s', de, L, de)
                tab[k, l] = tab[l, k] = ns[int(np.argmin(val))]
        return tab

    def region(self):
'''
assert anchor2 in s, 'anchor2 missing'
if 'def _pair_normals' not in s:
    s = s.replace(anchor2, ins2, 1)
    n_hit.append('pair_normals')

# ---------------- 插入 3：advance 签名 ----------------
old_sig = "    def advance(self, dt, aniso=0.0, npref=None, gamma0=None, herring=True,\n                adv_grad='upwind', extend='edt', band_cells=20, iface_band=2.0,\n                drag=None, pair_kernel=False, per_field=False):"
new_sig = "    def advance(self, dt, aniso=0.0, npref=None, gamma0=None, herring=True,\n                adv_grad='upwind', extend='edt', band_cells=20, iface_band=2.0,\n                drag=None, pair_kernel=False, per_field=False, pair_aniso=False):"
assert old_sig in s, 'advance signature missing'
if 'per_field=False, pair_aniso=False' not in s:
    s = s.replace(old_sig, new_sig, 1)
    n_hit.append('signature')

# ---------------- 插入 4：pair_aniso 体 ----------------
anchor4 = "        phb = np.take_along_axis(self.phi, larr[None], 0)[0]\n"
ins4 = '''        phb = np.take_along_axis(self.phi, larr[None], 0)[0]
        # ---- P0.2 (2026-09-26): 按**配对**选各向异性参考取向 ------------------
        #   (k,0) 类界面 -> npref[k] (变体对母相的惯习面)
        #   (k,l) 类界面 -> ncmp[k,l] (两变体的不变平面, 见 _pair_normals)
        #   旧写法一律用 winner 的 npref[k] => 在 f->1 时对绝大多数界面用错对象.
        #   界面法向用**差分场** d = phi_k - phi_l 的梯度 (两侧对称, 且就是该界面的法向).
        if pair_aniso and aniso > 0 and getattr(self, 'ncmp', None) is not None:
            gd_ = np.gradient(pha - phb, self.dx)
            gdn_ = np.sqrt(sum(g_ ** 2 for g_ in gd_)) + 1e-30
            ndir_ = np.stack([g_ / gdn_ for g_ in gd_], -1)
            ndir_ = ndir_ / (np.linalg.norm(ndir_, axis=-1, keepdims=True) + 1e-300)
            np_arr = np.full((nreg, 3), np.nan)
            if npref is not None:
                for kk, vv in npref.items():
                    if vv is not None and 0 <= int(kk) < nreg:
                        vv = np.asarray(vv, float)
                        np_arr[int(kk)] = vv / (np.linalg.norm(vv) + 1e-300)
            ncl = self.ncmp
            ki = np.clip(karr, 0, nreg - 1)
            li = np.clip(larr, 0, nreg - 1)
            has_pair = (karr > 0) & (larr > 0)
            nd_ref = np.where(has_pair[..., None], ncl[ki, li],
                              np.where((karr > 0)[..., None], np_arr[ki], np_arr[li]))
            badp = ~np.isfinite(nd_ref).all(-1)
            if badp.any():
                nd_ref = np.where(badp[..., None], np_arr[ki], nd_ref)
            c2p = np.clip(np.einsum('...i,...i->...', ndir_, nd_ref) ** 2, 0.0, 1.0)
            stk = herring_stiffness(c2p, self.gamma if gamma0 is None else gamma0,
                                    aniso, herring)
            self._pair_aniso_used = True
        elif pair_aniso:
            self._pair_aniso_used = False
'''
assert anchor4 in s, 'anchor4 missing'
if 'self._pair_aniso_used' not in s:
    s = s.replace(anchor4, ins4, 1)
    n_hit.append('pair_body')

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
print('patched:', n_hit if n_hit else 'nothing (already applied)')
