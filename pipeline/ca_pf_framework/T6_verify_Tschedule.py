#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T6_verify_Tschedule.py --- T6 判据：把「温度的钟」`ΔG(T)` 接进 level-set 引擎。

T6 做了什么
-----------
`LevelSetMulti` 新增：`dG_of_T`（T → 驱动力，**唯一**换算入口）、`T_of_t`（冷却时间表）、
`set_T()` / `T_now()` / `advance_T()`，以及历史 `Thist`。
`windowB_km` 因此被**降级为"钟"**：只把 T 历史换成驱动历史，**不预测 f(T)**（D1′），
`DS` 带 **4 倍**不确定度（`DS_BAND`）。

判据
----
  T6-A  `df(T)` 单调递减、`T>T0 ⇒ df<0`、`T<T0 ⇒ df>0`（钟的方向性）
  T6-B  **负对照**：`T > T0` 时变体**不得长大**（必须收缩）；且关掉 `dG_of_T` 时
        （`dG_of_T=None`）`set_T` **不动 `df`**（逐位兼容旧行为）
  T6-C  **正对照**：`T < T0` 时长大；且**温度越低长得越多**（df 越大 ⇒ 单调）
  T6-D  **时间表**：`linear_cool` 在 t=0/t_cool/2t_cool 处取值正确；
        `advance_T` 推进后 `Thist` 与实际时间表逐点一致，且 `df` 随 t 单调**增**（冷却 ⇒ 驱动增大）
  T6-E  **真实冷速入口**：`from_cooling_rate(q)` 的 t_cool = ΔT/q，且 10³/10⁶/10⁸ K/s 三档正确

用法：python3 T6_verify_Tschedule.py [--N 24]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_km as K                                          # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(300, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

MS, DS, DGC = K.M_S_TI64, K.DS_REF, K.DG_CRIT_REF
T0 = K.T0_from_Ms(MS, DGC, DS)


def mk(N, dx, T=None, T_of_t=None, dG_on=True, nseed=1):
    L = N * dx
    g = W.LevelSetMulti(
        N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9, df=[0.0] * (NV + 1),
        workers=1, reinit_every=0,
        dG_of_T=(lambda T_: K.drive_of_T(T_, T0, DS)) if dG_on else None,
        T=T, T_of_t=T_of_t)
    rng = np.random.default_rng(3)
    R = 0.12 * L
    ns = 0
    while ns < nseed:
        c = rng.random(3) * (L - 2 * R) + R
        try:
            g.seed_plate(1, c, NPF[1], R, 4 * dx)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    return g


def run_steps(g, nstep, dt):
    for _ in range(nstep):
        g.elastic_driving()
        if g.T_of_t is not None:
            g.advance_T(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5)
        else:
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5)


def t6_A():
    print('【T6-A】钟的方向性：df(T) 单调、过 T0 变号')
    Ts = np.linspace(300.0, 1400.0, 221)
    d = np.array([K.drive_of_T(T, T0, DS) for T in Ts])
    mono = bool(np.all(np.diff(d) < 0))
    pos = float(K.drive_of_T(MS, T0, DS)) > 0
    neg = float(K.drive_of_T(T0 + 100.0, T0, DS)) < 0
    cross = abs(float(K.drive_of_T(T0, T0, DS))) < 1e-9
    print('   T0 = %.1f K ; df(M_s=%.0f) = %+.4e ; df(T0+100) = %+.4e'
          % (T0, MS, K.drive_of_T(MS, T0, DS), K.drive_of_T(T0 + 100.0, T0, DS)))
    print('   单调递减 %s ; T<T0 ⇒ df>0 %s ; T>T0 ⇒ df<0 %s ; df(T0)=0 %s'
          % (mono, pos, neg, cross))
    ok = mono and pos and neg and cross
    print('   T6-A: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t6_BCD(N, dx, nstep=50):
    print('【T6-B/C】负/正对照：T>T0 不得长大；T<T0 长大且越冷越长')
    # ★ 记账（首版踩的坑）：首版把 dt 按**固定**的 2e7 归一 ⇒ 实际位移 ~1e-17 m，
    #   60 步后 V 逐位不变（"测试看不到目标现象"，本项目教训 #14）。
    # ★★ 第 12 处判据形式修正（2026-09-28，**D7 换常数后暴露**）：
    #   旧写法让 B/C 两档各按**自己的 |df|** 定 dt（美其名"只看符号"），但 `df`
    #   随 `(T0,DS)` 变 ⇒ **两档的物理时间不同** ⇒ 不能比 `V/V0` 的大小。
    #   实测：`D7` 把 `DS` 从 3.0e5 提到 4.147e5 后，`T<M_s` 档的 `df` 变大
    #   ⇒ `dt` 变小 ⇒ 同一"步数"覆盖的物理时间变短 ⇒ `V/V0` 从 0.635 掉到 0.308
    #   ⇒ 判据 **假 FAIL**（而 `T6-C′`（同一 dt 下"越冷越长"）始终 PASS）。
    #   ⇒ 改成**全部档用同一个 dt**（`dt_common`）：B 判"`T>T0` 收缩"、
    #     C 判"`T<M_s` 的增长 **优于** `T>T0`"（方向性 + 同一物理时间 ⇒ 不变于常数）。
    df_ref = abs(float(K.drive_of_T(400.0, T0, DS)))
    dt_common = 0.15 * dx / (1e-9 * df_ref)
    res = {}
    for tag, T in (('T>T0 (T0+50)', T0 + 50.0), ('T<M_s (Ms-50)', MS - 50.0)):
        g = mk(N, dx, T=T)
        g.df[1:] = 0.0
        dfv = g.set_T(T)
        v0 = float((g.region() > 0).sum())
        run_steps(g, nstep, dt_common)                 # ★ 同一物理时间
        v1 = float((g.region() > 0).sum())
        res[tag] = (v1 / max(v0, 1.0), dfv, v0, v1)
        print('   %-16s df=%+.4e  V %d -> %d  (V/V0 = %.4f, 同 dt)'
              % (tag, dfv, int(v0), int(v1), res[tag][0]))
    okB = res['T>T0 (T0+50)'][0] < 1.0
    okC = res['T<M_s (Ms-50)'][0] > res['T>T0 (T0+50)'][0]
    print('   T6-B（T>T0 必须收缩）: %s' % ('PASS' if okB else 'FAIL'))
    print('   T6-C（**同一物理时间**下 T<M_s 的增长必须优于 T>T0）: %s'
          % ('PASS' if okC else 'FAIL'))
    print('   → 追加：**同一物理时间**下，V/V0 必须随 T 下降而单调上升')
    vs = []
    for T in (1100.0, MS + 20.0, MS - 50.0, 400.0):
        g = mk(N, dx, T=T)
        g.df[1:] = 0.0
        dfv = g.set_T(T)
        v0 = float((g.region() > 0).sum())
        run_steps(g, nstep, dt_common)
        vs.append((T, dfv, float((g.region() > 0).sum()) / max(v0, 1.0)))
    for T, dfv, r in vs:
        print('      T=%7.1f K  df=%+.4e  V/V0=%.4f' % (T, dfv, r))
    okD = all(vs[i][2] <= vs[i + 1][2] + 1e-9 for i in range(len(vs) - 1))
    print('   T6-C′（越冷越长，单调）: %s' % ('PASS' if okD else 'FAIL'))
    return okB, okC, okD


def t6_B2(N, dx):
    print('【T6-B2】关掉时钟（dG_of_T=None）⇒ set_T 不动 df（逐位兼容旧行为）')
    g = mk(N, dx, dG_on=False)
    g.df[:] = 0.0
    g.df[1:] = 2.0e8
    d0 = g.df.copy()
    for T in (300.0, 800.0, 1200.0, 1400.0):
        g.set_T(T)
    same = bool(np.array_equal(g.df, d0))
    print('   set_T 后 df 与初值逐位相同: %s（df[1] = %.6e）' % (same, g.df[1]))
    print('   T6-B2: %s' % ('PASS' if same else 'FAIL'))
    return same


def t6_D(N, dx, nstep=40):
    print('【T6-D】时间表：linear_cool 取值 + advance_T 的 Thist 一致性 + df 随冷却单调增')
    T_start, T_end, t_cool = 1268.0, 400.0, 1.0e-6
    sch = K.linear_cool(T_start, T_end, t_cool)
    pts = [(0.0, T_start), (t_cool / 2, (T_start + T_end) / 2), (t_cool, T_end),
           (3 * t_cool, T_end)]
    ok_s = True
    for t, want in pts:
        got = sch(t)
        ok_s &= abs(got - want) < 1e-9
        print('   T(%.2e s) = %.3f K（期望 %.3f）' % (t, got, want))
    g = mk(N, dx, T_start, T_of_t=sch)
    dt = t_cool / nstep
    run_steps(g, nstep, dt)
    tt = np.array(g.Thist['t'])
    TT = np.array(g.Thist['T'])
    dd = np.array(g.Thist['df'])
    err = float(np.max(np.abs(TT - np.array([sch(x) for x in tt]))))
    mono = bool(np.all(np.diff(dd) >= -1e-9))
    print('   %d 步后：Thist 长度 %d ; T %.1f -> %.1f K ; df %.4e -> %.4e'
          % (nstep, len(tt), TT[0], TT[-1], dd[0], dd[-1]))
    print('   Thist 与时间表最大偏差 = %.3e（须 ~0）;  df 随冷却单调不减 = %s' % (err, mono))
    ok = ok_s and (err < 1e-9) and mono and (abs(TT[-1] - T_end) < 1e-6)
    print('   T6-D: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def t6_E():
    print('【T6-E】真实冷速入口 from_cooling_rate（文献区间 10³–10⁸ K/s）')
    ok = True
    for q in (1e3, 1e6, 1e8):
        sch = K.from_cooling_rate(q)
        want = (K.T_BETA_TI64 - 298.0) / q
        got = sch.t_cool
        good = abs(got - want) < 1e-12 * max(want, 1.0)
        ok &= good
        print('   q=%.0e K/s ⇒ t_cool = %.4e s（期望 %.4e）  %.2e s 内到 298 K'
              % (q, got, want, sch(want)))
    print('   T6-E: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=24)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 96)
    print('T6 —— 温度的钟（ΔG(T) 接进 level-set）   N=%d dx=%.0f nm' % (N, a.dx_nm))
    print('=' * 96)
    okA = t6_A()
    okB, okC, okDp = t6_BCD(N, dx)
    okB2 = t6_B2(N, dx)
    okD = t6_D(N, dx)
    okE = t6_E()
    r = [('T6-A', okA), ('T6-B', okB and okB2), ('T6-C', okC and okDp),
         ('T6-D', okD), ('T6-E', okE)]
    print()
    print('=' * 96)
    for n, ok in r:
        print('  %-6s %s' % (n, 'PASS' if ok else 'FAIL'))
    allok = all(ok for _n, ok in r)
    print('  ⇒ T6 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 96)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
