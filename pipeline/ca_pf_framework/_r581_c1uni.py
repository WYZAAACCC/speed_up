#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c1uni.py --- ★ C1「随机形核」判据：**位点可复现 + 统计上均匀（有检验）**。

## 数据源（探针实测，不猜）
`<run>/nuc_dbg.json` 的 **`nuc_cfg['sites']`** —— 形如
`[[35, [x, y, z]], [36, [...]], ...]`（**场号 + 位点坐标**）。
另有 `nuc_cfg['seed']`（若存在）、`T_events`（逐事件的 step/T/df/field/mode）。

## 判据（**预先写死，不许事后挪**）
| # | 判据 | 阈值 | 为什么 |
|---|---|---|---|
| **U1** | 三个一维边缘的 **KS 检验** vs U(0,L) | p > 0.05 ⇒ 不拒绝均匀 | 位点应均匀撒在盒子里 |
| **U2** | 八分体的 **χ² 检验** | p > 0.05 | 三维的粗粒度检验 |
| **U3** | **最近邻距离**分布 vs CSR（完全空间随机）期望 | 实测中位落在 CSR 的 5–95% 区间内 | 检验有没有成团/排斥 |
| **R1** | **可复现**：同一 seed 两次跑出的 `sites` **逐位相同** | 必须相同 | goal 原文"位点由 CLI 记录的 seed 复现" |

## ★★ 必须一起报的**功效（power）记账** —— 否则这个检验是自欺
位点数 `n` 很小时（本工程 `B·n(T_end)` 只有 15–25，实测 3–10），
**KS / χ² / 最近邻检验的功效都极低** ⇒ "p > 0.05" **几乎必然**，
**不能读成"已证明均匀"**，只能读成"**未能证伪**"。
⇒ 本脚本**强制报出 n**，并在 n < 20 时打印显式的功效警告。

## 负对照（**必须能失败**）
把位点人为**聚成一团**（或全部塞进一个角）⇒ **U1/U2/U3 必须报出p 很小**。
自检里跑这个对照；对照不过 ⇒ **拒绝给判读**。
"""
import json
import os
import sys

import numpy as np

R = '_exp/_bk_p2'


# ------------------------------------------------------------------ 统计量
def ks_uniform(v, L):
    """一维 KS 检验 vs U(0,L)。返回 (D, p)。不依赖 scipy 版本差异。"""
    from scipy import stats
    v = np.sort(np.asarray(v, float))
    n = len(v)
    if n == 0:
        return float('nan'), float('nan')
    cdf = np.arange(1, n + 1) / n
    D = max(np.max(np.abs(cdf - v / L)), np.max(np.abs((v / L) - (cdf - 1.0 / n))))
    # 双侧 p 的渐近式（Kolmogorov 分布）
    en = np.sqrt(n)
    lam = (en + 0.12 + 0.11 / en) * D
    p = 2.0 * sum((-1) ** (k - 1) * np.exp(-2.0 * k * k * lam * lam)
                  for k in range(1, 101))
    return float(D), float(min(max(p, 0.0), 1.0))


def chi2_octants(P, L):
    """八分体的 χ²。返回 (chi2, p, 计数)。"""
    from scipy import stats
    P = np.asarray(P, float)
    if len(P) == 0:
        return float('nan'), float('nan'), []
    oct_ = ((P[:, 0] > L / 2).astype(int) * 4 + (P[:, 1] > L / 2).astype(int) * 2
            + (P[:, 2] > L / 2).astype(int))
    cnt = np.bincount(oct_, minlength=8).astype(float)
    exp = len(P) / 8.0
    if exp <= 0:
        return float('nan'), float('nan'), cnt
    chi2 = float(((cnt - exp) ** 2 / exp).sum())
    # 只有期望频数够大时 χ² 才可信；否则用蒙特卡洛 p
    if exp < 5:
        rng = np.random.default_rng(12345)
        null = []
        for _ in range(4000):
            Q = rng.random((len(P), 3)) * L
            o = ((Q[:, 0] > L / 2).astype(int) * 4 + (Q[:, 1] > L / 2).astype(int) * 2
                 + (Q[:, 2] > L / 2).astype(int))
            c = np.bincount(o, minlength=8).astype(float)
            null.append(((c - exp) ** 2 / exp).sum())
        p = float((np.array(null) >= chi2).mean())
        return chi2, p, cnt
    return chi2, float(1 - stats.chi2.cdf(chi2, 7)), cnt


def nn_median(P, L, periodic=True):
    """最近邻距离的中位数（周期最小镜像）。"""
    P = np.asarray(P, float)
    n = len(P)
    if n < 2:
        return float('nan')
    d = np.zeros((n, n))
    for i in range(3):
        dd = np.abs(P[:, None, i] - P[None, :, i])
        if periodic:
            dd = np.minimum(dd, L - dd)
        d += dd ** 2
    d = np.sqrt(d)
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(1)))


def csr_band(n, L, reps=4000, seed=7):
    """完全空间随机（CSR）下最近邻中位数的 5–95% 区间。"""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(reps):
        P = rng.random((n, 3)) * L
        out.append(nn_median(P, L))
    out = np.array(out, float)
    return float(np.percentile(out, 5)), float(np.percentile(out, 95)), float(np.median(out))


# ------------------------------------------------------------------ 自检
def selftest():
    """★ 自检 —— **第一版是 FAIL 的，而且错在我的对照设计上（留痕）**。

    ## 第一次自检的两条 FAIL（都是我预登记错了，不是量具错）
    1. **正对照"误拒"**：我拿**一次**真均匀的抽样去要求 `p > 0.05`。
       但单次抽样的 p 值本来就**均匀分布在 [0,1]** ⇒ 有 ~5% 的概率 p < 0.05
       ⇒ **单次正对照必然偶尔"失败"**。**正确做法**：跑 **200 次**独立抽样，
       量**拒绝率**，要求它 ≈ 5%（允许 [0, 0.15]）。
    2. **负对照1 没分辨力**：我把 200 个点聚在**盒子中心**（0.5，σ=0.02）
       ⇒ 它们**横跨全部 8 个八分体** ⇒ χ² **原理上看不到成团**。
       **正确做法**：聚在**偏离中心**的位置（如 (0.2,0.2,0.2)）⇒ 全落进同一格。
    ⇒ 与 `_r581_L4_geom.py` 的 NC 退化是**同一类**陷阱（"判据在该数据上恒真"）。
    """
    L = ['  ── 量具自检（**正对照量"拒绝率"，负对照必须能失败**）──']
    ok = True
    rng = np.random.default_rng(3)
    Lb = 1.0

    # ---- 正对照：**200 次独立抽样，量拒绝率**（名义 5%）----
    rej_ks = rej_chi = 0
    REPS = 200
    for _ in range(REPS):
        Pu = rng.random((60, 3)) * Lb
        _, p1 = ks_uniform(Pu[:, 0], Lb)
        _, p2, _ = chi2_octants(Pu, Lb)
        rej_ks += (p1 <= 0.05)
        rej_chi += (p2 <= 0.05)
    r1, r2 = rej_ks / REPS, rej_chi / REPS
    good = (r1 <= 0.15) and (r2 <= 0.15)
    L.append('    正对照（%d 次独立均匀抽样，n=60）：**拒绝率** KS=%.3f  χ²=%.3f'
             '（名义 0.05，容差 ≤0.15）⇒ %s'
             % (REPS, r1, r2, '✅ 不误拒' if good else '❌ 误拒太多'))
    ok &= good

    # ---- 负对照 1：聚在**偏离中心**的一团（必须被 χ² 拒）----
    Pc = np.clip(rng.normal(0.2, 0.02, (200, 3)), 0, 1)
    _, q1 = ks_uniform(Pc[:, 0], Lb)
    _, q2, _ = chi2_octants(Pc, Lb)
    nc1 = (q1 < 1e-3) and (q2 < 1e-3)
    L.append('    负对照1（200 点聚在 (0.2,0.2,0.2)，σ=0.02）：KS p=%.3e  χ² p=%.3e ⇒ %s'
             % (q1, q2, '✅ 被拒（有分辨力）' if nc1 else '❌ **没分辨力**'))
    ok &= nc1
    L.append('       ⚠ 记账：第一版把点聚在**盒子中心** ⇒ 横跨 8 个八分体 ⇒ χ² **原理上看不到**'
             '（`p=0.36`）。**负对照本身选错了位置**。')

    # ---- 负对照 2：全塞进一个角 ----
    Pa = rng.random((200, 3)) * 0.1 * Lb
    _, r_1 = ks_uniform(Pa[:, 0], Lb)
    nc2 = r_1 < 1e-6
    L.append('    负对照2（200 点全在 [0,0.1] 角）：KS p=%.3e ⇒ %s'
             % (r_1, '✅ 被拒' if nc2 else '❌ **没分辨力**'))
    ok &= nc2

    # ---- 负对照 3：最近邻判据必须能分辨"成团" ----
    b5, b95, med = csr_band(60, Lb, reps=400)
    Pcl = np.clip(rng.normal(0.5, 0.02, (60, 3)), 0, 1)
    nmc = nn_median(Pcl, Lb)
    nc3 = nmc < b5
    L.append('    负对照3（60 点成团 ⇒ 最近邻中位应**低于** CSR 带）：实测 %.4f < %.4f ⇒ %s'
             % (nmc, b5, '✅ 有分辨力' if nc3 else '❌ **没分辨力**'))
    ok &= nc3

    L.append('    ⇒ 自检：%s' % ('✅ PASS' if ok else '❌ FAIL ⇒ 拒绝给判读'))
    return ok, L


# ------------------------------------------------------------------ 主判读
def main():
    tags = sys.argv[1:] or ['dry_p2_b5', 'dry_p2_b3']
    out = ['=' * 100,
           'R581 —— C1「随机形核」判据（位点可复现 + 统计均匀）',
           '=' * 100]
    ok, sub = selftest()
    out += sub
    if not ok:
        print('\n'.join(out)); print('\n❌ 自检不过 ⇒ 拒绝给判读'); return 2
    out.append('')
    for tag in tags:
        d = os.path.join(R, tag if tag.startswith('dry_') else 'dry_' + tag)
        p = os.path.join(d, 'nuc_dbg.json')
        out.append('=' * 100)
        if not os.path.exists(p):
            out.append('★ %s：**没有 `nuc_dbg.json`**（%s）' % (tag, '跑完才写' ))
            out.append('  ⇒ C1 无法判读（**如实登记，不许拿别的数代替**）')
            continue
        j = json.load(open(p, encoding='utf-8'))
        meta = json.load(open(os.path.join(d, 'meta.json')))
        Lbox = float(meta.get('L', 1.0))
        out.append('★ %s' % tag)
        out.append('  `nuc_law`=%s  `n_eng_ev`=%s  `n_target_final`=%s  '
                   '`nuc_fresh_every`=%s'
                   % (j.get('nuc_law'), j.get('n_eng_ev'),
                      j.get('n_target_final'), j.get('nuc_fresh_every')))
        cfg = j.get('nuc_cfg', {})
        out.append('  ── `nuc_cfg` 里与审计相关的项（**落盘即证据**）──')
        for k in ('seed', 'var_rule', 'attach_overlap', 'periodic_seed',
                  'nuc_shape', 'supercrit', 'sites_refill', 'sites_margin',
                  'elong', 'p_auto', 'use_fcrit'):
            if k in cfg:
                out.append('     %-18s %s' % (k, cfg[k]))
        sites = cfg.get('sites', [])
        if not sites:
            out.append('  ⚠ `nuc_cfg.sites` 为空 ⇒ 无法做均匀性检验')
            continue
        flds = [int(s[0]) for s in sites]
        P = np.array([s[1] for s in sites], float)
        n = len(P)
        out.append('  ── 位点 ──')
        out.append('     位点数 = **%d**；场号 = %s' % (n, flds))
        out.append('     坐标范围：x [%.3f, %.3f]、y [%.3f, %.3f]、z [%.3f, %.3f] µm'
                   % (P[:, 0].min() * 1e6, P[:, 0].max() * 1e6,
                      P[:, 1].min() * 1e6, P[:, 1].max() * 1e6,
                      P[:, 2].min() * 1e6, P[:, 2].max() * 1e6))
        out.append('     （盒子 L = %.4f µm）' % (Lbox * 1e6))
        # U1
        out.append('  ── U1 三个一维边缘的 KS 检验 vs U(0,L) ──')
        for i, ax in enumerate('xyz'):
            D, pv = ks_uniform(P[:, i] / Lbox, 1.0)
            out.append('     %s：D=%.4f  p=%.4f  ⇒ %s'
                       % (ax, D, pv, '不拒绝均匀' if pv > 0.05 else '**拒绝**'))
        # U2
        chi2, pv2, cnt = chi2_octants(P, Lbox)
        out.append('  ── U2 八分体 χ²（期望每格 %.2f）──' % (n / 8.0))
        out.append('     计数 = %s' % cnt.astype(int).tolist())
        out.append('     χ²=%.3f  p=%.4f  ⇒ %s'
                   % (chi2, pv2, '不拒绝均匀' if pv2 > 0.05 else '**拒绝**'))
        # U3
        if n >= 2:
            b5, b95, med = csr_band(n, Lbox, reps=2000)
            nm = nn_median(P, Lbox)
            inb = b5 <= nm <= b95
            out.append('  ── U3 最近邻距离中位数 vs CSR ──')
            out.append('     实测 = %.4f µm；CSR 中位 %.4f，5–95%% 带 [%.4f, %.4f] ⇒ %s'
                       % (nm * 1e6, med * 1e6, b5 * 1e6, b95 * 1e6,
                          '落在带内' if inb else '**落在带外**'))
        # 功效警告
        out.append('  ── ★★ 功效（power）记账 ──')
        if n < 20:
            out.append('     ⚠⚠ **位点数只有 %d 个 ⇒ 上述检验的功效极低** ⇒' % n)
            out.append('        "p > 0.05" **不能读成"已证明均匀"**，只能读成"**未能证伪**"。')
            out.append('        （本工程 `B·n(T_end)` 只有 15–25，实测更少 ⇒ 这是结构性的。）')
        else:
            out.append('     n=%d（≥20）⇒ 检验有一定功效。' % n)
        # 事件序
        te = j.get('T_events', [])
        if te:
            out.append('  ── 事件序（前 8 条）──')
            out.append('     %-6s %-10s %-10s %-8s %-6s %s'
                       % ('step', 'T(K)', 'df', 'field', 'k', 'mode'))
            for e in te[:8]:
                out.append('     %-6s %-10.2f %-10.4g %-8s %-6s %s'
                           % (e.get('step'), e.get('T', float('nan')),
                              e.get('df', float('nan')), e.get('field'),
                              e.get('k'), e.get('mode')))
            out.append('     ⚠ **C1 的另一半（seed 可复现）要有两次同 seed 的运行才能判** ——')
            out.append('        本脚本只能报"当前这一份的位点是什么"；')
            out.append('        逐位复现需要 `R1` 对照（同 seed 跑两次比 `sites`）。')
        out.append('')
    txt = '\n'.join(out)
    print(txt)
    open('_w2_r581_c1uni.log', 'w').write(txt + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
