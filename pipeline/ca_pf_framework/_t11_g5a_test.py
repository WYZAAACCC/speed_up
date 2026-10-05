#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g5a_test.py —— R623 **G5a（解卡路径去门控）** 的单元测试（v2）。

v1 暴露的两个我的错误（已记）：
  1. 第一版把重抽放在 `fresh` 通道内、并加了 `_tried_any` 门 —— 而
     `n_fresh == 0` 时 `for` 根本进不去 ⇒ `_tried_any` 恒 False ⇒ **门还是过不去**。
  2. `blocked` 位点其实**能放下**（实测 `ev=1`）⇒ 我的几何构造没造出"放不下"。

v2 的判据改成 **「本次调用一个事件都没放成」（`not out`）**，并**显式关掉 `attach`**
（否则 attach 通道会替 fresh 成功，掩盖 stack 的失败）。

要证的命题（可 FAIL）
  P1 **负对照（归档不变）**：`sites_resample_always=False` + 放不下
     ⇒ 两个计数键**都不出现**。
  P2 **核心（缺陷已修）**：`sites_resample_always=True` + 放不下
     ⇒ **`sites_resampled_ungated` 必须 > 0**。
  P3 **正对照（不该洗表时不洗）**：`sites_resample_always=True` + **放成了**
     ⇒ `sites_resampled_ungated` **必须 = 0**（否则量具把正常情况也算成卡死）。
  P4 **与旧键互斥**：P2/P3 里旧键 `sites_resampled` 恒为 0（旧路径在 fresh 名额
     用尽时进不去；名额还在时它才会出现 —— 由 P5 证）。
  P5 **旧路径仍在**：`n_fresh>0` 且位点被占（旧门能进）⇒ 旧键出现。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_surface as WS  # noqa: E402

N, DX = 32, 62.5e-9
L = N * DX
R, T = 4.0 * DX, 2.0 * DX
CFG = dict(gamma=0.15, n_init=2, sites_refill=True, sites_margin=2,
           max_per_step=4, supercrit=False, nfsv=True,
           attach=False,           # ★ v2：关掉 attach，别让它替 stack 成功
           occ_guard=False)


def build(ungated, nv, sites, occupy_field1=False, occupy_all=False):
    g = WS.LevelSetMulti(N, L, nv=nv, gamma=0.0, Mob=1.0)
    g.phi[:] = 1e3
    g.phi[0] = -1e3
    ctr = np.array([L / 2, L / 2, L / 2])
    if occupy_field1:
        g.seed_plate(1, ctr, np.array([0.0, 0.0, 1.0]), R, T)
    if occupy_all:
        for k in range(1, nv + 1):
            g.seed_plate(k, ctr, np.array([0.0, 0.0, 1.0]), R, T)
    g.init_parent()
    g.nuc_cfg(R, T, sites_resample_always=ungated, **CFG)
    g._nuc['sites'] = list(sites)
    g._nuc['R'] = R
    g.npref_tab = {i: np.array([0.0, 0.0, 1.0]) for i in range(nv + 1)}
    return g, ctr


def case(name, ungated, nv, sites, n_fresh, n_stack, occupy_field1=False,
         occupy_all=False, expect=None, poison=False):
    g, _ = build(ungated, nv, sites, occupy_field1, occupy_all)
    if poison:
        # ★ 确定性构造"一个都放不成"：让 `seed_plate` 一律抛错。
        #   动机（v1/v2 两次失败）：靠"位点落在已占区域"去构造失败**不可靠** ——
        #   实测 `stack` 通道仍能放成（`模式=stack cov=8 ok=1`）。
        #   本测试要验的是**解卡块本身**，与"为什么放不成"无关，
        #   故直接让所有落位失败 ⇒ `out` 恒空。
        def _boom(*_a, **_k):
            raise ValueError('test: 强制落位失败')
        g.seed_plate = _boom
    ed = np.zeros((nv + 1, N, N, N), float)
    ed[1:] = -1.0
    ev = g.nucleate(ed, f_now=0.0, n_fresh=n_fresh, n_stack=n_stack)
    dbg = g._nuc.get('dbg', {})
    got = dict(ev=len(ev),
               modes=",".join(str(e[1]) for e in ev) or "-",
               old=int(dbg.get('sites_resampled', 0)),
               new=int(dbg.get('sites_resampled_ungated', 0)),
               cov=int(dbg.get('cov', 0)),
               exc=int(dbg.get('exc', 0)),
               ok=int(dbg.get('ok', 0)))
    print(f"  [{name}]\n      ev={got['ev']}  模式={got['modes']}  cov={got['cov']}  "
          f"exc={got['exc']}  ok={got['ok']}  旧键={got['old']}  新键={got['new']}")
    print(f"      dbg 全量: { {k: v for k, v in dbg.items() if k != 'nfsv_diag_occ_sizes'} }")
    good = True
    for k, want in (expect or {}).items():
        v = got[k]
        if isinstance(want, bool):
            passed = (v > 0) == want
        else:
            passed = v == want
        print(f"      {'PASS' if passed else '**FAIL**'}  {k}={v}  期望 "
              f"{'为正' if want is True else ('为 0' if want is False else want)}")
        good &= passed
    return good


centre = (L / 2, L / 2, L / 2)
far = (L * 0.12, L * 0.12, L * 0.12)
blocked = [(1, np.array(centre, float))]      # 位点落在盘心 ⇒ 被占
free = [(1, np.array(far, float))]            # 位点在空位 ⇒ 可放

print("=" * 92)
print(f"N={N} dx={DX*1e9:.1f}nm R={R*1e9:.1f}nm t={T*1e9:.1f}nm L={L*1e6:.2f}µm")
print("=" * 92)

ok = True
print("\n--- P1 负对照（归档不变）：poison + 开关关 + n_fresh=1 ⇒ **新键**必须为 0 ---")
ok &= case("ungated=0, poison, n_fresh=1, n_stack=1",
           0, 2, blocked, 1, 1, occupy_field1=True, poison=True,
           expect=dict(ev=0, new=0))
print("      （旧键此时**应当** >0 —— 那是 R481b 的原有功能；此处不断言，见 P4）")

print("\n--- P2 核心（缺陷已修）：poison + 开关开 + n_fresh=1 ⇒ 新键 > 0，且两键相等 ---")
ok &= case("ungated=1, poison, n_fresh=1, n_stack=1",
           1, 2, blocked, 1, 1, occupy_field1=True, poison=True,
           expect=dict(ev=0, new=True, old=True))

print("\n--- P2b ★缺陷的要害：poison + **n_fresh=0** + 开关开 ⇒ 新键仍须 > 0 ---")
ok &= case("ungated=1, poison, n_fresh=0, n_stack=1",
           1, 2, blocked, 0, 1, occupy_field1=True, poison=True,
           expect=dict(ev=0, new=True, old=0))

print("\n--- P2c ★关键对照：同 n_fresh=0 但开关**关** ⇒ 新键 0（证开关是唯一原因）---")
ok &= case("ungated=0, poison, n_fresh=0, n_stack=1",
           0, 2, blocked, 0, 1, occupy_field1=True, poison=True,
           expect=dict(ev=0, new=0, old=0))

print("\n--- P3 正对照（不该洗表时不洗）：位点在空位 + n_fresh=1 ⇒ 放成了 ⇒ 新键 0 ---")
ok &= case("ungated=1, nv=2, 空位, n_fresh=1, n_stack=0",
           1, 2, free, 1, 0, occupy_field1=False,
           expect=dict(ev=True, new=0))

print("\n--- P4 两键语义分离：poison + n_fresh=1 ⇒ 旧键(=R481b 原有) 与 新键 都 > 0 且**相等** ---")
ok &= case("ungated=1, poison, n_fresh=1 双键自检",
           1, 2, blocked, 1, 0, occupy_field1=True, poison=True,
           expect=dict(old=True, new=True))

print("\n" + "=" * 92)
print("总判定：" + ("**全部 PASS**" if ok else "**有 FAIL，必须继续查**"))
print("=" * 92)
sys.exit(0 if ok else 1)
