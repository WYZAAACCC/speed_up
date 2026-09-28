#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T16_verify_rve.py --- T16：多核 RVE 的**组织统计**（中段取数 + 已校准量具）。

★ 三条前置约束（来自 `MEASUREMENT_SPEC.md` 与本阶段实测）
--------------------------------------------------------
  R0 量具全部已过正对照：`r_c^var`（变体标记相关长度，T13 正对照 5/5）、
     `M6p`（变体-母相界面法向 vs `npref[k]`，T13-B0 **机器精度** 0/90/45°）、
     三向尺度用 `max−min`（T15 修正，不加 `dx`）。
  R1 **中段取数**：晚段有"长度被盒子夹住 + 界面粗化"（T16 前置实测界面胞数 ×7、
     `p25` 3.5°→18.2°）⇒ 统计只在 `f ∈ [0.25, 0.50]` 取，且带**膨胀守卫**：
     若界面胞数超过 `f=0.25` 时的 1.5 倍，或触发绕盒，立即停止并标注。
  R4 `M6p` 用 **p25**（仓库记账：中位在宽面占比 <50% 时被非宽面污染）；
     整数计数（`N_var`）用 `|ΔN| ≤ 1` 而不是相对门槛。

判据
----
  T16-A **厚度定标**：两个 `N_v`（×1、×3）⇒ `t = r_c^var` 比值 ≈ `3^{-1/3}`（±30%）
  T16-B **取向**：`M6p` **p25 ≤ 20°**（宽面落在惯习面上）
  T16-C **自协调/择优**：`M6p` p25 必须显著低于随机对照（60.1°）
  T16-D **守卫生效**：采样点必须在"未绕盒 + 未粗化"的区间内（如实报告采样时 f）

⚠ 记账（本轮**不做**）：`block` / `packet` 的**尺寸分布**需要"变体对取向差表"
   （仓库 `_audit_m6.py` 的 `m6()` 口径）⇒ 与切面统计一起顺延到 P1 修复后。

用法：python3 T16_verify_rve.py [--L-um 3.2] [--dx-nm 62.5] [--f-target 0.35]
退出码：0 = PASS
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

# ★★★ 2026-09-28 **D7 落实 + 门控判据**：
#   `_probe_growth.py` 实测（单变体板条，60 步）：`Δf=2e8` 有弹性时 `dV/V0` 只有 **0.170**，
#   而**无弹性**是 **1.587** ⇒ **弹性把生长压低 ~9 倍**；`Δf` 提到 `4e8` 后恢复到 0.674。
#   ⇒ `Δf=2e8` 下到 `f=0.10` **物理上不可达**（这也解释了 T16/T24 跑到 2 h 无采样点）。
#   ⇒ 生产改用 **`Δf = 3.5e8`** —— 这正是 **D7 的文献 `ΔG(T)` 在 `T=298 K` 的值**
#     （`drive_of_T(298 K) = 3.512e8 J/m³`）。α′ 在 `M_s=873 K` 以下**持续降温**中长大，
#     室温驱动力是 `M_s` 处的 **3.1 倍**；用 `2e8` 相当于一直停在 ~663 K，
#     **低估了后期生长** ⇒ 改 `3.5e8` **既更可行、也更物理**。
#   ⚠ 记账：`Δf` 本应是温度的时间函数；用单常数是**准静态近似**。本项目取
#     「室温值 3.5e8」为**上界档**、「`M_s` 值 1.128e8」为**下界档**，两个都要报。
DF, MOB = 3.5e8, 1e-9
R_SEED, T_SEED = 3.0e-7, 2.0e-7   # t=200 nm：约束① t/Δx≥3 且更接近文献
N0 = 8


def corr_1e(chi, dx):
    x = chi.astype(np.float64)
    y = x - x.mean()
    F = np.fft.fftn(y)
    ac = np.real(np.fft.ifftn(F * np.conj(F))) / x.size
    ac = np.fft.fftshift(ac)
    ctr = np.array(ac.shape) // 2
    zz, yy, xx = np.indices(ac.shape)
    rr = np.sqrt((xx - ctr[2]) ** 2 + (yy - ctr[1]) ** 2 + (zz - ctr[0]) ** 2)
    nb = int(min(ac.shape) // 2)
    prof = np.full(nb, np.nan)
    for i in range(nb):
        m = (rr >= i) & (rr < i + 1)
        if m.any():
            prof[i] = ac[m].mean()
    if not np.isfinite(prof[0]) or prof[0] <= 0:
        return np.nan
    idx = np.where(prof <= prof[0] / np.e)[0]
    if idx.size == 0:
        return np.nan
    i = int(idx[0])
    if i == 0:
        return 0.0
    t = (prof[i - 1] - prof[0] / np.e) / max(prof[i - 1] - prof[i], 1e-300)
    return float((i - 1 + t) * dx)


def stats(g):
    reg = g.region()
    V = g.L ** 3
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    Sv = float(g.cell_area_geom().sum()) / V
    nvar = int(sum(1 for k in range(1, g.nreg)
                   if float((reg == k).sum()) / g.N ** 3 > 0.005))
    # 厚度：变体标记相关长度（R0 已验证）
    vals = []
    for k in range(1, g.nreg):
        chi = (reg == k)
        if chi.sum() < 8:
            continue
        rc = corr_1e(chi, g.dx)
        if np.isfinite(rc):
            vals.append(rc)
    t_var = float(np.mean(vals)) if vals else np.nan
    # M6p（R0 已验证；R4 用 p25）
    A = []
    for k in range(1, g.nreg):
        mk = (reg == k)
        if not mk.any() or NPF.get(k) is None:
            continue
        m2 = np.zeros(mk.shape, bool)
        for ax in range(3):
            m2 |= (np.roll(reg, 1, axis=ax) == 0)
        iface = mk & m2
        if iface.sum() < 5:
            continue
        gg = np.gradient(g.phi[k], g.dx, edge_order=2)
        gn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
        nrm = np.stack([t / gn for t in gg], -1)[iface]
        nd = np.asarray(NPF[k], float)
        nd = nd / np.linalg.norm(nd)
        A.append(np.degrees(np.arccos(np.clip(np.abs(nrm @ nd), 0, 1))))
    A = np.concatenate(A) if A else np.array([np.nan])
    return dict(f=f, nb=nb, Sv=Sv, nvar=nvar, t=t_var,
                m6p_p10=float(np.nanpercentile(A, 10)),
                m6p_p25=float(np.nanpercentile(A, 25)),
                m6p_med=float(np.nanmedian(A)), n_if=int(A.size))


RAND = 60.1


def run(L, dx, nseed, f_target, adv='central'):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(nseed * 8):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    nb_ref, out = None, None
    _t0 = time.time()
    for it in range(1, 900):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad=adv)
        # ★★ 记账（2026-09-28）：**必须有心跳**。首版整档跑完才打印第一行 ⇒
        #   作业跑到 85 min 时无法判断"是在长"还是"卡住了"（实测 ~40 s/步，
        #   而 f 到 0.05 约需 ~140 步 ⇒ 单档 ~1.5 h）。心跳每 20 步报 `f` 与步时。
        if it % 20 == 0:
            _reg0 = g.region()
            _f0 = 1.0 - float((_reg0 == 0).sum()) / g.N ** 3
            print('       [心跳] step=%-4d f=%.4f  步时=%.1f s  已用=%.1f min'
                  % (it, _f0, (time.time() - _t0) / it, (time.time() - _t0) / 60.0),
                  flush=True)
            # ★★★ W0-5（2026-09-28）：**带健康度**（只读，零引擎改动）。
            #   依据 `_w023.log` 实测：带内 median|∇d2| 120 步退化 26%，而全域 median 恒 0.9999、
            #   全域 max 涨到 4.89（把 reinit 的伪时间步压到 ≈20%）、reinit 触发 4 次无回弹、
            #   告警 0 次 ⇒ 这三个量必须进心跳，否则无法判读作业健康度。
            from _band_health import health as _bh, fmt as _bhf
            _hh = _bh(g)
            if not hasattr(g, '_bh0'):
                g._bh0 = _hh
            print('       ' + _bhf(_hh, base=g._bh0), flush=True)
        if it % 5:
            continue
        # ★★ 性能修正（记账）：**先用便宜的量判 f**（只做一次 argmin + 计数），
        #   只有接近目标 f 时才调用**昂贵**的 `stats()`（12 次 FFT + 12 次梯度）。
        #   首版每 5 步就调 `stats()` ⇒ 在 N=192 上统计开销远超推进，1 h 都跑不完一档。
        regc = g.region()
        f_now = 1.0 - float((regc == 0).sum()) / g.N ** 3
        if f_now < max(0.5 * f_target, 0.02):
            continue
        s = stats(g)
        if nb_ref is None and s['f'] >= 0.5 * f_target:
            nb_ref = s['nb']
        infl = (s['nb'] / nb_ref) if nb_ref else 1.0
        # ★ 修正：用**逐变体**口径（`wrap_axes(None)` 判的是"并集渗流"，
        #   那正是 impingement 的定义 ⇒ 多核下会误报，见 T12_verify_wrap2.py）
        wv = g.wrap_axes_any()
        wrap = len(wv) > 0
        # ★★ Round 97 修（`WINDOWB_AUDIT_REGISTER.md` / 量具审计 **M1**，实测）：
        #   判据 `T16-D` 读 `r[1].get('wrapped', False)`，而 `run()` **从来不写这个键**
        #   ⇒ `all(not False for …)` **恒为 True** ⇒ **T16-D 永远 PASS**。
        #   证据（同一份日志自相矛盾）：`_t16.log` 第 6/10 行打印
        #   「⚠ 守卫触发（逐变体绕盒=…）」，第 17 行却打印「T16-D 守卫未触发：PASS」。
        #   ⇒ 现在把**真实守卫状态**记进返回值。**修后 `_t16.log`/`_t16b.log` 的
        #     "守卫 PASS" 必须重判**（它们当时确实触发过绕盒 ⇒ 那些采样点无效）。
        if wrap or infl > 1.5:
            print('     ⚠ 守卫触发（step %d：**逐变体绕盒**=%s，界面胞数 ×%.2f）⇒ 停止并标注'
                  % (it, wv, infl))
            out = dict(s) if isinstance(s, dict) else dict(out or {})
            out.update(it=it, infl=infl, wrapped=True)
            break
        if s['f'] >= f_target:
            out = s
            out['it'] = it
            out['infl'] = infl
            out['wrapped'] = False
            break
        out = s
        out['it'] = it
        out['infl'] = infl
        out['wrapped'] = False
    out['ns'] = ns
    out.setdefault('wrapped', True)          # 走完循环却没标 ⇒ 保守视为已触发
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-um', type=float, default=3.2)
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--f-target', type=float, default=0.35)
    ap.add_argument('--n0', type=int, default=8,
                    help='基准核数（×1 档）。密度 ρ = n0/L³，须使 L/ρ^(-1/3) ≥ 4')
    ap.add_argument('--adv', default='proj2',
                    help='平流格式。**默认已改为 proj2**（D17，2026-09-28，用户批准）——'
                         'D17 的判定点（球 + 常数驱动，同一物理半径）实测：'
                         'central `R/R_ex−1 = +4.16%%`、粗糙度测度 **2.237**；'
                         'proj2 `−0.54%%`、**0.998** ⇒ **central 会产生界面自发粗化**（P1）。'
                         '⚠ 本行的默认值此前一直是 `central`，而引擎的默认已被 D17 改成 `proj2` '
                         '⇒ **本驱动会静默覆盖掉引擎的默认**（A3「改一半」陷阱的第 3 例，'
                         '2026-09-28 Round 137 发现并修正）。要复现 D17 之前的归档读数才显式传 central。')
    a = ap.parse_args()
    L, dx = a.L_um * 1e-6, a.dx_nm * 1e-9
    print('=' * 100)
    print('T16 —— 多核 RVE 组织统计   L=%.1f µm Δx=%.0f nm  f 目标 %.2f  平流=%s'
          % (a.L_um, a.dx_nm, a.f_target, a.adv))
    print('  R1 中段取数 + 膨胀守卫（界面胞数 >1.5×@f=0.25 或绕盒即停）')
    print('  D12d 盒子下限 L ≥ 4·ρ^(-1/3)；D12e 采样 f≈0.10（刚碰撞）；D16c 判据用 M6p p25')
    rho = a.n0 / L ** 3
    dsp = rho ** (-1 / 3.0)
    print('  种子：n0=%d ⇒ ρ=%.4f /µm³ ⇒ d=ρ^(-1/3)=%.3f µm ⇒ **L/d=%.2f**（判据 ≥4）'
          % (a.n0, rho * 1e-18, dsp * 1e6, L / dsp))
    print('=' * 100)
    rows = []
    for mult in (1, 3):
        print('  --- N_v ×%d（%d 个核）---' % (mult, a.n0 * mult))
        s = run(L, dx, a.n0 * mult, a.f_target, a.adv)
        rows.append((mult, s))
        print('   step=%-4d f=%.4f  界面胞=%-6d（×%.2f）  厚度 r_c^var=%.1f nm  '
              'Sv=%.3e  N_var=%d'
              % (s['it'], s['f'], s['nb'], s['infl'], s['t'] * 1e9, s['Sv'], s['nvar']))
        print('   **M6p** p10=%.1f°  **p25=%.1f°**  中位=%.1f°（随机 %.1f°）  界面点 %d'
              % (s['m6p_p10'], s['m6p_p25'], s['m6p_med'], RAND, s['n_if']), flush=True)
    s1, s3 = rows[0][1], rows[1][1]
    ratio = s3['t'] / max(s1['t'], 1e-30)
    theo = 3.0 ** (-1 / 3.0)
    okA = abs(ratio / theo - 1.0) < 0.30
    okB = (s1['m6p_p25'] <= 20.0) and (s3['m6p_p25'] <= 20.0)
    okC = (s1['m6p_p25'] < RAND - 10.0) and (s3['m6p_p25'] < RAND - 10.0)
    okD = all(not r[1].get('wrapped', False) for r in rows)
    print()
    print('  T16-A 厚度定标：%.1f → %.1f nm，比值 %.3f（理论 %.3f）⇒ %s'
          % (s1['t'] * 1e9, s3['t'] * 1e9, ratio, theo, 'PASS' if okA else 'FAIL'))
    print('  T16-B M6p p25 ≤20°：%.1f° / %.1f° ⇒ %s'
          % (s1['m6p_p25'], s3['m6p_p25'], 'PASS' if okB else 'FAIL'))
    print('  T16-C p25 显著低于随机（差 >10°）：%.1f/%.1f vs %.1f ⇒ %s'
          % (s1['m6p_p25'], s3['m6p_p25'], RAND, 'PASS' if okC else 'FAIL'))
    print('  T16-D 守卫未触发（无绕盒）：%s' % ('PASS' if okD else 'FAIL'))
    print()
    print('  ⚠ 记账：**未做** block/packet 的尺寸分布（需"变体对取向差表"口径），')
    print('     与切面统计一起顺延到 P1 修复后；本轮只出"厚度 + 取向 + 分数"三类。')
    print('=' * 100)
    allok = okA and okB and okC and okD
    print('  ⇒ T16 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
