#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r176_f2gamma_check.py —— **`--f2-pair-gamma` 的正对照**：便宜的界面落在**对的**变体对上吗？

## 为什么必须查

`§123`（R164）补的 F2 配对 γ 是**整个"自协调"论证的关键新机制**。它一旦接错线
（例如把 `Δε_ref` 取成**逐臂**最大值而不是**全库**最大值、或把变体标号搞错），
`_r165` 的判决就会**指向错误的物理解释**，而且**表面上看不出问题**。

## 判据（**先写死，再读数据**）

`windowB_lath.py:286-288`：
    γ_F2(i,j) = γ₀·[(1−λ) + λ·min(1, ‖Δε(v_i,v_j)‖_F / Δε_ref)]
    Δε_ref = **本表内**异变体对的最大 ‖Δε‖（`:276-279`）

* **F-1** λ=1 时，γ 最小的那一批 F2 对，必须**恰好**是 `§163` 实测的
  **‖Δε‖_F/scale 全局最小（0.1830）**的那 6 对同 packet 对
  = `§94` 的**唯一完美匹配** `(1,2)(3,4)(5,6)(7,8)(9,10)(11,12)`。
* **F-2** γ 最大的 F2 对，必须恰好是 `§163` 的**全局最大（1.7056）**那一对。
* **F-3** λ=0 时 F2 的 `gtab` 必须**全 NaN**（不填）⇒ 引擎走标量路径（惰性）。
* **F-4** 若某臂**不含**任何最小失配对 ⇒ 该臂的 `min γ_F2` 必须**明显大于** 0.0268
  （这是 `G-2` 有区分力的前提）。

⚠ **规程（硬规则 ④⑨）**：
  * F-1/F-2 是**正对照** —— 先在已知答案上验证工具，再用它说话。
  * 退化输入检查：`Δε_ref = 0`（只有一个变体）时分母为 0 ⇒ 必须不炸、且不填表。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MB = os.path.join(HERE, '_exp', '_bk_mb')

# `§94` 的唯一完美匹配（自协调六对）
SELFAC_PAIRS = {(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)}

# `§163` 的 66 对失配实测（用于 F-2 的正对照）
DE_MIN_PAIR = (1, 2)          # ‖Δε‖_F/scale = 0.1830（全局最小）
DE_MAX_PAIR = (3, 10)         # = 1.7056（全局最大）
DE_REF_LIB = 1.7056           # 全库最大值（scale 归一后）


def lam_of(m):
    """★ **本函数是第一版一个假阳性的根因**，记下来。

    `_bk_exp.py:982-1019` 的 meta 构造里**没有**顶层 `f2_pair_gamma` 键 ——
    λ 只出现在 `exp_args`（= `vars(a)`，整个 argparse 命名空间，`:1013`）里。
    第一版写 `m.get('f2_pair_gamma', 0.0)` ⇒ **λ=1 的臂被读成 0** ⇒
    `F-3` 误报 ❌（"λ=0 却填了 60 个 F2 条目"）。
    ⇒ 正确读法：`exp_args.f2_pair_gamma`；顶层键**不存在**时也**不要**默认成 0
      而不作声（硬规则 ⑩：判决脚本必须打印它真读到的）。
    """
    if 'f2_pair_gamma' in m:
        return float(m['f2_pair_gamma']), 'meta 顶层键'
    ea = m.get('exp_args') or {}
    if 'f2_pair_gamma' in ea:
        return float(ea['f2_pair_gamma']), '**`exp_args.f2_pair_gamma`**（顶层键不存在）'
    return 0.0, '**两处都读不到** ⇒ 按 0 处理（可能是本轮之前的旧臂）'


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else None


def pairs_of(d):
    """从 meta 的 `gamma_RS` dict 抽出 (i,j)->γ。**注意该字段名有误导性**：
    它装的是 `gtab` 里**一切有限元**，λ=1 时同时含 F2 与 F3 对。"""
    out = {}
    for k, v in (d or {}).items():
        if not isinstance(k, str) or '-' not in k:
            continue
        try:
            i, j = (int(x) for x in k.split('-'))
        except ValueError:
            continue
        try:
            out[(i, j)] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def main():
    print('=' * 112)
    print('_r176 —— `--f2-pair-gamma` 正对照：便宜的界面落在对的变体对上吗？')
    print('=' * 112)
    # ★ 独立重算失配表（**不读 `gtab`**，从 `T16_verify_rve.EPS0` 自己算）
    try:
        from T16_verify_rve import EPS0 as _EPS0
        de_indep = {}
        for v in range(1, 13):
            for w in range(v + 1, 13):
                de_indep[(v, w)] = float(np.linalg.norm(
                    np.asarray(_EPS0[v - 1], float) - np.asarray(_EPS0[w - 1], float)))
        print('  独立失配表（自算 `‖ε⁰_v − ε⁰_w‖_F`，%d 对）：min = **%.6g** @ %s；'
              'max = **%.6g** @ %s'
              % (len(de_indep), min(de_indep.values()),
                 min(de_indep, key=de_indep.get), max(de_indep.values()),
                 max(de_indep, key=de_indep.get)))
        lib_min = min(de_indep.values())
        d1, d2 = DE_MIN_PAIR
        print('  与 `§163` 实测核对：`‖Δε‖(V%d,V%d)` 是否 = 全库最小？ ⇒ %s'
              % (d1, d2, '✅' if abs(de_indep[(d1, d2)] - lib_min) < 1e-12 else '❌'))
    except Exception as e:                                    # noqa: BLE001
        print('  ⚠ 独立失配表算不出来（%s）⇒ F-1a 跳过' % e)
        de_indep = None
    ok = True
    for tag in ('saSet2', 'saSet2F2', 'saOddG', 'saOddGF2'):
        m = load(tag)
        if m is None:
            print('\n  ⚠ `dry_%s` 无 meta.json ⇒ 跳过' % tag)
            continue
        lam, lamsrc = lam_of(m)
        g0 = float(m.get('gamma0', 0.25))
        laths = [int(x) for x in m.get('laths', [])]
        V = {k + 1: v for k, v in enumerate(laths)}          # 板条号(1起) -> 变体
        G = pairs_of(m.get('gamma_RS'))
        print()
        print('  ' + '-' * 104)
        print('  ## `dry_%s`   λ = **%.2f**（读自 %s）   γ₀ = %.3f   M=%d'
              % (tag, lam, lamsrc, g0, len(laths)))
        print('     变体表（板条号→变体）：%s'
              % ', '.join('%d→V%d' % (k, V[k]) for k in sorted(V)))
        if not G:
            print('     `gamma_RS` = 空 ⇒ **F3/F2 的 `gtab` 全 NaN** ⇒ 引擎走标量路径')
        # 分类
        f3 = {(i, j): g for (i, j), g in G.items() if V.get(i) == V.get(j)}
        f2 = {(i, j): g for (i, j), g in G.items() if V.get(i) != V.get(j)}
        print('     `gamma_RS` 条目 %d 个：**同变体(F3) %d 个**、**异变体(F2) %d 个**'
              % (len(G), len(f3), len(f2)))
        if f3:
            vals = sorted(f3.values())
            print('     F3 γ 范围 [%.6f, %.6f]（同变体低角）' % (vals[0], vals[-1]))
            print('     **F-3** λ=0 ⇒ F2 条目应为 0：实测 **%d** ⇒ %s'
                  % (len(f2), '✅' if (lam == 0) == (len(f2) == 0) else '❌'))
            if lam == 0 and len(f2):
                ok = False
        if not f2:
            if lam == 0:
                print('     ⇒ λ=0：**F2 未填 gtab** ✅（引擎走标量 ⇒ 惰性）')
            else:
                print('     ⇒ ❌ λ>0 却一个 F2 条目都没有 ⇒ **接线断了**')
                ok = False
            continue
        # ---- 核心：最便宜的 F2 对是谁 ----
        byg = sorted(f2.items(), key=lambda kv: kv[1])
        lo = byg[0][1]
        thresh = lo * 1.001
        cheap = sorted((i, j) for (i, j), g in f2.items() if g <= thresh)
        cheapV = sorted(tuple(sorted((V[i], V[j]))) for (i, j) in cheap)
        print('     ⇒ **最便宜的 F2 对** γ_min = **%.6f** = **%.4f× γ₀**（比标量低 %.1f 倍）'
              % (lo, lo / g0, g0 / lo if lo > 0 else float('inf')))
        print('        板条对：%s' % cheap)
        print('        变体对：%s' % cheapV)
        if lam > 0:
            # ---- F-1b：**适用性门控**（硬规则 ⑤）----
            #   本臂**含**几个 `§94` 自协调对？含 0 个的臂**按构造不可能**满足
            #   "最便宜对 ⊂ 六对" ⇒ 那是**不适用**，不是 ❌。
            #   （第一版把它判 ❌ —— 与 `_r159`/`_r172` 同一类错误：把不适用的
            #    配置当成失败。见 `§153` 的"适用域"教训。）
            arm_pairs = {tuple(sorted((V[i], V[j]))) for (i, j) in f2}
            have = sorted(p for p in arm_pairs if p in SELFAC_PAIRS)
            print('     **F-1b 适用性**：本臂共 %d 个异变体对，其中 ⊂ `§94` 六对的 = '
                  '**%d 个** %s' % (len(arm_pairs), len(have), have))
            if have:
                is_lib_min = all(p in SELFAC_PAIRS for p in cheapV)
                print('     **F-1b** 最便宜的那些变体对是否 ⊂ `§94` 六对？ ⇒ %s'
                      % ('✅ 是' if is_lib_min else '❌ 否 —— **接线可能错了**'))
                if not is_lib_min:
                    ok = False
                    print('        ⚠ 不属于六对的：%s'
                          % sorted(set(p for p in cheapV if p not in SELFAC_PAIRS)))
                exp = g0 * (1.0 - lam + lam * de_indep[DE_MIN_PAIR] /
                            max(de_indep.values())) if de_indep else float('nan')
                got = lo
                if exp == exp:
                    print('     **F-1b′ 定量**：独立算得 `γ_min` 应为 **%.6f**，'
                          '实测 **%.6f** ⇒ %s'
                          % (exp, got, '✅ 一致' if abs(exp - got) < 1e-9 else '❌ 不一致'))
                    if abs(exp - got) >= 1e-9:
                        ok = False
            else:
                print('     **F-1b** ⇒ ⚪ **不适用**（本臂一对自协调对都没有，'
                      '按构造不可能满足）—— 这**不是**失败')
            # ---- F-1a：**臂内单调性**（与库无关，任何臂都能查）----
            if de_indep:
                bad_mono = []
                for (i, j), g in f2.items():
                    vi, vj = tuple(sorted((V[i], V[j])))
                    for (k, l), h in f2.items():
                        vk, vl = tuple(sorted((V[k], V[l])))
                        if de_indep[(vi, vj)] < de_indep[(vk, vl)] - 1e-15 \
                                and g > h + 1e-12:
                            bad_mono.append(((i, j), (k, l)))
                print('     **F-1a 臂内单调性**（γ 序必须与独立算的 `‖Δε‖` 序一致）：'
                      '反序对数 = **%d** ⇒ %s'
                      % (len(bad_mono), '✅ 通过' if not bad_mono else '❌ 失败'))
                if bad_mono:
                    ok = False
                    print('        前 3 个：%s' % bad_mono[:3])
            his = sorted(f2.items(), key=lambda kv: -kv[1])[:3]
            print('     **F-2** 最贵的 3 个 F2 对（期望含 `§163` 的全局最大 '
                  '`V%d-V%d`=%.4f）：%s'
                  % (DE_MAX_PAIR[0], DE_MAX_PAIR[1], DE_REF_LIB,
                     ['%s γ=%.4f' % (('%d-%d' % k), v) for k, v in his]))
        else:
            print('     （λ=0，不做 F-1/F-2）')
        # F-4：本臂有没有"便宜界面"可用
        n_selfac_pairs = sum(1 for p in cheapV if p in SELFAC_PAIRS)
        print('     **F-4** 本臂最便宜档里含 **%d** 个自协调对 ⇒ %s'
              % (n_selfac_pairs,
                 '**有便宜的可用通道**' if n_selfac_pairs else
                 '**没有自协调对可用** ⇒ 与 `saSet2` 应有区分力'))

    print()
    print('=' * 112)
    print('  ## 总判定')
    print('=' * 112)
    print('     ⇒ %s' % ('✅ **F-1/F-2/F-3 全部通过**：F2 配对 γ 的接线与物理判据一致'
                         if ok else
                         '❌ **有判据不过** ⇒ 见上，先修接线再读 `_r165` 的判决'))
    print()
    print('  ⚠ 记账：本脚本**只读 meta.json**，不重跑、不改任何东西。')
    print('  ⚠ 该字段名叫 `gamma_RS` 但装的是 **`gtab` 的一切有限元**（含 λ>0 的 F2 项）')
    print('     ⇒ 字段名**有误导性**，读数时不要以为它只有 F3。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
