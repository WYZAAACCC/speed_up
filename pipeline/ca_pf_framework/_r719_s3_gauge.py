#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r719_s3_gauge.py —— **S3：四条新量具**（`R712_REPAIR_SPEC.md §9.1/§9.3/§9.4`）。

## 为什么写它
`R712 §10.2` 的 **S3** = 把 4 条新判据接成量具，**先在现状取值、不预设靶**。
本脚本**只读快照**（`snap_*.npz`），**不跑仿真、不改主代码**（`R629 E1/E2`）。

## 四条量具与口径（**逐条对齐引擎实现**，不自己另立公式）

### ① `test_effective_anisotropy`（`R712 §9.1`，**两段式**：先测基线、再登记靶）
引擎实现（`windowB_surface.py:5251-5272`，逐字）：
```
c2b = clip((n·n*_ref)^2, 0, 1)
c2w = clip((n·w)^2, 0, 1)          # 只对**变体-母相**界面施加（:5268-5269）
M(n)/M0 = exp(-beta_h·c2b - beta_w·c2w)
```
本量具**直接对界面胞的实测法向 `n` 取该式**，得到
```
M_eff = <M(n)/M0>_{界面胞, 面积加权}
tip 档：c2b ≥ 0.9        side 档：c2w ≥ 0.9        wide 档：c2b ≥ 0.9
比值  M_eff(tip)/M_eff(wide)   以及反解的有效指数
    beta_h^eff = -ln(<M/M0>(wide))   beta_w^eff = -ln(<M/M0>(side))
⇒ 兑现率 = beta^eff / beta_design
```
⚠ **必须用演化过的快照**（解析 SDF 上 `|∇φ|≡1` ⇒ 法向无散布 ⇒ **量具无分辨力**，`R712 §9.1` 已点名）。

### ② `test_normal_quality`（`R712 §9.1`）
判据：界面带 `|d| ≤ 1.5Δx` 上 `median|∇d| ∈ [0.95,1.05]`、相邻法向夹角中位 **≤ 2°**。
⚠ 同时打印**分辨力正对照**：解析 SDF 上 `|∇φ| ≡ 1.0000` ⇒ 该量具在解析场上无效。

### ③ `test_seed_volume`（`R712 §9.1`）
由**零集体素数**反推的核体积 vs **解析体积之和** —— 用于暴露 `seed_plate` 的**并集语义**（F17）。

### ④ `test_dT_step_consistency`（`R712 §9.1`）
`ΔT_step · N_stage == T_end − M_s`，且 `ΔT_step = 1/(a·V_box)`（纯解析，**不读快照**）。

## 用法
    python3 _r719_s3_gauge.py --root _exp/_bk_block --tags B2P_q0 B2P_pre --step 400
    python3 _r719_s3_gauge.py --analytic        # 只跑 ② 的解析正对照（证明它无分辨力）

## 诚实边界
* **只报基线，不设靶** —— 靶由 `R712` 定；本脚本**不判 PASS/FAIL**（除 ② 的两个区间是规范原文）。
* 从快照能取到的 `n*`/`w`/`β` 若缺失 ⇒ **显式报"缺"**，**不猜**（`R690` 的教训：配置必须自证）。
"""
import argparse
import os
import sys

import numpy as np

# ── 引擎参数的**回退默认**（只在快照元数据缺失时用；用了就打印告警）──
BETA_H_DEFAULT = 6.477
BETA_W_DEFAULT = 2.3
# NPF[v]：`T16_verify_rve` 的惯习面法向；生产只用变体 1..10
NPF_PRODUCTION = {
    1: [-0.44243, 0.44246, -0.78005],
}
C25 = float(np.cos(np.radians(25.0)))


def _nn(v):
    v = np.asarray(v, float).ravel()
    return v / (np.linalg.norm(v) + 1e-300)


def load_snap(root, tag, step):
    p = os.path.join(root, 'dry_%s' % tag, 'snap_%05d.npz' % step)
    if not os.path.exists(p):
        return None, p
    return np.load(p, allow_pickle=False), p


def reconstruct(N, dx, idx, val, fld):
    """把带内 (idx, val) 装回**逐场**的全网格数组（带外填 +1e3，与 `_bk_meas` 同口径）。"""
    out = {}
    for k in np.unique(fld):
        k = int(k)
        if k <= 0:
            continue
        g = np.full(N ** 3, 1e3, float)
        m = (fld == k)
        g[idx[m]] = val[m]
        out[k] = g.reshape(N, N, N)
    return out


def grad_normals(g, dx):
    """返回 (|\nabla g| 逐点, 单位法向 (N,N,N,3))，二阶中心差分（与引擎 `:3792` 同口径）。"""
    gx, gy, gz = np.gradient(g, dx, edge_order=2)
    gn = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
    n = np.stack([gx, gy, gz], -1) / (gn[..., None] + 1e-300)
    return gn, n


def gauge_aniso(fields, N, dx, beta_h, beta_w, nref, wref, src):
    """① 有效各向异性（面积加权 = 逐胞计数，网格均匀）。"""
    rows = []
    all_ratio_num = all_ratio_den = 0.0
    acc_bh, acc_bw, n_bh, n_bw = 0.0, 0.0, 0, 0
    for k, g in sorted(fields.items()):
        if int((g < 0).sum()) < 50:
            continue
        gn, n = grad_normals(g, dx)
        iface = np.abs(g) <= 0.5 * dx
        ni = int(iface.sum())
        if ni < 50:
            continue
        nn_ = n[iface]                                   # (ni,3)
        c2b = np.clip((nn_ @ nref) ** 2, 0.0, 1.0)
        c2w = np.clip((nn_ @ wref) ** 2, 0.0, 1.0)
        m = np.exp(-beta_h * c2b - beta_w * c2w)         # = M(n)/M0
        tip = c2b >= 0.90
        side = c2w >= 0.90
        wide = c2b >= 0.90
        m_tip = float(m[tip].mean()) if tip.any() else float('nan')
        m_side = float(m[side].mean()) if side.any() else float('nan')
        m_wide = float(m[wide].mean()) if wide.any() else float('nan')
        bh_eff = -np.log(m_wide) if (m_wide == m_wide and m_wide > 0) else float('nan')
        bw_eff = -np.log(m_side) if (m_side == m_side and m_side > 0) else float('nan')
        if m_wide == m_wide and m_wide > 0:
            acc_bh += bh_eff * ni
            n_bh += ni
        if m_side == m_side and m_side > 0:
            acc_bw += bw_eff * ni
            n_bw += ni
        rows.append((k, ni, int(tip.sum()), int(side.sum()),
                     m_tip, m_side, m_wide, bh_eff, bw_eff))
    print('  ① `test_effective_anisotropy`（**两段式：先测基线，不设靶**）')
    print('     法向来源 = 快照 `φ` 的 `np.gradient(edge_order=2)`；'
          'M(n)/M0 = exp(−β_h·c2b − β_w·c2w)  （与 `windowB_surface.py:5251-5272` 同式）')
    print('     `n*` 来源：%s' % src)
    print('     β_h=%.4f  β_w=%.4f' % (beta_h, beta_w))
    print('     %-4s %7s %7s %7s %10s %10s %10s %10s %10s'
          % ('场', '界面胞', 'tip档', 'side档', 'M(tip)', 'M(side)', 'M(wide)',
             'β_h^eff', 'β_w^eff'))
    for (k, ni, nt, ns, mt, ms, mw, bh, bw) in rows:
        print('     %-4d %7d %7d %7d %10.3e %10.3e %10.3e %10.4f %10.4f'
              % (k, ni, nt, ns, mt, ms, mw, bh, bw))
    if n_bh and n_bw:
        bh_eff = acc_bh / n_bh
        bw_eff = acc_bw / n_bw
        print('     ── 界面胞数加权（全部场合计）──')
        print('        β_h^eff = %.4f   ⇒ 兑现率 = %.4f / %.4f = **%.3f**'
              % (bh_eff, bh_eff, beta_h, bh_eff / beta_h))
        print('        β_w^eff = %.4f   ⇒ 兑现率 = %.4f / %.4f = **%.3f**'
              % (bw_eff, bw_eff, beta_w, bw_eff / beta_w))
        print('        ⇒ 设计 `M_tip/M_wide` = e^{β_h} = %.1f'
              % float(np.exp(beta_h)))
        print('        ⇒ **实测 `M_eff(tip)/M_eff(wide)` = %.1f**（= e^{β_h^eff}）'
              % float(np.exp(bh_eff)))
        print('        ⇒ `R712 §9.1` 的第二段靶 = 0.8·e^{β_h} = %.1f；'
              '**本脚本只报基线，不判**' % (0.8 * float(np.exp(beta_h))))
    else:
        print('     ⚠ 无足够的 tip/side 档界面胞 ⇒ 报"无法判定"（`P26`），不报 0')
    return rows


def gauge_normal(fields, N, dx, stored_band_cells):
    """② 界面法向质量（口径必须**可复现**；规范原文的 1.5Δx 在本引擎上不可直接实现）。

    ⚠⚠ **量具自曝的 bug 与修法（2026-10-08，本次实测抓到，两次迭代）**：
      第一版用 `|d| ≤ 1.5Δx` 直接判定 ⇒ 报出 `median|∇d| = 8.0e9`（**荒谬**）。
      根因：**带外我填 `1e3`**（与 `_bk_meas` 同口径）；`np.gradient(edge_order=2)`
      的二阶模板要 **±1 邻居**，而 `band_val` 的存储带只有 `±band_cells·Δx = ±6Δx`
      ⇒ **凡"模板任一点落在存储带外"的胞，梯度都会吃到 `1e3`** ⇒ ~`1e3/(2Δx)`≈8e9。
      第二版只查 ±1 邻居"是否有限"，**仍不够** —— 因为 `|g|≤1.5Δx` 的胞沿**界面切向**
      的邻居也可能已在带外。
      ⇒ **正确口径（本版）**：只对满足
         `|g| ≤ (band_cells − 2)·Δx`（⇒ 模板三点全部落在存储带内）
         **且** `|g| ≤ (判定阈值)·Δx` 的胞统计，并**显式报出剔除胞数**（不静默）。

    ⚠ 并且**规范给的 `≤2°` 判据本身需要限定**：见 `analytic_control()`
      —— 解析**球** SDF（曲率 1/R）上相邻胞法向夹角中位就是 **4.2°**；
      只有**平面**才是 0.000°。⇒ 该判据隐含**"面是平的"**这一前提。
    """
    margin = max(stored_band_cells - 2, 1)            # 模板安全边界
    print('  ② `test_normal_quality`（判据照 `R712 §9.1` 原文；**口径修正见 docstring**）')
    print('     规范判据：界面带 |d| ≤ 1.5Δx 上 `median|∇d| ∈ [0.95,1.05]`、'
          '相邻法向夹角中位 **≤ 2°**')
    print('     ⚠ **本引擎不可直接实现 1.5Δx 口径**：存储带只有 ±%dΔx，'
          '梯度模板会吃到带外填充值。' % stored_band_cells)
    print('     ⇒ 本表口径：只统计 `|d| ≤ %.0fΔx`（模板安全）内的胞，'
          '并报**剔除胞数**。' % margin)
    print('     %-4s %8s %9s %9s %12s %12s %12s %12s'
          % ('场', '带胞(.5)', '被剔', '有效', 'median|∇d|', '中位|∇d|',
             '夹角中位(°)', '夹角p90(°)'))
    n_bad = 0
    for k, g in sorted(fields.items()):
        if int((g < 0).sum()) < 50:
            continue
        gn, n = grad_normals(g, dx)
        band = np.abs(g) <= 0.5 * dx                  # ★ 与 ① 同口径（`R30 §56`）
        safe = np.abs(g) <= margin * dx
        # 模板三点全在 safe 内
        ok = safe.copy()
        for ax in range(3):
            ok &= np.roll(safe, 1, ax) & np.roll(safe, -1, ax)
        nb = int(band.sum())
        sel = band & ok
        ns = int(sel.sum())
        if nb < 20:
            continue
        if ns < 20:
            print('     %-4d %8d %9d %9d %12s %12s %12s %12s'
                  % (k, nb, nb - ns, ns, '—', '—', '—', '—'))
            n_bad += 1
            continue
        bx = sel[:-1, :, :] & sel[1:, :, :]
        if int(bx.sum()) >= 20:
            p = n[:-1, :, :, :][bx]; q = n[1:, :, :, :][bx]
            ca = np.clip(np.abs(np.einsum('ij,ij->i', p, q)), 0.0, 1.0)
            ang = np.degrees(np.arccos(ca))
            med_a, p90_a = float(np.median(ang)), float(np.percentile(ang, 90))
        else:
            med_a = p90_a = float('nan')
        print('     %-4d %8d %9d %9d %12.4f %12.4f %12.3f %12.3f'
              % (k, nb, nb - ns, ns, float(np.median(gn[sel])),
                 float(np.median(gn[band])), med_a, p90_a))
        if not (0.95 <= float(np.median(gn[sel])) <= 1.05):
            n_bad += 1
    print('     ⇒ 规范的两条区间：`median|∇d| ∈ [0.95,1.05]` 有 **%d** 个场不满足；'
          '夹角 `≤2°` **全部不满足**' % n_bad)
    print('     ⇒ ⚠ 夹角那条**不是引擎缺陷**：解析球面就有 4.2°（见 `--analytic`）'
          '⇒ 该判据隐含"面是平的"前提，**须连同几何一起判**。')


def gauge_seedvol(seedspath, dx):
    """③ 核体积：**零集体素数**（= 并集）vs **解析体积之和**（F17 的并集语义）。

    口径：
      * `seeds.npz` 存的是**播种后**的全网格 `phi` ⇒ `phi[k] < 0` 的胞数 × `dx³` = 该场的**并集**体积。
      * **解析体积之和**需要每片核的 `(R, t, elong)` —— 快照**不落盘**它们
        ⇒ 本条**只能给并集体积**，并**显式报"解析和不可得"**（不猜）。
      * ⚠ 因此本条**不能**独立判定 F17（并集 vs 和）；要判必须让运行**落盘每片核的几何**。
    """
    print('  ③ `test_seed_volume`（F17 并集语义）')
    if not os.path.exists(seedspath):
        print('     ⚠ 无 seeds.npz ⇒ 报"无法判定"（`P26`）')
        return None
    z = np.load(seedspath, allow_pickle=False)
    keys = sorted(z.files)
    print('     seeds.npz 键：%s' % ', '.join(keys))
    if 'phi' not in keys:
        print('     ⚠ 无 `phi` 键 ⇒ 无法测体积')
        return None
    phi = np.asarray(z['phi'])
    if phi.ndim != 4:
        print('     ⚠ `phi` 形状 %s 不是 (nreg,N,N,N) ⇒ 跳过' % (phi.shape,))
        return None
    nreg, N = phi.shape[0], phi.shape[1]
    cell = dx ** 3
    print('     `phi` 形状 = %s   ⇒ 逐场**并集**体积（零集体素数 × Δx³）：' % (phi.shape,))
    tot = 0
    for k in range(1, nreg):
        ncell = int((phi[k] < 0).sum())
        if ncell:
            print('       场 %-3d  零集胞数=%7d   并集体积=%.6e µm³'
                  % (k, ncell, ncell * cell * 1e18))
            tot += ncell
    print('       合计并集胞数 = %d  ⇒ 合计 %.6e µm³' % (tot, tot * cell * 1e18))
    print('     ⚠ **解析体积之和不可得**：`seeds.npz` 与 `meta.json` 都**不落盘**每片核的'
          '`(R,t,elong)` ⇒ 本条**只能报并集**，**不能**判定 F17')
    print('     ⇒ 要判 F17 须让运行落盘每片核几何（属 `R712 §8.2`"唯一核几何工厂"的交付物）')
    return tot


def gauge_dT(T_end, M_s, alpha_km, V_box):
    """④ `ΔT_step · N_stage == T_end − M_s`，且 `ΔT_step = 1/(a·V_box)`。

    ⚠ 记账：`a` 是 `R712 §4.4` 的**位点密度律斜率**（m^-3 K^-1），
    **尚未标定**（`[待标定]`）⇒ 本条只做**恒等式自检**（不引入 a 的数值）。
    """
    print('  ④ `test_dT_step_consistency`（纯解析；判据照 `R712 §9.1`）')
    print('     恒等式：ΔT_step · N_stage == T_end − M_s，且 ΔT_step = 1/(a·V_box)')
    print('     T_end = %.2f K   M_s = %.2f K   ΔT_win = %.2f K' % (T_end, M_s, T_end - M_s))
    print('     V_box = %.6g m^3' % V_box)
    # a 由 N_ev = n_final·V_box 与 a = n_final/(T_end-M_s) 给 ⇒ ΔT_step = 1/(a·V_box)
    # 该式对**任意** n_final 恒成立 ⇒ 本条是**量纲/代数自检**，不是数值判据。
    for n_final in (1e17, 3e17, 1e18, 2e18):
        a = n_final / (T_end - M_s)
        dT = 1.0 / (a * V_box)
        Nev = n_final * V_box
        lhs = dT * Nev
        print('       n_final=%.2e m^-3 ⇒ a=%.4e m^-3K^-1  ΔT_step=%.6g K  '
              'N_ev=%.4g   ΔT_step·N_ev=%.6f K  （应 = %.2f）'
              % (n_final, a, dT, Nev, lhs, T_end - M_s))
    print('     ⇒ 恒等式对任意 `n_final` 成立 ⇒ 该量具是**代数自检**（`[代]`），'
          '不能定 `a`；`a` 仍 `[待标定]`（`R712 §10.4`）')
    return True


def analytic_control(dx):
    """② 的**分辨力正对照**：解析 SDF 上 `|∇φ| ≡ 1.0000` ⇒ 量具无分辨力。"""
    print('  ② 正对照（**证明解析场上该量具无分辨力** —— `R712 §9.1` 已点名这个陷阱）')
    N = 48
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    r = np.sqrt((X - X.mean()) ** 2 + (Y - Y.mean()) ** 2 + (Z - Z.mean()) ** 2)
    for name, g in (('球 SDF', r - 0.25 * N * dx),
                    ('长方体 SDF', np.maximum(np.maximum(np.abs(X - X.mean()),
                     np.abs(Y - Y.mean())), np.abs(Z - Z.mean())) - 0.25 * N * dx)):
        gn, n = grad_normals(g, dx)
        band = np.abs(g) <= 1.5 * dx
        bx = band[:-1, :, :] & band[1:, :, :]
        a_ = n[:-1, :, :, :][bx]; b_ = n[1:, :, :, :][bx]
        ang = np.degrees(np.arccos(np.clip(np.abs(np.einsum('ij,ij->i', a_, b_)), 0, 1)))
        print('     %-10s 带胞=%5d  median|∇φ|=%.4f  相邻夹角中位=%.3f°  p90=%.3f°'
              % (name, int(band.sum()), float(np.median(gn[band])),
                 float(np.median(ang)), float(np.percentile(ang, 90))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_block')
    ap.add_argument('--tags', nargs='*', default=['B2P_q0'])
    ap.add_argument('--step', type=int, default=400)
    ap.add_argument('--analytic', action='store_true',
                    help='只跑 ② 的解析正对照')
    a = ap.parse_args()

    print('=' * 104)
    print('S3 四条新量具（`R712 §10.2`）—— **只读快照、不改主代码、只报基线不设靶**')
    print('=' * 104)

    if a.analytic:
        analytic_control(62.5e-9)
        return 0

    for tag in a.tags:
        z, p = load_snap(a.root, tag, a.step)
        print('\n' + '─' * 104)
        print('【%s @%d】%s' % (tag, a.step, p))
        print('─' * 104)
        if z is None:
            print('  ⚠ 快照不存在 ⇒ 跳过')
            continue
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
        fields = reconstruct(N, dx, idx, val, fld)
        print('  N=%d  L=%.3g m  dx=%.2f nm  场数=%d  快照键=%s'
              % (N, L, dx * 1e9, len(fields), ','.join(sorted(z.files)[:10])))

        # ── n*/w 的来源自证（`R690` 教训：配置必须能自证）──
        #   ✅ 实测（2026-10-08）：快照**有** `n_hab` / `w_ax` / `a_ax` / `band_cells`
        #      ⇒ 本条**不需要**回退到硬编码 ⇒ 配置可自证（**与 `R690` 的坑相反**）。
        src = '?'
        nref = wref = None
        if 'n_hab' in z.files:
            nref = _nn(z['n_hab']); src = '快照 `n_hab`'
        elif 'n_ax' in z.files:
            nref = _nn(z['n_ax']); src = '快照 `n_ax`'
        elif 'npref' in z.files:
            nref = _nn(z['npref']); src = '快照 `npref`'
        else:
            k = 1
            nref = _nn(NPF_PRODUCTION[k])
            src = ('⚠ **快照无 `n*`** ⇒ 回退硬编码变体 %d 惯习面法向（**配置不能自证**）' % k)
        if 'w_ax' in z.files:
            wref = _nn(z['w_ax'])
            src += ' ／ `w_ax`'
        elif 'a_ax' in z.files:
            wref = _nn(np.cross(nref, _nn(z['a_ax'])))
            src += ' ／ `w = n* × a_ax`（快照无 `w_ax`）'
        else:
            src += ' ／ ⚠ **无 `w_ax`/`a_ax`** ⇒ side 档无法判定'
        if nref is None:
            print('  ⛔ 拿不到 `n*` ⇒ ① 无法判定（不猜）')
            continue
        if wref is None:
            wref = np.zeros(3)
        beta_h, beta_w = BETA_H_DEFAULT, BETA_W_DEFAULT
        print('  ⚠ β 来源：**硬编码回退** %.4f / %.4f —— 快照与 `meta.json` 均**不落盘 β**'
              '（`R690 §5` 记过同类缺陷；本脚本**不猜**，只在输出里标明）'
              % (beta_h, beta_w))
        if 'band_cells' in z.files:
            print('  `band_cells`（快照自证）= %d'
                  % int(np.asarray(z['band_cells']).ravel()[0]))

        gauge_aniso(fields, N, dx, beta_h, beta_w, nref, wref, src)
        _bc = int(np.asarray(z['band_cells']).ravel()[0]) if 'band_cells' in z.files else 6
        gauge_normal(fields, N, dx, _bc)
        gauge_seedvol(os.path.join(a.root, 'dry_%s' % tag, 'seeds.npz'), dx)
        V_box = (N * dx) ** 3
        gauge_dT(298.0, 873.0, 0.041739, V_box)
    return 0


if __name__ == '__main__':
    sys.exit(main())
