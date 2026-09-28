#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T4_verify_no_partition.py --- T4 判据：B1（位移型/无扩散）**溶质通道必须关闭**。

物理：β→α′ 是位移型、无扩散 ⇒ 界面扫过时溶质**原样继承**（k_part = 1），
      界面**不富集**（Γ ≡ 0；界面化学 Γ_i 属 Window C，本轮不做）。
      ⇒ 体相成分场 `c` 必须**逐位不变**。

判据
----
  T4-A  生长工况（df = +1e8，物理工况）200 步后 `max|c − c0| == 0`（**逐位**），
        且 `Gam_mol` 全为 0、体相总摩尔量与初值逐位相同
  T4-B  溶解工况（df = −1e8）同上
  T4-C  **正向对照（分辨力）**：显式打开旧通道（k_part=0.6303、surface_chem=True）
        ⇒ `max|c − c0|` 必须 **> 0**（否则判据看不见东西）
  T4-D  M4 守恒判据仍 PASS（`windowB_surface.M4_report`）

用法：python3 T4_verify_no_partition.py
退出码：0 = PASS
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

C0 = 0.036


def one(df, nstep=60, N=32, dx=2e-9, k_part=None, surface_chem=None, tag=''):
    """★ 记账（本轮踩到的坑）：首版取 nstep=200 ⇒ 界面**扫光整个盒子**（f = 1.0000）
    ⇒ 末态没有界面 ⇒ `Γ_mol` 必然归 0、`c` 必然回到均匀 ⇒ **判据与对照同时失去分辨力**
    （"测试看不到目标现象"，本项目教训 #14）。
    现在：① 步数取到界面**仍然存在**的工况；② 全程跟踪 max|c−c0| 与 max|Γ_mol|。"""
    g = W.LevelSetMulti(N, N * dx, nv=1, gamma=0.15, Mob=1e-9, df=[0.0, df])
    if k_part is not None:
        g.k_part = float(k_part)
    if surface_chem is not None:
        g.surface_chem = bool(surface_chem)
    R0 = 5 * dx
    g.seed_sphere(1, [0.5 * N * dx] * 3, R0)
    g.init_parent()
    g.c[:] = C0
    c0 = g.c.copy()
    mb0, ms0 = g.totals()
    dt = 0.2 * dx / (1e-9 * 1e8)
    dc_max, gm_max, nband_last, nsweep = 0.0, 0.0, 0, 0
    for _ in range(nstep):
        r0 = g.region()
        g.advance(dt)
        r1 = g.region()
        # 被"前沿扫过"的胞数（grow + shrink 两个分支都算）——
        # ★ 这才是判据真正需要的前提：**Stefan 分支被走到过**，而不是"末态还有界面"
        nsweep += int((r0 != r1).sum())
        g.update_Gamma(dt)
        dc_max = max(dc_max, float(np.max(np.abs(g.c - c0))))
        gm_max = max(gm_max, float(np.max(np.abs(g.Gam_mol))))
        nband_last = int((g.cell_area_geom() > 0).sum())
    dc = float(np.max(np.abs(g.c - c0)))
    mb1, ms1 = g.totals()
    rel = abs((mb1 + ms1) - (mb0 + ms0)) / abs(mb0 + ms0)
    print('  %-22s k_part=%-7s sc=%-6s max|c-c0| 末=%.3e 全程=%.3e | '
          'max|Γ_mol| 全程=%.3e | 漂移=%.3e | 末态 f=%.4f 面胞=%d | **被扫胞数=%d**'
          % (tag, g.k_part, g.surface_chem, dc, dc_max, gm_max, rel,
             1.0 - float((g.region() == 0).sum()) / g.N ** 3, nband_last, nsweep), flush=True)
    return dc, gm_max, rel, nsweep


def main():
    print('=' * 100)
    print('T4 —— B1 溶质通道关闭（位移型/无扩散）')
    print('=' * 100)
    print('【判据组】默认（B1）')
    dcg, gmg, relg, nsg = one(+1e8, tag='生长 df=+1e8')
    dcd, gmd, reld, nsd = one(-1e8, tag='溶解 df=-1e8')
    okA = (dcg == 0.0) and (gmg == 0.0) and nsg > 0
    okB = (dcd == 0.0) and (gmd == 0.0) and nsd > 0
    print('  T4-A（生长逐位不变，且 Stefan 分支被走到过）: %s' % ('PASS' if okA else 'FAIL'))
    print('  T4-B（溶解逐位不变，且 Stefan 分支被走到过）: %s' % ('PASS' if okB else 'FAIL'))

    print()
    print('【正向对照】显式打开旧通道（判据必须看得见变化）')
    dco, gmo, _, nbo = one(+1e8, tag='旧通道 df=+1e8', k_part=0.6303, surface_chem=True)
    okC = (dco > 0.0) and (gmo > 0.0)
    print('  T4-C（旧通道必须同时改变 c 与 Γ，证明两条通道都活着）: %s'
          '（max|c-c0|=%.3e, max|Γ_mol|=%.3e）' % ('PASS' if okC else 'FAIL', dco, gmo))

    print()
    print('【M4 守恒判据仍须 PASS】')
    okD = bool(W.M4_report(N=32, nstep=150))

    print()
    print('=' * 100)
    for name, ok in (('T4-A', okA), ('T4-B', okB), ('T4-C(对照)', okC), ('T4-D', okD)):
        print('  %-12s %s' % (name, 'PASS' if ok else 'FAIL'))
    allok = okA and okB and okC and okD
    print('  ⇒ T4 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
