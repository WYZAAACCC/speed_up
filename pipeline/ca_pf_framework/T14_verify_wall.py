#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T14_verify_wall.py --- T14：盒内**不可转变的 β 壁**对照。

物理
----
单个 prior-β 晶粒内部长板条时，若前方有**不可转变区**（晶界、另一晶粒、
或残留 β），板条应当**停在那里**。这条是 T16 里"block/packet 被晶界与
互相碰撞界定"的最小可检验版本。

做法（**不换弹性求解器**）
------------------------
用"**每步把壁内的 φ 复位到初值**"实现障碍边界条件 ⇒ 壁内永远保持母相，
且对谱法弹性**透明**（壁内的 eps0 仍是母相的 0）。
ρ 记账：这不是"真实晶界"，只是**几何障碍**；真实晶界的取向差效应属 Window C/后续。

量具（先正对照再判）
------------------
前沿位置 = 变体区域内沿生长方向 `n` 的**最大投影**（**整数胞**口径，无插值
⇒ 不会像 `iface_offset` 那样对倾斜前沿有偏，见 T11f 的教训）。

判据
----
  T14-A **正对照**：无壁档必须**越过**壁位置 **> 5 胞**（否则"壁挡住了"无从归因）
  T14-B 有壁档的前沿必须停在壁的近侧面 **≤ 2 胞**以内
  T14-C 壁内必须**始终是母相**（`region==0` 占比 = 100%）

用法：python3 T14_verify_wall.py [--N 96] [--dx-nm 25]
退出码：0 = PASS
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

DF, MOB = 2.0e8, 1e-9
K = 1


def build(N, dx, x_wall_nm=None, wall_t_nm=200.0):
    """★ 记账（首版构型选错方向）：沿**法向** `n_h` 生长极慢（`M(n)` 在 `n∥n*` 处
    只有 3%），400 步只长了 281 nm，**根本没到壁**（"测试看不到目标现象"）。
    改用**面内快生长方向** `a`（板条沿长度方向撞界）—— 这也更物理。"""
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0)
    n_h = np.asarray(NPF[K], float)
    n_h = n_h / np.linalg.norm(n_h)
    # 面内快生长方向 a ⊥ n_h
    tmp = np.array([1.0, 0.0, 0.0])
    if abs(tmp @ n_h) > 0.9:
        tmp = np.array([0.0, 1.0, 0.0])
    a_dir = np.cross(n_h, tmp)
    a_dir = a_dir / np.linalg.norm(a_dir)
    c0 = np.array([L / 2] * 3)
    rel = g.XYZ - c0
    s = rel @ a_dir                                  # 沿 a 的投影（生长方向）
    g.seed_plate(K, c0 - a_dir * (0.20 * L), n_h, 0.10 * L, 4 * dx)
    g.init_parent()
    mask = None
    x_wall = None
    if x_wall_nm is not None:
        x_wall = x_wall_nm * 1e-9
        mask = (s > x_wall) & (s <= x_wall + wall_t_nm * 1e-9)
    return g, L, a_dir, mask, x_wall


def front_pos(g, a_dir, c0):
    """变体区域沿 `a_dir` 的最大投影（整数胞口径）。"""
    reg = g.region()
    idx = np.argwhere(reg > 0)
    if idx.size == 0:
        return None
    p = (idx.astype(float) + 0.5) * g.dx - c0
    return float((p @ a_dir).max())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps', type=int, default=400)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    L = N * dx
    dt = 0.15 * dx / (MOB * DF)
    x_wall_nm = 0.16 * L * 1e9                      # 壁放在 +n 侧 0.16L 处
    print('=' * 100)
    print('T14 —— 不可转变 β 壁对照   N=%d  Δx=%.0f nm  L=%.2f µm  steps=%d'
          % (N, a.dx_nm, L * 1e6, a.steps))
    print('  壁位置（沿面内快生长方向 a）= %.0f nm，厚 200 nm；'
          '每步把壁内 φ 复位（障碍边界）' % x_wall_nm)
    print('=' * 100)
    out = {}
    for tag, xw in (('无壁（正对照）', None), ('有壁', x_wall_nm)):
        g, _, a_dir, mask, x_wall = build(N, dx, xw)
        c0 = np.array([L / 2] * 3)
        phi0 = g.phi.copy() if mask is not None else None
        for _ in range(a.steps):
            g.elastic_driving()
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                      mob_beta=3.5, mob_beta_w=2.3)
            if mask is not None:
                for j in range(g.nreg):
                    g.phi[j][mask] = phi0[j][mask]
        fp = front_pos(g, a_dir, c0)
        reg = g.region()
        wall_parent = (float((reg[mask] == 0).mean()) if mask is not None else 1.0)
        out[tag] = dict(fp=fp, wall_parent=wall_parent, x_wall=x_wall)
        print('  %-14s 前沿 = %s nm ；壁内母相占比 = %.4f'
              % (tag, 'None' if fp is None else '%.0f' % (fp * 1e9), wall_parent),
              flush=True)
    fp_no = out['无壁（正对照）']['fp']
    fp_w = out['有壁']['fp']
    xw = out['有壁']['x_wall']
    print()
    if fp_no is None or fp_w is None:
        print('  ⚠ 有档无变体 ⇒ 不作判定'); return 2
    over = (fp_no - xw) / dx
    stop = (fp_w - xw) / dx
    print('  无壁档越过壁位置：%.2f 胞（判据 > 5）' % over)
    print('  有壁档前沿相对壁的近侧面：%+.2f 胞（判据 ≤ 2）' % stop)
    print('  壁内母相占比 = %.4f（判据 = 1.0000）' % out['有壁']['wall_parent'])
    okA = over > 5.0
    okB = abs(stop) <= 2.0
    okC = out['有壁']['wall_parent'] == 1.0
    print()
    print('=' * 100)
    print('  T14-A %s | T14-B %s | T14-C %s'
          % tuple('PASS' if x else 'FAIL' for x in (okA, okB, okC)))
    allok = okA and okB and okC
    print('  ⇒ T14 %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
