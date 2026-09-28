#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_probe_reinit_onoff.py —— ★★★ **Gate A-1 的判决实验**：`reinit` 到底**有害**还是**有用**还是**白烧机时**？

为什么需要它（已有的证据链）
----------------------------
三条实测已经把 `reinit` 逼到墙角：

1. `_probe_reinit_norm.py` A-6：场退化到 0.8558 后，**100 次 Sussman 迭代只换 Δ=−0.0047**（恢复率 −0.033）；
2. `_probe_drift_ns.py`（`_w023.log`）：带内 120 步退化 26%，而 **4 次 reinit 处曲线完全单调光滑、无回弹**；
   且**告警 0 次**（门槛 0.5 太高）；
3. `T16`/`T24` 冒烟（本轮实测）：真实多变体运行里 **`节流 = _dte/dtau` 只有 6–15%**
   —— 即 **100 次迭代只干了 6–15 次满步的活**。

**但 Gate A-1 要回答的是三个不同的问题，不能混为一谈**：

| 问题 | 判据 |
|---|---|
| **Q1 有没有害？** | `region()` 逐胞翻转（守卫应保证 0）· **界面键数**（`P0-3` 指纹，单次比值）· 带胞数 |
| **Q2 有没有用？** | 带内 `median\|∇d2\|` 在一次 reinit 前后的**变化量**（判据用**前后比较**，不用水平值 —— `R4`/教训 #26） |
| **Q3 花多少机时？** | **ON / OFF 两臂的实测每步墙钟之比** |

**设计（单因素，其余逐字相同）**
* 同一 `seed_plate` + `init_parent()`；
* **ON 臂**：`reinit_every=0, reinit_dt=6.0e-7`（**与四个出数驱动逐字一致**）；
* **OFF 臂**：`reinit_every=0, reinit_dt=None`（⇒ 永不触发，**纯构造参数，不改引擎文件**）；
* 两臂跑同样步数，每 20 步用 `_band_health` 记录；
* 结束时对**同一状态**手动调一次 `reinitialize()`，量 Q1/Q2。

**⚠ 记账**：本探针**不改引擎**（OFF 是通过构造参数实现的），因此**不影响**正在跑的作业的 SHA 归属。

用法：python3 _probe_reinit_onoff.py [--N 96] [--dx-nm 50] [--steps 120] [--el 4]
"""
import os
import sys
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NV, NPF                      # noqa: E402
from _band_health import health, fmt                             # noqa: E402

MOB, DF, KV = 1e-9, 3.5e8, 1
ap = argparse.ArgumentParser()
ap.add_argument('--N', type=int, default=96)
ap.add_argument('--dx-nm', type=float, default=50.0)
ap.add_argument('--steps', type=int, default=120)
ap.add_argument('--el', type=float, default=4.0)
a = ap.parse_args()
N, dx = a.N, a.dx_nm * 1e-9
L = N * dx
print('=' * 108)
print('_probe_reinit_onoff —— Gate A-1 判决：reinit 有害 / 有用 / 白烧机时？')
print('  N=%d Δx=%.1f nm L=%.2f µm steps=%d' % (N, a.dx_nm, L * 1e6, a.steps))
print('=' * 108)

res = {}
for arm, kw in (('ON ', dict(reinit_every=0, reinit_dt=6.0e-7)),
                ('OFF', dict(reinit_every=0, reinit_dt=None))):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, **kw)
    c = np.array([L / 2] * 3)
    nh = np.asarray(NPF[KV], float)
    nh = nh / np.linalg.norm(nh)
    aa = np.asarray(g.atab[KV], float)
    aa = aa - (aa @ nh) * nh
    aa = aa / np.linalg.norm(aa)
    g.seed_plate(KV, c, nh, 300e-9, 200e-9, elong=a.el, along=aa)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    h0 = health(g)
    print('\n---- 臂 %s ----（%s）' % (arm, 'reinit_dt=6.0e-7（同出数驱动）' if kw['reinit_dt']
                                    else 'reinit_dt=None ⇒ 永不触发'))
    print('   step   f        med|∇d2|  全域med  全域max  节流   带胞    界面键  reinit   步时(s)')
    print('   %-5d  %.5f  %.4f   %.4f  %7.2f  %.3f  %-7d %-7d %d/%d     -'
          % (0, float((g.region() > 0).sum()) / N ** 3, h0['med_d2'], h0['gm_all'],
             h0['gmax_all'], h0['throttle'], h0['nband'], h0['bonds'],
             h0['rdone'], h0['rskip']))
    traj, wall = [], 0.0
    for st in range(20, a.steps + 1, 20):
        t0 = time.time()
        for _ in range(20):
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                      mob_beta=3.5, mob_beta_w=2.3, norm_smooth=2)
        el = time.time() - t0
        wall += el
        h = health(g)
        traj.append((st, h))
        print('   %-5d  %.5f  %.4f   %.4f  %7.2f  %.3f  %-7d %-7d %d/%d     %.2f'
              % (st, float((g.region() > 0).sum()) / N ** 3, h['med_d2'], h['gm_all'],
                 h['gmax_all'], h['throttle'], h['nband'], h['bonds'],
                 h['rdone'], h['rskip'], el / 20.0))
    # ---- Q1/Q2：对**同一退化状态**手动做一次 reinit，量立即效果 ----
    reg_b, hb = g.region(), health(g)
    import warnings as _w
    with _w.catch_warnings(record=True) as rec:
        _w.simplefilter('always')
        g.reinitialize()
    ha = health(g)
    reg_a = g.region()
    nw = sum(1 for r in rec if 'pair reinit' in str(r.message))
    res[arm] = dict(traj=traj, wall=wall, hb=hb, ha=ha,
                    flips=int((reg_a != reg_b).sum()), warn=nw,
                    rdone=getattr(g, '_reinit_done', 0),
                    rskip=getattr(g, '_reinit_skipped', 0))
    print('   ── 对该状态手动 reinit 一次 ──')
    print('      `region()` 翻转 = **%d**（守卫应保证 0）' % res[arm]['flips'])
    print('      带内 `med|∇d2|`：%.4f → **%.4f**（Δ = **%+.4f**）'
          % (hb['med_d2'], ha['med_d2'], ha['med_d2'] - hb['med_d2']))
    print('      界面键 %d → %d（**%.4f×**，P0-3 硬门槛 1.2×）'
          % (hb['bonds'], ha['bonds'], ha['bonds'] / max(hb['bonds'], 1)))
    print('      带胞   %d → %d（%.4f×）' % (hb['nband'], ha['nband'],
                                            ha['nband'] / max(hb['nband'], 1)))
    print('      本次 reinit：告警 %d 次；`_reinit_done`=%d `_reinit_skipped`=%d'
          % (nw, res[arm]['rdone'], res[arm]['rskip']))

# ------------------------------------------------------------------ 判决
print('\n' + '=' * 108)
print('【Gate A-1 判决】')
on, off = res['ON '], res['OFF']
d_on = on['traj'][-1][1]['med_d2'] - on['traj'][0][1]['med_d2']
d_off = off['traj'][-1][1]['med_d2'] - off['traj'][0][1]['med_d2']
print('  Q1 有害吗？  ON 臂手动 reinit：`region()` 翻转 **%d**、界面键 **%.4f×**、带胞 **%.4f×**'
      % (on['flips'], on['ha']['bonds'] / max(on['hb']['bonds'], 1),
         on['ha']['nband'] / max(on['hb']['nband'], 1)))
print('  Q2 有用吗？  带内 `med|∇d2|` 一次 reinit 的 Δ = **%+.4f**（恢复率 %+.3f）'
      % (on['ha']['med_d2'] - on['hb']['med_d2'],
         (on['ha']['med_d2'] - on['hb']['med_d2']) / max(1e-9, 1.0 - on['hb']['med_d2'])))
print('  Q2b 长程效果？整段漂移 ON **%+.4f**  vs  OFF **%+.4f**（差 **%+.4f**）'
      % (d_on, d_off, d_on - d_off))
print('  Q3 代价？    %d 步墙钟 ON **%.1f s**  vs  OFF **%.1f s** ⇒ **×%.3f**（ON 多花 %.1f%%）'
      % (a.steps, on['wall'], off['wall'], on['wall'] / max(off['wall'], 1e-9),
         (on['wall'] / max(off['wall'], 1e-9) - 1) * 100))
print('  reinit 触发次数（ON 臂）：**%d** 次 / %d 步' % (on['traj'][-1][1]['rdone'], a.steps))
print('\n  ⇒ 判读（判据全部是**前后比较**与**两臂比较**，不用水平值）：')
_gain = abs(d_on) - abs(d_off)          # >0 ⇒ ON 臂退化更少（reinit 有用）
_cost = on['wall'] / max(off['wall'], 1e-9) - 1.0
print('     **收益**：ON 臂少退化 **%+.4f**，占总退化 **%+.1f%%**'
      % (_gain, 100.0 * _gain / max(abs(d_off), 1e-12)))
print('     **代价**：ON 臂多花墙钟 **%+.1f%%**' % (_cost * 100))
if _cost > 1e-9:
    print('     **性价比** = 收益/代价 = **%.2f**（>1 才划算）'
          % ((_gain / max(abs(d_off), 1e-12)) / _cost))
# ★ 判据不用绝对阈值（本探针第一版用 `|Δ漂移| < 0.02` 打"无影响成立"，
#   而 0.0133 其实是 **6.3%** 的改善 —— 绝对阈值会把"小但真实"读成"没有"。
#   故一律报**比值**，并让读者按代价自行权衡。
if on['flips'] == 0:
    print('     **无害**成立：`region()` 逐胞翻转 0、界面键 %.4f×（P0-3 门槛 1.2×）'
          % (on['ha']['bonds'] / max(on['hb']['bonds'], 1)))
if (_gain / max(abs(d_off), 1e-12)) / max(_cost, 1e-12) < 1.0:
    print('     ⇒ ★ **性价比 < 1（实测 %.2f）**：花的机时多于换回的改善。'
          % ((_gain / max(abs(d_off), 1e-12)) / max(_cost, 1e-12)))
    print('       但**这不等于"该关掉"** —— 根因是`_gmax`把步长压到 1.5%（`_probe_grad_fixpoint.py`），')
    print('       修好统计量的域之后，**同样的代价本应换回大得多的改善**。')
    print('       ⇒ 首选 **Gate A-1 选项①（把 `_gm`/`_gmax` 改为带内）**；③（关掉）作为回退。')
print('  ⚠ 本探针**不改引擎**（OFF 由构造参数实现）⇒ 不影响在跑作业的 SHA 归属。')
print('=' * 108)
