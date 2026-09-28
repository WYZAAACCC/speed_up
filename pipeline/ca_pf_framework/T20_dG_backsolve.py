#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T20_dG_backsolve.py --- **D7 路径 (b)**：用**文献长厚比反解** β→α′ 的化学驱动力 ΔG。

背景（D7 的由来）
----------------
`T7_verify_dGsens.py` 实测：形貌（长/厚）对 `ΔG` 极敏感 ——
`df = 0.5 / 1.0 / 2.0 ×10⁸ J/m³` ⇒ 长/厚 = **1.165 / 2.207 / 4.170**（相对散布 **119.5%**，
判据门槛 10%）。而 CALPHAD 给 Ti-6Al-4V 的 `ΔS` 有 **~4 倍**不确定度
（`DS_BAND = (1.5e5, 6.0e5)` J/(m³K)）⇒ **A2（组织正确）被阻塞**。
用户 2026-09-28 的决定：**先找文献；找不到就用文献的长厚比反解 ΔG。**

本脚本做的就是把那个"反解"变成一条**可复算的标定曲线**
------------------------------------------------------
  calib  扫 `df` ⇒ 量**长/厚**（量具 = T15 已验证的"三向投影 `max−min`"）
         ⇒ log-log 最小二乘拟合 `长/厚 = C·df^b`（报 R²、残差带、单调性）
  invert 给文献长/厚 `AR` 与其不确定度 ⇒ 反解 `df` 与**区间**

R0 正对照（**强制**，见 `MEASUREMENT_SPEC.md` R0）
------------------------------------------------
  先用**同一条量具**量**种子本身**：`seed_plate(k, c, n, R, t)` 的解析三向尺度 =
  `(2R, 2R, t)` ⇒ 长/厚 = `2R/t` 已知。量具必须复现它，否则读数不得使用。

记账
----
* 平流格式走**当前生产默认**（D17 后 = `proj2`）；`--adv central` 可复现 D17 之前的归档值。
* 本标定把 `ΔG` 当作**标定参数**（D7 选项 b），**不是**从 CALPHAD 算出来的 ——
  写进论文必须如实标注，并给出反解区间。
* `elastic_driving` 打开（弹性项的量级与 `df` 可比，T7 已记账）。

用法：
  python3 T20_dG_backsolve.py --mode calib --adv proj2
  python3 T20_dG_backsolve.py --mode invert --ar 8.93 --ar-band 0.35
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

MOB = 1e-9
DF_REF = 2.0e8
N, DXN = 96, 25.0
DX = DXN * 1e-9
L = N * DX
R_SEED, T_SEED = 0.10 * L, 100e-9
STEPS = 120


# ---------------------------------------------------------------- 量具
def extents(phi, k, dx, npar=None):
    """三向尺度（**T15 已验证**：投影 `max−min`，**不加** `dx`）。
       返回 (长, 中, 薄)（降序）与最薄方向的单位向量。"""
    idx = np.argwhere(phi == phi)       # 占位；真正用 region 调用
    raise NotImplementedError


def measure(g, k=1):
    reg = g.region()
    idx = np.argwhere(reg == k)
    if idx.size < 30:
        return None
    p = (idx.astype(float) + 0.5) * g.dx
    q = p - p.mean(0)
    ev, evec = np.linalg.eigh(np.cov(q.T))
    ext = []
    for i in range(3):
        u = evec[:, i]
        s = q @ u
        ext.append(float(s.max() - s.min()))        # ★ 不加 dx（T15 修正）
    order = np.argsort(ext)[::-1]
    return dict(long=ext[order[0]], mid=ext[order[1]], thin=ext[order[2]],
                u_thin=evec[:, order[2]], ar=ext[order[0]] / max(ext[order[2]], 1e-30),
                ar_mid=ext[order[1]] / max(ext[order[2]], 1e-30),
                f=float((reg == k).sum()) / g.N ** 3)


def control_seed():
    """R0 正对照：**种子本身**的已知长/厚 = `2R/t`。"""
    print('-' * 104)
    print('  ★ R0 正对照：量具必须复现**种子本身**的解析三向尺度 (2R, 2R, t) = (%.0f, %.0f, %.0f) nm'
          % (2 * R_SEED * 1e9, 2 * R_SEED * 1e9, T_SEED * 1e9))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF_REF] * NV, workers=4, reinit_every=0)
    g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), R_SEED, T_SEED)
    g.init_parent()
    m = measure(g)
    ar_known = 2 * R_SEED / T_SEED
    ok = True
    for nm, v, known in (('长', m['long'], 2 * R_SEED),
                         ('中', m['mid'], 2 * R_SEED),
                         ('薄', m['thin'], T_SEED)):
        dev = v / known - 1
        good = abs(dev) < 0.15
        ok &= good
        print('     %s：量得 %7.1f nm  解析 %7.1f nm  偏差 %+7.2f%%  %s'
              % (nm, v * 1e9, known * 1e9, 100 * dev, '✓' if good else '✗'))
    print('     长/厚：量得 %.3f  解析 %.3f（偏差 %+.2f%%）⇒ %s'
          % (m['ar'], ar_known, 100 * (m['ar'] / ar_known - 1),
             'PASS' if abs(m['ar'] / ar_known - 1) < 0.15 else 'FAIL'))
    print('     最薄方向 vs npref[1] = %.2f°（应 < 20°）'
          % np.degrees(np.arccos(np.clip(abs(m['u_thin'] @ NPF[1]), 0, 1))))
    print('-' * 104)
    return ok


# ---------------------------------------------------------------- calib
def one(df, adv):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [df] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), R_SEED, T_SEED)
    g.init_parent()
    dt = 0.15 * DX / (MOB * DF_REF)          # ★ 固定 dt ⇒ 固定物理时间
    for _ in range(STEPS):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5,
                  mob_beta_w=2.3, adv_grad=adv)
    phi = g.phi
    dtot = float(np.max(dt * np.zeros(1)) + 0.0)
    dg = float(np.max(np.abs(g.dF_el))) if hasattr(g, 'dF_el') else np.nan
    m = measure(g)
    return m, STEPS * dt


def calib(adv):
    print('=' * 104)
    print('T20-calib —— **形貌 ↔ ΔG 的标定曲线**（N=%d Δx=%.0f nm L=%.2f µm，%d 步，'
          '固定物理时间，平流=%s）' % (N, DXN, L * 1e6, STEPS, adv))
    print('  种子：R=%.0f nm t=%.0f nm ⇒ 初始长/厚 = %.2f' % (R_SEED * 1e9, T_SEED * 1e9,
                                                              2 * R_SEED / T_SEED))
    print('-' * 104)
    rows = []
    print('  %-10s %-10s %-9s %-9s %-11s %-9s %s'
          % ('df (J/m³)', '长(nm)', '中(nm)', '薄(nm)', '长/厚', '中/厚', 'f'))
    for df in (0.5e8, 1.0e8, 1.5e8, 2.0e8, 4.0e8):
        m, t_end = one(df, adv)
        if m is None:
            print('  %-10.2e 变体太小' % df)
            continue
        rows.append((df, m))
        print('  %-10.2e %-10.1f %-9.1f %-9.1f %-11.3f %-9.3f %.5f'
              % (df, m['long'] * 1e9, m['mid'] * 1e9, m['thin'] * 1e9,
                 m['ar'], m['ar_mid'], m['f']), flush=True)
    if len(rows) < 3:
        print('  ⚠ 有效点不足 3 ⇒ INCONCLUSIVE')
        return None
    x = np.log(np.array([r[0] for r in rows]))
    y = np.log(np.array([r[1]['ar'] for r in rows]))
    b, a = np.polyfit(x, y, 1)
    pred = a + b * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / max(ss_tot, 1e-30)
    resid = float(np.max(np.abs(np.exp(y - pred) - 1)))
    print('-' * 104)
    print('  拟合：**长/厚 = %.6e · df^%.4f**   R² = %.5f   最大相对残差 = %.2f%%'
          % (np.exp(a), b, r2, 100 * resid))
    print('  单调性检查：长/厚 是否随 df 单调上升 ⇒ %s'
          % ('是 ✓' if np.all(np.diff([r[1]['ar'] for r in rows]) > 0) else '**否 ✗**'))
    print('  反解式：**df = (长/厚 / %.6e)^(1/%.4f)**' % (np.exp(a), b))
    print('  参考点（把模型自己的生产值带进去自洽性检查）：')
    for ar_test in (2.0, 4.36, 8.0, 10.0):
        df_inv = (ar_test / np.exp(a)) ** (1.0 / b)
        print('     长/厚 = %-6.2f ⇒ ΔG = **%.3e J/m³**（= %.2f × 10⁸）'
              % (ar_test, df_inv, df_inv / 1e8))
    np.save('_t20_calib.npy', np.array([(r[0], r[1]['ar'], r[1]['ar_mid'],
                                         r[1]['f']) for r in rows]))
    print('  （标定点已存 `_t20_calib.npy`）')
    print('=' * 104)
    return dict(a=float(a), b=float(b), r2=r2, resid=resid)


def invert(ar, band, fit=None):
    print('=' * 104)
    print('T20-invert —— **用文献长厚比反解 ΔG**（D7 选项 b）')
    if fit is None:
        try:
            d = np.load('_t20_calib.npy')
        except OSError:
            print('  ⚠ 先跑 `--mode calib`'); return
        x = np.log(d[:, 0]); y = np.log(d[:, 1])
        b, a = np.polyfit(x, y, 1)
        pred = a + b * x
        r2 = 1 - float(np.sum((y - pred) ** 2)) / max(float(np.sum((y - y.mean()) ** 2)), 1e-30)
        fit = dict(a=float(a), b=float(b), r2=r2, resid=0.0)
    print('  标定：长/厚 = %.6e·df^%.4f（R²=%.5f）' % (np.exp(fit['a']), fit['b'], fit['r2']))
    print('  文献长/厚 = %.3f ± %.1f%%（区间 %.3f – %.3f）'
          % (ar, 100 * band, ar * (1 - band), ar * (1 + band)))
    for tag, arv in (('下界', ar * (1 - band)), ('中心', ar), ('上界', ar * (1 + band))):
        df_inv = (arv / np.exp(fit['a'])) ** (1.0 / fit['b'])
        print('     %-4s 长/厚 = %-7.3f ⇒ **ΔG = %.3e J/m³**（= %.2f × 10⁸）'
              % (tag, arv, df_inv, df_inv / 1e8))
    print('  ⚠ 记账：这是**标定**，不是从 CALPHAD 算出来的。若文献 ΔG 可用，应优先用文献值')
    print('     （D7 选项 a），并把本反解作为**交叉检查**。')
    print('=' * 104)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='calib', choices=('calib', 'invert', 'control'))
    ap.add_argument('--adv', default='proj2')
    ap.add_argument('--ar', type=float, default=8.93)
    ap.add_argument('--ar-band', type=float, default=0.35)
    a = ap.parse_args()
    if a.mode == 'control':
        sys.exit(0 if control_seed() else 1)
    if a.mode == 'calib':
        ok = control_seed()
        if not ok:
            print('  ✗ 量具正对照 FAIL ⇒ 标定读数不得使用'); sys.exit(1)
        calib(a.adv)
    else:
        invert(a.ar, a.ar_band)


if __name__ == '__main__':
    main()
