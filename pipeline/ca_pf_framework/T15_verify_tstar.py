#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T15_verify_tstar.py --- T15：单核板条的 **`t*` 图景**（决策点 D15a）。

物理图景（计划 §6 T15）
---------------------
`v(n) = M0·exp[−β_h (n·n*)² − β_w (n·w)²]·Δf` ⇒ 形状演化有两个阶段：
  ① **瞬时阶段**：面内长得快、法向长得慢 ⇒ **长/厚上升**，峰值 ≈ `2a₀/(n₀+a₀e^{−β_h})`
  ② **渐近阶段**：趋向 Wulff 包络 ⇒ 长/厚 → **`√(2β_h)·e^{1/2}` = 4.36**（β_h=3.5）
⇒ 预期"**先升到峰值再衰减**"。

★ 本轮先做两条前置（新工作规则）
-------------------------------
  (I) **量具正对照**：三向尺度用 `seed_plate` 的**已知** `a₀/n₀` 校验
      （用"沿三方向的投影极差"，整数胞口径、无插值）
  (II) **可行性估算**：峰值何时到、渐近何时到、盒子够不够
      —— 若渐近阶段落不进盒子，必须**如实声明该判据在本轮预算内不可达**，
      而不是跑一个"看起来衰减了"的结果去凑。

判据
----
  T15-0 **量具正对照**：已知 `2a₀`、`t` 的三档，三向量具误差 < 15%
  T15-A **峰值存在**：`长/厚(t)` 必须出现**内部极大**（先升后降）
  T15-B **峰值量级**：峰值与 `2a₀/(n₀+a₀e^{−β_h})` 差 < 20%
  T15-C **渐近**：与 `√(2β_h)·e^{1/2}` 差 < 15% —— **若预算内不可达则标 INCONCLUSIVE**

用法：python3 T15_verify_tstar.py [--N 96] [--dx-nm 25] [--steps 400]
退出码：0 = PASS / 3 = 含 INCONCLUSIVE
"""
import os
import sys
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

DF, MOB, BH, BW = 2.0e8, 1e-9, 3.5, 2.3
K = 1
WULFF = np.sqrt(2 * BH) * np.exp(0.5)          # 4.357


def axes_of(n_h, k=K):
    n_h = np.asarray(n_h, float)
    n_h = n_h / np.linalg.norm(n_h)
    tmp = np.array([1.0, 0.0, 0.0])
    if abs(tmp @ n_h) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])
    a = np.cross(n_h, tmp)
    a = a / np.linalg.norm(a)
    w = np.cross(n_h, a)
    w = w / np.linalg.norm(w)
    return n_h, w, a                            # 厚方向、宽方向、长方向


def extents(g, ax3, k=K):
    reg = g.region()
    idx = np.argwhere(reg == k)
    if idx.size == 0:
        return None
    p = (idx.astype(float) + 0.5) * g.dx - np.array([g.L / 2] * 3)
    out = []
    for u in ax3:
        s = p @ u
        out.append(float(s.max() - s.min()) + g.dx)     # +dx：极差→尺度
    return np.array(out)                                 # [厚, 宽, 长]


def t15_0(dx):
    """量具正对照：已知 a₀ / t 的板条，三向尺度应 ≈ (t, 2a₀, 2a₀)。"""
    print('【T15-0】三向尺度量具正对照（已知 a₀ / t）')
    L = 2.4e-6
    N = int(round(L / dx))
    ok = True
    for a0_nm, t_nm in ((240, 100), (240, 200), (120, 100)):
        g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=MOB,
                            df=[0.0, DF], workers=1, reinit_every=0)
        n_h = np.asarray(NPF[K], float)
        ax3 = axes_of(n_h)
        g.seed_plate(1, [L / 2] * 3, ax3[0], a0_nm * 1e-9, t_nm * 1e-9)
        g.init_parent()
        e = extents(g, ax3, 1)
        want = np.array([t_nm, 2 * a0_nm, 2 * a0_nm], float) * 1e-9
        dev = np.abs(e - want) / want
        good = bool(dev.max() < 0.15)
        ok &= good
        print('   已知 (t,2a₀,2a₀) = (%3.0f, %3.0f, %3.0f) nm ⇒ 量得 (%5.1f, %5.1f, %5.1f) nm'
              '，最大偏差 %.1f%%  %s'
              % (t_nm, 2 * a0_nm, 2 * a0_nm, e[0] * 1e9, e[1] * 1e9, e[2] * 1e9,
                 100 * dev.max(), 'OK' if good else '✗'))
        del g
    print('  T15-0: %s' % ('PASS' if ok else 'FAIL'))
    return ok


def feasibility(a0, n0, dx):
    """可行性估算：峰值与渐近各需要多少步、多少盒子。"""
    v_fast = MOB * DF                       # m/s（面内）
    v_thick = v_fast * np.exp(-BH)          # 法向（n∥n*，最慢）
    dstep = 0.15 * dx
    peak = 2 * a0 / (n0 + a0 * np.exp(-BH))
    # 峰值时刻：长/厚达到峰值 ⇒ 近似当 2a ≈ peak·2n 时
    t_peak = max(0.0, (peak * 2 * n0 - 2 * a0) / (2 * dstep))
    # 渐近：厚度需要增到 长/WULFF
    n_asym = (a0 + dstep * (t_peak + 2000)) / WULFF    # 粗略：与步数耦合
    steps_asym = max(0.0, (n_asym - n0) / (0.5 * dstep * np.exp(-BH)))
    L_need = 2 * (a0 + 2 * dstep * steps_asym)
    return dict(peak=peak, t_peak=t_peak, steps_asym=steps_asym, L_need=L_need,
                v_thick=v_thick)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=400)
    ap.add_argument('--a0-nm', type=float, default=240.0)
    ap.add_argument('--t-nm', type=float, default=100.0)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    dt = 0.15 * dx / (MOB * DF)
    a0, n0 = a.a0_nm * 1e-9, 0.5 * a.t_nm * 1e-9
    print('=' * 100)
    print('T15 —— 单核 t* 图景   N=%d Δx=%.0f nm L=%.2f µm steps=%d'
          % (N, a.dx_nm, L * 1e6, a.steps))
    print('  a₀=%.0f nm, n₀(thickness/2)=%.0f nm ⇒ 初始 长/厚 = %.2f'
          % (a.a0_nm, a.t_nm / 2, a0 / n0))
    print('  β_h=%.1f ⇒ 预测峰值 = 2a₀/(n₀+a₀e^{−β}) = %.2f ; Wulff 渐近 = √(2β)e^{1/2} = %.2f'
          % (BH, 2 * a0 / (n0 + a0 * np.exp(-BH)), WULFF))
    print('=' * 100)
    ok0 = t15_0(dx)

    fs = feasibility(a0, n0, dx)
    print()
    print('【T15-可行性】估算（新工作规则：先算"能不能看到"）')
    print('  面内速度 %.3e m/s；法向速度 %.3e m/s（= 面内 × e^{−β_h} = %.3f）'
          % (MOB * DF, fs['v_thick'], np.exp(-BH)))
    print('  峰值预计在 ~%.0f 步；**渐近阶段需要 ~%.0f 步**，'
          '那时板条长 ~%.1f µm ⇒ 需要 L ≳ %.1f µm'
          % (fs['t_peak'], fs['steps_asym'], fs['L_need'] * 1e6, fs['L_need'] * 1e6))
    print('  当前盒子 L=%.2f µm, 预算 %d 步 ⇒ 渐近阶段**%s**'
          % (L * 1e6, a.steps,
             '可达' if (fs['steps_asym'] <= a.steps and fs['L_need'] <= L) else '**不可达**'))

    print()
    print('【T15-A/B】长/厚(t) 轨迹')
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    n_h = np.asarray(NPF[K], float)
    ax3 = axes_of(n_h)
    g.seed_plate(K, [L / 2] * 3, ax3[0], a0, a.t_nm * 1e-9)
    g.init_parent()
    traj = []
    wrapped = False
    for it in range(1, a.steps + 1):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=BH, mob_beta_w=BW)
        if it % 20 == 0:
            e = extents(g, ax3, K)
            if e is None:
                break
            ar = e[2] / max(e[0], 1e-30)
            traj.append((it, e[0] * 1e9, e[2] * 1e9, ar))
            if g.wrap_axes(K):
                wrapped = True
                print('  ⚠ step %d 起**绕盒** ⇒ 长度读数失效，停止记录' % it)
                break
    print('  step   厚(nm)   长(nm)   长/厚')
    for it, th, ln, ar in traj:
        print('  %-6d %-8.1f %-8.1f %.3f' % (it, th, ln, ar))
    ars = np.array([t[3] for t in traj])
    if ars.size < 5:
        print('  ⚠ 轨迹太短 ⇒ 不作判定')
        return 2
    imax = int(np.argmax(ars))
    peak_meas = float(ars[imax])
    peak_theo = 2 * a0 / (n0 + a0 * np.exp(-BH))
    has_peak = 0 < imax < ars.size - 1 and ars[imax] > ars[0] and ars[imax] > ars[-1]
    okA = has_peak
    okB = abs(peak_meas / peak_theo - 1.0) < 0.20
    print()
    print('  峰值：实测 %.3f（第 %d 个采样点）; 理论 %.3f ⇒ 偏差 %.1f%%（判据 <20%%）'
          % (peak_meas, imax, peak_theo, 100 * abs(peak_meas / peak_theo - 1)))
    print('  内部极大（先升后降）: %s' % has_peak)
    print('  末态 长/厚 = %.3f（Wulff %.2f；偏差 %.1f%%）'
          % (ars[-1], WULFF, 100 * abs(ars[-1] / WULFF - 1)))
    print('  T15-A: %s' % ('PASS' if okA else 'FAIL'))
    print('  T15-B: %s' % ('PASS' if okB else 'FAIL'))
    reachable = (fs['steps_asym'] <= a.steps) and (fs['L_need'] <= L)
    okC = None
    if reachable:
        okC = abs(ars[-1] / WULFF - 1.0) < 0.15
        print('  T15-C: %s' % ('PASS' if okC else 'FAIL'))
    else:
        print('  T15-C: **INCONCLUSIVE** —— 渐近阶段在本轮盒子/步数预算内不可达'
              '（需要 ~%.0f 步、L ≳ %.1f µm）' % (fs['steps_asym'], fs['L_need'] * 1e6))
    if wrapped:
        print('  ⚠ 本轮出现绕盒 ⇒ T15-A/B 的"长"读数在绕盒后已失效（已停止记录）')
    print()
    print('=' * 100)
    print('  T15-0 %s | T15-A %s | T15-B %s | T15-C %s'
          % tuple('PASS' if x else ('INCONCLUSIVE' if x is None else 'FAIL')
                  for x in (ok0, okA, okB, okC)))
    allok = ok0 and okA and okB and (okC is not False)
    print('  ⇒ T15 %s' % ('PASS' if allok and okC else
                          ('PASS(含 T15-C 未定)' if allok else 'FAIL')))
    print('=' * 100)
    return 0 if (allok and okC) else (3 if allok else 1)


if __name__ == '__main__':
    sys.exit(main())
