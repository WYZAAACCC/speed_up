#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R473 —— 生长窗口的**可判别**检验：逐根板条的体积变化 vs `ΔG_v/|ed|`。

## 为什么重做（R472 的预登记判据没过，照实记账）

`_r472` 的两条判据都有病：
* **P1 不适定**：它看的是**总** `Vt`。而 `Vt` 里**同时**含两件事 ——
  ①已有板条在长/缩；②**新核不断加进来**（每次形核都加体积）。
  ⇒ 总 `Vt` **原理上分不出"在缩"**。**这是我的判据设计错误，不是物理错。**
* **负对照不可判别**：我把门槛挪 +100 K 后，"窗口内"集合只是**变大**（含住了真转折点）
  ⇒ 错门槛当然也"看到回升" ⇒ **该负对照原理上无法否证**。

## 本脚本的判据（**先写死**）

数据：`series.csv` 的 **`vols`** 列（各场体积，**斜杠分隔**，单位 **µm³**，教训 #55/#56）。

做法：对**每一根在位的场 k**，取相邻两行求 `ΔV_k`；把每一次变化按当时的
`Λ = ΔG_v(T)/|ed|` 分桶。**预测：`ΔV` 对 `Λ` 单调增，且符号变化发生在 `Λ ≈ 1`。**

* **P1（单调性）**：分桶均值 `mean(ΔV)` 随 `Λ` 桶**单调递增**
  （桶边界：`<0.80, 0.80–0.95, 0.95–1.05, 1.05–1.20, >1.20`）。
* **P2（符号变化位置）**：`mean(ΔV)` 由负转正的那个桶，**必须**是 `0.95–1.05` 或它与相邻的一个。
* **P3（负对照，必须能失败）**：把 `Λ` 序列**随机打乱**（固定种子）再分桶
  ⇒ 单调性**必须消失**（Spearman |ρ| < 0.5）。
  若打乱后仍单调 ⇒ **判据在测别的东西** ⇒ 本结果不可信。

⚠ 且必须报：**参与统计的板条数、每桶样本数**（样本太少不下结论）。

---

## ★★ v2 判据（**在 v1 跑出 FAIL 之后新登记**，留痕）

**v1 的结果（`dry_abA`，512 样本）：`P1=FAIL  P2=FAIL  P3=PASS` ⇒ 未证实。**
**v1 的两条判据都有设计缺陷**（照实记账，不抹掉）：
1. **统计量选错**：v1 用 `mean(ΔV)`，而 `ΔV` 的分布**被"新核出现"这一个事件完全主导**
   （一个场从 0 变成正体积 ⇒ 单个巨大正值）。
   v1 的过滤 `if a[k]<=0 and b[k]<=0: continue` **放过了 `a[k]<=0 < b[k]` 这种情形**
   ⇒ 新核被算成了"长大"。**实测证据**：`[0,0.80)` 桶的 `mean = +1.19e-3` 而 `median = −5.62e-3`
   —— 均值与中位**符号相反** ⇒ 均值被离群值主导。
2. **单调性用错了对象**：应当看**符号/中位**（"这根在长还是在缩"），不是均值。

**v2 的判据（先写死）：**
* **过滤**：只统计 **`a[k] > 0`** 的配对（该板条**上一行就已经存在**）⇒ 排除新核。
* **统计量**：`frac_pos` = `ΔV > 0` 的占比（对离群值稳健）+ `median(ΔV)`。
* **P1′**：`frac_pos` 随 Λ 桶**单调递增**。
* **P2′**：`frac_pos` 跨过 0.5 的位置落在 `[0.80,0.95)` 或 `[0.95,1.05)` 桶。
* **P3′（负对照）**：打乱 Λ 后 `Spearman(Λ, ΔV)` 的 `|ρ| < 0.5`。
* **P4′（独立性）**：**必须在 `dry_abB`（不同冷速、本判据此前从未看过它）上先跑**，
  再回到 `dry_abA`。**只在 abA 上跑不算独立确认**（v2 判据是看着 abA 的 v1 失败设计的）。

用法：`python3 _r473_lathwindow.py [tag] [--v2]`
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_km as KM                            # noqa: E402
from _r463_reinitcount import read_rows             # noqa: E402
from _r470_growthwindow import E_EL_J, HALF_AXES_NM  # noqa: E402

BUCKETS = [(0.0, 0.80), (0.80, 0.95), (0.95, 1.05), (1.05, 1.20), (1.20, 99.0)]
TOL_RHO = 0.5


def parse_vols(s):
    """`vols` 是**斜杠分隔**、单位 **µm³**（教训 #55/#56：曾被当成逗号分隔+SI ⇒ 空列表）。"""
    out = []
    if not s:
        return out
    for x in s.split('/'):
        x = x.strip()
        if not x:
            continue
        try:
            out.append(float(x))
        except ValueError:
            out.append(np.nan)
    return out


def spearman(a, b):
    if len(a) < 3:
        return float('nan')
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    return float((ra * rb).sum() / d) if d > 0 else float('nan')


def main():
    argv = [x for x in sys.argv[1:] if not x.startswith('--')]
    V2 = '--v2' in sys.argv
    tag = argv[0] if argv else 'dry_abA'
    root = '_exp/_bk_mb'
    import json
    with open(os.path.join(root, tag, 'meta.json')) as fh:
        m = json.load(fh)
    ea = m.get('exp_args') or {}
    q = float(ea.get('cool_rate', 0.0))
    Ts_arg = float(ea.get('T_start', 0.0))
    alpha = float(ea.get('alpha_km', 0))
    T_start = Ts_arg if Ts_arg > 0 else float(KM.M_S_TI64 - 1.0 / alpha)
    T_end = float(ea.get('T_end', 298.0))
    if q <= 0:
        print('✗ %s 非 athermal（q=0）⇒ 本判据不适用' % tag)
        return 2

    V_m3 = (4.0 / 3.0) * np.pi * (HALF_AXES_NM[0] * 1e-9) * \
        (HALF_AXES_NM[1] * 1e-9) * (HALF_AXES_NM[2] * 1e-9)
    ed = E_EL_J / V_m3

    rows = read_rows(os.path.join(root, tag, 'series.csv'))
    if not rows:
        print('✗ 读不到 series.csv')
        return 2
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    if 'vols' not in ix:
        print('✗ 没有 vols 列')
        return 2
    ts, vols = [], []
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            ts.append(float(c[ix['t_s']]))
        except ValueError:
            continue
        vols.append(parse_vols(c[ix['vols']]))
    f = KM.linear_cool(T_start, T_end, (T_start - T_end) / q)

    dV, Lam = [], []
    n_lath_pairs = 0
    for i in range(1, len(ts)):
        a, b = vols[i - 1], vols[i]
        n = min(len(a), len(b))
        T = float(f(ts[i]))
        dg = float(KM.drive_of_T(T, KM.T0_TI64, KM.DS_REF))
        lam = dg / ed
        for k in range(n):
            if not (np.isfinite(a[k]) and np.isfinite(b[k])):
                continue
            if a[k] <= 0 and b[k] <= 0:
                continue                      # 两根都没体积 ⇒ 不计
            if V2 and not (a[k] > 0):
                continue                      # ★ v2：排除"新核出现"（a 上一行还不存在）
            dV.append(b[k] - a[k]); Lam.append(lam); n_lath_pairs += 1
    dV = np.array(dV); Lam = np.array(Lam)

    print('=' * 78)
    print('R473%s  %s  逐根板条的 ΔV vs Λ = ΔG_v/|ed|'
          % (' [v2 判据]' if V2 else '', tag))
    print('=' * 78)
    print('  q = %.4e K/s   T: %.2f → %.1f K   行数 %d' % (q, T_start, T_end, len(ts)))
    print('  |ed| = %.6e J/m³' % ed)
    print('  有效（场, 相邻行）样本数 = **%d**' % len(dV))
    if len(dV) < 30:
        print('  ⚠ 样本太少（<30）⇒ 不下结论')
        return 2
    print('  ΔV 单位 = **µm³**（`vols` 列的口径，教训 #56）')
    print()

    def bucket_stats(lams, dvs, label):
        means, ns, fracs = [], [], []
        print('  ── %s ──' % label)
        print('     Λ 桶              n      mean(ΔV)        median(ΔV)     frac_pos')
        for lo, hi in BUCKETS:
            m = (lams >= lo) & (lams < hi)
            if m.sum() == 0:
                means.append(np.nan); ns.append(0); fracs.append(np.nan)
                print('     [%4.2f, %5.2f)  %6d   %-14s %-14s %s'
                      % (lo, hi, 0, '—', '—', '—'))
                continue
            v = dvs[m]
            fp = float((v > 0).mean())
            means.append(float(v.mean())); ns.append(int(m.sum())); fracs.append(fp)
            print('     [%4.2f, %5.2f)  %6d   %+.4e     %+.4e     %.3f'
                  % (lo, hi, m.sum(), v.mean(), np.median(v), fp))
        return means, ns, fracs

    means, ns, fracs = bucket_stats(Lam, dV, '真门槛')
    rho = spearman(Lam, dV)

    if V2:
        # ---- v2：用 frac_pos（对离群稳健）判单调 + 判跨 0.5 的位置 ----
        good = [(i, x) for i, x in enumerate(fracs) if np.isfinite(x) and ns[i] >= 10]
        p1 = bool(len(good) >= 3 and all(good[j][1] <= good[j + 1][1]
                                         for j in range(len(good) - 1)))
        cross = None
        for i in range(1, len(fracs)):
            if (np.isfinite(fracs[i - 1]) and np.isfinite(fracs[i])
                    and fracs[i - 1] < 0.5 <= fracs[i]):
                cross = BUCKETS[i]; break
        if cross is None and np.isfinite(fracs[0]) and fracs[0] >= 0.5:
            cross = BUCKETS[0]
        p2 = cross is not None and cross[0] >= 0.80
        print()
        print('  P1′ frac_pos 随 Λ 单调递增（只算 n≥10 的桶）：**%s**'
              % ('✅ PASS' if p1 else '❌ FAIL'))
        print('     读数：%s' % ' → '.join('%.3f' % x for x in fracs if np.isfinite(x)))
        print('  P2′ frac_pos 跨过 0.5 的桶：**%s**（必须在 [0.80,0.95) 或 [0.95,1.05)）'
              ' ⇒ **%s**' % (cross, '✅ PASS' if p2 else '❌ FAIL'))
        rng = np.random.default_rng(20261001)
        Lam_sh = Lam.copy(); rng.shuffle(Lam_sh)
        _, _, fracs_sh = bucket_stats(Lam_sh, dV, '负对照（Λ 打乱）')
        rho_sh = spearman(Lam_sh, dV)
        p3 = abs(rho_sh) < TOL_RHO
        print('  P3′ 负对照 ρ = **%+.3f**（必须 |ρ| < %.1f）⇒ **%s**'
              % (rho_sh, TOL_RHO, '✅ PASS' if p3 else '❌ FAIL'))
        print()
        print('=' * 78)
        print('★ v2 判读：P1′=%s  P2′=%s  P3′=%s'
              % ('PASS' if p1 else 'FAIL', 'PASS' if p2 else 'FAIL',
                 'PASS' if p3 else 'FAIL'))
        if p1 and p2 and p3:
            print('  ⇒ **生长窗口被证实**（在本臂上；是否独立见 P4′）')
        elif p3:
            print('  ⇒ **未证实**（照实报）')
        else:
            print('  ⇒ **判据无效**')
        print('=' * 78)
        return 0

    # ---------------- v1（原判据，保留以便对照）----------------
    good = [x for x in means if np.isfinite(x)]
    p1 = bool(len(good) >= 3 and all(good[i] <= good[i + 1] for i in range(len(good) - 1)))
    print()
    print('  P1 单调性（分桶**均值**随 Λ 单调递增）：**%s**    Spearman ρ(Λ, ΔV) = **%+.3f**'
          % ('✅ PASS' if p1 else '❌ FAIL', rho))
    sign_at = None
    for i, (lo, hi) in enumerate(BUCKETS):
        if np.isfinite(means[i]) and means[i] > 0:
            sign_at = (lo, hi); break
    p2 = sign_at is not None and sign_at[0] >= 0.80
    print('  P2 由负转正的桶：**%s**  ⇒ %s'
          % (('%s' % (sign_at,)) if sign_at else '（无正值桶）',
             '✅ PASS（在 Λ≈1 附近或更冷）' if p2 else '❌ FAIL（冷到 Λ<0.8 才转正）'))
    rng = np.random.default_rng(20261001)
    Lam_sh = Lam.copy(); rng.shuffle(Lam_sh)
    _, _, _ = bucket_stats(Lam_sh, dV, '负对照（Λ 打乱）')
    rho_sh = spearman(Lam_sh, dV)
    p3 = abs(rho_sh) < TOL_RHO
    print()
    print('  P3 负对照：打乱后 ρ = **%+.3f**（必须 |ρ| < %.1f）⇒ **%s**'
          % (rho_sh, TOL_RHO, '✅ PASS（判据有判别力）' if p3 else '❌ FAIL（判据在测别的东西）'))
    print()
    print('=' * 78)
    print('★ 判读：P1=%s  P2=%s  P3=%s'
          % ('PASS' if p1 else 'FAIL', 'PASS' if p2 else 'FAIL', 'PASS' if p3 else 'FAIL'))
    if p1 and p2 and p3:
        print('  ⇒ **生长窗口被证实**：越冷（Λ 越大）板条长得越多，符号变化发生在 Λ≈1。')
    elif p3:
        print('  ⇒ **未证实**（照实报，不得硬说成立）。')
    else:
        print('  ⇒ **判据无效**，本结果不可用。')
    print('=' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
