"""_bkr_f3.py —— F3（同变体 α'/α' 低角界面）的**有效迁移率**直接测量。

目的（对应 BLOCK_DERIVATION.md §3.3 / §5.4 / §6.6）：
  · A6：同变体两根"板条"（eps0 逐位相同）时，Δe_el 是否**逐位**为 0（含 elastic_soft=True）；
  · §3.3/§6.6：F3 界面的 M_eff/M0 到底是多少？文档假设 = exp(-3.5) = 0.0302
    （⇒ 需要 n_ref = npref = n*）。而 `_pair_normals` 对同变体对给出的是 **de=0 退化解**
    （Fibonacci 第 0 点，有限值）⇒ facet_nref **不会**回退到 npref ⇒ n_ref 是垃圾向量。

装置：球（场 1，变体 1）在基体（场 2，**同一变体 1**）里 ⇒ 全部界面都是 F3。
  · 纯曲率流：d(R^2)/dt = -4·γ0·M_eff，M_eff = M0·<exp(-β_h·(n·n_ref)^2)>_球面
  · 三臂只差一个因素：n_ref 的来源（无钉扎 / 有守卫回退 npref / 现状垃圾向量）
"""
import os
import sys
import time
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import windowB_surface as W                                       # noqa: E402
from windowB_pf3d import C_cubic, argmin_normal                   # noqa: E402
from windowB_ti64_variants import variants                        # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NPF = {}
for v in range(len(EPS0)):
    NPF[v + 1] = argmin_normal(C, np.asarray(EPS0[v], float))[0]

N, dx = 48, 25e-9
L = N * dx
DF, MOB, BETA = 3.5e8, 1e-9, 3.5
GAM = 0.15
dt = 0.15 * dx / (MOB * DF)
STEPS = 700
R0 = 125e-9                    # 5 dx
V0 = 4.0 / 3.0 * math.pi * R0 ** 3
print('N=%d dx=%.1f nm L=%.0f nm R0=%.0f nm dt=%.4e s steps=%d -> t=%.3e s'
      % (N, dx * 1e9, L * 1e9, R0 * 1e9, dt, STEPS, STEPS * dt))

# 球面平均的解析预测： <exp(-b cos^2)> = ∫_0^1 exp(-b x^2) dx
def sphere_avg(b, nref):
    nref = np.asarray(nref, float)
    nref = nref / np.linalg.norm(nref)
    xs = np.linspace(-1, 1, 200001)
    # 均匀球面上 cos(theta) = n.nref 的密度是 1/2 on [-1,1]
    return float(np.sum(np.exp(-b * xs ** 2)) * (xs[1] - xs[0]) / 2.0)


X = (np.arange(N) + 0.5) * dx
XX, YY, ZZ = np.meshgrid(X, X, X, indexing='ij')
CEN = np.array([L / 2] * 3)
RAD = np.sqrt((XX - CEN[0]) ** 2 + (YY - CEN[1]) ** 2 + (ZZ - CEN[2]) ** 2)

results = {}
for arm in ('b_guard_npref', 'c_asis_garbage'):
    t0 = time.time()
    eps_dup = [np.asarray(EPS0[0], float), np.asarray(EPS0[0], float)]
    g = W.LevelSetMulti(N, L, C=C, eps0=eps_dup, gamma=GAM, Mob=MOB,
                        df=[0.0, DF, DF], workers=4,
                        reinit_every=0, reinit_dt=6.0e-7, reinit_band_cells=6.0)
    g.phi[:] = 1e3
    g.phi[1] = RAD - R0
    g.phi[2] = R0 - RAD
    g.npref = {k: v for k, v in NPF.items()}
    # 保证比对的是同一个变体对 (1,2)
    print('\n---- arm %s ----' % arm)
    print('   ncmath[1,2] = %s' % g.ncmp[1, 2])
    if arm == 'b_guard_npref':
        g.ncmp[1, 2] = np.nan
        g.ncmp[2, 1] = np.nan
        print('   手动把 ncmp[1,2] 设为 NaN（模拟文档 I-2 的守卫）')
    if arm == 'a_nopin':
        beta = 0.0
    else:
        beta = BETA

    # ---- A6：弹性驱动是否逐位相同 ----
    ed = g.elastic_driving()
    d_ed = float(np.max(np.abs(ed[1] - ed[2])))
    _ones = np.ones((N, N, N), np.intp)
    edk, edl = g.elastic_driving_pair(_ones, 2 * _ones)
    d_pair = float(np.max(np.abs(edk - edl)))
    print('   A6  max|ed[1]-ed[2]| = %.3e ；elastic_driving_pair(k=1,l=2) 的 max 差 = %.3e'
          % (d_ed, d_pair))
    print('   A6  elastic_soft=%s（默认值）；Δe_el(F3) %s'
          % (g.elastic_soft, '逐位为 0 ✓' if (d_ed == 0.0 and d_pair == 0.0) else '**非零**'))

    n0 = int((g.region() == 1).sum())
    hist = []
    dG_max_hist = []
    for it in range(1, STEPS + 1):
        g.advance(dt, aniso=0.0, npref=g.npref, band_cells=20,
                  mob_beta=beta, mob_beta_w=0.0, adv_grad='proj2',
                  facet_lam=0.0, norm_smooth=0)
        if it % 10 == 0 or it == 1:
            nc = int((g.region() == 1).sum())
            hist.append((it, nc))
            dG_max_hist.append(float(getattr(g, 'dG_max', np.nan)))
    hist = np.array(hist, float)
    R = (3.0 * hist[:, 1] * dx ** 3 / (4.0 * math.pi)) ** (1.0 / 3.0)
    t = hist[:, 0] * dt
    R2 = R ** 2
    sl = np.polyfit(t, R2, 1)[0]
    # 去掉前 10% 的瞬态后再拟合一次
    k = max(1, int(0.1 * len(t)))
    sl2 = np.polyfit(t[k:], R2[k:], 1)[0]
    nref_used = (NPF[1] if arm == 'b_guard_npref' else g.ncmp[1, 2])
    if arm == 'a_nopin':
        pred_M = MOB
    else:
        pred_M = MOB * sphere_avg(BETA, nref_used)
    pred_slope = -4.0 * GAM * pred_M
    print('   n0=%d  n_end=%d  R: %.1f -> %.1f nm  (ΔR=%.2f nm = %.2f dx)'
          % (n0, hist[-1, 1], R[0] * 1e9, R[-1] * 1e9,
             (R[0] - R[-1]) * 1e9, (R[0] - R[-1]) / dx))
    print('   d(R²)/dt 实测 = %.4e m²/s   (去瞬态 %.4e)' % (sl, sl2))
    print('   预测  = -4γ0·M0·<exp(-β(n·n_ref)²)> = %.4e   ⇒ 比值 %.3f'
          % (pred_slope, sl2 / pred_slope if pred_slope else float('nan')))
    if arm != 'a_nopin':
        print('   （若按文档假设 n_ref=n*、M_eff=exp(-3.5)=%.4f：预测 = %.4e ⇒ 比值 %.3f）'
              % (math.exp(-BETA), -4 * GAM * MOB * math.exp(-BETA),
                 sl2 / (-4 * GAM * MOB * math.exp(-BETA))))
    print('   dG_max 首/末 = %.3e / %.3e J/m³ ；区域 1 胞数 %d -> %d ；耗时 %.0f s'
          % (dG_max_hist[0], dG_max_hist[-1], n0, int(hist[-1, 1]), time.time() - t0))
    results[arm] = dict(slope=float(sl2), nref=np.asarray(nref_used).tolist(),
                        d_ed=d_ed, R0=float(R[0]), Rend=float(R[-1]))

print('\n================ 汇总 ================')
for k, v in results.items():
    print('  %-16s d(R²)/dt = %.4e   n_ref = %s' % (k, v['slope'], np.round(v['nref'], 4)))
