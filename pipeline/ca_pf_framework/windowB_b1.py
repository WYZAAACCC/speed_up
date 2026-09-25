#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_b1.py --- B1 子模型（beta -> alpha'）的 **athermal 形核 + 生长** 驱动（T2.1b-8）。

为什么要形核层（WINDOWB_SURFACE_AUDIT §11.7 的实测结论）：
  自协调 12 变体下 sum_v dev(eps0_v) = 0（C4 已验）⇒ 弹性能几乎不随 f 增长
  ⇒ 驱动力不随 f 消失 ⇒ **只靠生长**任何正驱动都推到几何饱和（实测 f ~= 0.96，
    且与驱动无关，5 个驱动点离散仅 0.019）。
  ⇒ α' 的分数 vs T **只能来自 athermal 形核**（HYBRID_FRAMEWORK §8 item 4：形核是输入）。

闭合（KJMA + 线性形核律 ⇒ 自动给出 KM，见 windowB_km 第四节）：
  N_v(T) = alpha_KM (M_s - T)/v_0 ；f(T) = 1 - exp(-N_v v_0) = KM
  **v_0 必须由模型自己量**（由 N_seed 个预置晶核的饱和分数反解），不许猜。

本模块只做三件事：
  1) 建 12 变体 level-set RVE（复用生产路径 windowB_surface.LevelSetMulti）；
  2) 按 T 时间表 **只在降温时** 插入新晶核（athermal；等温不新增）；
  3) 晶核的 **变体选择**：默认 autocatalytic（取当前内应力下弹性驱动最大的变体）。

记账：
  [T] 线性形核律 + KJMA + autocatalytic 选择；[A] alpha_KM 是输入（占位 + 敏感度带）。
  **未做**：真实形核位置的偏好（晶界/先前板条尖端）、Green/Greer 判据、变体选择的
  自催化核（现在用瞬时弹性能贪心近似）。
"""

import numpy as np

import windowB_km as K
from windowB_surface import LevelSetMulti


class B1Athermal(object):
    """B1：athermal 形核 + 生长的 level-set RVE。"""

    def __init__(self, N=32, dx=1e-8, Ms=K.M_S_TI64, alpha=K.ALPHA_KM_REF,
                 v0=None, DS=K.DS_REF, dG_crit=K.DG_CRIT_REF,
                 C_override=None, gamma=0.15, aniso=0.4, herring=True,
                 Mob=1e-9, rfrac=0.22, plate_t_dx=2.0, workers=4, seed=0,
                 npref_n=200, use_elastic=True, policy='autocatalytic',
                 use_literature_variants=True, verbose=False, aniso_elastic=False):
        if v0 is None:
            raise ValueError('B1Athermal: 必须显式给 v0（由饱和分数反解 '
                             'K.v0_from_saturation），不许内部猜')
        self.N, self.dx, self.L = N, dx, N * dx
        self.V = self.L ** 3
        self.Ms, self.alpha, self.v0 = float(Ms), float(alpha), float(v0)
        self.DS, self.dG_crit = float(DS), float(dG_crit)
        self.T0 = K.T0_from_Ms(self.Ms, self.dG_crit, self.DS)
        self.gamma, self.aniso, self.herring = gamma, aniso, herring
        self.Mob, self.rfrac = Mob, rfrac
        self.plate_t = plate_t_dx * dx
        self.workers = workers
        self.use_elastic = use_elastic
        self.policy = policy
        self.verbose = verbose
        self.rng = np.random.default_rng(seed)
        self.npref_n = npref_n
        from windowB_ti64_variants import variants
        eps0, Fs, meta = variants()
        self.eps0 = eps0
        self.nv = len(eps0)
        from windowB_pf3d import C_iso3, C_cubic, _lam_full
        self._lam_full = _lam_full
        if C_override == 'off':
            C = None
        elif C_override is None:
            C = C_cubic(134.0e9, 110.0e9, 36.0e9)
        else:
            C = C_override
        self._C = C
        # 各变体弹性最省能法向（= 晶核取向；与 M2 同一做法）
        self.npref = {}
        if C is not None:
            for v in range(self.nv):
                best, bn = None, None
                for n in self.rng.normal(size=(npref_n, 3)):
                    n = n / np.linalg.norm(n)
                    val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v],
                                                _lam_full(C, n), eps0[v]))
                    if best is None or val < best:
                        best, bn = val, n
                self.npref[v + 1] = bn
        self.aniso_elastic = bool(aniso_elastic)
        g = LevelSetMulti(N, self.L, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                          df=[0.0] * (self.nv + 1), workers=workers,
                          reinit_every=25, aniso_elastic=aniso_elastic)
        g.init_parent()
        self.g = g
        self.n_inserted = 0
        self.hist = dict(t=[], T=[], f=[], n=[], dG=[])

    # ---------------------------------------------------------------- 形核
    def _ed(self):
        if self._C is None:
            return None
        return self.g.elastic_driving()

    def _pick_variant(self, ed, idx):
        """变体选择：默认 autocatalytic = 当前内应力下弹性驱动最大的变体。"""
        if ed is None or self.policy == 'random':
            return int(self.rng.integers(1, self.nv + 1))
        vals = ed[1:, idx[0], idx[1], idx[2]]
        return int(np.argmax(vals)) + 1

    def _seed_nuclei(self, n_new):
        """在**母相**里随机位置插入 n_new 个晶核（板条），返回实际插入数。"""
        g = self.g
        reg = g.region()
        pa = np.argwhere(reg == 0)
        if pa.size == 0:
            return 0
        ed = self._ed()
        R = self.rfrac * self.L
        n_done = 0
        for _ in range(int(n_new)):
            c = pa[self.rng.integers(0, len(pa))] * self.dx + 0.5 * self.dx
            idx = tuple((c / self.dx).astype(int) % self.N)
            k = self._pick_variant(ed, idx)
            nrm = self.npref.get(k)
            if nrm is None:
                nrm = self.rng.normal(size=3)
                nrm = nrm / np.linalg.norm(nrm)
            g.seed_plate(k, c, nrm, R, self.plate_t)
            n_done += 1
        g.init_parent()
        self.n_inserted += n_done
        return n_done

    # ---------------------------------------------------------------- 演化
    def _step_T(self, T):
        g = self.g
        g.df[1:] = -K.dG_chem(T, self.T0, self.DS)        # df>0 = 变体有利（已判决）
        return float(g.df[1])

    def _record(self, t, T, dG):
        g = self.g
        vt = np.array([g.volume(j) for j in range(g.nreg)])
        f = 1.0 - vt[0] / self.V
        self.hist['t'].append(float(t))
        self.hist['T'].append(float(T))
        self.hist['f'].append(float(f))
        self.hist['n'].append(int(self.n_inserted))
        self.hist['dG'].append(float(dG))

    def run(self, t_cool=5.0e-7, T_end=350.0, t_hold=0.0, cfl=0.15,
            band_cells=20, adv_grad='upwind', nrec=10,
            f_target=None, n_max=80, km_tol=0.02):
        """降温 + （可选）保温。返回 hist（含 t/T/f/n/dG 轨迹）。"""
        g = self.g
        self._step_T(self.Ms)
        self._record(0.0, self.Ms, g.df[1])
        v0 = self.Mob * abs(g.df[1]) if g.df[1] != 0 else self.Mob * 1e8
        dt = cfl * self.dx / max(v0, 1e-30)
        t = 0.0
        k = 0
        t_all = t_cool + t_hold
        nrec_steps = max(1, int(nrec))
        next_rec = t_cool / nrec_steps
        while t < t_all:
            if t < t_cool:
                T = self.Ms - (self.Ms - T_end) * (t / t_cool)
            else:
                T = T_end
            dG = self._step_T(T)
            if f_target == 'KM':
                # ★ 路线 (a)：**把 KM 当输入模型**（用户已批准的"KM 形状"路线）。
                #   自协调 RVE 里相容板条没有驱动耗尽（小 alpha 实测 f -> 1.0 而 KM 只有 0.39，
                #   见 audit §11.9）⇒ 第一性的 N_v ∝ (M_s - T) 给不出 f(T)。
                #   这里改为：**形核数当控制量**，让模型自身的 f 跟住 KM(T)；
                #   于是 N(T) 变成**输出**（= 所需的 athermal 形核数密度），可与文献/Greer 比。
                km = 1.0 - np.exp(-self.alpha * max(self.Ms - T, 0.0))
                f_now = 1.0 - self.g.volume(0) / self.V
                while (f_now < km - km_tol and self.n_inserted < n_max
                       and t < t_cool + 1e-30):
                    if self._seed_nuclei(1) == 0:
                        break
                    f_now = 1.0 - self.g.volume(0) / self.V
            else:
                n_tgt = K.N_target(T, self.Ms, self.alpha, self.v0, self.V)
                n_new = int(np.floor(n_tgt)) - self.n_inserted
                if n_new > 0 and t < t_cool + 1e-30:
                    self._seed_nuclei(n_new)
            g.advance(dt, aniso=self.aniso, npref=self.npref, herring=self.herring,
                      adv_grad=adv_grad, band_cells=band_cells, iface_band=2.0)
            ndt = g.suggest_dt(cfl=cfl, dt_prev=dt)
            if ndt:
                dt = ndt
            t += dt
            k += 1
            if t >= next_rec or t >= t_all or k == 1:
                self._record(t, T, dG)
                while next_rec <= t:
                    next_rec += t_cool / nrec_steps
        self.k_used = k
        return self.hist

    def f_N(self):
        return (np.array(self.hist['f']), np.array(self.hist['n']),
                np.array(self.hist['T']), np.array(self.hist['t']))
