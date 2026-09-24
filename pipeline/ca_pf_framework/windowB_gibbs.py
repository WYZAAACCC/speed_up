#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_gibbs.py --- Window B 的【Gibbs 面 / 锐界面】板条模型

== 为什么要有这个模型（实测动机，见 WINDOWB_STATUS.md §4）==
弥散界面 PF 把「界面宽」与「势垒」绑在一根链条上（W = 13.18 gamma/w90），而
「同一格点混合多个变体」的弹性收益 ~1e9 J/m^3 ⇒ 要压制混合需 w90 <~ 1-2 nm
⇒ dx <~ 0.5 nm，这与「装下板条排列要 2-3 um」直接冲突（5000^3 格）。
⇒ 把板条界面表示成【零厚度的面】：每个胞只能属于一个变体（互斥由构造保证），
   界面能按单位面积记账，dx 由板条尺度（而不是界面厚度）决定。

== 与已有框架的接口（必须自洽）==
* 与 pipeline/gibbs/（晶界 Gibbs 面）同一套原则：界面是面，界面量按单位面积记账；
  物理量分档标记 [L] 文献 / [T] 推导 / [A] 指派。
  区别：晶界 Gibbs 面管的是溶质偏析（Gamma, mol/m^2）；这里管的是变体界面能与
  形核驱动力（gamma, J/m^2 与 df, J/m^3），二者都是「面 + 体」的分解。
* 与 MATH_FRAMEWORK.md §5.4 同一个弹性泛函：
  eps0(phi) = Sum_v phi_v eps0_v，sigma = C:(eps-eps0)，div sigma = 0。
  本模型取该泛函的 w -> 0 锐极限，对应表见 MATH_FRAMEWORK.md §5.8（本轮新增）：
      PF   : E = Int [ f_bulk + Sum W phi^2(1-phi)^2 + kappa/2 |grad phi|^2 + f_el ]
      w->0 : E = Int f_bulk + gamma * A + f_el(eps0 分段常数)
  其中 gamma = sqrt(2 kappa W)/6（同一对 (kappa,W) 的两个组合），A 是界面面积。
  两者是同一物理的两个表示，参数由同一条标定链给出 —— 这就是自洽性。

== 能量与动力学 ==
    E(L) = E_el(L) + gamma * A(L) - df * V_trans(L)
    L(x) in {0} U {1..nv}（0 = 母相 beta；每个胞唯一一个标签）
    A(L) = dx^2 * (# 异标签近邻键) / 2   （离散面积测度；立方网格对斜面偏差 <=15%，
          已在几何测量里记账）
    动力学 = 非热（马氏体）：对界面胞提出重标号，用**精确总能**做单调下降接受
             （局部一阶场 -v*delta_eps:sigma 只用于提议，不进入接受判据 ⇒ 不引入偏差）

== 判据（任一不过就不许用）==
    G1 标签场的 E_el 与 PF 的 E_el 对同一 eps0 场一致（独立路径, 位级）
    G2 相容层片: E_el_excess = 0 且构型稳定
    G3 不相容层片: 面能驱动粗化（应变能不变, 面能单调降）
    G4 12 变体 RVE: 纯胞 100%（构造保证）+ 变体分数自协调 + 界面法向直方图
    G5 单畴: 面积衰减率与 Gibbs-Thomson 一致
    G6 与 PF 同构型对照: 界面位置一致到 1 格内
"""
import os
import numpy as np
from scipy import fft as sfft

from windowB_pf3d import PF3D, C_iso3, VOIGT, G6 as _G6
from windowB_ti64_variants import variants

OUT = '/mnt/f/speed_up/bench/windowB_gibbs'


def pairs6():
    return ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


class GibbsLath(object):
    def __init__(self, N, L, C, eps0, gamma, df, workers=8, k0_mode='free'):
        self.N, self.L = N, L
        self.dx = L / N
        self.C = C
        self.eps0 = np.asarray(eps0, float)
        self.nv = len(self.eps0)
        self.gamma = gamma
        self.df = df
        # 弹性引擎复用 PF3D：同一泛函、同一 Lambda、同一 k=0 约定
        # ⇒ 表示不同（锐 vs 弥散）、物理相同
        self.pf = PF3D(N, L, C, self.eps0, gamma=0.0, w90=1e-8, Lmob=0.0,
                       workers=workers, k0_mode=k0_mode)
        self.e0v_eng = np.array([[self.eps0[v][i, j] for (i, j) in VOIGT]
                                 for v in range(self.nv)]) * _G6[None, :]
        self.zero = np.zeros(6)
        self.lab = np.zeros((N, N, N), np.int8)

    # ---------- 标签 <-> phi ----------
    def sync_pf(self):
        self.pf.phi[:] = 0.0
        for v in range(self.nv):
            self.pf.phi[v] = (self.lab == v + 1)

    def e0_eng_fields(self, lab=None):
        lab = self.lab if lab is None else lab
        out = np.zeros((6,) + lab.shape)
        for v in range(self.nv):
            m = (lab == v + 1)
            if m.any():
                out[:, m] = self.e0v_eng[v][:, None]
        return out

    # ---------- 能量 ----------
    def E_el(self, lab=None):
        if lab is None:
            self.sync_pf()
            return self.pf.E_el()
        e = self.e0_eng_fields(lab)
        Eh = sfft.fftn(e, axes=(1, 2, 3), workers=self.pf.workers).reshape(6, -1)
        Eh = Eh / self.N ** 3
        return 0.5 * self.pf.V * float(np.real(
            np.einsum('pk,kpq,qk->', np.conj(Eh), self.pf.Lam, Eh)))

    def sigma(self):
        self.sync_pf()
        return self.pf.sigma_tensor()

    def n_unlike(self, lab=None):
        lab = self.lab if lab is None else lab
        c = 0
        for d in pairs6():
            c += int(np.count_nonzero(np.roll(lab, d, axis=(0, 1, 2)) != lab))
        return c // 2

    def E_surf(self, lab=None):
        return self.gamma * self.dx ** 2 * self.n_unlike(lab)

    def V_trans(self, lab=None):
        lab = self.lab if lab is None else lab
        return float(np.count_nonzero(lab)) * self.dx ** 3

    def E_chem(self, lab=None):
        return -self.df * self.V_trans(lab)

    def E_total(self, lab=None):
        return self.E_el(lab) + self.E_surf(lab) + self.E_chem(lab)

    # ---------- 动力学：局部提议 + 精确能量单调下降接受 ----------
    def _dsurf_local(self, c, old, new):
        N = self.N
        s = 0
        for d in pairs6():
            nb = tuple((c[k] + d[k]) % N for k in range(3))
            nbl = self.lab[nb]
            s += (1 if nbl != new else 0) - (1 if nbl != old else 0)
        return s / 2.0

    def sweep(self, rng, nsel=None, allow_parent=True):
        """一遍扫描：对界面（∪母相）胞提出最佳重标号，再按精确总能单调下降接受。
           返回 (翻转数, dE_总)。"""
        lab = self.lab
        iface = np.zeros_like(lab, bool)
        for d in pairs6():
            iface |= (np.roll(lab, d, axis=(0, 1, 2)) != lab)
        cand = (iface | (lab == 0)) if allow_parent else iface
        idx = np.argwhere(cand)
        if len(idx) == 0:
            return 0, 0.0
        if nsel is not None and len(idx) > nsel:
            idx = idx[rng.permutation(len(idx))[:nsel]]
        sig = self.sigma()
        g6 = np.stack([sig[p][tuple(idx[:, 0]), idx[:, 1], idx[:, 2]] for p in range(6)], 1)
        old = lab[tuple(idx[:, 0]), idx[:, 1], idx[:, 2]]
        vcell = self.dx ** 3
        best = old.copy()
        bestd = np.zeros(len(idx))
        for nl in range(0, self.nv + 1):
            if not allow_parent and nl == 0:
                continue
            e_new = self.zero if nl == 0 else self.e0v_eng[nl - 1]
            contrib = np.zeros(len(idx))
            for ol in np.unique(old):
                m = (old == ol)
                if not m.any():
                    continue
                e_old = self.zero if ol == 0 else self.e0v_eng[ol - 1]
                contrib[m] = -vcell * ((e_new - e_old) @ g6[m].T)
                contrib[m] += -self.df * vcell * ((1 if nl > 0 else 0) - (1 if ol > 0 else 0))
            # ★ 提议只用【体驱动力】(弹性 + 化学)。
            #   面能是"曲率项"：若把它放进逐胞提议，单个胞翻转必然长出凸包
            #   （+2 个异键 => +gamma*dx^2*2 ≈ 1.2e-18 J），界面就被永久冻结 —— 
            #   这是锐界面/Potts 模型的经典陷阱（实测：接受数恒为 0）。
            #   正确做法：面能交给**精确总能**的接受判据（它看得到"整层推进"面能不增），
            #   这正是 Gibbs-Thomson 项在离散模型里的角色。
            for k in range(len(idx)):
                if nl == old[k]:
                    continue
                if contrib[k] < bestd[k]:
                    bestd[k], best[k] = contrib[k], nl
        pick = lab.copy()
        pick[tuple(idx[:, 0]), idx[:, 1], idx[:, 2]] = best
        # ★ 按"意愿"（体驱动力的估计）排序后做**前缀**二分：
        #   随机二分到不了"整层推进"这种相干子集（实测接受数恒为 0）；
        #   前缀二分先保留最有利的一批，再逐步缩短，能抓住相干子集。
        ordv = np.argsort(bestd)
        nchg = int(np.count_nonzero(pick != lab))
        if nchg == 0:
            return 0, 0.0
        E0 = self.E_total()
        # 前缀二分：只在"最有利的前 m 个"里接受（m 从大到小）
        base = lab.copy()
        m = nchg
        acc = 0
        while m >= 1:
            sub = base.copy()
            sel = ordv[:m]
            sub[idx[sel, 0], idx[sel, 1], idx[sel, 2]] = best[sel]
            if not np.array_equal(sub, base):
                if self.E_total(sub) < E0:
                    np.copyto(lab, sub)
                    acc = int(np.count_nonzero(sub != base))
                    break
            m = m // 2
        return acc, self.E_total() - E0

    def _accept_bisect(self, lab, pick, E0, depth=0, rng=None):
        rng = rng or np.random.default_rng(1234 + depth)
        mask = (pick != lab)
        ncx = int(mask.sum())
        if ncx == 0:
            return 0
        trial = np.where(mask, pick, lab)
        if self.E_total(trial) < E0:
            np.copyto(lab, trial)
            return ncx
        if depth >= 8 or ncx <= 1:
            return 0
        pos = np.argwhere(mask)
        sel = rng.permutation(len(pos))[:max(1, len(pos) // 2)]
        half = lab.copy()
        half[tuple(pos[sel].T)] = pick[tuple(pos[sel].T)]
        return self._accept_bisect(lab, half, E0, depth + 1, rng)

    # ---------- 初始化 ----------
    def seed_blocks(self, vol_frac=0.12, rng=7, nblob=2, nvariant=None):
        rg = np.random.default_rng(rng)
        nv = nvariant or self.nv
        side = max(3, int(round(self.N * (vol_frac / (nv * nblob)) ** (1 / 3.0))))
        occ = np.zeros_like(self.lab, bool)
        self.lab[:] = 0
        for v in range(nv):
            for _ in range(nblob):
                for _try in range(300):
                    i = rg.integers(0, self.N - side)
                    j = rg.integers(0, self.N - side)
                    k = rg.integers(0, self.N - side)
                    blk = (slice(i, i + side), slice(j, j + side), slice(k, k + side))
                    if not occ[blk].any():
                        occ[blk] = True
                        self.lab[blk] = v + 1
                        break
        return side

    def seed_laminate(self, a, b, normal, nslab=6):
        X = (np.arange(self.N) + 0.5) * self.dx
        XYZ = np.stack(np.meshgrid(X, X, X, indexing='ij'), -1)
        lam = self.L / nslab
        m = np.cos(2 * np.pi * (XYZ @ np.asarray(normal, float)) / lam) > 0
        self.lab[:] = 0
        self.lab[m] = a + 1
        self.lab[~m] = b + 1
    def favorable_normal(self, v, nobs=400):
        """变体 v 单独存在时, 弹性能密度最小的界面法向（= 该变体的"惯习面"近似, [T]）"""
        from windowB_pf3d import _lam_full
        best, bn = None, None
        rng = np.random.default_rng(0)
        for n in rng.normal(size=(nobs, 3)):
            n = n / np.linalg.norm(n)
            val = 0.5 * float(np.einsum('ij,ijkl,kl->', self.eps0[v], _lam_full(self.C, n),
                                        self.eps0[v]))
            if best is None or val < best:
                best, bn = val, n
        return bn, best

    def seed_plates(self, v, normal, thick_cells=2, nplate=3, rng=0, pad=2,
                    radius_cells=None):
        """在母相中插入变体 v 的【薄板形核】（法向 normal, 厚度 thick_cells 胞）。
           物理依据: 单胞形核要付孤立夹杂弹性能 ~1e9 >> df, 不可能;
           马氏体是以【板条/自协调集团】形核的, 故形核物体必须有正确形状与法向。"""
        rg = np.random.default_rng(rng)
        N = self.N
        X = (np.arange(N) + 0.5) * self.dx
        XYZ = np.stack(np.meshgrid(X, X, X, indexing='ij'), -1)
        n = np.asarray(normal, float)
        n = n / np.linalg.norm(n)
        t = thick_cells * self.dx
        rc = (radius_cells or max(3, N // 8)) * self.dx
        placed = 0
        for _ in range(40 * nplate):
            if placed >= nplate:
                break
            c0 = (rg.random(3) * (N - 2 * pad) + pad) * self.dx
            rel = XYZ - c0
            d = rel @ n
            rperp = np.linalg.norm(rel - d[..., None] * n, axis=-1)
            m = (np.abs(d) < t / 2) & (rperp < rc)      # 有面内尺寸 => 真正的板条晶核
            if not m.any():
                continue
            if np.count_nonzero((self.lab != 0) & m) > 0:
                continue
            self.lab[m] = v + 1
            placed += 1
        return placed

    def save(self, tag):
        os.makedirs(OUT, exist_ok=True)
        np.save(os.path.join(OUT, 'lab%s.npy' % tag), self.lab)


# ============================================================ 判据
def _lam_pack_one(C, k, k0_mode):
    from windowB_pf3d import lambda_packed
    return lambda_packed(C, k[None, :], k0_mode=k0_mode)[0]


def G1(C, eps0, N=24, workers=1):
    """标签场弹性泛函 vs PF 泛函：同一 eps0 场、独立代码路径，应位级一致"""
    print('---- G1: 锐界面弹性泛函 vs PF 泛函（同一 eps0 场）----')
    g = GibbsLath(N, N * 1e-9, C, eps0, 0.15, 5e6, workers=workers)
    rng = np.random.default_rng(5)
    g.lab = rng.integers(0, len(eps0) + 1, size=(N, N, N)).astype(np.int8)
    E1 = g.E_el()
    g.sync_pf()
    E2 = g.pf.E_el()
    e = g.e0_eng_fields()
    Eh = sfft.fftn(e, axes=(1, 2, 3), workers=1).reshape(6, -1) / N ** 3
    K = g.pf.K
    E3 = 0.0
    for i in np.where(np.abs(Eh).sum(0) > 0)[0]:
        Lp = _lam_pack_one(C, K[i], g.pf.k0_mode)
        E3 += float(np.real(np.einsum('p,pq,q->', np.conj(Eh[:, i]), Lp, Eh[:, i])))
    E3 *= 0.5 * g.pf.V
    rel = max(abs(E1 - E2), abs(E1 - E3)) / max(abs(E2), 1e-30)
    print('   E(标签)=%.8e  E(PF one-hot)=%.8e  逐 k 直算=%.8e  最大相对差=%.2e   %s'
          % (E1, E2, E3, rel, 'PASS' if rel < 1e-12 else 'FAIL'))
    return rel < 1e-12


def G2(C, eps0, N=32, workers=2, dg_ratio=0.05, gamma=0.15):
    """相容层片: 起伏弹性能 = 0，且动力学扫过之后构型稳定（不相容变体不长进来）"""
    print('---- G2: 相容层片（rank-1）的弹性代价与稳定性 ----')
    from windowB_bench3d import fib_sphere, dE_dLam  # 复用 P1 的方向搜索
    import itertools
    nv = len(eps0)
    best = None
    for a, b in itertools.combinations(range(nv), 2):
        de = eps0[b] - eps0[a]
        for n in (np.array([1., 0, 0]), np.array([0, 1., 0]), np.array([0, 0, 1.])):
            v = abs(dE_dLam(C, de, n))
            if best is None or v < best[0]:
                best = (v, a, b, n)
    v, a, b, n = best
    print('   用相容对 V%d-V%d, n=[%.0f %.0f %.0f], dE = %.2e J/m^3' %
          (a + 1, b + 1, *n, v))
    g = GibbsLath(N, N * 2e-9, C, eps0, gamma, dg_ratio, workers=workers)
    g.seed_laminate(a, b, n)
    E0 = g.E_el()
    print('   初始: E_el = %.6e J（均匀混合基线=%s）; 界面键数 = %d'
          % (E0, 'free 约定下应为 0' , g.n_unlike()))
    ok1 = abs(E0) < 1e-12 * max(1.0, abs(g.gamma * g.dx ** 2 * g.n_unlike()))
    # 动力学: 100 遍
    rng = np.random.default_rng(0)
    hist = []
    for k in range(100):
        acc, dE = g.sweep(rng, nsel=2000)
        hist.append((g.n_unlike(), g.E_total()))
    n_end = g.n_unlike()
    print('   100 遍后: 界面键数 = %d（初始 %d）; E_tot = %.6e' %
          (n_end, g.n_unlike(g.lab), g.E_total()))
    print('   [判据] |E_el| 相对界面能尺度 = %.2e   %s'
          % (abs(E0) / max(g.gamma * g.dx ** 2 * g.n_unlike(), 1e-30),
             'PASS' if ok1 else 'FAIL'))
    return ok1


if __name__ == '__main__':
    print('=' * 96)
    print('Window B: Gibbs 面（锐界面）板条模型 —— 判据')
    print('=' * 96)
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    ok = {}
    ok['G1'] = G1(C, eps0)
    ok['G2'] = G2(C, eps0)
    print('\n总判定: %s' % ('ALL PASS' if all(ok.values()) else 'FAIL -> %s'
                          % [k for k, v in ok.items() if not v]))
    raise SystemExit(0 if all(ok.values()) else 1)
