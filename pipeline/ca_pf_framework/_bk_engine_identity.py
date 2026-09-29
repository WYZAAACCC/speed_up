#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_engine_identity.py —— 引擎 R-block 改动的**逐位身份 + 活性**判据。

## 改了什么（`git show b00914f6:pipeline/ca_pf_framework/windowB_surface.py` 是改动前版本）

| # | 改动 | 默认行为 |
|---|---|---|
| E-1 | `_pair_normals`：**零应变差**（同变体板条在场层面被复制）⇒ 该表项**保持 NaN** | 只有出现重复 `eps0` 时才触发 |
| E-2 | `__init__` 新增 `self.lath = None` | `None` ⇒ 新路径整段关闭 |
| E-3 | 新增 `facet_gamma_sub(k, lsub, gamma0)` | `lath is None` ⇒ **原样返回 `gamma0`** |
| E-4 | `advance._geom_k` 用 `self.facet_gamma_sub(...)` 取代裸 `gamma0` | 同上 |

## 四条判据

| # | 判据 | 为什么 |
|---|---|---|
| **T-1** | **12 个不同变体 + `lath=None`**：新旧引擎 `phi` **逐位相同** | 证明改动对生产路径**零影响** |
| **T-2** | **复制 `eps0` + `lath=None`**：新旧**必须不同**，且新引擎的 `ncmp` 是 NaN、参考法向回到 `npref` | 这是 E-1 的**目的**；若"相同"说明守卫没生效 |
| **T-3** | 挂 `LathTable` 后 F3 界面刚度**确实**变成 `γ_RS(θ)`（与解析值逐位比） | 证明 E-3/E-4 是**活**的（不是"改了但没接上"，AGENTS §3.1 坑 7 的同类） |
| **T-4** | 挂 `LathTable` vs `lath=None`：`phi` **不逐位相同** | 正对照：证明 T-1 的"相同"不是"两条路都没跑" |

跑法：  python3 _bk_engine_identity.py
"""
import os
import subprocess
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402

OLD_SHA = 'b00914f6'
OLD_FILE = os.path.join(_HERE, '_bk_engine_old.py')

F = []


def ck(tag, ok, det=''):
    print('  %-62s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def dump_old():
    if os.path.exists(OLD_FILE):
        return
    src = subprocess.run(
        ['git', '-C', os.path.dirname(os.path.dirname(_HERE)),
         'show', '%s:pipeline/ca_pf_framework/windowB_surface.py' % OLD_SHA],
        capture_output=True, text=True)
    if src.returncode != 0:
        raise SystemExit('git show 失败：%s' % src.stderr[:300])
    with open(OLD_FILE, 'w', encoding='utf-8') as f:
        f.write(src.stdout)
    print('已导出改动前引擎 -> %s（%d 行）'
          % (os.path.basename(OLD_FILE), src.stdout.count('\n')))


def main():
    dump_old()
    import windowB_surface as NEW
    import _bk_engine_old as OLD
    import windowB_lath as WL
    from T16_verify_rve import C, EPS0, NPF, DF, MOB

    print('=' * 104)
    print('_bk_engine_identity —— 逐位身份判据（旧版 = git %s）' % OLD_SHA)
    print('=' * 104)
    N, L, nstep = 32, 2.0e-6, 8
    dx = L / N
    dt = 0.15 * dx / (MOB * DF)
    n_hab = np.asarray(NPF[1], float); n_hab /= np.linalg.norm(n_hab)
    w_ax = np.asarray(NPF[1], float) * 0.0
    c0 = np.array([L / 2] * 3)

    def build(mod, eps0, nv, npref, gamma=0.15, lath=None):
        g = mod.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=gamma, Mob=MOB,
                              df=[0.0] + [DF] * nv, workers=1, reinit_every=0,
                              reinit_dt=6.0e-7, reinit_band_cells=6.0)
        g.lath = lath
        w = np.asarray(g.wtab[1], float); w = w / np.linalg.norm(w)
        a = np.asarray(g.atab[1], float); a = a / np.linalg.norm(a)
        g.seed_plate(1, c0 - 0.1e-6 * n_hab, n_hab, 0.4e-6, 0.2e-6,
                     elong=2.0, along=a, flat_end=True)
        if nv >= 2:
            # ★ 两片必须**贴合**（中心距 = 厚度 0.2 µm ⇒ 半厚 0.1 µm 各让一半）
            #   否则中间夹着母相 ⇒ **一个 F3 胞都没有** ⇒ 后面所有 F3 判据
            #   都会"PASS 但空转"（本文件第一版就踩了这个坑：κ 读数 0 被误读成
            #   "平面界面 κ≡0"，其实是"根本没有界面"）。
            g.seed_plate(2, c0 + 0.1e-6 * n_hab, n_hab, 0.4e-6, 0.2e-6,
                         elong=2.0, along=a, flat_end=True)
        g.init_parent()
        return g, a

    def n_f3(g):
        reg = g.region()
        m1, m2 = (reg == 1), (reg == 2)
        if not m1.any() or not m2.any():
            return 0
        f3 = np.zeros(reg.shape, bool)
        for axx in (0, 1, 2):
            for sh in (1, -1):
                f3 |= (m1 & np.roll(m2, sh, axis=axx))
                f3 |= (m2 & np.roll(m1, sh, axis=axx))
        return int(f3.sum())

    KW = dict(aniso=0.4, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
              adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05)

    def perturb(g, a_ax, amp_dx=0.5, lam_dx=4.0):
        """给 `phi[2]` 加一条正弦扰动 ⇒ **F3 界面上 κ ≠ 0**。

        ★★ 为什么必须加：`seed_plate` 给的是**精确长方体 SDF**，
          在平面共享面上 `np.gradient` 给出的法向**逐位恒定** ⇒ `κ ≡ 0`（逐位）
          ⇒ `dG = −stk·κ ≡ 0` ⇒ **界面刚度 γ 逐位不起作用**（实测 T-5）。
          不加扰动时"改了 γ 而 phi 不变"**不是 bug，是 κ=0 的必然结果**。
        """
        N = g.N
        ii = np.arange(N)
        rel = [ii[:, None, None] * g.dx, ii[None, :, None] * g.dx,
               ii[None, None, :] * g.dx]
        pa = a_ax[0] * rel[0] + a_ax[1] * rel[1] + a_ax[2] * rel[2]
        bump = (amp_dx * g.dx) * np.cos(2.0 * np.pi * pa / (lam_dx * g.dx))
        band = np.abs(g.phi[2]) < 3.0 * g.dx
        g.phi[2] = g.phi[2] + np.where(band, bump, 0.0)

    def kappa_f3(g, interior=False):
        """F3 胞上的最大 |κ|。★ **必须取 winner 自己的曲率** ——
        `advance` 里 `kap_w` 由 `_geom_k(k)` 用**第 k 个场自己的** ∇φ 算
        （`windowB_surface.py:2521` `curvature_of(k, ...)`）。

        `interior=True` ⇒ **排除与母相相邻的 F3 胞**（即只留"平坦共享面的内部"）。
        ★★ 为什么必须分开量（本文件实测发现）：
          共享面的**内部**是精确平面 ⇒ κ **逐位为 0**；
          但共享面的**周界**（板条端部/侧面，与母相三叉）κ ≠ 0（实测 2.2e7 = 0.36/Δx）。
          ⇒ 「平 F3 界面 κ≡0」这句话**只对内部成立**，写成"整张 F3 界面"是**过强**的。
        """
        reg = g.region()
        m1, m2 = (reg == 1), (reg == 2)
        if not m1.any() or not m2.any():
            return 0.0, 0
        f3 = np.zeros(reg.shape, bool)
        for axx in (0, 1, 2):
            for sh in (1, -1):
                f3 |= (m1 & np.roll(m2, sh, axis=axx))
                f3 |= (m2 & np.roll(m1, sh, axis=axx))
        if interior:
            m0 = (reg == 0)
            nb0 = np.zeros(reg.shape, bool)
            for axx in (0, 1, 2):
                for sh in (1, -1):
                    nb0 |= np.roll(m0, sh, axis=axx)
            f3 = f3 & ~nb0
        if not f3.any():
            return 0.0, 0
        kap = np.zeros(reg.shape)
        for k in np.unique(reg[f3]):
            mk = f3 & (reg == k)
            kap[mk] = g.curvature_of(int(k))[mk]
        return float(np.max(np.abs(kap[f3]))), int(f3.sum())

    # ---------- T-1 12 个不同变体：必须逐位相同 ----------
    print('-' * 104)
    print('T-1  12 个不同变体（生产路径）+ lath=None ⇒ 新旧 phi 逐位相同')
    e12 = [np.asarray(EPS0[v], float).copy() for v in range(12)]
    p12 = {v + 1: np.asarray(NPF[v + 1], float) for v in range(12)}
    ga, aa = build(NEW, e12, 12, p12)
    gb, _ = build(OLD, e12, 12, p12)
    for _ in range(nstep):
        ga.advance(dt, npref=p12, **KW)
        gb.advance(dt, npref=p12, **KW)
    same = np.array_equal(ga.phi, gb.phi)
    ck('T-1.1 phi 逐位相同（np.array_equal）', same,
       'max|Δφ| = %.3e' % (np.max(np.abs(ga.phi - gb.phi)) if not same else 0.0))
    ck('T-1.2 region 逐位相同', np.array_equal(ga.region(), gb.region()),
       'flips=%d' % int((ga.region() != gb.region()).sum()))
    ck('T-1.3 ncmp 逐位相同（无重复 eps0 ⇒ 守卫不触发）',
       np.array_equal(np.nan_to_num(ga.ncmp, nan=-7.7),
                      np.nan_to_num(gb.ncmp, nan=-7.7)),
       'NaN 数 new=%d old=%d'
       % (int(np.isnan(ga.ncmp).sum()), int(np.isnan(gb.ncmp).sum())))

    # ---------- T-2 复制 eps0：新引擎必须**不同**（守卫生效）----------
    print('-' * 104)
    print('T-2  复制 eps0（同变体两根板条）+ lath=None ⇒ 守卫必须生效')
    e2 = [np.asarray(EPS0[0], float).copy(), np.asarray(EPS0[0], float).copy()]
    p2 = {1: np.asarray(NPF[1], float), 2: np.asarray(NPF[1], float)}
    gc, ac = build(NEW, e2, 2, p2)
    gd, _ = build(OLD, e2, 2, p2)
    ck('T-2.0 装置有效：两片贴合 ⇒ F3 胞数 > 0（**守卫：否则后面全是空转**）',
       n_f3(gc) > 0, 'n_f3=%d' % n_f3(gc))
    nan_new = int(np.isnan(gc.ncmp[1, 2]).sum())
    nan_old = int(np.isnan(gd.ncmp[1, 2]).sum())
    ck('T-2.1 新引擎 ncmp[1,2] **全 NaN**（零应变差）', nan_new == 3,
       '%d/3  NaN' % nan_new)
    ck('T-2.2 旧引擎 ncmp[1,2] **非 NaN**（一个无意义的随机法向）',
       nan_old == 0, 'old ncmp[1,2]=%s' % np.array2string(gd.ncmp[1, 2], precision=4))
    # 参考法向：新引擎应回退到 npref
    nref_new = gc.facet_nref(1, np.array([2, 2]), p2)
    ck('T-2.3 新引擎的 F3 参考法向 == npref[1]（惯习面）',
       nref_new is not None and np.allclose(
           np.asarray(nref_new)[0] / np.linalg.norm(np.asarray(nref_new)[0]),
           np.asarray(NPF[1], float) / np.linalg.norm(NPF[1]), atol=1e-12),
       '%s' % np.array2string(np.asarray(nref_new)[0], precision=4))
    k0, n0 = kappa_f3(gc)
    k0i, n0i = kappa_f3(gc, interior=True)
    pred120 = MOB * np.exp(-3.5) * 0.15 * k0 * (120 * dt) / dx
    for _ in range(nstep):
        gc.advance(dt, npref=p2, **KW)
        gd.advance(dt, npref=p2, **KW)
    ck('T-2.4 ★ 由 F3 上**实测** κ 预测的 120 步位移 < 0.05 Δx（§6.6 的正确表述）',
       pred120 < 0.05, 'κ_all=%.3e ⇒ d=%.4f Δx（实测 smoke：0.010 Δx）'
       % (k0, pred120))
    ck('T-2.4b 平坦面的**内部**比**周界**更平（κ_int < κ_all）',
       k0i < k0, 'interior %.3e（%d 胞） < 全部 %.3e（%d 胞）'
       % (k0i, n0i, k0, n0))
    ck('T-2.4c ⚠ 「平坦面内部 κ **逐位为 0**」**过强** —— 实测非 0（有限板条的棱）',
       k0i > 0.0, 'interior max|κ| = %.3e = %.4f/Δx' % (k0i, k0i * dx))
    ck('T-2.5 守卫改了 F3 的 n_ref ⇒ 有 F3 胞的装置上新旧 phi **必须不同**',
       not np.array_equal(gc.phi, gd.phi),
       'max|Δφ| = %.3e m = %.4f Δx'
       % (np.max(np.abs(gc.phi - gd.phi)),
          np.max(np.abs(gc.phi - gd.phi)) / dx))

    # ---------- T-2b **加了扰动之后**：新旧必须不同（守卫生效的真实判据）----------
    print('-' * 104)
    print('T-2b 加正弦扰动（κ≠0）后重做：守卫改的参考法向**必须**体现在结果里')
    ge2, ae2 = build(NEW, e2, 2, p2)
    gd2, _ = build(OLD, e2, 2, p2)
    perturb(ge2, ae2); perturb(gd2, ae2)
    k1, n1 = kappa_f3(ge2, interior=True)
    for _ in range(nstep):
        ge2.advance(dt, npref=p2, **KW)
        gd2.advance(dt, npref=p2, **KW)
    ck('T-2b.1 扰动后**内部** κ ≠ 0（扰动穿透到平坦面内部）', k1 > 0.0,
       'interior max|κ| = %.3e 1/m' % k1)
    ck('T-2b.2 新旧 phi **不同**（守卫真的改了物理）',
       not np.array_equal(ge2.phi, gd2.phi),
       'max|Δφ| = %.3e' % np.max(np.abs(ge2.phi - gd2.phi)))

    # ---------- T-3 挂 LathTable：刚度必须 == γ_RS ----------
    print('-' * 104)
    print('T-3  挂 LathTable ⇒ F3 刚度逐胞 == Read–Shockley γ_RS(θ)')
    lt = WL.LathTable([1, 1], omegas=WL.default_omega(2, 5.0),
                      eps0_var=EPS0, npref_var=NPF, gamma0=0.15)
    th = lt.theta[1, 2]
    gRS = float(WL.gamma_rs(th))
    ge, ae = build(NEW, e2, 2, p2, lath=lt)
    lsub = np.array([0, 1, 2, 2, 1])
    gc_sub = ge.facet_gamma_sub(1, lsub, 0.15)
    ck('T-3.1 有 F3 的胞返回数组且值 == γ_RS(θ)',
       np.ndim(gc_sub) == 1 and abs(gc_sub[3] - gRS) < 1e-15
       and abs(gc_sub[0] - 0.15) < 1e-15,
       'γ_RS(%.4f°)=%.6f；数组=%s'
       % (np.degrees(th), gRS, np.array2string(gc_sub, precision=5)))
    ck('T-3.2 同变体 ⇒ γ_RS > gamma0=0.15（θ 够大）', gRS > 0.15,
       '%.6f vs 0.15' % gRS)
    gnone = build(NEW, e2, 2, p2)                      # lath=None
    ck('T-3.3 lath=None 时 facet_gamma_sub 原样返回标量',
       np.ndim(gnone[0].facet_gamma_sub(1, lsub, 0.15)) == 0
       and abs(float(gnone[0].facet_gamma_sub(1, lsub, 0.15)) - 0.15) < 1e-16,
       '%.6f' % float(gnone[0].facet_gamma_sub(1, lsub, 0.15)))

    # ---------- T-4 活性正对照：挂表 vs 不挂表必须不同 ----------
    print('-' * 104)
    print('T-4  正对照：挂 LathTable 与不挂，必须体现在结果里')
    gf, af = build(NEW, e2, 2, p2, lath=None)
    gg, ag = build(NEW, e2, 2, p2, lath=lt)
    # 4a 单元级：`_stiff_of` 的输出必须按 γ 逐胞缩放
    _g = np.gradient(ge.phi[1], dx, edge_order=2)
    _gn = np.sqrt(sum(x ** 2 for x in _g)) + 1e-30
    _lr = np.full((N, N, N), 2, np.intp)
    s_arr = ge._stiff_of(1, _g, _gn, p2, 0.4,
                         ge.facet_gamma_sub(1, _lr, 0.15), True, 0.0, 0.05)
    s_sca = ge._stiff_of(1, _g, _gn, p2, 0.4, 0.15, True, 0.0, 0.05)
    ratio = (s_arr / s_sca)
    ck('T-4a `_stiff_of` 的输出 == 标量版 × γ_RS/γ0（逐胞）',
       np.ndim(s_arr) >= 1 and np.allclose(ratio, gRS / 0.15, rtol=1e-14),
       'ndim=%d 比值 min/max = %.6f/%.6f  期望 %.6f'
       % (np.ndim(s_arr), ratio.min(), ratio.max(), gRS / 0.15))
    # 4b 端到端：加扰动后 phi 必须不同
    perturb(gf, af); perturb(gg, ag)
    for _ in range(nstep):
        gf.advance(dt, npref=p2, **KW)
        gg.advance(dt, npref=p2, **KW)
    ck('T-4b 扰动后 挂表 vs 不挂 ⇒ phi 不同（**钩子是活的**）',
       not np.array_equal(gf.phi, gg.phi),
       'max|Δφ| = %.3e' % np.max(np.abs(gf.phi - gg.phi)))
    ck('T-4c 两者都有限（不是 NaN 造成的"不同"）',
       bool(np.all(np.isfinite(gg.phi)) and np.all(np.isfinite(gf.phi))))

    print('-' * 104)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 104)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(main())
