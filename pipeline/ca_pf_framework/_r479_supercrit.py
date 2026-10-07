#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r479_supercrit.py —— **超临界判据（任务(2) ②）的验收**。

## 被验的对象

判据（`PHYSICS_FIRST_SPEC §6.1`）：**板条站得住 ⟺ `ΔG_v(T) + ed_face > 2γ/t`**。
实现：`LevelSetMulti._supercrit_probe(kk, cover, reg, df, t, gamma)`
—— **试放**：造一个"假如把 `cover` 划给 `kk`"的试放 `region`，跑一次弹性求解，
读该板条自己的 `ed`，**什么都不改**地返回。

## 为什么"试放"这个近似必须被单独验证

实现**不写任何场**（所以不需要备份/回滚 9.2 GB 的 `phi`），依据是
「`sigma_tensor(idx)` 只认 `region`、不认 `phi`」。
**⇒ 那么"试放 `region` 给出的 `ed`"与"真 `seed_plate` 之后的 `ed`"必须足够接近**，
否则整个判据是在判一个不存在的东西。

## 预登记判据（**先写死，且必须能失败**）

| # | 检验 | 判据 |
|---|---|---|
| **T1** | **试放 vs 真放**（核心） | `\|med_ed_trial − med_ed_real\| / \|med_ed_real\| ≤ 0.15` |
| **T2** | **内部自洽** | 返回值必须满足 `ok == (df + med_ed > fcrit)` |
| **T3** | **正对照**：`df = +1e12`（大得离谱） | `ok` **必须** True |
| **T4** | **负对照**：`df = 0` 且 `t` 很小（⇒ `2γ/t` 极大） | `ok` **必须** False |
| **T5** | **判据不是恒真/恒假** | 存在某个 `df` 使 `ok` **翻转**（二分求 `df*`），且 `df*+med_ed ≈ fcrit` |
| **T6** | **不改场**（实现承诺） | 调用 `_supercrit_probe` 前后 `phi` **逐位相同** |

⚠ 若 T1 不过 ⇒ 试放近似不成立 ⇒ **必须改成真放 + 回滚**（代价另算）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W                                  # noqa: E402
import windowB_km as KM                                      # noqa: E402
from T16_verify_rve import C, EPS0                           # noqa: E402

N = 64
DX = 62.5e-9
NV = 4
GAMMA = 0.25
T_NUC = 510e-9
R_NUC = 320e-9
TOL_T1 = 0.15
BIG = 1e12


def P(s):
    print(s, flush=True)


def build():
    eps0 = [np.asarray(e, float) for e in EPS0]
    return W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=GAMMA, Mob=1e-9,
                           df=[0.0] + [1.2e8] * NV, workers=1,
                           reinit_every=0, reinit_dt=1e-4)


def plate_cover(g, center, nrm, R, t):
    rel = g.XYZ - np.asarray(center, float)
    d = rel @ np.asarray(nrm, float)
    rp = np.linalg.norm(rel - d[..., None] * np.asarray(nrm, float), axis=-1)
    return (np.abs(d) <= t / 2) & (rp <= R)


def main():
    P('=' * 92)
    P('_r479  超临界判据（试放）验收')
    P('=' * 92)
    g = build()
    P('  引擎：N=%d  L=%.2f µm  nv=%d  γ=%.3f' % (N, g.L * 1e6, NV, GAMMA))
    kk = 2                                   # 板条在场号 2（变体 2）
    # ⚠ 自查：第一版用 `g._npref_of(kk)` ⇒ RuntimeError「`npref_tab` 未设置」
    #   （它要 `advance(npref=...)` 先被调过）。这里**直接向收敛的 argmin 要**，
    #   与 `T16_verify_rve`/`LevelSetMulti.__init__` 用的是同一个函数。
    nrm = np.asarray(W._argmin_normal(C, np.asarray(EPS0[kk - 1], float))[0], float)
    ctr = np.array([N * DX / 2, N * DX / 2, N * DX / 2])
    cover = plate_cover(g, ctr, nrm, R_NUC, T_NUC)
    P('  试放位点 = 盒中心；核 R=%.0f nm t=%.0f nm ⇒ cover = %d 胞'
      % (R_NUC * 1e9, T_NUC * 1e9, int(cover.sum())))
    if cover.sum() == 0:
        P('  ✗ cover 为空 ⇒ 测试无意义')
        return 2
    reg = g.region()
    if not bool((reg[cover] == 0).all()):
        P('  ⚠ cover 内不全是母相（%d 个非 0）—— 仍继续，但记一笔'
          % int((reg[cover] != 0).sum()))

    ok_all = True

    # ---------------- T6 不改场（净效果） ----------------
    phi_before = g.phi.copy()
    ok_t, med_t, fc_t, nc_t = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC,
                                                 cover, 1.2e8, GAMMA)
    same = bool(np.array_equal(g.phi, phi_before))
    P('\n[T6 不改场（净效果必须为零）]  调用后 `phi` 逐位相同 = **%s**  ⇒ %s'
      % (same, '✅ PASS' if same else '❌ FAIL（回滚没还原干净！）'))
    ok_all &= same

    # ---------------- T1 试放 vs 真放 ----------------
    #   ★ 注意语义变化：现在的 `_supercrit_probe` **就是**"真放 + 回滚"
    #     ⇒ T1 不再比"两种近似"，而是比"**探针报的 med_ed**"与
    #       "**独立做一次真放后读到的 med_ed**"是否一致（应当**逐位相同**）。
    P('\n[T1 探针报的 med_ed vs 独立真放（必须一致）]')
    P('  探针：med_ed = %.6e   判据 fcrit = %.6e   ok = %s' % (med_t, fc_t, ok_t))
    g.seed_plate(kk, ctr, nrm, R_NUC, T_NUC)
    reg_real = g.region()
    ed_real = g.elastic_driving()
    med_r = float(np.median(ed_real[kk][cover]))
    n_real = int((reg_real[cover] == kk).sum())
    P('  真放：med_ed = %.6e   （cover 内 %d/%d 胞归了场 %d）'
      % (med_r, n_real, int(cover.sum()), kk))
    rel = abs(med_t - med_r) / max(abs(med_r), 1e-300)
    # ★ 判据收紧到 1e-9：既然两者是**同一条路径**，就应当逐位一致。
    ok1 = rel <= 1e-9
    P('  ⇒ 相对差 = **%.3e**（判据 ≤ 1e-9，因为两者是同一条路径）⇒ **%s**'
      % (rel, '✅ PASS' if ok1 else '❌ FAIL（探针与真放不一致 ⇒ 实现有 bug）'))
    ok_all &= ok1

    # ---------------- T2 内部自洽 ----------------
    ok2 = (ok_t == (1.2e8 + med_t > fc_t))
    P('\n[T2 内部自洽]  ok == (df + med_ed > fcrit) ？ **%s**  ⇒ %s'
      % (ok2, '✅ PASS' if ok2 else '❌ FAIL'))
    ok_all &= ok2

    # ---------------- T3/T4 正负对照 ----------------
    P('\n[T3/T4 正负对照]')
    o3, m3, f3, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cover, BIG, GAMMA)
    P('  T3 df=+1e12 ⇒ ok = %s  必须 True ⇒ %s'
      % (o3, '✅ PASS' if o3 else '❌ FAIL'))
    ok_all &= bool(o3)
    o4, m4, f4, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, 5e-9, cover, 0.0, GAMMA)
    P('  T4 df=0、t=5 nm（fcrit=%.3e）⇒ ok = %s  必须 False ⇒ %s'
      % (f4, o4, '✅ PASS' if (not o4) else '❌ FAIL'))
    ok_all &= (not o4)

    # ---------------- T5 存在翻转点 ----------------
    P('\n[T5 存在翻转点（判据不是恒真/恒假）]')
    lo, hi = -1e10, 1e10
    f_lo, _, _, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cover, lo, GAMMA)
    f_hi, _, _, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cover, hi, GAMMA)
    if f_lo == f_hi:
        P('  ❌ 两端同值（%s）⇒ 判据恒真或恒假 ⇒ FAIL' % f_lo)
        ok_all = False
    else:
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cover, mid, GAMMA)[0]:
                hi = mid
            else:
                lo = mid
        df_star = hi
        _, m5, f5, _ = g._supercrit_probe(kk, ctr, nrm, R_NUC, T_NUC, cover, df_star, GAMMA)
        resid = abs(df_star + m5 - f5) / max(abs(f5), 1e-300)
        ok5 = resid < 1e-6
        P('  翻转点 df* = **%.6e**（二分 60 次）；核对 df*+med_ed = %.6e vs fcrit = %.6e'
          % (df_star, df_star + m5, f5))
        P('  ⇒ 相对残差 %.2e ⇒ **%s**' % (resid, '✅ PASS' if ok5 else '❌ FAIL'))
        ok_all &= ok5
        # ★ 自查发现的错误 #86：第一版这里打印
        #     `dg = abs(df_star + m5)` ⇒ 那拿到的是 **fcrit（≈9.8e5）**，不是 df*。
        #     于是印出"T ≲ 1142.6 K"这种**荒谬**读数（等于说"任何温度都能形核"），
        #     与同一行上面的 `df* = 3.18e8` **自相矛盾**。**正确读数是 `ΔG_v ≳ df*`。**
        P('  ⇒ 物理读数：该位点需要的 `ΔG_v` ≳ **%.4e J/m³**（= 翻转点 `df*`）' % df_star)
        P('     （对照：判据阈值 `2γ/t = %.4e`；差额 = 该盘的**弹性罚** `|med_ed|`）' % f5)
        TT = 1145.0 - df_star / 4.147e5
        dg298 = float(KM.drive_of_T(298.0, KM.T0_TI64, KM.DS_REF))
        P('     用 `ΔG_v(T)=4.147e5·(1145−T)` 折算 ⇒ 需要 **T ≲ %.1f K**' % TT)
        P('     对照 `ΔG_v(298 K) = %.4e` ⇒ 比值 **%.3f×** ⇒ %s'
          % (dg298, dg298 / df_star,
             '**该位点在 298 K 够格**（但只在冷却的最后一段）'
             if dg298 > df_star else '**该位点即使到 298 K 也不够格**'))

    P('\n' + '=' * 92)
    P('★ 总结论：%s' % ('**全部 PASS ⇒ 超临界判据可用**' if ok_all
                        else '❌ **有 FAIL ⇒ 不得宣称任务(2) ② 完成**'))
    P('=' * 92)
    return 0 if ok_all else 3


if __name__ == '__main__':
    sys.exit(main())
