#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_cost.py --- ★ 测量「多核 RVE」在给定盒/分辨率下的**真实**计算消耗

为什么要单独测
-------------
此前所有关于 N=384（24 µm / 62.5 nm）的代价都只是**估算**，其中最大的不确定项是
**弹性求解（FFT 微弹性）的内存**——它可能比 `self.phi` 还大。本探针把它变成实测。

走的路径 = `T16_verify_rve.py:run()` 的**同一条重活路径**（逐项照抄，含
`reinit_dt`/`reinit_band_cells`/`elastic_driving()`+`advance(...)` 的参数），
只是把"跑到 f_target"换成"跑固定步数"，以便在几分钟内测完。

⚠ 术语：本处的"多核"= **一个 prior-β 晶粒内的多个变体核**（T16/T24 口径）。
   若指"多个 prior-β 晶粒"，**当前引擎不支持**（`LevelSetMulti` 只有一套
   `eps0/wtab/atab`，即单一母相取向）——那需要引擎改动，本探针不覆盖。

测什么
------
  C-1 **峰值 RSS**（`VmHWM`）—— 决定"跑不跑得动"
  C-2 **逐步耗时** —— 决定"要跑多久"
  C-3 **静态/动态拆分**：构造完成时的 RSS vs 跑起来之后的 RSS
      ⇒ 分清"场存储"与"求解工作数组"各占多少
  C-4 **扫描标度**：用本脚本跑多个 N，报 `s/步` 与 RSS 随 N³ 的比例

用法：
  python3 _probe_cost.py --L-um 24 --dx-nm 62.5 --n0 64 --steps 4
  python3 _probe_cost.py --L-um 24 --dx-nm 125  --n0 64 --steps 6
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF, DF, MOB, R_SEED, T_SEED   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--L-um', type=float, default=24.0)
ap.add_argument('--dx-nm', type=float, default=62.5)
ap.add_argument('--n0', type=int, default=64)
ap.add_argument('--steps', type=int, default=4)
ap.add_argument('--adv', default='proj2')
ap.add_argument('--reinit-band', type=float, default=6.0)
ap.add_argument('--tag', default='')
a = ap.parse_args()


def rss_gb():
    """当前 RSS / 峰值 RSS（VmHWM），单位 GB。Linux /proc。"""
    cur = hwm = float('nan')
    try:
        with open('/proc/self/status') as f:
            for ln in f:
                if ln.startswith('VmRSS:'):
                    cur = float(ln.split()[1]) / 1048576.0
                elif ln.startswith('VmHWM:'):
                    hwm = float(ln.split()[1]) / 1048576.0
    except OSError:
        pass
    return cur, hwm


L = a.L_um * 1e-6
dx = a.dx_nm * 1e-9
N = int(round(L / dx))
ncell = N ** 3
print('=' * 104)
print('_probe_cost  %s' % a.tag)
print('  盒 %.2f µm   Δx %.2f nm   ⇒  N = %d   ⇒  胞数 = %.4g' % (a.L_um, a.dx_nm, N, ncell))
print('  多核 RVE：n0 = %d，核 R=%.0f nm / t=%.0f nm（T16 口径）'
      % (a.n0, R_SEED * 1e9, T_SEED * 1e9))
print('  理论场存储：`phi` = %d 区 × N³ × 8 B = **%.2f GB**（未计工作数组）'
      % (NV + 1, (NV + 1) * ncell * 8 / 2**30))
print('=' * 104)

t0 = time.time()
g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                    df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                    reinit_dt=6.0e-7, reinit_band_cells=(None if a.reinit_band == 0
                                                         else a.reinit_band))
t_build = time.time() - t0
cur, hwm = rss_gb()
print('\nC-3a 构造完成（含 12 个 `argmin_normal` + wtab/atab + ncmp 66 对）：')
print('       耗时 %.1f s ；RSS = %.2f GB ；峰值 = %.2f GB' % (t_build, cur, hwm))

rng = np.random.default_rng(7)
ns = 0
for _ in range(a.n0 * 8):
    if ns >= a.n0:
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
cur, hwm = rss_gb()
print('       播种 %d 个核后：RSS = %.2f GB ；峰值 = %.2f GB' % (ns, cur, hwm))

dt = 0.15 * dx / (MOB * DF)
print('       dt = %.4e s  ⇒  标称位移 %.2f nm/步' % (dt, 0.15 * a.dx_nm))

t1 = time.time()
per = []
for it in range(1, a.steps + 1):
    ts = time.time()
    g.elastic_driving()
    t_ed = time.time() - ts
    g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
              mob_beta=3.5, mob_beta_w=2.3, adv_grad=a.adv)
    t_ad = time.time() - ts
    per.append((t_ed, t_ad))
    cur, hwm = rss_gb()
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / ncell
    print('   [step %-3d] elastic_driving %7.2f s + advance %7.2f s = %7.2f s'
          '   f=%.4f   RSS=%.2f GB  峰值=%.2f GB'
          % (it, t_ed, t_ad - t_ed, t_ad, f, cur, hwm), flush=True)

tt = time.time() - t1
cur, hwm = rss_gb()
ed_m = float(np.mean([x[0] for x in per]))
ad_m = float(np.mean([x[1] - x[0] for x in per]))
print('\n' + '=' * 104)
print('结果（%s）' % (a.tag or '%.2f µm / %.2f nm' % (a.L_um, a.dx_nm)))
print('  C-1 **峰值 RSS = %.2f GB**  （当前 %.2f GB）' % (hwm, cur))
print('  C-2 **步时 = %.2f s/步**（elastic_driving %.2f + advance %.2f），共 %d 步 %.1f s'
      % (ed_m + ad_m, ed_m, ad_m, a.steps, tt))
print('      每胞每步 = %.3e s' % ((ed_m + ad_m) / ncell))
print('  C-3 拆分：构造后 %.2f GB ；播种后 %.2f GB ；跑起来峰值 %.2f GB'
      % (float('nan'), float('nan'), hwm))
print('  C-4 换算到生产：要覆盖 15 µm 标称位移需 %.0f 步  ⇒  **%.1f 小时**'
      % (15000.0 / (0.15 * a.dx_nm), 15000.0 / (0.15 * a.dx_nm) * (ed_m + ad_m) / 3600.0))
print('=' * 104)
