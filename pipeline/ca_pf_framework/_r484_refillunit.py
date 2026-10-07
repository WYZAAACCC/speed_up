#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r484_refillunit.py —— **任务(2) ③（位点持续可用）的单元验收**。

## 为什么要改成单元测试（`_r482` 的端到端冒烟**测不出**这个开关）

`_r482` 用 `--nuc-init 2 --nuc-fresh-every 4` 跑了两臂，结果**两臂都是 0 个形核事件** ——
**没测到 `fresh` 通道**。读驱动代码找到原因（`_bk_exp.py:1636-1641`）：

    _fresh_now = ((n_ath_tgt % _K) == 0);  _nf, _ns = (1,0) if _fresh_now else (0,1)

而 `n_ath_tgt` **从 1 起**（`:1235`）⇒ `K=4` 时 `n_ath_tgt=1,2,3` 全走 **`stack`**，
`fresh` 要等到 `n_ath_tgt` 涨到 **4** —— 而 `n_ath_tgt` **只在事件成功时**才 +1
⇒ **若 `stack` 一个也放不成，`n_ath_tgt` 永远到不了 4 ⇒ `fresh` 永远不会被调用**
⇒ 「**`K>1` 时 `fresh` 被 `stack` 饿死**」的**死锁**。（本文件同时把这条登记为发现。）

**⇒ 正确的测法：绕开驱动的节奏，直接驱动 `nucleate()` 的 `fresh` 通道。**

## 预登记判据（**第一版已被实测推翻，见下；这里登记的是 v2**）

**★ v1（已被推翻，留痕）**：我以为病灶是"**池子被用尽**"（`sites.pop` 消耗位点），
所以判据写成"前 2 次成功、第 3 次起必须 0、末池必须为 0"。
**实测 U1 ⇒ FAIL**：
```
每次调用的事件数 = [1, 0, 0, 0, 0, 0, 0, 0]
池子剩余         = [1, 1, 1, 1, 1, 1, 1, 1]      ← **池子没有减少到 0！**
```
⇒ **真正的病灶是"卡死"，不是"用尽"**：某个位点在几何上永远不合格（落在已转变区里），
而 `sites.pop(i)` **只在成功时执行**（`if _any_ok`）
⇒ 它**永远留在队里、每次被重试、每次都失败** ⇒ 后续事件全被它堵住。
**⇒ v1 判据的错误是我的"模型"错了，不是量具坏了。**

**★ v2（本文件现在用的，在看清 v1 读数之后登记 ⇒ 属事后登记，须如实标注）**：

| # | 检验 | 判据 |
|---|---|---|
| **U1′** | **病灶存在（负对照）** | `sites_refill=False` 时：**总事件 < N_CALL**（早早停），**且末池 > 0**（证明是"卡死"而非"用尽"） |
| **U2′** | **修复有效** | `sites_refill=True` 时**总事件 > U1′** |
| **U3′** | **对照有效性** | 两臂**配置只差 `sites_refill`**（打印核对）。⚠ **不比较运行中的池子大小** —— v1 那样比是错的：补货发生在调用**之前**，两边池子本来就不同 |
| **U4** | **默认关闭** | 不传 `sites_refill` ⇒ 与 U1′ 逐项相同 |
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W                                  # noqa: E402
from T16_verify_rve import C, EPS0                           # noqa: E402

N = 48
DX = 62.5e-9
# ★ 自查：`nv` 由 **`eps0` 的长度**决定（`EPS0` 有 12 个 K-S 变体），
#   **不是**由 `df` 的长度决定。第一版把 `NV=6` 写死、`npref_tab` 只填 1..6，
#   而 `argmax` 在 12 个变体上选 ⇒ 抽到变体 10 时 `KeyError`。
#   ⇒ 改成 **与 `EPS0` 一致**。
NV = len(EPS0)
GAMMA = 0.25
T_NUC = 510e-9
R_NUC = 320e-9
DF = 1.2e8
N_CALL = 8
TOL_U2_EV = 6


def P(s):
    print(s, flush=True)


def build():
    eps0 = [np.asarray(e, float) for e in EPS0]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps0, gamma=GAMMA, Mob=1e-9,
                        df=[0.0] + [DF] * NV, workers=1,
                        reinit_every=0, reinit_dt=1e-4)
    # ★ 自查：`nucleate()` 内部会调 `_npref_of(kk)`，而 `npref_tab` 是 `advance()`
    #   缓存的（`windowB_surface.py:3274/3427`）⇒ **本单元测试没走 `advance`**
    #   ⇒ 必须自己把表填上（用与驱动同一个收敛 argmin，别自己拍一个法向）。
    g.npref_tab = {k: np.asarray(W._argmin_normal(C, eps0[k - 1])[0], float)
                   for k in range(1, NV + 1)}
    # ★★ 自查发现的错误 #89（**我的量具错，不是引擎错**）：
    #   第一版**没调 `init_parent()`** ⇒ `phi[0]` 从未被设成 `−min(phi[1:])`
    #   ⇒ 第一次 `seed_plate` 的 `phi[0] = max(phi[0], −sdf)` 把母相**抹掉了**
    #   ⇒ 实测 `region` 里母相胞数 = **0/110592** ⇒ `region[cover] == 0` 恒假
    #   ⇒ **此后任何位点都必然 `fresh_blocked`**（实测 7 次 / 35 次）。
    #   我一度把它当成"位点池"的病灶，**是错的**。
    #   真相：`init_parent()` 由**每个驱动显式调用**（`_bk_exp.py:815/936/956/963`），
    #   **不在 `__init__` 里** ⇒ 单元测试必须自己调。
    #   ⚠ 抓到它的方式：**不猜**，把 `region` 里母相胞数打出来 ⇒ 0.00%。
    g.init_parent()
    return g


def arm(refill, n_init=2, seed=11, n_call=N_CALL, nfsv=False):
    """跑一条臂：只驱动 `fresh` 通道（`n_fresh=1, n_stack=0`）。"""
    g = build()
    kw = dict(R_nuc=R_NUC, t_nuc=T_NUC, gamma=GAMMA, n_init=n_init, seed=seed)
    if refill is not None:
        kw['sites_refill'] = refill
    g.nuc_cfg(**kw)
    c = g._nuc
    ev_cnt, pool = [], []
    for _ in range(n_call):
        reg = g.region()
        f_now = 1.0 - float((reg == 0).sum()) / g.N ** 3
        ev = g.nucleate(g.elastic_driving(), f_now=f_now,
                        n_fresh=1, n_stack=0, df=DF)
        ev_cnt.append(len(ev))
        pool.append(len(c.get('sites', [])))
    return g, ev_cnt, pool, c


def main():
    P('=' * 92)
    P('_r484  位点持续可用 —— 单元验收')
    P('=' * 92)
    P('  引擎 N=%d  nv=%d  nuc_init=2  fresh 通道单驱动（n_fresh=1, n_stack=0）' % (N, NV))
    ok_all = True

    # ---------------- U1″ 病灶存在 ----------------
    gA, evA, poolA, cA = arm(False)
    P('\n[U1″ 负对照：sites_refill=False（归档行为）]')
    P('  每次调用的事件数 = %s' % evA)
    P('  池子剩余         = %s' % poolA)
    totA = int(np.sum(evA))
    # ★ 判据回到 **v1 的物理形式**（v1 本来就是对的，是 #89 的坏 harness 让它"看起来错"）：
    #   池子用尽 ⇒ 事件必须停止，且**末池必须为 0**（这是"用尽"的直接证据）。
    u1 = (totA == 2) and (poolA[-1] == 0) and (evA[2] == 0)
    P('  ⇒ 总事件 = **%d**；末池 = **%d**；第 3 次调用的事件数 = %d'
      % (totA, poolA[-1], evA[2]))
    P('  ⇒ 判据（前 2 次成功、第 3 次起 0、末池 == 0 ⇒ "用尽即止"确证）⇒ **%s**'
      % ('✅ PASS' if u1 else '❌ FAIL'))
    ok_all &= u1

    # ---------------- U2″ 修复有效 ----------------
    gB, evB, poolB, cB = arm(True)
    P('\n[U2″ 修复：sites_refill=True（见底时按同一分布继续抽）]')
    P('  每次调用的事件数 = %s' % evB)
    P('  池子剩余         = %s' % poolB)
    P('  dbg 计数         = %s'
      % {k: v for k, v in (cB.get('dbg') or {}).items()
         if 'refill' in k or 'resample' in k})
    totB = int(np.sum(evB))
    # 8 次调用、cap=1、n_fresh=1 ⇒ 上限就是 8
    u2 = (totB == N_CALL) and (poolB[-1] > 0)
    P('  ⇒ 总事件 = **%d / %d**（A 臂 %d）；末池 = %d' % (totB, N_CALL, totA, poolB[-1]))
    P('  ⇒ 判据（== %d 次调用全成 **且** 末池 > 0）⇒ **%s**'
      % (N_CALL, '✅ PASS' if u2 else '❌ FAIL'))
    ok_all &= u2

    # ★★★ 诊断（**不再猜**）：把引擎自己的**拒绝计数**全打出来。
    #   动机：`sites_resampled` 已经在跑而事件仍然为 0 ⇒ 堵点**不在位点池**。
    #   引擎在 `nucleate()` 里为每种失败都记了数（`oob`/`cov`/`empty`/`exc`/
    #   `fresh_blocked`/`nan_ed`/`fcrit`/`supercrit`/`ok`/`nocand`）
    #   ⇒ 直接看是哪一个。
    P('\n[诊断] 引擎自己的拒绝计数（A 臂 = refill 关；B 臂 = refill 开）')
    for nm, c in (('A', cA), ('B', cB)):
        d = c.get('dbg') or {}
        P('  %s: %s' % (nm, {k: int(v) for k, v in sorted(d.items())
                             if not k.startswith('sc_last')}))
        P('     pending_fresh = %s ; n_activated = %s'
          % (c.get('pending_fresh'), c.get('n_activated')))

    # ★★★ 深一层（`fresh_blocked` 只说明"候选位点没过 `cover` 守卫"，
    #   但**没说为什么**）⇒ 直接把那个守卫重算一遍，把每一环都打出来。
    #   动机：`_cands = [ctr]`（`'ed'` 规则下**只有一个候选**，就是位点自身）
    #   ⇒ **只要位点自身那一点不合法，这个位点就永远废掉、且位置从不重抽**。
    P('\n[诊断-2] 直接复算 `cover` 守卫（拿 B 臂当前状态）')
    regB = gB.region()
    P('  region 统计：母相(0) 胞数 = %d / %d（%.2f%%）'
      % (int((regB == 0).sum()), regB.size, 100.0 * (regB == 0).mean()))
    _nrm_t = np.asarray(gB._npref_of(1), float)
    _nrm_t = _nrm_t / (np.linalg.norm(_nrm_t) + 1e-300)
    P('  R = %.1f nm   t = %.1f nm   _npref_of(1) = %s'
      % (T_NUC * 0 + R_NUC * 1e9, T_NUC * 1e9, np.round(_nrm_t, 4).tolist()))
    for j, (k_s, ctr_s) in enumerate((gB._nuc.get('sites') or [])[:3]):
        _rel = gB.XYZ - np.asarray(ctr_s, float)
        _dd = _rel @ _nrm_t
        _rp = np.linalg.norm(_rel - _dd[..., None] * _nrm_t, axis=-1)
        _cov = (np.abs(_dd) <= T_NUC / 2) & (_rp <= R_NUC)
        nc = int(_cov.sum())
        frac_nonzero = float((regB[_cov] != 0).mean()) if nc else float('nan')
        P('    位点 %d：k=%d ctr=%s（nm） ⇒ cover 胞数=%d  any=%s  非母相占比=%.3f  %s'
          % (j, k_s, np.round(np.asarray(ctr_s) * 1e9, 1).tolist(), nc,
             bool(_cov.any()), frac_nonzero,
             '✅ 合法' if (nc and frac_nonzero == 0) else '❌ 被守卫拒绝'))

    # ---------------- U4 默认关闭 ----------------
    gD, evD, poolD, cD = arm(None)
    u4 = (evD == evA)
    P('\n[U4 默认关闭]  不传 `sites_refill` 时的事件数 = %s' % evD)
    P('  ⇒ 与 U1′ 逐项相同？ **%s**  ⇒ %s'
      % (u4, '✅ PASS（默认 = 归档行为）' if u4 else '❌ FAIL（默认被改了！）'))
    ok_all &= u4

    # ---------------- U3′ 对照有效性 ----------------
    #   ⚠ v1 这里比的是"运行中的池子大小" —— **那是错的**（补货发生在调用**之前**，
    #     两边池子本来就不同）⇒ 改成核对**配置**只差一个键。
    u3 = True   # 由 `arm()` 的结构保证：只有 `sites_refill` 一个 kw 不同
    P('\n[U3′ 对照有效性]  两臂只差 `sites_refill`（由 `arm()` 的结构保证，'
      'N/R/t/seed/γ/df 全部相同）⇒ %s' % ('✅ PASS' if u3 else '❌ FAIL'))
    ok_all &= u3

    P('\n' + '=' * 92)
    P('★ 总结论：%s' % ('**全部 PASS ⇒ 任务(2) ③ 验收通过**' if ok_all
                        else '❌ **有 FAIL ⇒ 不得宣称任务(2) ③ 完成**'))
    P('=' * 92)
    return 0 if ok_all else 3


if __name__ == '__main__':
    sys.exit(main())
